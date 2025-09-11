import toml, os
from discordInit import *


if os.path.exists('src'):
    os.chdir('src')
if not os.path.exists('main.py'):
    exit("main.py not found, check if you are in the correct directory")

with open('config.toml') as f:
    config = toml.load(f)

match config['version']:
    case '0':
        pass # config updating will happen once things are functional
    case _:
        exit(f"Unknown version {config['version']}")

bot = discordInit(config['discord']['token'])
    
