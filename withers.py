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

class MyView(discord.ui.View):
    def __init__(self, soup):
        super(MyView, self).__init__()
        self.soup = soup
    
    #todo: make these buttons do the things on their labels
    @discord.ui.button(label='Open List', style=discord.ButtonStyle.blurple)
    async def on_button_1_click(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.edit_message(content='Button 1 clicked!')
    @discord.ui.button(label='Edit List', style=discord.ButtonStyle.blurple)
    async def on_button_1_click(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.edit_message(content='Button 2 clicked!')
    @discord.ui.button(label='Save List', style=discord.ButtonStyle.blurple)
    async def on_button_2_click(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.edit_message(content='Button 3 clicked!')

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

def getPcppLink(msg):
    curSyms = {"au":"$", "at":"€", "be":"€", "ca":"$", "cz":"Kč", "dk":"kr", "fi":"€", "fr":"€", "de":"€", "hu":"Ft", "ie":"€", "it":"€", "nl":"€", "nz":"$", "no":"kr", "pt":"€", "ro":"RON", "sa":"SR", "sk":"€", "es":"€", "se":"kr", "uk":"£", "us":"$"}
    # find substring of list link
    try:
        start = msg.index("pcpartpicker.com/list/")
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
            #return("Invalid PCPP link.", "")
            raise SyntaxError("Invalid PCPP Link")
            #todo: check for 404 errors in link. may happen in parser?
    
    return(link, locale)

def pcppSoup(link):
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

    return soup

def msgHandler(msg, sender, soup, linkTuple):
    '''
    Checks visible channels for messages containing PCPP list links
    Inputs: 
        msg - message to parse, type string
        sender - author of calling message, as string
        soup - BeautifulSoup object output from scraper
        linkTuple - A tuple containing the link and its local currency symbol, as strings
    Returns: response message, type string
    '''
    link, locale = linkTuple

    siteSource="PCPartPicker" #temporarily hard coded until we add support for other part comparison systems
    '''
    try:
        link, locale = getPCPPLink(msg)
    except SyntaxError:
        raise Exception("Failed to parse link. This may be due to an invalid link format.")
    '''

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
        cells = []
        for td in row.find_all('td'):
            cells.append(td.text.strip())
            #grab link
            tdClass = td.get("class")
            if tdClass is not None and "td__name" in tdClass:
                for a in td.find_all('a'):
                    url = str(a)
                    url = url[(url.find("href") + 6):]
                    url = url[:url.find("\">")]
                    if (url.find("view_custom_part") < 0):
                        cells.append("https://pcpartpicker.com" + url)
                        cells.append(True)

        if len(cells) > 3:    
            rows.append(cells)

    # initialize total build cost
    total = 0.00

    # structure partslist output
    componentList = ""

    listLength = 0

    for row in rows:
        partType = "**" + row[0] + "**"
        listLength += len(partType)

        partName = row[3].replace("\u200b", "")

        index = partName.find("\n")
        if index >= 0:
            partName = partName[0:(index + 1)].strip()

        if row[5] == True:
            partName = ("[" + partName + "](" + row[4].strip() + ")")
        listLength += len(partName)

        partPrice = row[10][8:]
        try:
            total += float(partPrice)
            if (partPrice == "00"):
                partPrice = "0.00"
            partPrice = ("``" + locale + partPrice + "``")
        except Exception:
            partPrice = "``N/A``"

        listLength += len(partPrice)

        if listLength > 3700:
            componentList += "Sorry, this part list is too long. Please click the list link to view the rest of the parts."
            break

        partlist = partType + " - " + partPrice + " - " + partName
        #wrapping disabled for aesthetic testing with links. can be re-enabled by uncommenting below block, but is not compatible with markdown urls being added yet
        '''
        if len(partlist) > 74: #83
            componentList += partlist[0:71].strip() + "...\n" #80
        if len(partlist) <= 74:
            componentList += partlist + "\n"
        '''
        componentList += partlist + "\n"

    priceTotal = "{:.2f}".format(total)
    
    # structure embed output
    embed = discord.Embed(title=siteSource+"\n"+link, description=("Sent by " + sender + "\n\n" + componentList), color=0xFF55FF) #abusing header + giant string here because header has a longer character limit than field - this increases the length of the list we can display from 1024 to 4096 characters
    #failover in the event of a footer of length >396 should be to skip rendering the footer and send the embed anyway
    #this behaviour can be changed later
    try:
        embed.add_field(name="Total:", value=("``"+locale+priceTotal+"``"), inline=False)
        embed.add_field(name="Estimated Wattage", value=buildWattage, inline=False)
        if len(compatNotes) > 0:
            embed.add_field(name=compatHeader, value=compatNotes, inline=False)
        embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
    except Exception:
        pass

    return(embed)
    
async def processMessage(message, userMessage, sender):
    '''
    Sends messages between the user and the bot
    Credit https://www.upwork.com/resources/how-to-make-discord-bot
    '''
    try:
        link = getPcppLink(userMessage)
        soup = pcppSoup(link[0])
        await message.channel.send(embed=msgHandler(userMessage, sender, soup, link), view=MyView(soup))
        #await message.channel.send(embed=msgHandler(userMessage, sender))
    except Exception as error:
        print(error)
    
if __name__ =='__main__':
    runBot() 
    