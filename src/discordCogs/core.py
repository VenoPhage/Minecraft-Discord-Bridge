import discord
from discord.ext import commands
import utils.functions as func
from discord.commands import Option, OptionChoice
from utils.exception import *


class core(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{self.bot.user} is ready and online!")

    owner = discord.SlashCommandGroup("owner", guild_ids=[1413909321326268457])

    @owner.command()
    @commands.is_owner()
    async def shutdown(self, ctx):
        await ctx.respond("Shuting down...")
        await self.bot.close()

    @owner.command()
    @commands.is_owner()
    async def unload(
        self,
        ctx,
        cog: str = Option(
            description="Select a cog to unload",
            choices=[
                OptionChoice(name=cog) for cog in func.get_all_cogs()
            ],  # Ensure this list is not empty
        ),
    ):
        try:
            self.bot.unload_extension(f"discordCogs.{cog}")
        except Exception as e:
            await ctx.respond(f"Failed to unload {cog}\nReason:\n{e}")
        else:
            await ctx.respond(f"Unloaded {cog}")

    @owner.command()
    @commands.is_owner()
    async def reload(
        self,
        ctx,
        cog: str = Option(
            description="Select a cog to reload",
            choices=[OptionChoice(name=cog) for cog in func.get_all_cogs()],
        ),
    ):
        try:
            self.bot.reload_extension(f"discordCogs.{cog}")
        except SetupError as e:
            await ctx.respond(f"Failed to reload (setup) {cog}\nReason:\n{e}")
        except Exception as e:
            await ctx.respond(f"Failed to reload {cog}\nReason:\n{e}")
        else:
            await ctx.respond(f"Reloaded {cog}")

    @owner.command()
    @commands.is_owner()
    async def load(
        self,
        ctx,
        cog: str = Option(
            description="Select a cog to load",
            choices=[OptionChoice(name=cog) for cog in func.get_all_cogs()],
        ),
    ):
        try:
            self.bot.load_extension(f"discordCogs.{cog}")
        except SetupError as e:
            await ctx.respond(f"Failed to reload (setup) {cog}\nReason:\n{e}")
        except Exception as e:
            await ctx.respond(f"Failed to load {cog}\nException:\n{e}")
        else:
            await ctx.respond(f"Loaded {cog}")

    @owner.command()
    @commands.is_owner()
    async def list_cogs(self, ctx):
        message = " ".join(func.get_all_cogs())
        await ctx.respond(message)

    @owner.command(name="sync_commands")
    @commands.is_owner()
    async def sync_commands(self, ctx):
        await self.bot.sync_commands()
        await ctx.respond("commands synced")

    enable = discord.SlashCommandGroup("enable-minecraft")

    @enable.command(name="updater")
    async def enable_updater(self, ctx, mode: bool):
        if mode == False:
            func.conf_add(ctx.guild.id, ["Minecraft"], "updater-enabled", False)
            await ctx.respond("Updater disabled")
            return
        try:
            api = func.conf_get(
                server_id=ctx.guild.id,
                keys=["Minecraft", "panel"],
            )
        except:
            await ctx.respond(
                "Cannot enable updater without panel config.\nRun `/setup-minecraft panel`"
            )
        if api is None:
            return
        func.conf_add(ctx.guild.id, ["Minecraft"], "updater-enabled", True)
        await ctx.respond("Updater enabled!")

    @enable.command(name="chat")
    async def enable_chat(self, ctx, mode: bool, chat_channel: discord.TextChannel):
        if mode:
            if chat_channel is None:
                await ctx.respond(
                    "Please select a channel for messages to be sent and received from"
                )
                return
        else:
            func.conf_add(ctx.guild.id, ["Minecraft"], "updater-enabled", False)
            await ctx.respond("Updater disabled")
            return

        sftp = func.conf_get(
            server_id=ctx.guild.id,
            keys=["Minecraft", "sftp"],
        )
        sftp_command = self.bot.get_application_command("setup-minecraft sftp")
        if sftp == None:
            await ctx.respond(
                f"Cannot enable updater without panel config.\nRun {sftp_command.mention}"
            )
            return

        rcon = func.conf_get(
            server_id=ctx.guild.id,
            keys=["Minecraft", "rcon"],
        )
        rcon_command = self.bot.get_application_command("setup-minecraft rcon")
        if rcon == None:
            await ctx.respond(
                f"Cannot enable updater without panel config.\nRun {rcon_command.mention}"
            )
            return

        func.conf_add(ctx.guild.id, ["Minecraft"], "chat-enabled", True)
        func.conf_add(ctx.guild.id["Minecraft"], "chat_channel_id", chat_channel.id)
        await ctx.respond("Chat enabled!")

    setup = discord.SlashCommandGroup("setup-minecraft")

    @setup.command(name="panel")
    async def setup_panel(self, ctx):
        rq_pages = [True, False]
        title = "Panel Ino"
        descriptions = [""]
        pages = [
            [
                {"name": "Server ID"},
                {"name": "base url"},
                {"name": "api key"},
            ],
        ]
        m = func.modal(
            title,
            pages,
            descs=descriptions,
            page_required=rq_pages,
            confirm_msg="**Optional**: Configure {desc}?",
        )
        await ctx.send_modal(m)
        data = await m.wait_until_done()
        for key, value in data.items():
            func.conf_add(ctx.guild.id, ["Minecraft", "panel"], key, value)

        await ctx.respond("Info Collected :)")

    @setup.command(name="management-server")
    async def setup_management(self, ctx):
        rq_pages = [True, False]
        title = "Management Server"
        descriptions = ["", "TLS"]
        pages = [
            [
                {"name": "Numerical IP"},
                {"name": "Port", "default": 25585},
                {"name": "Secret"},
            ],
            [{"name": "TLS Keystore"}, {"name": "Keystore Password"}],
        ]
        m = func.modal(
            title,
            pages,
            descs=descriptions,
            page_required=rq_pages,
            confirm_msg="**Optional**: Configure {desc}?",
        )
        await ctx.send_modal(m)
        data = await m.wait_until_done()
        for key, value in data.items():
            func.conf_add(ctx.guild.id, ["Minecraft", "panel"], key, value)
        await ctx.respond("Info Collected :)")

    @setup.command(name="rcon")
    async def setup_rcon(self, ctx):
        rq_pages = [True]
        title = "RCON Info"
        descriptions = [""]
        pages = [
            [
                {"name": "RCON Port", "default": 25575},
                {"name": "RCON Password"},
            ]
        ]
        m = func.modal(
            title,
            pages,
            descs=descriptions,
            page_required=rq_pages,
            confirm_msg="**Optional**: Configure {desc}?",
        )
        await ctx.send_modal(m)
        data = await m.wait_until_done()

        for key, value in data.items():
            func.conf_add(ctx.guild.id, ["Minecraft", "panel"], key, value)
        await ctx.respond("Info Collected :)")

    @setup.command(name="server")
    async def setup_rcon(self, ctx):
        rq_pages = [True]
        title = "Minecraft Server"
        descriptions = [""]
        pages = [
            [
                {"name": "Numerical IP"},
                {"name": "Port", "default": 25585},
            ]
        ]

        m = func.modal(
            title,
            pages,
            descs=descriptions,
            page_required=rq_pages,
            confirm_msg="**Optional**: Configure {desc}?",
        )
        await ctx.send_modal(m)
        data = await m.wait_until_done()

        for key, value in data.items():
            func.conf_add(ctx.guild.id, ["Minecraft", "panel"], key, value)
        await ctx.respond("Info Collected :)")


def setup(bot):
    bot.add_cog(core(bot))
