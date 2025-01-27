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
            await processMessage(message, message.content, str(message.author.mention))
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
    
    # print user-agent to console for testing 
    #driver_ua = driver.execute_script("return navigator.userAgent")
    #print("User agent in-use: "+driver_ua)
    
    # scrape url with selenium and feed to soup for html parsing
    driver.get(link)
    soup = BeautifulSoup(driver.page_source,"html.parser")

    # define the table to pull
    table = soup.find('table', class_='xs-col-12')
    
    # scrape and format build wattage
    buildWattage = (' '.join(soup.find('div', class_='partlist__keyMetric',).text.split()))[-5:]
    
    # scrape and format compatibility notes
    compatHeader = soup.find('div', class_='subTitle__header').find('h2').text
    compatNotes = ""
    compatTags = soup.find_all('p', {'class':['note__text note__text--info','note__text note__text--warning']})
    compatTags.pop()

    for note in compatTags:
        note = str(note)
        note = note[note.find("</span>") + 8:-4]
        compatNotes += ("- " + note + "\n") 
    
    # scrape and format partslist table body
    rows = []
    for row in table.find_all('tr')[1:]:  
        cells = [td.text.strip() for td in row.find_all('td')]
        if len(cells) > 3:
            rows.append(cells)

    # initialize total build cost
    total = 0.00

    # structure partslist output
    componentList = ""

    for row in rows:
        partType = "**" + row[0] + "**"

        partName = row[3].replace("\u200b", "")

        if partName.find("\n"):
            partName = partName[0:partName.find("\n")]

        partPrice = row[8][8:]
        try:
            total += float(partPrice)
            if (partPrice == "00"):
                partPrice = "0.00"
            partPrice = ("``" + locale + partPrice + "``")
        except Exception:
            partPrice = "``N/A``"

        partlist = partType + " - " + partPrice + " - " + partName

        if len(partlist) > 83:
            componentList += partlist[0:80].strip() + "...\n"
        if len(partlist) < 83:
            componentList += partlist + "\n"

    priceTotal = "{:.2f}".format(total)
    
    # structure embed output
    embed = discord.Embed(title=siteSource+"\n"+link, description=("Sent by " + sender + "\n\n" + componentList), color=0xFF55FF)
    embed.add_field(name="Total:", value=("``"+locale+priceTotal+"``"), inline=False)
    embed.add_field(name="Estimated Wattage", value=buildWattage, inline=False)
    if len(compatNotes) > 0:
        embed.add_field(name=compatHeader, value=compatNotes, inline=False)
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
    