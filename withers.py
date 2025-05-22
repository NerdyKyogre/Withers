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
import sys

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

    #update user agents
    soul.updateUserAgents()

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
            #start webdriver instance for this message
            driver = await pcpp.startWebDriver()
            await processMessage(message, rqMsg, driver)
        #PCPT
        if ("pcpricetracker.in/b/s/" in message.content) and ("--use-extended-modules" in sys.argv):
            driver = await pcpt.startWebDriver()
            rqMsg = pcpt.Msg(message, message.content, str(message.author.mention))
            await processMessage(message, rqMsg, driver)
        #Geizhals Network
        if ("geizhals.de/wishlists/" in message.content) or ("geizhals.at/wishlists/" in message.content) or ("geizhals.eu/wishlists/" in message.content) or ("skinflint.co.uk/wishlists/" in message.content) or ("cenowarka.pl/wishlists/" in message.content):
            driver = await geizhals.startWebDriver()
            rqMsg = geizhals.Msg(message, message.content, str(message.author.mention))
            await processMessage(message, rqMsg, driver)
        #Tweakers
        if ("tweakers.nl/gallery" in message.content) or ("tweakers.net/gallery" in message.content) or ("tweakers.net/pricewatch/bestelkosten" in message.content) or ("tweakers.nl/pricewatch/bestelkosten" in message.content):
            driver = await tweakers.startWebDriver()
            rqMsg = tweakers.Msg(message, message.content, str(message.author.mention))
            await processMessage(message, rqMsg, driver)
        #BAPCGG
        if (("buildapc.gg" in message.content) or ("komponentkoll.se" in message.content)) and (("/build/" in message.content) or ("/bygg/" in message.content)):
            driver = await bapcgg.startWebDriver()
            rqMsg = bapcgg.Msg(message, message.content, str(message.author.mention))
            await processMessage(message, rqMsg, driver)
        #meupc
        if ("meupc.net/build/" in message.content):
            rqMsg = meupc.Msg(message, message.content, str(message.author.mention))
            driver = await meupc.startWebDriver()
            await processMessage(message, rqMsg, driver)
        #hinta
        if ("hinta.fi/ostoskori" in message.content):
            rqMsg = hinta.Msg(message, message.content, str(message.author.mention))
            driver = await hinta.startWebDriver()
            await processMessage(message, rqMsg, driver)

        # if this is a DM, forward it to the support channel
        if ((isinstance(message.channel, discord.DMChannel)) and (DM_CHANNEL is not None)):
            # Getting the channel
            channel = client.get_channel(DM_CHANNEL)
            await channel.send(embed=(await recieveDM(message)))
        else: 
            return
    client.run(TOKEN)

async def processMessage(message, rqMsg, driver):
    '''
    Takes user message and handles it, outputting a response message from the bot
    Inputs: 
        - message: discord message object we're using
        - rqMsg: BuildListMessage child object containing the necessary lists
        - driver: customized selenium webdriver object to match the site we need
    Returns: N/A
    '''
    try:
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
                #in the event of a bad list, we need to send the embed immediately - easiest solution is to give buildtable the message and then raise an exception
                try:
                    await message.channel.send(embed=(await buildList.buildTable(await rqMsg.getSender(), message)), view=soul.Buttons(await buildList.getSoup(), await buildList.getLink(), await buildList.getButtons()))
                except ValueError:
                    pass
        
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