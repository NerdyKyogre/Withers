'''
Withers Bot Site Head - buildapc.gg
Handles buildapc.gg build list links
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
        Recursively finds all BAPCGG build links in the message and adds them to the list of links
        Inputs: 
            - driver: Selenium webdriver object
            - text: the message or message segment to look for a link in - defaults to self.msgText
        Returns: N/A
        '''
        if text is None:
            #replace swedish links here for easier parsing - we'll set them back when we add
            text = self.msgText.replace("komponentkoll.se/", "buildapc.gg/se/").replace("/bygg/", "/build/")

        # find substring of list link if it exists
        try:
            start = text.index("buildapc.gg/")
        except Exception:
            return
        
        # figure out the actual url by looping over characters until we hit the right length
        # we do this instead of slicing so we can more easily detect invalid/cut off links
        link = "https://"
        for i in range(start, start + 26):
            try:
                link += text[i] 
            except Exception:
                pass

        if (" " not in link) and ("/build/" in link): #check for this as this site name is prone to being mentioned outside of a link
            self.links.append(link.replace("buildapc.gg/se/", "komponentkoll.se/").replace("buildapc.gg/build/", "buildapc.gg/us/build/"))

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
        if "komponentkoll.se" in link:
            self.siteSource = "KomponentKoll"
        else:
            self.siteSource = "buildapc.gg"
    
    async def generateSoup(self, driver):
        '''
        Scrapes BAPCGG build page with Selenium and feeds the data table into BeautifulSoup for formatting and parsing.
        Sets self.soup to this object when complete
        Inputs:
            - driver: selenium webdriver object
        Returns: N/A
        '''
        # scrape url with selenium and feed to soup for html parsing
        driver.get(self.link)
        #wait a second for translation if needed
        #only us and uk lists will default to english
        if ("us" not in self.link) and ("uk" not in self.link):
            await asyncio.sleep(1)
        
        #open all parts to make product pages visible
        #elements = driver.find_elements(By.CLASS_NAME, 'summary')
        elements = driver.find_elements(By.TAG_NAME, 'picture')
        for element in elements:
            try:
                driver.execute_script("arguments[0].scrollIntoView();", element)
                element.click()
                await asyncio.sleep(0.25)
            except Exception:
                pass
        await asyncio.sleep(2) #need to wait for the link load function to complete, otherwise we feed "Loading..." into soup


        self.soup = BeautifulSoup(driver.page_source,"html.parser")

    async def buildTable(self, sender, message):
        '''
        Parses data table from BAPCGG build list into a discord embed
        Inputs: 
            sender - author of calling message, type string
            message - calling discord message object
        Returns: response message, type discord embed object
        '''
        #get title and country first
        #title only exists in a valid list
        try:
            title = self.soup.find("div", class_="title-wrap").find("h1").get_text().strip()
        except Exception:
            return await self.badListEmbed(sender, message)
        
        country = self.link[20:22]
        if country == "uk":
            country = "gb"
        #swedish links follow a different format
        if "komponentkoll.se/" in self.link:
            country = "se"

        #get all part rows
        partRows = self.soup.find_all("div", class_="product-summary")

        #structure output
        #initialize giant string of output
        componentList = ""
        #these variables are needed for handling lists over the ~3700 character limit
        tooLong = False
        overCount = 0

        for partRow in partRows:
            #get basic info about part
            partInfo = partRow.find("div", class_="info")
            partName = partInfo.find("h4").get_text().strip()
            #remove quantity in advance
            if partName[-2] == 'x':
                #we need to copy this string using an empty join because otherwise we slice by reference and soup wigs out for unknown reasons
                partName = ''.join(partName[:-2])
            partType = partInfo.find("h5").get_text().strip()

            rowLinks = partRow.find_all("a")
            partLink = ""
            for linkTag in rowLinks:
                if "produkt" in linkTag['href']:
                    #country is annoyingly included in the link href
                    if "komponentkoll.se" not in self.link:
                        partLink = self.link[:(self.link.find("/build/")) - 3] + linkTag['href']
                    else:
                        partLink = self.link[:(self.link.find("/build/"))] + linkTag['href']
            if len(partLink) > 1:
                partName = "[" + partName + "](" + partLink + ")"

            partCount = 1
            try:
                partCount = int(partRow.find("span", class_="count").get_text().replace("x", "").replace("\u200b","").strip())
                if partCount > 1:
                    partName = ("**("+ str(partCount) + "x)** " + partName)
            except Exception:
                pass

            try:
                partPrice = partRow.find("div", class_="price").get_text().strip()

                #translating from swedish screws up formatting - undo what it does
                partPrice = partPrice.replace("SEK", "kr").replace(",","")

                #move kr to front and set up float so we can do regex
                if "kr" in partPrice:
                    partPrice = ("kr " + partPrice.replace(" ", "").replace("kr", ".00"))

                if partCount > 1:
                    unitPrice = re.findall("\d+\.\d+", partPrice)
                    totalPrice = partCount * (float(unitPrice[0]))
                    partPrice = partPrice.replace(unitPrice[0], ("%.2f" % totalPrice))
                
                partPrice = ("``" + partPrice + "``")
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
            componentList = componentList + "**" + partType + "**" + " - " + partPrice + " - " + partName + "\n"

        #if we went over the character limit, explain ourselves
        if tooLong:
            componentList += ("\n*Sorry, this part list is too long. " + str(overCount) + " part(s) were not shown. Please click the button below to see the full list.*")

        #get total - there's no guaranteed position for this so we have to loop through
        totals = self.soup.find_all("div", class_="total")
        total = "N/A"
        for row in totals:
            try:
                total = row.find("span", class_="price").get_text().strip()
            except Exception:
                pass

        #format it to match other prices
        total = total.replace("SEK", "kr").replace(",","")
        if "kr" in total:
            total = total.replace(" ", "").replace("kr", ".00")
            total = "kr " + total
            
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
        embed = discord.Embed(title="Private or invalid buildapc.gg build list\n" + self.link, description=("Sent by " + sender + "\n"), color=0xFF0000)
        embed.add_field(name="", value="I ran into some trouble opening a list you sent.\n\nPlease make sure all the buildapc.gg part list links in your message are valid.")
        #timestamp for better legibility
        embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
        await message.channel.send(embed=embed)
        raise ValueError("Bad or private Buildapc.gg list detected")
            


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
    #for BAPCGG, we need to enable automatic translation from either swedish, danish or norwegian
    #for some reason, translating this site breaks formatting horribly when we're faced with parts of quantity > 1 -- needs further investigation
    
    prefs = {
        "translate_whitelists": {"da":"en", "sv":"en", "no":"en"},
        "translate":{"enabled":"true"}
    }
    options.add_experimental_option("prefs", prefs)
    
    driver = webdriver.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    stealth(driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
        )

    return driver