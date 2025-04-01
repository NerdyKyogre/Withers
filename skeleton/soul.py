'''
Withers Skeleton Soul
This file contains templates for useful classes for the bot, such as buttons
It also contains superclass definitions for site-specific classes, such as messages and lists.
'''
import discord
from selenium import webdriver
from selenium_stealth import stealth
import undetected_chromedriver as uc

'''
NOTE:
All functions apart from RunBot() and constructors, INCLUDING ALL OTHER CLASS METHODS AND THEIR DESCENDANTS, MUST be async.
This is because discord's gateway depends on receiving heartbeat packets at regular intervals, which blocking functions prevent while they are running.
Having all functions async prevents gateway warnings and makes the bot more resilient to rate limiting/disconnection under heavy load.
'''

class Buttons(discord.ui.View):
    def __init__(self, soup, link, buttons):
        '''
        Instantiates a custom view below the embed with the necessary URL button(s) for list actions
        inputs:
        - Soup - beautifulsoup output from the list link
        - link - list url as string
        - buttons - tuple containing button functions in order edit, save
        '''
        super(Buttons, self).__init__()
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

class BuildListMsg:
    '''
    Parent class for messages containing relevant links
    Values:
        - msg: discord message object
        - msgText: the contents of the message as a string
        - sender: the sender of the message
        - links: string array containing each helpful link found
    '''

    def __init__(self, msg, msgText, sender):
        '''
        Simple constructor for message parent class
        Inputs:
            - msg: discord message object
            - msgText: the contents of the message as a string
            - sender: the sender of the message as a string
        '''
        self.msg = msg
        self.msgText = msgText
        self.sender = sender
        self.soup = None #implemented at call time

        self.links = [] #call findLinks later

    '''
    Simple Getters
    '''
    async def getMsg(self):
        return self.msg
    
    async def getMsgText(self):
        return self.msgText
    
    async def getSender(self):
        return self.sender
    
    async def getLinks(self):
        return self.links
    
    async def findLinks(self, driver, text=None):
        '''
        Finds links for the specific list type within the message
        Inputs: 
            - driver: selenium webdriver object
        Returns: N/A, but sets self.links[] to contain the links

        This function MUST follow the following implementation format:
        lists = []
        for link in self.links:
            lists.append(List(link))
        return lists
        This is not a global function because the List type definition is dependent on the site module.
        '''
        raise NotImplementedError("This method should be implemented by the site-specific subclass, but we couldn't find it. Check soul.py for the specification.")
    
    async def generateLists(self):
        '''
        Loops over every link found in the message and creates a new list object for it, returning them all
        Inputs: N/A
        Returns: Array of BuildList objects
        '''
        raise NotImplementedError("This method should be implemented by the site-specific subclass, but we couldn't find it.")
    
class BuildList:
    '''
    Parent class for build list tables
    Values:
        - link: link to the part list as a string
        - soup: beautifulsoup object generated during parsing
        - buttons: info required to generate secondary buttons below the message - not implemented yet
        - siteSource: Source of the build site, type string
    '''
    def __init__(self, link):
        '''
        Simple constructor for build list parent class
        Inputs:
            - link: link to the part list, type string
        '''
        self.link = link
        self.soup = None #call generateSoup later
        self.buttons = None #not implemented yet
        self.siteSource = "" #to be implemented by child class

    '''
    Simple getters
    '''
    async def getLink(self):
        return self.link
    
    async def getSoup(self):
        return self.soup
    
    async def getButtons(self):
        return self.buttons
    
    async def generateSoup(self, driver):
        '''
        Parses the part list and generates a BeautifulSoup object from it
        Returns: BeautifulSoup object with the relevant table
        '''
        raise NotImplementedError("This method should be implemented by the site-specific subclass, but we couldn't find it.")
    
    async def buildTable(self, sender):
        '''
        Generates and prepares the discord embed table for the part list
        Inputs:
            - sender: sender of the original message, type string
        Returns: Discord embed object
        '''
        raise NotImplementedError("This method should be implemented by the site-specific subclass, but we couldn't find it.")
        

async def startWebDriver():
    '''
    Initializes a customized-default Chrome Webdriver instance and returns it
    Inputs: N/A
    Returns: Selenium Webdriver object
    This function should be called once for every message we handle
    '''
    # initialize selenium chrome webdriver with necessary settings
    options = webdriver.ChromeOptions()
    #options.add_argument('--headless')
    options.add_argument('--window-size=1920x1032')
    options.add_argument('--no-sandbox')
    #not specifically going out of our way to tell the site we're a bot helps with rate limiting
    options.add_argument("--disable-blink-features=AutomationControlled")
    #options.add_experimental_option("excludeSwitches", ["enable-automation"])
    #options.add_experimental_option("useAutomationExtension", False)
    #the below three options improve performance
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-extensions')
    options.add_argument('--dns-prefetch-disable')
    #set user agent to mimic real chrome
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36")
    driver = uc.Chrome(options=options)
    #driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    stealth(driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
        )

    return driver
