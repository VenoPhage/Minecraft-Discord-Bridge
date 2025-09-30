import os, discord
import utils.functions as func

if os.path.exists("src"):
    os.chdir("src")  # if running from base instead of source
if not os.path.exists("main.py"):
    exit(
        "main.py not found, check if you are in the correct directory"
    )  # if this doesn't exist running dir is bad

if not os.path.exists("data"):
    os.makedirs("data")  # not included in git so its created

try:
    cDoc = func.get_conf()
except FileNotFoundError:  # file doesnt exist, so create one
    with open("config.toml", "a"):
        pass
except Exception as e:
    exit(
        f"Error reading or parsing config.toml, suggested fix rename config.toml and restart\nException:\n{e}"
    )  # unknown error, just exit and allow user to diagnose

try:
    token = func.get_conf(keys=["Discord", "Token"])
except:
    token = input("Enter Discord bot Token:")
    func.conf_add(keys=["Discord"], name="Token", value=token, comment="Required")

bot = discord.Bot(intents=discord.Intents.all())

bot.load_extension("discordCogs.core")

try:
    bot.run(token)
except (TypeError, discord.LoginFailure):
    token = input("Enter Discord bot Token:")
    func.conf_add(keys=["Discord"], name="Token", value=token, comment="Required")
except Exception as e:
    exit(f"Unhandled exception\n{e}")
finally:
    bot.run(token)
