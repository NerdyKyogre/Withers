'''
Withers Bot Site Head - Geizhals
Handles Geizhals/Skinflint/Cenowarka wish list links
'''
import discord
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium_stealth import stealth
#import undetected_chromedriver as uc
from random import choice
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import datetime
import re
import asyncio

import skeleton.soul as soul

class Msg(soul.BuildListMsg):

    def __init__(self, msg, msgText, sender):
        super().__init__(msg, msgText, sender)

    async def findLinks(self, driver, text=None):
        '''
        Recursively finds all Geizhals network list links in the message and adds them to the list of links
        Inputs: 
            - driver: Selenium webdriver object
            - text: the message or message segment to look for a link in - defaults to self.msgText
        Returns: N/A
        '''
        if text is None:
            text = self.msgText

        # find substring of list link if it exists, by sequentially searching backward through the message for each type
        linkBodies = ["geizhals.de/wishlists/", "geizhals.at/wishlists/", "geizhals.eu/wishlists/", "cenowarka.pl/wishlists/", "skinflint.co.uk/wishlists/"]
        linkStartIndex = 4001 #maximum length of discord message 
        bodyLength = -1
        #we need to find the links in order, so we check all types, see which one occurs first, and use that
        for linkBody in linkBodies:
            try:
                start = text.index(linkBody)
                if start < linkStartIndex:
                    linkStartIndex = start
                    bodyLength = len(linkBody)
            except Exception:
                continue
        #if we don't find anything, our index is out of bounds and we can break the recursion
        if linkStartIndex > 4000:
            return

        # figure out the actual url by looping over characters until we hit the right length
        # we do this instead of slicing so we can more easily detect invalid/cut off links
        link = "https://"
        #geizhals link suffixes are 7 digit numbers
        for i in range(linkStartIndex, (linkStartIndex + bodyLength + 7)):
            try:
                link += text[i] 
            except Exception:
                pass
        
        self.links.append(link)

        text = text.replace(link[8:], "")
        await self.findLinks(driver, text) #recurse on the remaining links in the message
        return
    
    async def generateLists(self):
        '''
        Loops over every link found in the message and creates a new list object for it, returning them all
        Inputs: N/A
        Returns: Array of BuildList objects
        '''
        lists = []
        for link in self.links:
            lists.append(List(link))
        return lists

