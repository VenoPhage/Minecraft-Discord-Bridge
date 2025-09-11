# Minecraft Vanilla Discord Bridge Chat
This script runs completely remotely from a Minecraft server, making it perfect for dedicated servers, or even when you're just running vanilla (especially great for snapshot servers).

## Setup
1. install dependencies: `pip install -r requirements.txt` (recommended to run in a venv)
2. run the script `python main.py` this will create the `config.toml` file and stop the script
3. edit the new `config.toml` file
4. run the script again `python main.py` (this is now your startup command)

## Features
No features fully complete yet

## Planned Features (in no particular order)
- [ ] Management server
    - [ ] Secure connection
    - [ ] Receiving Minecraft messages
    - [ ] Sending messages to Minecraft (maybe RCon might be better?)

- [ ] RCon server
    - [ ] Sending messages to Minecraft 

- [ ] Discord
    - [ ] /List command
        - [x] Running command
        - [ ] Formatting
    - [ ] Whitelisting members
        - [ ] Trusted members whitelisting



  
