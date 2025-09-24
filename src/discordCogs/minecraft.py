import discord, toml, paramiko, re, os, json, hashlib
from discord.ext import commands, tasks
from mcrcon import MCRcon
from utils.functions import getRconConfig, getSFTPConfig
from discord import Webhook
import aiohttp, requests


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

        if not os.path.exists("data"):
            os.makedirs("data")

        self.message_tracker = MinecraftLogProcessor()
        self.fetchLogsLoop.start()
        self.checkServerUpdates.start()

    @discord.slash_command()
    async def list(self, ctx):
        rcon = getRconConfig()
        with MCRcon(rcon["host"], rcon["password"], rcon["port"]) as mcr:
            list = mcr.command("list")

        await ctx.respond(list)

    @discord.slash_command(
        name="resync",
        description="[OWNER ONLY] resyncs the channel. (currently only deletes and recreates the channel)",
    )
    @commands.is_owner()
    async def resync(self, ctx):
        # delete and recreate channel and fetch all logs
        self.fetchLogsLoop.stop()
        with open("config.toml") as f:
            config = toml.load(f)
        oldChannel = self.bot.get_channel(config["discord"]["channel_id"])

        newChannel = await ctx.guild.create_text_channel(
            name=oldChannel.name,
            overwrites=oldChannel.overwrites,
            category=oldChannel.category,
            position=oldChannel.position,
            topic=oldChannel.topic,
            slowmode_delay=oldChannel.slowmode_delay,
            nsfw=oldChannel.nsfw,
            reason="resync",
        )
        await oldChannel.delete(reason="resync")

        config["discord"]["channel_id"] = newChannel.id
        with open("config.toml", "w") as f:
            f.write(toml.dumps(config))

        self.fetchLogsLoop.start()
        await ctx.respond("resynced")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return

        with open("config.toml") as f:
            config = toml.load(f)

        if int(config["discord"]["channel_id"]) != message.channel.id:
            return

        rconConf = getRconConfig()

        with MCRcon(rconConf["host"], rconConf["password"], rconConf["port"]) as mcr:
            mcr.command(
                f'tellraw @a {{text:"[DISCORD] <{message.author.name}> {message.content}"}}'
            )

    @tasks.loop(hours=1)
    async def checkServerUpdates():
        with open("data/currentVersion.txt") as f:
            currentVersion = f.read()
        versionsURL = "https://launchermeta.mojang.com/mc/game/version_manifest.json"
        versionsManifest = requests.get(versionsURL).json()
        if versionsManifest["versions"][0]["id"] == currentVersion:
            return
        latestURL = versionsManifest["versions"][0]["url"]
        snapshotManifest = requests.get(latestURL).json()
        serverDownloadURL = snapshotManifest["downloads"]["server"]["url"]
        server = requests.get(serverDownloadURL).content
        with open("server.jar", "wb") as f:
            f.write(server)

        rconConf = getRconConfig()

        with MCRcon(rconConf["host"], rconConf["password"], rconConf["port"]) as mcr:
            mcr.command("stop")

        sftpConf = getSFTPConfig()

        with paramiko.SSHClient() as ssh:
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                sftpConf["host"],
                username=sftpConf["username"],
                password=sftpConf["password"],
                port=sftpConf["port"],
            )
            with ssh.open_sftp() as sftp:
                sftp.put("server.jar", "server.jar")

        with MCRcon(rconConf["host"], rconConf["password"], rconConf["port"]) as mcr:
            mcr.command("start")

        # save current installed version
        currentVersion = snapshotManifest["id"]
        with open("data/currentVersion.txt", "w") as f:
            f.write(str(currentVersion))
        # delete old server.jar
        os.remove("server.jar")

    @tasks.loop(seconds=1)
    async def fetchLogsLoop(self):
        rconConf = getRconConfig()

        # check for players online
        with MCRcon(rconConf["host"], rconConf["password"], rconConf["port"]) as mcr:
            listOutput = mcr.command("list")
            playerCount = re.search(r"\d+", listOutput).group(0)
        if playerCount == "0":
            return  # no players online so no need to look for messages

        sftpConf = getSFTPConfig()

        # fetch latest log
        try:
            with paramiko.SSHClient() as ssh:
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(
                    sftpConf["host"],
                    username=sftpConf["username"],
                    password=sftpConf["password"],
                    port=sftpConf["port"],
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

        with open("config.toml") as f:
            config = toml.load(f)

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

        for timestamp, username, message, message_hash in new_messages:
            try:
                if config["discord"]["use_webhook"] == True:
                    async with aiohttp.ClientSession() as session:
                        webhook = Webhook.from_url(
                            config["discord"]["webhook_url"], session=session
                        )
                        await webhook.send(
                            content=message,
                            username=username,
                            avatar_url=f"https://minotar.net/avatar/{username}/100.png",
                        )
                else:
                    channel = self.bot.get_channel(config["discord"]["channel_id"])
                    await channel.send(f"{username}: {message}")
            except Exception as e:
                print(f"Error sending message: {e}")


def setup(bot):

    bot.add_cog(minecraft(bot))
