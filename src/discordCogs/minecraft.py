import discord, os, json, aiohttp, paramiko, requests, hashlib, re
from discord.ext import commands, tasks
from mcrcon import MCRcon
import utils.functions as util
from utils.exception import *
from discord import Webhook


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
        try:
            rcon = util.conf_get(["Minecraft", "rcon"])
        except Exception as e:
            await ctx.respond("Rcon details missing")
            return
        with MCRcon(rcon["host"], rcon["password"], rcon["port"]) as mcr:
            list = mcr.command("list")

        await ctx.respond(list)

    admin = discord.SlashCommandGroup("mc-admin")

    @admin.command(
        name="resync",
        description="Resyncs the channel. (currently only deletes and recreates the channel)",
    )  # add command management
    async def resync(self, ctx):
        # delete and recreate channel and fetch all logs
        self.fetchLogsLoop.stop()
        discord = util.get_conf(["Discord"])
        oldChannel = self.bot.get_channel(discord["channel_id"])

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
        util.conf_add(["Discord"], "channel_id", newChannel.id)

        self.fetchLogsLoop.start()
        await ctx.respond("resynced")

    @discord.slash_command()
    @commands.is_owner()  # TODO: check if admin perm OR has staff role
    async def update(self, ctx):
        self.checkServerUpdates
        await ctx.respond("Checking for updates...")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return
        mc_conf = util.conf_get(message.guild.id, ["Minecraft"])
        if mc_conf["chat_enabled"] == False or None:
            return
        if message.channel.id != mc_conf["chat_channel_id"]:
            return

        rcon = util.conf_get(message.guild.id, ["Minecraft", "rcon"])
        if rcon is None:
            return

        with MCRcon(rcon["host"], rcon["password"], rcon["port"]) as mcr:
            mcr.command(
                f'tellraw @a {{text:"[DISCORD] <{message.author.name}> {message.content}"}}'
            )

    @tasks.loop(hours=1)
    async def checkServerUpdates(self):  # TODO Cut down function
        for guild in self.bot.guilds:
            try:
                is_enabled = util.conf_get(
                    guild.id, keys=["Minecraft", "updater_enabled"]
                )
            except:
                continue
            if not is_enabled:
                continue

            api = util.conf_get(guild.id, keys=["Minecraft", "panel"])
            headers = {
                "Authorization": f"Bearer {api['api_key']}",
                "Content-Type": "application/json",
                "Accept": "Application/vnd.pterodactyl.v1+json",
            }
            url = api["url"]
            response = requests.get(url, headers=headers)
            is_minecraft = response.json()["attributes"]["is_minecraft"]
            if not is_minecraft:
                continue
            mc_conf = util.conf_get(guild.id, keys=["Minecraft"])
            try:
                currentVersion = mc_conf["currentVersion"]
            except:
                currentVersion = None
            versionsURL = (
                "https://launchermeta.mojang.com/mc/game/version_manifest.json"
            )
            versionsManifest = requests.get(versionsURL).json()
            latestVersion = versionsManifest["versions"][0]["id"]
            if latestVersion == currentVersion:
                return
            latestURL = versionsManifest["versions"][0]["url"]
            snapshotManifest = requests.get(latestURL).json()
            serverDownloadURL = snapshotManifest["downloads"]["server"]["url"]
            server = requests.get(serverDownloadURL).content
            with open("server.jar", "wb") as f:
                f.write(server)
            power_url = f"{api['url']}/api/client/servers/{api['server_id']}/power"
            requests.post(power_url, headers=headers, json='{"signal": "stop"}')

            upload_url = (
                f"{api['url']}/api/client/servers/{api['server_id']}/files/upload"
            )
            response = requests.get(
                upload_url, headers=headers, params={"directory": "/"}
            )
            signed_url = response.json()["attributes"]["url"]

            with open("/server.jar", "rb") as f:
                files = {"files": f}
                data = {"directory": "/"}
                requests.post(signed_url, files=files, data=data)

            requests.post(power_url, headers=headers, json='{"signal": "start"}')

            currentVersion = snapshotManifest["id"]
            util.conf_add(
                guild.id,
                keys=["Minecraft"],
                name="currentVersion",
                value=currentVersion,
            )
            os.remove("server.jar")

    # REQUIRES RCON, SFTP
    @tasks.loop(seconds=1)
    async def fetchLogsLoop(self):
        for guild in self.bot.guilds:
            try:
                is_enabled = util.conf_get(guild.id, keys=["Minecraft", "chat_enabled"])
            except:
                continue
            if not is_enabled:
                continue
            rcon = util.conf_get(["Minecraft", "rcon"])
            if rcon is None:
                return

            # check for players online
            with MCRcon(rcon["host"], rcon["password"], rcon["port"]) as mcr:
                listOutput = mcr.command("list")
                playerCount = re.search(r"\d+", listOutput).group(0)
            if playerCount == "0":
                return  # no players online so no need to look for messages

            sftp = util.conf_get(["Minecraft", "sftp"])
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

            discord = util.conf_get(["Discord"])
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
    bot.add_cog(minecraft(bot))
