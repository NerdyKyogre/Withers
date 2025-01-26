'''
Withers
A discord bot that parses PCPartPicker (hereafter PCPP) list links and posts them as a user-readable message, similar to PCPP's in-house Smithers bot
Authors: @NerdyKyogre and @Spiritfader
'''
import discord
INTENTS = discord.Intents.default()
INTENTS.message_content = True
import os
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from selenium import webdriver
import datetime


def runBot():
    # get discord token from .env file for security purposes
    load_dotenv()
    TOKEN = os.getenv("DISCORD_TOKEN")
    client = discord.Client(intents=INTENTS)

    # print to console when we are live and process every message
    # credit upwork https://www.upwork.com/resources/how-to-make-discord-bot
    @client.event
    async def on_ready():
        print({client.user}, 'is live')
 
    @client.event
    async def on_message(message):
        if message.author == client.user:
            return
        # only do anything if message contains relevant string
        if "pcpartpicker.com/list/" in message.content:
            await processMessage(message, message.content, str(message.author))
        else: 
            return
    client.run(TOKEN)

def msgHandler(msg, sender):
    '''
    Checks visible channels for messages containing PCPP list links
    Inputs: 
        msg - message to parse, type string
        sender - author of calling message, as string
    Returns: response message, type string
    '''
    curSyms = {"au":"$", "at":"€", "be":"€", "ca":"$", "cz":"Kč", "dk":"kr", "fi":"€", "fr":"€", "de":"€", "hu":"Ft", "ie":"€", "it":"€", "nl":"€", "nz":"$", "no":"kr", "pt":"€", "ro":"RON", "sa":"SR", "sk":"€", "es":"€", "se":"kr", "uk":"£", "us":"$"}
    # find substring of list link
    try:
        start = msg.index("pcpartpicker.com/list/")
        siteSource="PCPartPicker"
    except Exception:
        return None
    
    # check for regional PCPP URLs, which are 31 characters long after https:// to USA's 28
    if msg[start - 1] == ".":
        start -= 3
        length = 31
        try:
            locale=curSyms[msg[start:(start + 2)]] 
        except Exception:
            locale=""
    else: 
        length = 28
        locale=curSyms["us"]

    # figure out the actual url
    link = "https://"
    for i in range(start, start + length):
        try:
            link += msg[i] 
        except Exception:
            return("Invalid PCPP link.")
            #todo: check for 404 errors in link. may happen in parser?
    
    # initialize selenium chrome webdriver with settings
    useragent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36"
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-extensions')
    options.add_argument('--dns-prefetch-disable')
    options.add_argument("--user-agent="+useragent)
    driver = webdriver.Chrome(options=options)
    
    # display user-agent for testing 
    #driver_ua = driver.execute_script("return navigator.userAgent")
    #print("User agent in-use: "+driver_ua)
    
    # scrape url with selenium and feed to soup for html parsing
    driver.get(link)
    soup = BeautifulSoup(driver.page_source,"html.parser")

    # define the table to pull
    table = soup.find('table', class_='xs-col-12')

    # extract table body
    rows = []
    for row in table.find_all('tr')[1:]:  
        cells = [td.text.strip() for td in row.find_all('td')]
        if len(cells) > 3:
            rows.append(cells)

    # initialize total build cost
    total = 0.00

    # print message header
    embed = discord.Embed(title=siteSource+"\n"+link, description=("Sent by " + sender), color=0xFF55FF)

    # formulate build list
    types = ""
    names = ""
    costs = ""

    for row in rows:
        partType = row[0]
        while len(partType) < 14:
            partType += " "
        types += (partType + "\n")

        partName = row[3]
        partName = partName.replace("\u200b", "")

        if len(partName) > 50:
            partName = partName[0:49]
        while len(partName) < 49:
            partName += " "
        names += (partName + "..." + "\n")
        
        partPrice = row[8][8:]
        try:
            total += float(partPrice)
            partPrice = (locale + partPrice)
        except Exception:
            partPrice = "-"
        
        while len(partPrice) < 8:
            partPrice = " " + partPrice
        costs += (partPrice + "\n")

    priceTotal = "{:.2f}".format(total)

    # structure embed output
    embed.add_field(name="Type", value=types, inline=True)
    embed.add_field(name="Name", value=names, inline=True)
    embed.add_field(name="Cost", value=costs, inline=True)
    embed.add_field(name="Total:", value=(locale+priceTotal), inline=False)
    #embed.add_field(name="Compatibility: ", value="buildCompat", inline=False)
    #embed.add_field(name="PSU Wattage: ", value="buildWattage", inline=False)
    #embed.set_footer(text='\u200b',icon_url="")
    embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
    

    return(embed)
    
async def processMessage(message, userMessage, sender):
    '''
    Sends messages between the user and the bot
    Credit https://www.upwork.com/resources/how-to-make-discord-bot
    '''
    try:
        await message.channel.send(embed=msgHandler(userMessage, sender))
    except Exception as error:
        print(error)
    
if __name__ =='__main__':
    runBot() 
    