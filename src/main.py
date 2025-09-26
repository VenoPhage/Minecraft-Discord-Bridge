import os, discord
import tomlkit as tk
from pathlib import Path

if os.path.exists("src"):
    os.chdir("src")
if not os.path.exists("main.py"):
    exit("main.py not found, check if you are in the correct directory")

if not os.path.exists("data"):
    os.makedirs("data")

try:
    with open("config.toml", "r") as f:
        cDoc = tk.parse(f.read())
except FileNotFoundError:
    cDoc = tk.document()  # file doesnt exist, so create one
except Exception as e:
    exit(
        f"Error reading or parsing config.toml, suggested fix rename config.toml and restart\nException:\n{e}"
    )

try:
    token = cDoc["Discord"]["Token"]
except:
    DCtab = tk.table()
    DCtab.add("Token", "")
    DCtab["Token"].comment("Required")
    cDoc["Discord"] = DCtab
    token = None

if token == None:
    token = input("Enter Discord bot Token:")
    cDoc["Discord"]["Token"] = token
    with open("config.toml", "w") as f:
        f.write(tk.dumps(cDoc))


bot = discord.Bot(intents=discord.Intents.all())
cog_list = [
    str(p.relative_to(Path("./discordCogs")).with_suffix("")).replace("/", ".")
    for p in Path("./discordCogs").rglob("*.py")
]
for cog in cog_list:
    bot.load_extension(f"discordCogs.{cog}")
bot.run(token)
