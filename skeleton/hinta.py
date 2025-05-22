'''
Withers Bot Site Head - Hinta.fi
Handles Hinta.fi shopping list links
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


    async def findLinks(self, driver, text=None):
        '''
        Recursively finds all Hinta.fi list links in the message and adds them to the list of links
        Inputs: 
            - driver: Selenium webdriver object
            - text: the message or message segment to look for a link in - defaults to self.msgText
        Returns: N/A
        '''
        if text is None:
            #replace swedish links here for easier parsing - we'll set them back when we add
            text = self.msgText

        # find substring of list link if it exists
        try:
            start = text.index("hinta.fi/ostoskori/")
        except Exception:
            return
        
        # figure out the actual url by looping over characters until we hit the right length
        # we do this instead of slicing so we can more easily detect invalid/cut off links
        link = "https://"
        for i in range(start, start + 28):
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
        self.siteSource = "Hinta.fi"

    async def generateSoup(self, driver):
        '''
        Scrapes Hinta.fi shopping list page with Selenium and feeds the data table into BeautifulSoup for formatting and parsing.
        Sets self.soup to this object when complete
        Inputs:
            - driver: selenium webdriver object
        Returns: N/A
        '''
        # scrape url with selenium and feed to soup for html parsing
        driver.get(self.link)
        #wait for translation - always from fi
        await asyncio.sleep(1)
        #finally, feed the whole page into beautifulsoup
        self.soup = BeautifulSoup(driver.page_source,"html.parser")

    async def buildTable(self, sender, message):
        '''
        Parses data table from Hinta.fi wish list link into a discord embed
        Inputs: 
            sender - author of calling message, type string
            message - calling discord message object
        Returns: response message, type discord embed object
        '''
        #make sure list is real
        try:
            #grab the parts list table
            table = self.soup.find('ol', class_="hv-cprl")
            rows = table.find_all('li', class_="hv-cprli")
        except Exception:
            return (await self.badListEmbed(sender, message))
        
        #structure output
        #initialize giant string of output
        componentList = ""
        #these variables are needed for handling lists over the ~3700 character limit
        tooLong = False
        overCount = 0
        #hinta doesn't count a total so we have to do it ourselves
        total = 0.00

        for row in rows:
            #grab part info
            partType = "**" + row.find("div", class_="hv-prl_group").get_text().strip() + "**"
            partName = row.find("h3", class_="hv-prl_name").get_text().strip()
            #only some parts have extra relevant details, like capacity or form factor
            try:
                partName = partName + " " + row.find("div", class_="hv-prl_features").get_text().strip()
            except Exception:
                pass
            partLink = "https://hinta.fi/" + row.find("a", class_="hv-prli-c1")['href']
            #format it
            partName = ("[" + partName + "](" + partLink + ")")

            #grab quantity and handle
            quantity = int(row.find("input", class_="hv-cart-quantity-in")["value"])
            partPrice = row.find("a", class_="hv-prli-c3-price").get_text().strip().replace(",", "")
            unitPrice = re.findall("\d+\.\d+", partPrice)
            totalPrice = quantity * (float(unitPrice[0]))
            total += totalPrice

            if quantity > 1:
                partName = ("**("+ str(quantity) + "x)** " + partName)
                partPrice = partPrice.replace(unitPrice[0], ("%.2f" % totalPrice))
            partPrice = "``" + partPrice + "``"

            #check to make sure we're not over the character limit
            #do length check here
            #length 4000 leaves room for the total in the 4096 character limit - Hinta has minimal footer
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

         # structure embed output
        #abusing header + giant string here because header has a longer character limit than field - this increases the length of the list we can display from 1024 to 4096 characters
        embed = discord.Embed(title=(self.siteSource + " :flag_fi" + ":\n" + self.link + "\n"), description=("Sent by " + sender + "\n\n" + componentList), color=0x4fff98)
        try:
            embed.add_field(name="Total:", value=("``€%.2f``" % total), inline=False)
            embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
        #failover in the event of a footer of length >96 should be to skip rendering the footer and send the embed anyway
        except Exception as e:
            print(e)
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
        embed = discord.Embed(title="Private or invalid Hinta.fi shopping list\n" + self.link, description=("Sent by " + sender + "\n"), color=0xFF0000)
        embed.add_field(name="", value="I ran into some trouble opening a list you sent.\n\nPlease make sure all the Hinta.fi shopping list links in your message are valid.")
        #timestamp for better legibility
        embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
        await message.channel.send(embed=embed)
        raise ValueError("Bad or private Hinta.fi list detected")

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
        "translate_whitelists": {"fi":"en"},
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