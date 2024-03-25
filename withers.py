import discord
INTENTS = discord.Intents.default()
INTENTS.message_content = True
import os
from dotenv import load_dotenv

def runBot():
    #get discord token from .env file for security purposes
    load_dotenv()
    TOKEN = os.getenv("DISCORD_TOKEN")
    client = discord.Client(intents=INTENTS)

    #print to console when we are live
    #and handle processing of every message
    #credit upwork https://www.upwork.com/resources/how-to-make-discord-bot
    @client.event
    async def on_ready():
        print({client.user}, 'is live')
 
    @client.event
    async def on_message(message):
        if message.author == client.user:
            return
        #only do anything if message contains relevant string
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

    #find substring of list link
    try:
        start = msg.index("pcpartpicker.com/list/")
        print(start)
    except Exception:
        return None
    
    #check for regional PCPP URLs, which are 31 characters long after https:// to USA's 28
    if msg[start - 1] == ".":
        start -= 3
        length = 31
    else: 
        length = 28

    #figure out the actual url
    link = "https://"
    for i in range(start, start + length):
        try:
            link += msg[i] 
        except Exception:
            return("Invalid PCPP link.")
            #todo: check for 404 errors in link. may happen in parser?
    
    #todo: parse data from pcpp url
    #response = parse(link)
    
    response = "I think you sent the PCPP link: " + link
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
    