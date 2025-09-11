import toml, os
from discordInit import *


if os.path.exists('src'):
    os.chdir('src')
if not os.path.exists('main.py'):
    exit("main.py not found, check if you are in the correct directory")
try:
    with open('config.toml') as f:
        config = toml.load(f)
except FileNotFoundError:
    config = {"version": -1}
    with open('config.toml', 'w') as f:
        f.write(toml.dumps(config))


match config['version']:
    case 0:
        pass 
    case _:
        toml_string = """version = 0 # DO NOT CHANGE

[minecraft]
host = '127.0.0.1' #default: 127.0.0.1
chat_method_get = 'sftp' #for getting messages from minecraft. Options: 'sftp', 'management_server' (maybe)
chat_method_send = 'rcon' #for sending messages to minecraft. Options: 'rcon', 'management_server' (maybe)

[minecraft.management_server]
host = '0' #default: 0 (0 uses minecraft host)
port = 25585 #default: 25585
secret = ''

[minecraft.sftp]
host = '' #default: 0 (0 uses minecraft host)
port = 22 #default: 22
username = ''
password = ''

[minecraft.rcon]
host = '0' #default: 0 (0 uses minecraft host)
port = 25575 #default: 25575
password = ''

[discord]
use_webhook = true #default: true
token = ''  #required
channel_id = '' #required
webhook_url = '' #required if use_webhook is true  
"""
        with open('config.toml', 'w') as f:
            f.write(toml_string)
        exit("config.toml created, please edit it and run the script again")

discordInit(config['discord']['token'])
    
