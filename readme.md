# <p align=center> Withers

- [What is this?](#what-is-this)
- [Why Withers?](#why-withers)
- [Usage](#usage)
- [Deploying Yourself](#deploying-yourself)
- [What's New](#whats-new-in-this-version)


## What is this?
Withers is a discord bot written in Python for the purpose of parsing PCPartPicker (and eventually other) build lists and automatically posting them in an organized manner. This facilitates a more fluid and efficient approach to helping people craft the build of their dreams.
<br>

If you would like to try the bot and partake in our lovely community of PC enthusiasts, or simply inquire about your own build, feel free to join [The Official Tech™ Discord Server](https://discord.gg/fGNSuWzNHG)!

Withers is the official Part List Bot of The Tech™ since 2025.

## Why Withers?
Withers offers a number of unique features that set it apart from other buildhelp bots.

- It supports a variety of parts comparison platforms; currently PCPartPicker and PCPriceTracker are supported, with more to come soon!
- It has indicators for parametric filters, duplicate parts, and other helpful extras for making build lists.
- It links custom part URLs correctly and handles multiple currencies in one list; if you can make the list, Withers can display it!
- It uses the *full* character limit to show more parts in a single embed.
- It supports all forms of PC build lists including PCPP saved lists and completed builds.
- It can detect common mistakes in buildhelp channels and offer guidance on how to fix them, saving your advisors a headache.
- It's open-source - you can spin up your own instance easily whenever you want!

## Usage

Using the bot is incredibly simple. All one must do is provide the build list url in the channel as they would normally do. The bot will automatically parse and post the organized contents of the list immediately to the same channel the list was originally posted in. 

<p align=center> <img src="examples/example-1.png?raw=true" alt="Withers output example" style="max-width:100%;max-height:100%;"/>


## Deploying Yourself 
We assume you know how to setup a discord bot account and have already done so. If not, go to the [Discord Dev Portal](https://discord.com/developers/docs/quick-start/getting-started) and RTFM from Step 1.
Once you have that account:

- Install and configure ``Python 3.11`` or higher. This is a **hard requirement** (obviously, this is a python bot.)
- Clone this repo using your method of choice, then enter it:
    ```Sh
    git clone https://github.com/NerdyKyogre/Withers
    cd Withers
    ```
    <br>
Next, it's ***highly*** recommended to create a venv (virtual python environment) to ensure code reproducibility and avoid dependency contamination. If you are unsure how, read on:
- create a venv in the root of the repo as follows:
    ```Sh
    python -m venv ./.withers-venv
    ```
- Source the newly created venv:
    ```Sh
    source ./.withers-venv/bin/activate
    ```
#### <p align=center>  NO ISSUES WILL BE ENTERTAINED IF ATTEMPTING TO RUN OUTSIDE A VENV. 
#### <p align=center>  IF YOU DARE, YOU'RE ON YOUR OWN KID
<br>

Now you can interact with python regularly, with the newly created venv as the source of your python environment.
- Install the required dependencies from ``requirements-3.13.txt`` if you're using ``python 3.13`` or higher 
    ```Sh
    pip install --no-cache-dir -r requirements-3.13.txt
    ```
- Otherwise, install the required dependencies from ``requirements-3.12.txt`` if you're using ``python 3.12`` or lower 
    ```Sh
    pip install --no-cache-dir -r requirements-3.12.txt
    ```
- If necessary, download the chromium driver per the [selenium documentation](https://pypi.org/project/selenium/) or install it from your distribution repository.

- Create a new file called ``.env`` in the base root of the repo. This file should look like the below example;
    ```Sh
    DISCORD_TOKEN = [INSERTYOURTOKENHERE]
    ```
- You can obtain your 72-character token in the Bot tab of your Discord app's dashboard.

    <p align=center> <img src="examples/app-dashboard.png?raw=true" alt="Withers output example" style="max-width:100%;max-height:100%;"/>

- While you're in this tab, scroll down and enable the Message Content gateway intent - the bot depends on this to be able to read messages.

- Optionally, you can add another line to .env which will redirect DMs sent to the bot to your own support channel, given by its ID. In this case, your .env file will look something like this:
    ```Sh
    DISCORD_TOKEN = [INSERTYOURTOKENHERE]
    DM_CHANNEL = [INSERTCHANNELID HERE]
    ```

- You can obtain the ID of a channel by right clicking in your channel list, then clicking "Copy Channel ID". Note that this feature is experimental at this time; it may have bugs, and updates may change its behaviour without warning.

- Finally, run the bot
    ```Sh
    python ./withers.py
    ```

- If you want to update the bot later to keep up with the latest features, simply enter the directory and do
    ```Sh
    git pull
    ```
### <p align=center> That's it, you're good to go!

## What's new in this version:
- Added support for PCPriceTracker.in build links
- Links to individual parts in PCPP lists now match the country of the full list.
- The bot can now recieve DMs in a channel of your choice. (experimental)
- Changed how the webdriver is structured, tailoring settings to each site for improved reliability and performance.
<br>

#### <p align=center> For the full roadmap, please consult [our wiki's changelog page](https://github.com/NerdyKyogre/Withers/wiki/Changelog).
