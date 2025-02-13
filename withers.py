'''
 Withers -- Discord bot to parse PC build lists
 
 Copyright (C) 2024, 2025 NerdyKyogre
 Copyright (C) 2024, 2025 spiritfader

 This program is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program.  If not, see <https://www.gnu.org/licenses/>.
'''

import discord
INTENTS = discord.Intents.default()
INTENTS.message_content = True
import os
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
import datetime
import asyncio
import re


class MyView(discord.ui.View):
    def __init__(self, soup, link, buttons):
        '''
        Instantiates a custom view below the embed with the necessary URL button(s) for list actions
        inputs:
        - Soup - beautifulsoup output from the list link
        - link - list url as string
        - buttons - tuple containing button functions in order edit, save
        '''
        super(MyView, self).__init__()
        self.link = link
        self.soup = soup
        self.buttons = buttons

        #style override appears to be non-functional if we use a url
        openButton = discord.ui.Button(label='Open List', style=discord.ButtonStyle.url, url=self.link)
        self.add_item(openButton)

        #These two buttons will most likely never be implemented, but their template remains for the brave, prophesied pull-request-writer who one day will unearth them and restore them to their deserved glory.
        #the idea is to execute jquery upon getRequest to call the function in the edit and save buttons, then pass the result forward to the user's browser. 
        '''
        editButton = discord.ui.Button(label='Edit List', style=discord.ButtonStyle.url, url=self.link)#self.buttons[0])
        self.add_item(editButton)
        
        saveButton = discord.ui.Button(label='Save List', style=discord.ButtonStyle.url, url=self.link)#self.buttons[1])
        self.add_item(saveButton)
        '''
    
def runBot():
    '''
    Initializes the bot and checks for new messages in all connected channels.
    Inputs: N/A
    Returns: N/A
    '''
    # get discord token from .env file for security purposes
    load_dotenv()
    TOKEN = os.getenv("DISCORD_TOKEN")
    #initialize a new client instance with the necessary intents - we need the import message content intent for parsing
    client = discord.Client(intents=INTENTS)
    
    # print to console when we are live, then begin processing messages
    @client.event
    async def on_ready():
        print({client.user}, 'is live')
 
    @client.event
    async def on_message(message):
        #ignore messages we send
        if message.author == client.user:
            return
        # look for relevant part list link in message contents, then process it
        if "pcpartpicker.com/list/" in message.content:
            await processMessage(message, message.content, str(message.author.mention))
        else: 
            return
    client.run(TOKEN)

'''
NOTE:
All functions called by RunBot(), i.e. everything below this point MUST be async.
This is because discord's gateway depends on receiving heartbeat packets at regular intervals, which blocking functions prevent while they are running.
Having all functions async prevents gateway warnings and makes the bot more resilient to rate limiting/disconnection under heavy load.
'''

async def getPcppLink(msg):
    '''
    Finds PCPartPicker link within the contents of a message
    Inputs:
        - msg: message content, type string
    Returns full link as a string.
    '''
    # find substring of list link if it exists
    try:
        start = msg.index("pcpartpicker.com/list/")
    except Exception:
        return None
    
    # check for regional PCPP URLs, which are 31 characters long after https:// to USA's 28
    # regional url prefixes have a . before pcpartpicker, whereas the base american one has a /. we use this to differentiate them
    if msg[start - 1] == ".":
        start -= 3
        length = 31
    else: 
        length = 28

    # figure out the actual url by looping over characters until we hit the right length
    # we do this instead of slicing so we can more easily detect invalid/cut off links
    link = "https://"
    for i in range(start, start + length):
        try:
            link += msg[i] 
        except Exception:
            #return("Invalid PCPP link.", "")
            raise SyntaxError("Invalid PCPP Link")
    
    return link