class List(soul.BuildList):

    def __init__(self, link):
        super().__init__(link)
        self.siteSource = "Geizhals"
        if "cenowarka" in link:
            self.siteSource = "Cenowarka"
        elif "skinflint" in link:
            self.siteSource = "Skinflint"
        self.quantities = []
    
    async def generateSoup(self, driver):
        '''
        Scrapes Geizhals wishlist page with Selenium and feeds the data table into BeautifulSoup for formatting and parsing.
        Sets self.soup to this object when complete
        Inputs:
            - driver: selenium webdriver object
        Returns: N/A
        '''
        # scrape url with selenium and feed to soup for html parsing
        driver.get(self.link)
        #clear cookie consent if we get it - if not, ignore the exception
        try:
            rejectCookieButton = driver.find_element(By.ID, "onetrust-reject-all-handler")
            rejectCookieButton.click()
        except Exception:
            pass
        #wait for parts to populate
        try:
            WebDriverWait(driver, timeout=10, poll_frequency=1).until(
                EC.presence_of_element_located((By.CLASS_NAME, "card"))
            )
        except Exception as e:
            print("Couldn't load Geizhals Network wishlist link in time - no data after 10 seconds")
        if ("geizhals" in self.link) or ("cenowarka" in self.link):
            await asyncio.sleep(1)
        #get lazy loaded quantities early
        elements = driver.find_elements(By.CLASS_NAME, "quantity-input")
        for element in elements:
            try:
                driver.execute_script("arguments[0].scrollIntoView();", element)
                self.quantities.append(int(element.get_attribute('value')[0]))
            except Exception:
                pass
        self.soup = BeautifulSoup(driver.page_source,"html.parser")

    async def buildTable(self, sender, message):
        '''
        Parses data table from Geizhals network wishlist link into a discord embed
        Inputs: 
            sender - author of calling message, type string
            message - calling discord message object
        Returns: response message, type discord embed object
        '''
        #get country from link:
        country = ""
        if "geizhals" in self.link: #this can be de, at, or eu
            country = self.link[17:19]
        elif "skinflint" in self.link:
            country = "gb"
        elif "cenowarka" in self.link:
            country = "pl"

        #title and parts are onvly visible if list is valid and public
        try:
            #get list title
            title = self.soup.find("a", href=self.link).get_text()

            #grab list of all part cards
            partCards = self.soup.find_all("div", class_="card")
        except Exception:
            return (await self.badListEmbed(sender, message))

        #structure output
        #initialize giant string of output
        componentList = ""
        #these variables are needed for handling lists over the ~3700 character limit
        tooLong = False
        overCount = 0

        for i in range(len(partCards)):
            partCard = partCards[i]
            #every element in these tables is inside a div - get the only link element inside product name. its href is part link, and text is part name
            partNameField = partCard.find("div", class_="productname").find("a")
            partName = partNameField.get_text().strip() 
            partLink = partNameField["href"].strip()
            #format into hyperlink
            partName = ("[" + partName + "](" + partLink + ")")

            #find part category
            #category is 3 fields - we want the SECOND one specifically
            partCategory = partCard.find("ol", class_="category-breadcrumb").find_all("a")[1].get_text().strip()
            partCategory = ("**" + partCategory + "**")

            #wrap price check in try-catch; if the element doesn't exist (we're oos) it's N/A
            try:
                #get price per unit
                #price is the text of a link to the offerlist for the part
                partPrice = partCard.find("span", class_="bestprice").find("a").get_text().strip()
                partPrice = partPrice.replace(",",".")

                #get quantity from parallel array - we need to adjust total price if it's more than 1
                quantity = self.quantities[i]

                #if we have multiple, adjust part price in the same way as we did for pcpp
                if quantity > 1:
                    unitPrice = re.findall("\d+\.\d+", partPrice)
                    totalPrice = quantity * (float(unitPrice[0]))
                    partPrice = partPrice.replace(unitPrice[0], ("%.2f" % totalPrice))
                    partName = ("**("+ str(quantity) + "x)** " + partName)

                partPrice =  ("``" + partPrice + "``")

            except Exception:
                partPrice = "``N/A``"

            #check to make sure we're not over the character limit
            #do length check here
            #length 4000 leaves room for the total in the 4096 character limit - Geizhals has minimal footer
            if (not tooLong) and (len(componentList) > 4000):
                tooLong = True
            #we continue to parse the list as normal regardless of its length so we can count the number of remaining parts
            if tooLong:
                overCount += 1
                continue

            #add the part to the string
            componentList = componentList + partCategory + " - " + partPrice + " - " + partName + "\n"
        
        #if we went over the character limit, explain ourselves
        if tooLong:
            componentList += ("\n*Sorry, this part list is too long. " + str(overCount) + " part(s) were not shown. Please click the button below to see the full list.*")
        
        #grab total - it's the second of two fields
        total = self.soup.find_all("span", class_="wishlist-sum")[1].get_text().strip().replace(",",".") #tweak format for consistency

        # structure embed output
        #abusing header + giant string here because header has a longer character limit than field - this increases the length of the list we can display from 1024 to 4096 characters
        embed = discord.Embed(title=(self.siteSource + " :flag_" + country + ":\n" + self.link + "\n" + title + "\n"), description=("Sent by " + sender + "\n\n" + componentList), color=0x38aefc)
        try:
            embed.add_field(name="Total:", value=("``"+total+"``"), inline=False)
            embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
        #failover in the event of a footer of length >96 should be to skip rendering the footer and send the embed anyway
        except Exception:
            pass
        
        return(embed)
    
    async def badListEmbed(self, sender, message):
        '''
        Creates and sends an embedded message in the event that we detect a private or malformed link
        Inputs: 
            - sender: the sender id of the message
            - message: calling discord message object
        Returns: N/A
        '''
        #set up embed
        embed = discord.Embed(title="Private or invalid Geizhals wishlist\n" + self.link, description=("Sent by " + sender + "\n"), color=0xFF0000)
        embed.add_field(name="", value="I ran into some trouble opening a list you sent.\n\nPlease make sure all the Geizhals network wishlist links (geizhals, skinflint, cenowarka) in your message are valid and set to Public.")
        #upload the image
        file = discord.File("./assets/private_geizhals.png", filename="private_geizhals.png")
        embed.set_image(url="attachment://private_geizhals.png")
        #timestamp for better legibility
        embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
        await message.channel.send(file=file, embed=embed)
        raise ValueError("Bad or private Geizhals list detected")

            

async def startWebDriver():
    '''
    Initializes a Chrome Webdriver instance and returns it
    Inputs: N/A
    Returns: Selenium Webdriver object
    This function should be called once for every message we handle
    '''
    # initialize selenium chrome webdriver with necessary settings
    #custom user agent prevents rate limiting by emulating a real desktop user
    useragents = await soul.getUserAgents()
    options = await soul.setDefaultDriverOptions(webdriver.ChromeOptions())
    #pick a random user agent for each driver instance, helps to avoid rate limiting
    options.add_argument("--user-agent="+choice(useragents))
    #for geizhals, we need to enable automatic translation from either german or polish
    prefs = {
        "translate_whitelists": {"de":"en", "pl":"en"},
        "translate":{"enabled":"true"}
    }
    options.add_experimental_option("prefs", prefs)

    #driver = uc.Chrome(options=options, version_main=134)
    driver = webdriver.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    stealth(driver,
        languages=["en-UK", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
        )

    return driver