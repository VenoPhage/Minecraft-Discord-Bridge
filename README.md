# Minecraft Vanilla Discord Bridge Chat

This script runs completely remotely from a Minecraft server, making it perfect for dedicated servers, or even when you're just running vanilla (especially great for snapshot servers).

## Setup (Note this script is not functional yet)

1. rename the config.example.toml to config.toml
2. edit the config.toml with settings for your server
3. install dependencies: `pip install -r requirements.txt` (recommended to run in a venv)
4. run the script: `python main.py` (should work with most python versions, developed on python 3.13.5)

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



  
