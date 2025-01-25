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
            await processMessage(message, message.content)
        else: 
            return
    client.run(TOKEN)

def msgHandler(msg):
    '''
    Checks visible channels for messages containing PCPP list links
    Inputs: 
        msg - message to parse, type string
    Returns: response message, type string
    '''

    # find substring of list link
    try:
        start = msg.index("pcpartpicker.com/list/")
        print(start)
    except Exception:
        return None
    
    # check for regional PCPP URLs, which are 31 characters long after https:// to USA's 28
    if msg[start - 1] == ".":
        start -= 3
        length = 31
    else: 
        length = 28

    # figure out the actual url
    link = "https://"
    for i in range(start, start + length):
        try:
            link += msg[i] 
        except Exception:
            return("Invalid PCPP link.")
            #todo: check for 404 errors in link. may happen in parser?
    
    # initialize selenium chrome webdriver and begin scraping   
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-extensions')
    #options.add_argument('--dns-prefetch-disable')
    driver = webdriver.Chrome(options=options)
        
    # pull url with selenium and feed to soup for html parsing
    driver.get(link)
    soup = BeautifulSoup(driver.page_source,"lxml")

    # define the table to pull
    table = soup.find('table', class_='xs-col-12')

    # extract table body
    rows = []
    for row in table.find_all('tr')[1:]:  
        cells = [td.text.strip() for td in row.find_all('td')]
        rows.append(cells)
    rows.pop()

    # print message header
    response = "PCPP List Link:\n"
    response += "<" + link + ">\n```"

    # initialize total build cost
    total = 0.00

    for row in rows:
        partType = row[0]
        while len(partType) < 14:
            partType += " "
        
        partName = row[3]
        partName = partName.replace("\u200b", "")

        if len(partName) > 30:
            partName = partName[0:29]
        while len(partName) < 30:
            partName += " "
        
        partPrice = row[8][8:]
        try:
            total += float(partPrice)
        except Exception:
            partPrice = "-"
        
        while len(partPrice) < 8:
            partPrice = " " + partPrice

        response += (partType + partName + partPrice + "$\n")

    response += "----------------------------------------------------\n"
    strTotal = "{:.2f}".format(total)
    response += ("TOTAL: $" + strTotal)
    response += "```\n"
    return response
    

async def processMessage(message, userMessage):
    '''
    Sends messages between the user and the bot
    Credit https://www.upwork.com/resources/how-to-make-discord-bot
    '''
    try:
        botResponse = msgHandler(userMessage)
        await message.channel.send(botResponse)
    except Exception as error:
        print(error)
    
if __name__ =='__main__':
    runBot() 
    