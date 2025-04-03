'''
Withers Bot Site Head - Tweakers
Handles Tweakers.net wish list links
'''
import discord
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium_stealth import stealth
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

    async def findLinks(self, driver):
        '''
        Recursively finds all Geizhals network list links in the message and adds them to the list of links
        Inputs: 
            - driver: Selenium webdriver object
        Returns: N/A
        '''

        #convert all tweakers.nl links to tweakers.net
        self.msgText = self.msgText.replace(".nl", ".net")

        #grab all price breakdown links and convert them to regular lists
        await self.breakdownToLinks(driver)

        #then, grab all the regular links and save them
        await self.linksToLists(self.msgText)
        
        return

    async def breakdownToLinks(self, driver):
        '''
        Recursively converts tweakers.nl parts breakdown links in msgText into their regular list links
        Inputs:
            - driver: selenium webdriver object
        Returns: N/A
        '''
        # find substring of list link if it exists
        try:
            start = text.index("tweakers.net/pricewatch/bestelkosten/")
        except Exception:
            return

        # figure out the actual url by looping over characters until we hit the right length
        # we do this instead of slicing so we can more easily detect invalid/cut off links
        link = ""
        for i in range(start, start + 44):
            try:
                link += text[i] 
            except Exception:
                pass

        #load the page into webdriver - we need to navigate to the edit part list button
        driver.get("https://" + link)
        #skip cookie check
        try:
            cookieButton = driver.find_element(By.ID, "pg-accept-btn")
            cookieButton.click()
        except Exception:
            pass
        
        #wait for page to load, then find the button to view the list and get its href
        driver.implicitly_wait(5)
        editButton = driver.find_element(By.CLASS_NAME, "ctaButton")
        listLink = editButton.get_attribute("href")
            
        #replace the link in MsgText
        self.msgText = self.msgText.replace(link, listLink)
        #recurse
        await self.breakdownToLinks(driver)
        return

    async def linksToLists(self, text):
        '''
        Recursively finds tweakers.nl wish list links in message text and adds them to the list of links
        Inputs:
            - text: String of text to search through
        Returns: N/A
        '''
        # find substring of list link if it exists
        try:
            start = self.msgText.index("tweakers.net/gallery")
            #make sure we go to a saved link and NOT a blank gallery page - assigning this will throw an exception if it fails
            finish = (self.msgText.index("/wenslijst/?wish_id=") + 27)
        except Exception:
            return

        #add it to the list
        link = ("https://" + self.msgText[start:finish])
        self.links.append(link)

        text = text.replace(link[8:], "")
        await self.linksToLists(text) #recurse on the remaining links in the message
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
        self.siteSource = "Tweakers"

    async def generateSoup(self, driver):
        '''
        Scrapes Tweakers wishlist page with Selenium and feeds the data table into BeautifulSoup for formatting and parsing.
        Sets self.soup to this object when complete
        Inputs:
            - driver: selenium webdriver object
        Returns: N/A
        '''
        # scrape url with selenium and feed to soup for html parsing
        driver.get(self.link)

        #skip cookie check
        try:
            cookieButton = driver.find_element(By.ID, "pg-accept-btn")
            cookieButton.click()
        except Exception:
            pass
        
        #wait for parts to populate
        try:
            WebDriverWait(driver, timeout=10, poll_frequency=1).until(
                EC.presence_of_element_located((By.CLASS_NAME, "galleryInnerTable"))
            )
        except Exception as e:
            print("Couldn't load Tweakers wishlist link in time - no data after 10 seconds")
        #need to wait to translate list for categories
        await asyncio.sleep(1)

        #finally, feed the whole page into beautifulsoup
        self.soup = BeautifulSoup(driver.page_source,"html.parser")
    
    async def buildTable(self, sender):
        '''
        Parses data table from Geizhals network wishlist link into a discord embed
        Inputs: 
            sender - author of calling message, type string
        Returns: response message, type discord embed object
        '''
        #title and parts are onvly visible if list is valid and public
        try:
            #get list title
            title = self.soup.find("span", class_="linkHover").get_text()

            #get table, ignoring category headers
            table = self.soup.find("table", class_="galleryInnerTable").find("tbody")
        except Exception:
            return (await self.badListEmbed(sender))

        #break table down into rows
        rows = table.find_all("tr")
        #the last row always just contains the total price
        totalRow = rows.pop()
        #get total cost early, and format accordingly
        total = totalRow.find("td", class_="price").get_text().strip().replace(",", ".")

        #structure output
        #initialize giant string of output
        componentList = ""
        #these variables are needed for handling lists over the ~3700 character limit
        tooLong = False
        overCount = 0

        for row in rows:
            #get part name first
            #this gives us a list of two links - the first one has the name of the part as its text, and the second has the category
            partHeaders = row.find("td", class_="title").find_all("a")
            partName = partHeaders[0].get_text().strip()
            partLink = partHeaders[0]["href"].strip()
            partType = partHeaders[1].get_text().strip()
            #format this info into hyperlink
            partName = ("[" + partName + "](" + partLink + ")")
            partType = "**" + partType + "**"
        
            #part quantity is blank if we have one, and filled if we have multiple
            quantity = int(row.find("td", class_="amount").find("p").get_text().strip().replace("x", ""))

            try: #get part unit price
                #there are two of these TDs, both containing the value - to save a list index, we just go with the first
                partPrice = row.find("td", class_="price").find("a").get_text().strip().replace(",", ".")

                #if we have multiple of the part, adjust part price in the same way as we did for pcpp
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
            #length 4000 leaves room for the total in the 4096 character limit - Tweakers has minimal footer
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
        
        # structure embed output
        #abusing header + giant string here because header has a longer character limit than field - this increases the length of the list we can display from 1024 to 4096 characters
        embed = discord.Embed(title=(self.siteSource + " :flag_nl:\n" + self.link + "\n" + title + "\n"), description=("Sent by " + sender + "\n\n" + componentList), color=0xe836eb)
        try:
            embed.add_field(name="Total:", value=("``"+total+"``"), inline=False)
            embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
        #failover in the event of a footer of length >96 should be to skip rendering the footer and send the embed anyway
        except Exception:
            pass
        
        return(embed)
        
    async def badListEmbed(self, sender):
        '''
        Creates and sends an embedded message in the event that we detect a private or malformed link
        Inputs: 
            - sender: the sender id of the message
        Returns: N/A
        '''
        #set up embed
        embed = discord.Embed(title="Private or invalid Tweakers wishlist detected", description=("Sent by " + sender + "\n"), color=0xFF0000)
        embed.add_field(name="", value="I ran into some trouble opening a list you sent.\n\nPlease make sure all the Tweakers wishlist links in your message are valid and set to Public.")
        '''
        #upload the image
        file = discord.File("./assets/private_tweakers.png", filename="private_tweakers.png")
        embed.set_image(url="attachment://private_tweakers.png")
        '''
        #timestamp for better legibility
        embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
        return embed

async def startWebDriver():
    '''
    Initializes a Chrome Webdriver instance and returns it
    Inputs: N/A
    Returns: Selenium Webdriver object
    This function should be called once for every message we handle
    '''
    # initialize selenium chrome webdriver with necessary settings
    #custom user agent prevents rate limiting by emulating a real desktop user
    useragents = ["Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36", "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:136.0) Gecko/20100101 Firefox/136.0", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.3124.95"]
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--window-size=1920x1032')
    options.add_argument('--no-sandbox')
    #not specifically going out of our way to tell the site we're a bot helps with rate limiting
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    #the below three options improve performance
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-extensions')
    options.add_argument('--dns-prefetch-disable')
    #pick a random user agent for each driver instance, helps to avoid rate limiting
    options.add_argument("--user-agent="+choice(useragents))
    #for tweakers, we need to enable automatic translation from dutch
    prefs = {
        "translate_whitelists": {"nl":"en"},
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