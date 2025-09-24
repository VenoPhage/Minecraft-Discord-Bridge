import toml, tomlkit, os
from discordInit import *

currentVersion = 1
base_toml_string = """version = 0 # DO NOT CHANGE

[minecraft]
host = '127.0.0.1' #default: 127.0.0.1
chat_method_get = 'sftp' #for getting messages from minecraft. Options: 'sftp', 'management_server' (maybe)
chat_method_send = 'rcon' #for sending messages to minecraft. Options: 'rcon', 'management_server' (maybe)

[minecraft.management_server]
host = '0' #default: 0 (0 uses minecraft host)
port = 25585 #default: 25585
secret = ''

[minecraft.sftp]
host = '0' #default: 0 (0 uses minecraft host)
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

if os.path.exists("src"):
    os.chdir("src")
if not os.path.exists("main.py"):
    exit("main.py not found, check if you are in the correct directory")

try:
    with open("config.toml", "r") as f:
        config = toml.loads(f.read())
except:
    with open("config.toml", "w") as f:
        f.write(base_toml_string)
    with open("config.toml", "r") as f:
        config = toml.loads(f.read())
if "version" not in config:
    with open("config.toml", "w") as f:
        f.write(base_toml_string)
    with open("config.toml", "r") as f:
        config = toml.loads(f.read())
while config["version"] != currentVersion:
    with open("config.toml", "r") as f:
        configDoc = tomlkit.parse(f.read())
    match configDoc["version"]:
        case 1:
            pass
        case 0:
            tab = tomlkit.table()
            tab.add("whitelist_role_id", 0)
            tab.add("waiting_channel_id", 0)
            tab.add("whitelist_manager_role_id", 0)
            tab.add(
                "waiting_message",
                "Hello {@user}! Please wait for a {@whitelist_role} to whitelist you.\nIf you want to speed up the process, click the button below.",
            )

            configDoc["discord.management"] = tab
            configDoc["version"] = 1

    with open("config.toml", "w") as f:
        f.write(tomlkit.dumps(configDoc))

if len(config["discord"]["token"]) < 10:
    exit("No token found in config.toml")
discordInit(config["discord"]["token"])
