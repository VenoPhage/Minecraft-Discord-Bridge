# Minecraft Vanilla Discord Bridge Chat
This script runs completely remotely from a Minecraft server, making it perfect for dedicated servers, or even when you're just running vanilla (especially great for snapshot servers).

## Requirements
- Python 3.10.11

## Setup
1. install dependencies: `pip install -r requirements.txt` (recommended to run in a venv)
2. run the script `python main.py` this will create the `config.toml` file and stop the script
3. edit the new `config.toml` file
4. run the script again `python main.py` (this is now your startup command)

## Features
- [X] Bridge Chat
    - [ ] Management server
        - [ ] Secure connection
        - [ ] Receiving Minecraft events
    - [X] RCon server
        - [X] Sending messages to Minecraft 

- [X] Discord
    - [X] Commands
        - [ ] /map
            - [ ] research options
        - [X] /List 
            - [x] Running command
            - [ ] Formatting
    - [ ] Whitelisting members
        - [ ] Trusted members whitelisting

