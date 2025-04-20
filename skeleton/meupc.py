'''
Withers Bot Site Head - Meupc
Handles meupc.net build list links
'''
import discord
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium_stealth import stealth
from random import choice
from selenium.webdriver.common.by import By
import datetime
import re
import asyncio

import skeleton.soul as soul

class Msg(soul.BuildListMsg):
    def __init__(self, msg, msgText, sender):
        super().__init__(msg, msgText, sender)

    async def findLinks(self, driver, text=None):
        '''
        Recursively finds all Meupc list links in the message and adds them to the list of links
        Inputs: 
            - driver: Selenium webdriver object
        Returns: N/A
        '''
        if text is None:
            text = self.msgText

        # find substring of list link if it exists
        try:
            start = text.index("meupc.net/build/")
        except Exception:
            return

        # figure out the actual url by looping over characters until we hit the right length
        # we do this instead of slicing so we can more easily detect invalid/cut off links
        link = "https://"
        for i in range(start, start + 22):
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
        self.siteSource = "Meupc"

    async def generateSoup(self, driver):
        '''
        Scrapes Meupc build list page with Selenium and feeds the data table into BeautifulSoup for formatting and parsing.
        Sets self.soup to this object when complete
        Inputs:
            - driver: selenium webdriver object
        Returns: N/A
        '''
        # scrape url with selenium and feed to soup for html parsing
        driver.get(self.link)
        #wait for translation - always from pt
        await asyncio.sleep(1)
        #invalid lists redirect to the empty list - since we're out of scope to error here, we simply leave self.soup empty and then catch an exception in the table parser
        if len(driver.current_url) < 30 :
            return
        #finally, feed the whole page into beautifulsoup
        self.soup = BeautifulSoup(driver.page_source,"html.parser")

    async def buildTable(self, sender, message):
        '''
        Parses data table from Geizhals network wishlist link into a discord embed
        Inputs: 
            sender - author of calling message, type string
            message - calling discord message object
        Returns: response message, type discord embed object
        '''
        #wrap this logic in try-catch to make sure list is real
        try:
            #grab the parts list table
            table = self.soup.find('table')
            rows = table.find_all('tbody')
            totals = []
            #regular rows have no class so this will keyerror when done
            try:
                while (str(rows[-1]['class']).find("total") >= 0):
                    totals.append(rows.pop())
            except KeyError:
                pass
        except Exception:
            return (await self.badListEmbed(sender, message))
        
        #structure output
        #initialize giant string of output
        componentList = ""
        #these variables are needed for handling lists over the ~3700 character limit
        tooLong = False
        overCount = 0

        for row in rows:
            partType = row.find("th", class_="table-responsive-title").find("a").get_text().strip()
            
            #parts of the same type are contained within the same tbody - we can compare the tr tags inside to concatenate parts
            parts = row.find_all("tr")

            i = 0
            while i < len(parts):
                #get info for this part
                partTitleTag = parts[i].find("td", class_="table-responsive-selection").find("a")
                partName = partTitleTag.get_text().strip()
                partLink = partTitleTag['href'].strip()
                #prices have two fields if discounted, 1 otherwise
                #the field will be entirely nonexistent if no price is avaialble
                try:
                    priceField = parts[i].find("td", class_="table-responsive-price")
                    try:
                        partPrice = priceField.find("b").get_text().strip().replace(",","")
                    except Exception:
                        partPrice = priceField.get_text().strip().replace(",","")
                except Exception:
                    partPrice = "N/A"

                if partPrice == "":
                    partPrice = "N/A"

                #check if part is purchased - retailer field only has text if purchased
                if len(parts[i].find("td", class_="table-responsive-loja").get_text().strip()) > 1:
                    purchased = True
                    partPrice = partPrice + " (Purchased)"
                else:
                    purchased = False
                
                #initialize quantity to the one known value
                partQuantity = 1
                
                #check next part for a match
                #if the parts have the same name and are both either purchased or not, move i past and don't make a new row
                #this accounts for both identical and mixed parts of the same type in the build
                while i < (len(parts) - 1):
                    nextName = parts[i + 1].find("td", class_="table-responsive-selection").find("a").get_text().strip()
                    if len(parts[i + 1].find("td", class_="table-responsive-loja").get_text().strip()) > 1:
                        nextPurchased = True
                    else:
                        nextPurchased = False

                    if (nextName == partName) and (nextPurchased == purchased):
                        partQuantity += 1
                        i += 1    
                    else:
                        break
                    
                
                try:
                    if partQuantity > 1:
                        unitPrice = re.findall("\d+\.\d+", partPrice)
                        totalPrice = partQuantity * (float(unitPrice[0]))
                        partPrice = partPrice.replace(unitPrice[0], ("%.2f" % totalPrice))
                
                    partPrice = ("``" + partPrice + "``")
                except Exception:
                    partPrice = "``N/A``"

                #format part name now that we no longer need it for comparison
                partName = "[" + partName + "](" + partLink + ")"
                partName = ("**("+ str(partQuantity) + "x)** " + partName)

                #check to make sure we're not over the character limit
                #length 3700 leaves room for the total and compat footer in the 4096 character limit
                if (not tooLong) and (len(componentList) > 3700):
                    tooLong = True
                #we continue to parse the list as normal regardless of its length so we can count the number of remaining parts
                if tooLong:
                    overCount += 1
                    continue

                #add the part to the string
                componentList = componentList + "**" + partType + "**" + " - " + partPrice + " - " + partName + "\n"
                #increment iterator
                i += 1
        
        #if we went over the character limit, explain ourselves
        if tooLong:
            componentList += ("\n*Sorry, this part list is too long. " + str(overCount) + " part(s) were not shown. Please click the button below to see the full list.*")

        #parse totals
        total = totals[0].find("b").get_text().strip().replace(",","")
        #if we have purchased parts, there will be 2 elements here
        
        if len(totals) > 1:
            notPurchased = totals[1].find("strong").get_text().strip().replace(",","")
            #easier to just calculate purchased
            purchased = "R$ %.2f" % (float(total[3:]) - float(notPurchased[3:]))
            total = (total + " (" + notPurchased + " Not Yet Purchased, " + purchased + " Purchased)")

        #get wattage
        wattage = self.soup.find("div", class_="consumption").find("strong").get_text().strip()

        #get compat info
        compatNotes = ""
        compatWarns = self.soup.find_all("article", class_="message")
        for block in compatWarns:
            for warning in block.find_all("li"):
                compatNotes += "- " + warning.get_text().strip() + "\n"

        # structure embed output
        #abusing header + giant string here because header has a longer character limit than field - this increases the length of the list we can display from 1024 to 4096 characters
        embed = discord.Embed(title=(self.siteSource+ " :flag_br:\n"+self.link), description=("Sent by " + sender + "\n\n" + componentList), color=0xFA8148)
        try:
            embed.add_field(name="Total:", value=("``"+total+"``"), inline=False)
            embed.add_field(name="Estimated Wattage", value=wattage, inline=False)
            #only bother displaying compatibility notes if something is detected
            if len(compatNotes) > 0:
                embed.add_field(name="Compatibility Notes/Warnings", value=compatNotes, inline=False)
            embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
        #failover in the event of a footer of length >396 should be to skip rendering the footer and send the embed anyway
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
        embed = discord.Embed(title="Invalid Meupc build list\n" + self.link, description=("Sent by " + sender + "\n"), color=0xFF0000)
        embed.add_field(name="", value="I ran into some trouble opening a list you sent.\n\nPlease make sure all the Meupc part list links in your message are valid.")
        #timestamp for better legibility
        embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
        await message.channel.send(embed=embed)
        raise ValueError("Bad Meupc list detected")

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
        "translate_whitelists": {"pt":"en"},
        "translate":{"enabled":"true"}
    }
    options.add_experimental_option("prefs", prefs)

    #driver = uc.Chrome(options=options, version_main=134)
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