async def pcppSoup(link):
    '''
    Multi-purpose function to scrape the PCPartPicker page with Selenium and feed the data table into BeautifulSoup for formatting and parsing.
    Inputs:
        - link: Part list link, type string
    Returns: tuple (soup, (button1, button2)) where:
        - soup is a BeautifulSoup object containing the table contents
        - button1 and button2 are clickable element objects that we can interface with using webdriver
    Note that button1 and button2 are not currently implemented and are None at this time.
    '''

    # initialize selenium chrome webdriver with necessary settings
    #custom user agent prevents rate limiting by emulating a real desktop user
    useragent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36"
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--window-size=1920x1080')
    options.add_argument('--no-sandbox')
    #the below three options improve performance
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-extensions')
    options.add_argument('--dns-prefetch-disable')
    options.add_argument("--user-agent="+useragent)
    driver = webdriver.Chrome(options=options)
    
    # scrape url with selenium and feed to soup for html parsing
    driver.get(link)

    #this loop looks for clickable custom part links, scrolls to the correct location, and clicks to open them.
    #we need to do this because PCPP does not load custom URLs until the button is clicked to view them.
    elements = driver.find_elements(By.XPATH, '//a[contains(@href,"#view_custom_part")]')
    for element in elements:
        try:
            driver.execute_script("arguments[0].scrollIntoView();", element)
            element.click()
        #custom parts without custom URLs are not clickable - this is expected behaviour
        except Exception:
            pass
    await asyncio.sleep(0.3) #need to wait for the link load function to complete, otherwise we feed "Loading..." into soup
    
    soup = BeautifulSoup(driver.page_source,"html.parser")

    #legacy button functions
    #editClick = driver.find_element(By.CLASS_NAME, "actionBox__options--edit")
    #saveClick = driver.find_element(By.CLASS_NAME, "actionBox__options--save")
    editClick, saveClick = (None, None)

    return (soup, (editClick, saveClick))

