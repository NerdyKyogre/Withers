# <p align=center> Withers

- [What is this?](#what-is-this)
- [Usage](#usage)
- [Deploying Yourself](#deploying-yourself)
- [Roadmap](#roadmap)


## What is this?
Withers is a discord bot written in python for the purpose of parsing PCPartPicker (and eventually other) build lists automatically posting them in an organized manner. This facilitates a more fluid and efficient approach to helping people craft the build of their dreams.


## Usage

Using the bot is incredibly simple. All one must do is provide is provide the build list url in the channel as they would normally do. The bot will automatically parse and post the organized contents of the list immediately to the same channel the list was originally posted in. 

<p align=center> <img src="examples/example-1.png?raw=true" alt="Withers output example" style="width:695px;height:995px"/>



## Deploying Yourself 
- Install and configure ``Python 3.1x``. This is a **hard requirement** (obviously, this is a python bot.)
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
    <br>
Now you can interact with python regularly, with the newly created venv as the source of your python environment.
- Install the required dependencies from "requirements.txt"
    ```Sh
    pip install --no-cache-dir -r requirements.txt
    ```
- Run the bot
    ```Sh
    python ./withers.py
    ```
## <p align=center> That's it, you're good to go!
<br>
<br>

### <p align=center> Disclaimer:

### <p align=center> **NO ISSUES WILL BE ENTERTAINED IF ATTEMPTING TO RUN OUTSIDE A VENV**
<br>
<br>

## Roadmap
- *TODO:*
  - Refactor for code efficiency
  - Integrate support for additional PC building site lists
  - Add client side latency/performance/load metrics
  - Implement sharding algorithm for better load balancing
  -  *and much, much more planned...*