import discord, toml, paramiko, re, os, json, hashlib
from discord.ext import commands, tasks
from mcrcon import MCRcon
from discord import Webhook
import aiohttp, requests
import utils.functions as util
from utils.exception import *


class MinecraftLogProcessor:
    def __init__(self, state_file="data/log_state.json"):
        self.state_file = state_file
        self.processed_messages = set()
        self.load_state()

    def load_state(self):
        """Load the processing state from file"""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r") as f:
                    data = json.load(f)
                    self.processed_messages = set(data.get("processed_messages", []))
            except:
                self.processed_messages = set()

    def save_state(self):
        """Save the current processing state to file"""
        with open(self.state_file, "w") as f:
            json.dump({"processed_messages": list(self.processed_messages)}, f)

    def add_message(self, message_hash):
        """Add a message hash to the processed set"""
        self.processed_messages.add(message_hash)
        self.save_state()

    def has_message(self, message_hash):
        """Check if a message hash has been processed"""
        return message_hash in self.processed_messages


class minecraft(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.message_tracker = MinecraftLogProcessor()
        self.checkServerUpdates.start()

    @discord.slash_command()
    async def list(self, ctx):
        rcon = util.get_conf(["Minecraft", "rcon"])
        if rcon is None:  # TODO check for other configs
            return
        with MCRcon(rcon["host"], rcon["password"], rcon["port"]) as mcr:
            list = mcr.command("list")

        await ctx.respond(list)

    ### TODO Update to new config
    # @discord.slash_command(
    #    name="resync",
    #    description="[OWNER ONLY] resyncs the channel. (currently only deletes and recreates the channel)",
    # )
    # @commands.is_owner()
    # async def resync(self, ctx):
    #    # delete and recreate channel and fetch all logs
    #    self.fetchLogsLoop.stop()
    #    with open("config.toml") as f:
    #        config = toml.load(f)
    #    oldChannel = self.bot.get_channel(config["discord"]["channel_id"])
    #
    #    newChannel = await ctx.guild.create_text_channel(
    #        name=oldChannel.name,
    #        overwrites=oldChannel.overwrites,
    #        category=oldChannel.category,
    #        position=oldChannel.position,
    #        topic=oldChannel.topic,
    #        slowmode_delay=oldChannel.slowmode_delay,
    #        nsfw=oldChannel.nsfw,
    #        reason="resync",
    #    )
    #    await oldChannel.delete(reason="resync")
    #
    #    config["discord"]["channel_id"] = newChannel.id
    #    with open("config.toml", "w") as f:
    #        f.write(toml.dumps(config))
    #
    #    self.fetchLogsLoop.start()
    #    await ctx.respond("resynced")

    @discord.slash_command()
    @commands.is_owner()
    async def update(self, ctx):
        self.checkServerUpdates
        await ctx.respond("Checking for updates...")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return
        rcon = util.get_conf(["Minecraft", "rcon"])
        if rcon is None:
            return

        with MCRcon(rcon["host"], rcon["password"], rcon["port"]) as mcr:
            mcr.command(
                f'tellraw @a {{text:"[DISCORD] <{message.author.name}> {message.content}"}}'
            )

    @tasks.loop(hours=1)
    async def checkServerUpdates(self):  # TODO Cut down function
        print("Checking for updates...")
        try:
            with open("data/currentVersion.txt") as f:
                currentVersion = f.read()
        except:
            currentVersion = None
        print(f"Current version is {currentVersion}")
        versionsURL = "https://launchermeta.mojang.com/mc/game/version_manifest.json"
        versionsManifest = requests.get(versionsURL).json()
        latestVersion = versionsManifest["versions"][0]["id"]
        if latestVersion == currentVersion:
            return
        print(f"Current version doesnt match latest {latestVersion}")
        latestURL = versionsManifest["versions"][0]["url"]
        snapshotManifest = requests.get(latestURL).json()
        serverDownloadURL = snapshotManifest["downloads"]["server"]["url"]
        server = requests.get(serverDownloadURL).content
        with open("server.jar", "wb") as f:
            f.write(server)

        rcon = util.get_conf(["Minecraft", "rcon"])
        if rcon is None:
            return
        print("ensuring server is offline")
        try:
            with MCRcon(rcon["host"], rcon["password"], rcon["port"]) as mcr:
                mcr.command("stop")
        except:
            pass  # server is probably offline already

        sftp = util.get_conf(["Minecraft", "sftp"])
        if sftp is None:
            return
        print("uploading new server.jar")
        with paramiko.SSHClient() as ssh:
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                sftp["host"],
                username=sftp["username"],
                password=sftp["password"],
                port=sftp["port"],
            )
            with ssh.open_sftp() as sftp:
                sftp.put("server.jar", "server.jar")

        print("Server jar uploaded attempting to start up server")
        api = util.get_conf(["Minecraft", "panel"])
        headers = {
            "Authorization": f"Bearer {api['api_key']}",
            "Content-Type": "application/json",
            "Accept": "Application/vnd.pterodactyl.v1+json",
        }

        response = requests.get(api["url"], headers=headers)
        print(response)

        power_url = f"{api['url']}/api/client/servers/{api['server_id']}/power"
        power_data = {"signal": "start"}

        power_response = requests.post(power_url, headers=headers, json=power_data)

        if power_response.status_code == 204:
            print("Server start command sent successfully!")
        else:
            print(f"Error: {power_response.status_code} - {power_response.text}")
        currentVersion = snapshotManifest["id"]
        with open("data/currentVersion.txt", "w") as f:
            f.write(str(currentVersion))
        os.remove("server.jar")

    @tasks.loop(seconds=1)
    async def fetchLogsLoop(self):
        rcon = util.get_conf(["Minecraft", "rcon"])
        if rcon is None:
            return

        # check for players online
        with MCRcon(rcon["host"], rcon["password"], rcon["port"]) as mcr:
            listOutput = mcr.command("list")
            playerCount = re.search(r"\d+", listOutput).group(0)
        if playerCount == "0":
            return  # no players online so no need to look for messages

        sftp = util.get_conf(["Minecraft", "sftp"])
        if sftp is None:
            return

        # fetch latest log
        try:
            with paramiko.SSHClient() as ssh:
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(
                    sftp["host"],
                    username=sftp["username"],
                    password=sftp["password"],
                    port=sftp["port"],
                )
                with ssh.open_sftp() as sftp:
                    sftp.get("logs/latest.log", "data/latest.log")
        except Exception as e:
            print(f"Failed to fetch logs: {e}")
            return

        if os.path.exists("data/lastPosition.txt"):
            with open("data/lastPosition.txt", "r") as f:
                last_pos = int(f.read().strip())
        else:
            last_pos = 0
        current_size = os.path.getsize("data/latest.log")
        if current_size < last_pos:
            last_pos = 0

            self.message_tracker.processed_messages = set()
            self.message_tracker.save_state()

        new_messages = []

        with open("data/latest.log", "r", encoding="utf-8", errors="ignore") as f:
            f.seek(last_pos)

            pattern = r"^\[(\d{2}:\d{2}:\d{2})\] \[.*?\]: <(\w+)> (.*)$"

            for line in f:
                match = re.match(pattern, line)
                if match:
                    timestamp, username, message = match.groups()

                    message_hash = hashlib.md5(
                        f"{timestamp}:{username}:{message}".encode()
                    ).hexdigest()

                    if not self.message_tracker.has_message(message_hash):
                        new_messages.append(
                            (timestamp, username, message, message_hash)
                        )
                        self.message_tracker.add_message(message_hash)

            # Save the new position
            with open("data/lastPosition.txt", "w") as pos_file:
                pos_file.write(str(f.tell()))

        discord = util.get_conf(["Discord"])
        if discord is None:
            return

        for timestamp, username, message, message_hash in new_messages:
            try:
                if discord["use_webhook"] == True:
                    async with aiohttp.ClientSession() as session:
                        webhook = Webhook.from_url(
                            discord["webhook_url"], session=session
                        )
                        await webhook.send(
                            content=message,
                            username=username,
                            avatar_url=f"https://minotar.net/avatar/{username}/100.png",
                        )
                else:
                    channel = self.bot.get_channel(discord["channel_id"])
                    await channel.send(f"{username}: {message}")
            except Exception as e:
                print(f"Error sending message: {e}")


def setup(bot):
    # try:
    #    mcConf = util.get_conf(["Minecraft"])
    # except KeyError:
    #    raise SetupError(
    #        "Minecraft config does not exist, please run `/setup minecraft`"
    #    )
    # else:
    bot.add_cog(minecraft(bot))
