'''
Withers Bot Site Head - PCPartPicker
Handles PCPartpicker build list, completed build, and saved list links
'''
import discord
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
import datetime
import asyncio
import re

import skeleton.soul as soul

class Msg(soul.BuildListMsg):
    
    def __init__(self, msg, msgText, sender):
        super().__init__(msg, msgText, sender)
        self.priv = False #indicator to determine whether a list is private

    async def findLinks(self, driver):
        '''
        Finds PCPartPicker link within the contents of a message
        Inputs: 
            - driver: selenium webdriver instance
        Returns array of links as strings
        '''
        #convert saved part lists and completed builds into regular list links in the message
        await self.buildsToLists(driver)
        #strip out all #view= in the message to convert view links into saved lists
        self.msgText = self.msgText.replace("#view=", "")
        await self.savedToLists(driver)

        #check for blank list link
        if ("pcpartpicker.com/list/sF8TwP" in self.msgText):
            self.msgText = self.msgText.replace("pcpartpicker.com/list/sF8TwP", " ")
            await self.noPartsEmbed()

        #add list links to table
        await self.linksToLists(self.msgText)

        #if we found empty lists or privated saved lists, handle them here
        #check for empty link
        self.msgText = (self.msgText + " ")
        if ("pcpartpicker.com/list " in self.msgText) or ("pcpartpicker.com/list/ " in self.msgText):
            await self.blankEmbed()
            pass
        #check for priv
        if (self.priv):
            await self.privEmbed()
            pass

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
    
    async def buildsToLists(self, driver):
        '''
        Recursively finds all completed build links in the message and replaces them with the corresponding list link
        Inputs:
            - driver: selenium webdriver instance
        Returns: N/A, but updates self.msgText with the new link values
        '''
        # find substring of build link if it exists
        try:
            start = self.msgText.index("pcpartpicker.com/b/")
        except Exception:
            return
        
        # check for regional PCPP URLs, which are 31 characters long after https:// to USA's 28
        # regional url prefixes have a . before pcpartpicker, whereas the base american one has a /. we use this to differentiate them
        country = "" #we need to store the country code in order to get the correct locale for the list link
        if self.msgText[start - 1] == ".":
            start -= 3
            length = 28
            country = self.msgText[start:(start + 3)]
        else: 
            length = 25
        
        # figure out the actual url by looping over characters until we hit the right length
        # we do this instead of slicing so we can more easily detect invalid/cut off links
        link = "https://"
        for i in range(start, start + length):
            try:
                link += self.msgText[i] 
            except Exception:
                return
        try:
            #now we can load the url into webdriver and look for the part list link
            driver.get(link)
            #we don't need to do anything special with driver, so just soup it
            bSoup = BeautifulSoup(driver.page_source,"html.parser")
            #grab all the a tags with destinations, and search for one of the format "/list/XXXXXX"
            aTags = bSoup.find_all('a', href=True)
            for tag in aTags:
                href = tag['href']
                if (href.find("/list/") == 0) and (len(href) > 6): #specify length to avoid taking us to an empty /list/
                    partsLink = ("https://" + country + "pcpartpicker.com" + href)
        except Exception: #if we can't load the page or we can't find the button, error
            self.priv = True
            partsLink = ""

        #now that we have the link, replace it in msgText
        self.msgText = self.msgText.replace(link, partsLink)

        #recurse in case there are more builds to find
        await self.buildsToLists(driver)
        return
    
    async def savedToLists(self, driver):
        '''
        Recursively finds all saved part list links in the message and replaces them with the corresponding list link
        Inputs:
            - driver: selenium webdriver instance
        Returns: N/A, but updates self.msgText with the new link values
        '''
        # find substring of list link if it exists
        try:
            start = self.msgText.index("pcpartpicker.com/user/")
            #make sure we go to a saved link and NOT a user page - assigning this will throw an exception if it fails
            finish = (self.msgText.index("/saved/") + 13)
        except Exception:
            return
        #check for regional urls
        if self.msgText[start - 1] == ".":
            start -= 3
        #skip checking for malformed links here as this is too difficult considering the variable length of the username field
        link = ("https://" + self.msgText[start:finish])

        #wrap this in a try-catch because find_element will error if the list is private or malformed - we want to handle that
        try:
            #load the page into webdriver - we need to navigate to the edit part list button
            driver.get(link)

            editButton = driver.find_element(By.XPATH, '//a[contains(@class,"actionBox__options--edit")]')
            editButton.click()
            #need this to check for page to fully load before we find the link
            await asyncio.sleep(4)
            
            #make it into a soup and find the link
            sSoup = BeautifulSoup(driver.page_source,"html.parser")
            #get all text input fields, and look for the one with the link in its value
            partsLink = sSoup.find("input", class_="text-input", type="text")['value']
        except Exception as error:
            self.priv = True
            partsLink = ""

        #now that we have the link, replace it in msgText
        self.msgText = self.msgText.replace(link, partsLink)
        
        #recurse in case there are more saved lists to find
        await self.savedToLists(driver)
        return


    async def linksToLists(self, text):
        '''
        Recursively finds all PCPP list links in the message and adds them to the list of links
        Inputs: 
            - text: the message or message segment to look for a link in
        Returns: N/A
        '''
        # find substring of list link if it exists
        try:
            start = text.index("pcpartpicker.com/list/")
        except Exception:
            return
        
        # check for regional PCPP URLs, which are 31 characters long after https:// to USA's 28
        # regional url prefixes have a . before pcpartpicker, whereas the base american one has a /. we use this to differentiate them
        if text[start - 1] == ".":
            start -= 3
            length = 31
        else: 
            length = 28

        # figure out the actual url by looping over characters until we hit the right length
        # we do this instead of slicing so we can more easily detect invalid/cut off links
        link = "https://"
        for i in range(start, start + length):
            try:
                link += text[i] 
            except Exception:
                return
        
        self.links.append(link)
        await self.linksToLists(text.replace(link, "")) #recurse on the remaining links in the message
        return
    
    async def privEmbed(self):
        '''
        Creates and sends an embedded message in the event that we detect a private or malformed link
        Inputs: N/A
        Returns: N/A
        '''
        #set up embed
        embed = discord.Embed(title="Private or invalid link detected", description=("Sent by " + self.sender + "\n"), color=0xFF0000)
        embed.add_field(name="", value="I ran into some trouble opening a list you sent.\n\nPlease make sure all the PCPartPicker links in your message are valid, and that any saved part lists are public (\"Private\" checkbox unchecked).")
        #upload the image
        file = discord.File("./assets/private_checkbox.png", filename="private_checkbox.png")
        embed.set_image(url="attachment://private_checkbox.png")
        #timestamp for better legibility
        embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
        await self.msg.channel.send(file=file, embed=embed)

    async def blankEmbed(self):
        '''
        Creates and sends an embedded message in the event that we detect an empty PCPP link
        Inputs: N/A
        Returns: N/A
        '''
        #set up embed
        embed = discord.Embed(title="Empty list detected", description=("Sent by " + self.sender + "\n"), color=0xFF0000)
        embed.add_field(name="", value="Please make sure to copy the correct link when sending your PCPartPicker list, otherwise I can't read it.\n\nDon't worry, this happens all the time :pensive:")
        #upload the image
        file = discord.File("./assets/wrong_link.png", filename="wrong_link.png")
        embed.set_image(url="attachment://wrong_link.png")
        #timestamp for better legibility
        embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
        await self.msg.channel.send(file=file, embed=embed)

    async def noPartsEmbed(self):
        '''
        Creates and sends an embedded message in the event that we detect the link to the empty PCPP list
        Inputs: N/A
        Returns: N/A
        '''
        #set up embed
        embed = discord.Embed(title="PCPartIgnorer", description=("Sent by " + self.sender + "\n"), color=0xE8EB34)
        embed.add_field(name="", value="You forgot to put parts in your part list!\n\nNow I don't have a job to do... :cry:")
        #upload the image
        file = discord.File("./assets/empty_list.jpeg", filename="empty_list.jpeg")
        embed.set_image(url="attachment://empty_list.jpeg")
        #timestamp for better legibility
        embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
        await self.msg.channel.send(file=file, embed=embed)