def tableHandler(sender, soup, link):
    '''
    Parses data table from PCPP list link into a discord embed
    Inputs: 
        sender - author of calling message, type string
        soup - BeautifulSoup object output from scraper
        link - part list link, type string
    Returns: response message, type discord embed object
    '''
    
    #site source is temporarily hard coded until we add support for other part comparison systems
    #in the future we will have separate link and soup functions for each site, and separate tablehandlers for sites that produce sufficiently different output.
    #at that point this will probably become a parameter
    siteSource="PCPartPicker"

    # define the information table to pull based on its class
    table = soup.find('table', class_='xs-col-12')
    
    # scrape and format existing build wattage estimate
    buildWattage = (' '.join(soup.find('div', class_='partlist__keyMetric',).text.split()))
    wattageSplit = buildWattage.find(":") + 2 
    buildWattage = buildWattage[wattageSplit:]
    
    # scrape and format compatibility notes
    compatHeader = soup.find('div', class_='subTitle__header').find('h2').text
    compatNotes = ""
    compatTags = soup.find_all('p', {'class':['note__text note__text--info','note__text note__text--warning', 'note__text note__text--problem']})
    #Every list that has at least one non-custom internal part contains the same compatibility warning about some measurements not being checked, which we ignore because it's meaningless.
    try:
        compatTags.pop()
    except Exception: #a list composed entirely of custom parts or peripherals won't have this warning
        compatHeader = "No issues or incompatibilities detected."
        compatNotes = ""
    #now format each compatibility note into a list
    for note in compatTags:
        note = str(note)
        if ("currently not supported" in note):
            continue
        note = note[note.find("</span>") + 8:-4]
        compatNotes += ("- " + note + "\n") 
    
    # scrape and format part list table body
    rows = [] #parts
    shortRows = [] #non-part rows - we're mainly interested in total price
    #each part is a tr tag, and each information piece in it is a td tag
    for row in table.find_all('tr')[1:]:  
        cells = []
        for td in row.find_all('td'):
            cells.append(td.text.strip())
            #grab link if row is of the appropriate type, and add to info for the part
            tdClass = td.get("class")
            if tdClass is not None and "td__name" in tdClass:
                #this type will always contain at least one a tag
                for a in td.find_all('a'):
                    url = str(a)
                    url = url[(url.find("href") + 6):]
                    url = url[:url.find("\">")]
                    #first, get link the regular way for non-custom parts
                    #note that auto-added amazon parts also work this way
                    if (url.find("view_custom_part") < 0):
                        cells.append("https://pcpartpicker.com" + url)
                        #we append True to the next field in any successful link so we can easily check if the field has a link when getting it later
                        cells.append(True)
                    #for custom parts, the url ends up on its own line at the end of the name field, and may or may not exist
                    else:
                        customPartLink = cells[3]
                        #find the last newline in the name, then slice and use the remainder
                        while "\n" in customPartLink:
                            customPartLink = customPartLink[customPartLink.find("\n") + 1:]
                        if len(customPartLink) <= 0:
                            pass
                        #make sure the link is valid, otherwise discord markdown will fail to recognize it
                        if "https://" not in customPartLink: 
                            continue
                        cells.append(customPartLink)
                        cells.append(True)
        #we want parts (long rows) and info (short rows) sorted into their respective arrays
        if len(cells) > 3:    
            rows.append(cells)
        else:
            shortRows.append(cells)

    # structure part list output
    #initialize giant string of output
    componentList = ""
    #initialize part dictionary - used for concatenating identical parts
    #keys are formatted as (type, name, unit price), value is count (int)
    partList = {}

    #these variables are needed for handling lists over the ~3700 character limit
    listLength = 0
    tooLong = False
    overCount = 0

    #add a new entry to componentList for each part in the long rows
    for row in rows:
        #part type e.g. CPU, Memory, Storage, etc is the first field, so we can simply tack it on and bold it
        partType = "**" + row[0] + "**"

        #next, find the name of the part, and include its hyperlink which we'll format into the name
        #excessive zero width spaces do nothing but inflate character count, remove them
        partName = row[3].replace("\u200b", "").strip()
        #Some part names begin with a leading newline, remove it
        index = partName.find("\n")
        if index >= 0:
            partName = partName[0:(index + 1)].strip()
        #this is where we check if we found a link earlier and set up the hyperlink
        if row[5] == True:
            partName = ("[" + partName + "](" + row[4].strip() + ")")

        #part price will show up in different places depending on the presence of links, parametrics, etc, so we have to search for it
        partPrice = ""
        for field in row:
            try:
                if "Price" in field:
                    partPrice = field[5:].strip() #if price in field, field strips... iykyk ( ͡° ͜ʖ ͡°)
                #if the part is purchased, this will always be indicated in the field directly after price
                if "Purchased" in field:
                    partPrice = partPrice + " (Purchased)"
            except Exception:
                pass
        
        #"No Price Available" is cumbersome and blank prices cause discord to make unexpected non-inline code blocks, get rid of both
        if (partPrice == "No Prices Available") or (partPrice == ""):
            partPrice = "``N/A``"
        else:
            partPrice = ("``" + partPrice + "``") 
        
        #partList is keyed based on type, name, and unit price, and the value is the count
        partKey = (partType, partName, partPrice)
        #if a part of these attributes exists, count one more
        if partKey in partList.keys():
            partList[partKey] += 1
        #if it doesn't exist, add it
        else:
            partList[partKey] = 1
        
    #loop over rows to add to final string
    for partKey in partList.keys():
        #set up variables
        partType = partKey[0]
        partName = partKey[1]
        partPrice = partKey[2]
        count = partList[partKey]

        #if we have multiple of a part, concatenate
        if count > 1:
            #attempt to multiply price by count. need to get number from it first
            unitPrice = re.findall("\d+\.\d+", partPrice)
            #this length will be zero if the price is n/a
            if len(unitPrice) > 0:
                #multiply and replace if possible
                totalPrice = count * (float(unitPrice[0]))
                partPrice = partPrice.replace(unitPrice[0], ("%.2f" % totalPrice))
            
            #if count > 1, add count in brackets at start of part name
            partName = ("**("+ str(count) + "x)** " + partName)
        
        #whack the whole thing into a great big string
        partLine = partType + " - " + partPrice + " - " + partName

        #do length check here
        listLength += len(partLine)
        #length 3700 leaves room for the footer sections in the 4096 character limit
        if (not tooLong) and (listLength > 3700):
            tooLong = True
        #we continue to parse the list as normal regardless of its length so we can count the number of remaining parts
        if tooLong:
            overCount += partList[partKey]
            continue

        #finally add the string to a line in the final string
        componentList += partLine + "\n"

    #if we went over the character limit, explain ourselves
    if tooLong:
        componentList += ("\n*Sorry, this part list is too long. " + str(overCount) + " part(s) were not shown. Please click the button below to see the full list.*")

    #find the grand Total row in shortRows, ignoring all secondary totals as well as shipping/tax/promo under normal circumstances
    priceTotal = ""
    purchasedParts = False
    for short in shortRows:
        #this ugly if finds just Total, only Total, not any other kind of total
        if ("Total" in short[0]) and ("Base" not in short[0]) and ("Purchased" not in short[0]):
            #we add the + in case we have to parse multiple currencies in the same list, then strip leading + for obvious reasons
            priceTotal += (" + " +short[1]) 
        if ("Purchased" in short[0]):
            purchasedParts = True

    priceTotal = priceTotal.strip(" + ")

    #if we have a mix of purchased and non-purchased parts
    if purchasedParts and (len(priceTotal) > 1):
        #put rest of totals in parentheses
        priceTotal += (" (")
        #find "purchased" and "not yet purchased" fields and add them as above
        for short in shortRows:
            if ("Purchased" in short[0]):
                indicator = short[0].replace("Total (", "")
                indicator = indicator.replace("):", "")
                priceTotal += (short[1] + " " + indicator + ", ")
        
        priceTotal = priceTotal.strip(", ")
        priceTotal += ")"

    #this case only triggers if the entire list is purchased
    #find it, and assume purchased
    elif purchasedParts:
        for short in shortRows:
            if ("Purchased" in short[0]):
                priceTotal += (short[1] + " (Purchased)")
    
    #only give up if there is truly no total (avoids triggering discrete code block)
    if len(priceTotal) < 1:
        priceTotal = "N/A"
    
    # structure embed output
    #abusing header + giant string here because header has a longer character limit than field - this increases the length of the list we can display from 1024 to 4096 characters
    embed = discord.Embed(title=siteSource+"\n"+link, description=("Sent by " + sender + "\n\n" + componentList), color=0xFF55FF) 
    try:
        embed.add_field(name="Total:", value=("``"+priceTotal+"``"), inline=False)
        embed.add_field(name="Estimated Wattage", value=buildWattage, inline=False)
        #only bother displaying compatibility notes if something is detected
        if len(compatNotes) > 0:
            embed.add_field(name=compatHeader, value=compatNotes, inline=False)
        embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
    #failover in the event of a footer of length >396 should be to skip rendering the footer and send the embed anyway
    except Exception:
        pass
    
    return(embed)
    
async def processMessage(message, userMessage, sender):
    '''
    Takes user message and handles it, outputting a response message from the bot
    Inputs: 
        - message: discord message object
        - userMessage: message contents
        - sender: user profile that sent the message
    Returns: N/A
    '''
    try:
        #grab the link
        link = await getPcppLink(userMessage)
        #scrape it
        soup, buttons = await pcppSoup(link)
        #handle it, embedding the results and adding a View to store the button(s).
        await message.channel.send(embed=tableHandler(sender, soup, link), view=MyView(soup, link, buttons))
    #any exception encountered while parsing the list should result in the bot refusing to reply and continuing to look for new messages
    except Exception as error:
        print(error)
        #raise(error)
    
if __name__ =='__main__':
    runBot() 
    