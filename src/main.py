import toml, os
from discordInit import *



if os.path.exists('src'):
    os.chdir('src')
if not os.path.exists('main.py'):
    exit("main.py not found, check if you are in the correct directory")

with open('config.toml') as f:
    config = toml.load(f)


if config['discord']['use_webhook'] == False:
    bot = discordInit(config['discord']['token'])
    
