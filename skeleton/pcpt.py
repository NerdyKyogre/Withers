'''
Withers Bot Site Head - PCPriceTracker
Handles PCPriceTracker build list links
'''
import discord
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium_stealth import stealth
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import datetime

#from seleniumwire import webdriver as wirewd - DEBUG ONLY - requires selenium-wire AND blinker==1.7.0 

import skeleton.soul as soul

class Msg(soul.BuildListMsg):

    def __init__(self, msg, msgText, sender):
        super().__init__(msg, msgText, sender)
    
    async def findLinks(self, driver, text=None):
        '''
        Recursively finds all PCPT list links in the message and adds them to the list of links
        Inputs: 
            - text: the message or message segment to look for a link in - defaults to self.msgText
        Returns: N/A
        '''
        if text is None:
            text = self.msgText

        # find substring of list link if it exists
        try:
            start = text.index("pcpricetracker.in/b/s/")
        except Exception:
            return

        # figure out the actual url by looping over characters until we hit the right length
        # we do this instead of slicing so we can more easily detect invalid/cut off links
        link = "https://"
        for i in range(start, start + 58):
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
        self.siteSource = "PCPriceTracker"

    async def generateSoup(self, driver):
        '''
        Scrapes PCPriceTracker page with Selenium and feed the data table into BeautifulSoup for formatting and parsing.
        Sets self.soup to this object when complete
        Inputs:
            - driver: selenium webdriver object
        Returns: N/A
        '''
        # scrape url with selenium and feed to soup for html parsing
        driver.get(self.link)
        try:
            element = WebDriverWait(driver, timeout=15, poll_frequency=7).until(
                EC.presence_of_element_located((By.ID, "shared_build"))
            )
        except Exception as e:
            print(e)

        '''
        for request in driver.requests:
            print(request.url) # <--------------- Request url
            print(request.headers) # <----------- Request headers
            print(request.response.headers) # <-- Response headers
        '''

        self.soup = BeautifulSoup(driver.page_source,"html.parser")

    async def buildTable(self, sender, message):
        '''
        Parses data table from PCPP list link into a discord embed
        Inputs: 
            sender - author of calling message, type string
            message - calling discord message object
        Returns: response message, type discord embed object
        '''
        #wrap this logic in try-catch to make sure list is real
        try:
            #grab the parts list table
            table = self.soup.find('table', id="shared_build").find('tbody')
            parts = table.find_all('tr')
            totals = parts.pop()
        except Exception:
            return (await self.badListEmbed(sender))

        #structure output
        #initialize giant string of output
        componentList = ""
        #don't concatenate identical parts - this site only has the potential for a couple of duplicates anyway, and they have separate IDs
        #these variables are needed for handling lists over the ~3700 character limit
        tooLong = False
        overCount = 0
        #last row will always be totals

        for part in parts:
            #part type e.g. CPU, Memory, Storage, etc is the category lead
            partType = "**" + part.find("td", class_="category lead").get_text().strip() + "**"

            #grab part name and link
            partNameField = part.find("td", class_="selection").find("a")
            partName = partNameField.get_text().strip()
            partLink = ("https://pcpricetracker.in" + partNameField["href"].strip())

            #format it
            partName = ("[" + partName + "](" + partLink + ")")

            #grab part retailer
            partRetailer = part.find("td", class_="source").get_text().strip()
            partPrice = ("₹" + part.find("td", class_="price").find("a").get_text().strip())
            #format it
            partPrice = ("``" + partPrice + " @ " + partRetailer + "``")

            #check to make sure we're not over the character limit
            #do length check here
            #length 4000 leaves room for the total in the 4096 character limit - PCPT has minimal footer
            if (not tooLong) and (len(componentList) > 4000):
                tooLong = True
            #we continue to parse the list as normal regardless of its length so we can count the number of remaining parts
            if tooLong:
                overCount += 1
                continue

            #add the part to the string
            componentList = componentList + partType + " - " + partPrice + " - " + partName + "\n"
        
        #if we went over the character limit, explain ourselves
        if tooLong:
            componentList += ("\n*Sorry, this part list is too long. " + str(overCount) + " part(s) were not shown. Please click the button below to see the full list.*")

        #grab total
        total = ("₹" + totals.find("td", class_="price").get_text())

        # structure embed output
        #abusing header + giant string here because header has a longer character limit than field - this increases the length of the list we can display from 1024 to 4096 characters
        embed = discord.Embed(title=(self.siteSource + " :flag_in:\n" + self.link), description=("Sent by " + sender + "\n\n" + componentList), color=0x019119)
        try:
            embed.add_field(name="Total:", value=("``"+total+"``"), inline=False)
            embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
        #failover in the event of a footer of length >396 should be to skip rendering the footer and send the embed anyway
        except Exception:
            pass
        
        return(embed)
    
    async def badListEmbed(self, sender):
        '''
        Generates an error message to embed in the event of an invalid link
        Inputs:
            - sender: sender id, string
        Returns: discord embed object
        '''
        #set up embed
        embed = discord.Embed(title=("Couldn't read PCPriceTracker list\n" + self.link), description=("Sent by " + sender + "\n"), color=0xFF0000)
        embed.add_field(name="", value="I couldn't find a valid parts table in this list link. Please make sure you've copied the link correctly.\n\nIf you're certain the link is correct and this error persists, there may be a bug - check my About Me for support.")
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
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--window-size=1920x1032')
    options.add_argument('--no-sandbox')
    #not specifically going out of our way to tell the site we're a bot helps with rate limiting
    options.add_argument("--disable-blink-features=AutomationControlled")
    #options.add_experimental_option("excludeSwitches", ["enable-automation"])
    #options.add_experimental_option("useAutomationExtension", False)
    #the below three options improve performance
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-extensions')
    options.add_argument('--dns-prefetch-disable')
    #custom user agent prevents rate limiting by emulating a real desktop user
    options.add_argument("--user-agent=" + await soul.getStaticUserAgent())
    driver = uc.Chrome(options=options, version_main=134)
    #driver = wirewd.Chrome(options=options)
    #driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    stealth(driver,
        languages=["en-IN", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
        )
    
    #set up correct geolocation for pcpt - New Delhi
    params = {
        "latitude": 28.6139,
        "longitude": 77.2088,
        "accuracy": 100 
    }
    driver.execute_cdp_cmd("Page.setGeolocationOverride", params)

    return driver