class List(soul.BuildList):

    def __init__(self, link):
        super().__init__(link)
        self.siteSource = "PCPartPicker"

    async def generateSoup(self, driver):
        '''
        Multi-purpose function to scrape the PCPartPicker page with Selenium and feed the data table into BeautifulSoup for formatting and parsing.
        Sets self.soup to this object when complete
        Inputs:
            - driver: selenium webdriver object
        Returns: N/A
        '''
        
        # scrape url with selenium and feed to soup for html parsing
        driver.get(self.link)

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
        
        self.soup = BeautifulSoup(driver.page_source,"html.parser")

        #legacy button functions
        #editClick = driver.find_element(By.CLASS_NAME, "actionBox__options--edit")
        #saveClick = driver.find_element(By.CLASS_NAME, "actionBox__options--save")
        #editClick, saveClick = (None, None)

        #return soup #, (editClick, saveClick)
    
    async def buildTable(self, sender):
        '''
        Parses data table from PCPP list link into a discord embed
        Inputs: 
            sender - author of calling message, type string
        Returns: response message, type discord embed object
        '''

        #wrap this logic in try-catch to make sure list is real
        try:
            # define the information table to pull based on its class
            table = self.soup.find('table', class_='xs-col-12')
            
            # scrape and format existing build wattage estimate
            buildWattage = (' '.join(self.soup.find('div', class_='partlist__keyMetric',).text.split()))
            wattageSplit = buildWattage.find(":") + 2 
            buildWattage = buildWattage[wattageSplit:]
            
            # scrape and format compatibility notes
            compatHeader = self.soup.find('div', class_='subTitle__header').find('h2').text
            compatNotes = ""
            compatTags = self.soup.find_all('p', {'class':['note__text note__text--info','note__text note__text--warning', 'note__text note__text--problem']})
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
        except Exception:
            return (await self.badListEmbed(sender))

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
        paramGlobal = False

        #add a new entry to componentList for each part in the long rows
        for row in rows:
            #part type e.g. CPU, Memory, Storage, etc is the first field, so we can simply tack it on and bold it
            partType = "**" + row[0] + "**"

            #next, find the name of the part, and include its hyperlink which we'll format into the name
            #excessive zero width spaces do nothing but inflate character count, remove them
            partName = row[3].replace("\u200b", "").strip()
            #check for parametric BEFORE stripping it off of partName
            parametric = False
            if partName.find("parametric") >= 0:
                parametric = True
                paramGlobal = True #setting this value is quicker than checking it and then setting it
            #Some part names begin with a leading newline, remove it
            index = partName.find("\n")
            if index >= 0:
                partName = partName[0:(index + 1)].strip()
            #this is where we check if we found a link earlier and set up the hyperlink
            if row[5] == True:
                partName = ("[" + partName + "](" + row[4].strip() + ")")
            #if we detected a parametric filter for this part, add an asterisk
            if parametric:
                partName = partName + "**\***"

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

        #if we had at least one parametric part, indicate as such
        if paramGlobal:
            componentList += ("\n*\* Indicates a part selected by a parametric filter. Please open the full list for more information.*\n")

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
        #get country code from link
        country = "us"
        if len(self.link) > 36:
            country = self.link[8:10]
        #fix issues with discord emoji compat
        if country == "uk":
            country = "gb"
        #abusing header + giant string here because header has a longer character limit than field - this increases the length of the list we can display from 1024 to 4096 characters
        embed = discord.Embed(title=(self.siteSource+ " :flag_" + country + ":\n"+self.link), description=("Sent by " + sender + "\n\n" + componentList), color=0xFF55FF)
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
    
    async def badListEmbed(self, sender):
        '''
        Generates an error message to embed in the event of an invalid link
        Inputs:
            - sender: sender id, string
        Returns: discord embed object
        '''
        #set up embed
        embed = discord.Embed(title=("Couldn't read list\n" + self.link), description=("Sent by " + sender + "\n"), color=0xFF0000)
        embed.add_field(name="", value="I couldn't find a valid parts table in this list link. Please make sure you've copied the link correctly.\n\nIf you're certain the link is correct and this error persists, there may be a bug - check my About Me for support.")
        embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
        return embed