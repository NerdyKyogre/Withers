import discord
intents = discord.Intents.default()
intents.message_content = True
import os
from dotenv import load_dotenv

def runBot():
    #get discord token from .env file for security purposes
    load_dotenv()
    TOKEN = os.getenv("DISCORD_TOKEN")
    client = discord.Client(intents=intents)

    #print to console when we are live
    #and handle processing of every message
    #credit upwork
    @client.event
    async def on_ready():
        print({client.user}, 'is live')
 
    @client.event
    async def on_message(message):
        if message.author == client.user:
            return
        #only do anything if message contains relevant string
        if "https://pcpartpicker.com/list/" in message.content:
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
        start = msg.index("https://pcpartpicker.com/list/")
    except Exception:
        return None

    #find substring of list link
    #pcpp links are always 36 characters long
    link = ""
    for i in range(start, start + 36):
        link += msg[i]
    
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
    