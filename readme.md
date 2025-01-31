# Withers

- [What is this?](#what-is-this)
- [Usage](#usage)
- [Running the Bot Yourself](#running-it-yourself)
- [Roadmap](#roadmap)


## What is this?
Withers is a discord bot written in python for the purpose of parsing PCPartPicker build lists and automatically posts them in an organized manner. This facilitates a more fluid and efficient approach to helping people craft the build of their dreams.

![Sample output](/examples/example-1.png?raw=true "Sample output")

## Usage

Using the bot is incredibly simple. All one must do is provide is provide the build list url in the channel as they would normally do. The bot will automatically parse and post the organized contents of the list immediately to the same channel the list was originally posted in. 


## Running it yourself 
- Install and configure Python 3.1x. This is a hard requirement (obviously, this is a python bot.)
- Clone this repo using your method of choice, then enter it:
    ```Sh
    git clone https://github.com/NerdyKyogre/Withers
    cd Withers
    ```
Next, it's *highly* recommended to create a venv (virtual python environment) to ensure code reproducability and avoid dependency contamination. If you are unsure how, read on:
- create a venv in the root of the repo as follows:
    ```Sh
    python -m venv ./.withers-venv
    ```
- Source the newly created venv:
    ```Sh
    source ./.withers-venv/bin/activate
    ```
Now you can interact with python regularly, with the newly created venv as the source of your python environment.
- Install the required dependencies from "requirements.txt"
    ```Sh
    pip install --no-cache-dir -r requirements.txt
    ```
- Run the bot
    ```Sh
    python ./withers.py
    ```
You're good to go!
<br>

**!NO ISSUES WILL BE RESPECTED IF ATTEMPTING TO RUN OUTSIDE A VENV!**



## Roadmap
- *TODO:*
  - Refactor for code efficiency
  - Integrate support for additional PC building site lists
  - Add client side latency/performance/load metrics
  - Implement sharding algorithm for better load balancing
  -  *and much more planned...*