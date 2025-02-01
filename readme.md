# <p align=center> Withers

- [What is this?](#what-is-this)
- [Usage](#usage)
- [Deploying Yourself](#deploying-yourself)
- [Roadmap](#roadmap)


## What is this?
Withers is a discord bot written in Python for the purpose of parsing PCPartPicker (and eventually other) build lists and automatically posting them in an organized manner. This facilitates a more fluid and efficient approach to helping people craft the build of their dreams.


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

- Finally, run the bot
    ```Sh
    python ./withers.py
    ```
### <p align=center> That's it, you're good to go!

## Roadmap
- *TODO:*
  - Integrate support for additional PC building site lists
  - Add client side latency/performance/load metrics
  - Implement sharding algorithm for better load balancing
  -  *and much, much more planned...*