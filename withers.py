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

from skeleton import *

def runBot():
    '''
    Initializes the bot and checks for new messages in all connected channels.
    Inputs: N/A
    Returns: N/A
    '''
    # get discord token from .env file for security purposes
    load_dotenv()
    TOKEN = os.getenv("DISCORD_TOKEN")
    # load support channel from .env if it exists
    try:
        DM_CHANNEL = int(os.getenv("DM_CHANNEL"))
    except Exception:
        DM_CHANNEL = None

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
        #PCPP
        if ("pcpartpicker.com/list/" in message.content) or ("pcpartpicker.com/b/" in message.content) or ("pcpartpicker.com/user/" in message.content):
            rqMsg = pcpp.Msg(message, message.content, str(message.author.mention))
            await processMessage(message, rqMsg)
        #PCPT
        if ("pcpricetracker.in/b/s/" in message.content):
            rqMsg = pcpt.Msg(message, message.content, str(message.author.mention))
            await processMessage(message, rqMsg)
        # if this is a DM, forward it to the support channel
        if ((isinstance(message.channel, discord.DMChannel)) and (DM_CHANNEL is not None)):
            # Getting the channel
            channel = client.get_channel(DM_CHANNEL)
            await channel.send(embed=(await recieveDM(message)))
        else: 
            return
    client.run(TOKEN)

async def processMessage(message, rqMsg):
    '''
    Takes user message and handles it, outputting a response message from the bot
    Inputs: 
        - rqMsg: BuildListMessage child object containing the necessary lists
    Returns: N/A
    '''
    try:
        #start webdriver instance for this message
        driver = await soul.startWebDriver()
        #first, find all the links
        await rqMsg.findLinks(driver)
        #handle a message for each link in the list
        lists = await rqMsg.generateLists()
        if len(lists) == 0:
            pass
        else:
            for buildList in lists:
                #scrape this link
                await buildList.generateSoup(driver)
                #embed the results and add a View to store the button(s).
                await message.channel.send(embed=(await buildList.buildTable(await rqMsg.getSender())), view=soul.Buttons(await buildList.getSoup(), await buildList.getLink(), await buildList.getButtons()))
        
        driver.quit()
    #any exception encountered while parsing the list should result in the bot refusing to reply and continuing to look for new messages
    except Exception as error:
        print(error)
        #raise(error)

async def recieveDM(message):
    embed = discord.Embed(title=("DM from: " + str(message.author)), description=(""), color=0xFFFFFF)
    embed.add_field(name="", value=message.content)
    return embed

if __name__ =='__main__':
    runBot()   