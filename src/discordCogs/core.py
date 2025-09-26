import discord, sqlite3
import tomlkit as tk
from discord.ext import commands
from pathlib import Path


class core(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    def get_all_cogs():
        cog_list = [
            str(p.relative_to(Path("./discordCogs")).with_suffix("")).replace("/", ".")
            for p in Path("./discordCogs").rglob("*.py")
        ]
        return cog_list

    @discord.slash_command()
    @discord.is_owner
    @discord.option("cog", choices=get_all_cogs().pop("core"))
    async def unload(self, ctx, cog: str):
        try:
            self.bot.unload_extension(cog)
        except Exception as e:
            await ctx.respond(f"Failed to unload {cog}\nReason:\n{e}")
            return
        await ctx.respond(f"Unloaded {cog}")

    @discord.slash_command()
    @discord.is_owner
    @discord.option("cog", choices=get_all_cogs())
    async def reload(self, ctx, cog: str):
        try:
            discord.bot.reload_extension(cog)
        except Exception as e:
            await ctx.respond(f"Failed to reload {cog}\nReason:\n{e}")
            return
        ctx.respond(f"Reloaded {cog}")

    @discord.slash_command()
    @discord.is_owner
    @discord.option("cog", choices=get_all_cogs().pop("core"))
    async def load(self, ctx, *cog: str):
        try:
            self.bot.load_extension(cog)
        except Exception as e:
            await ctx.respond(f"Failed to load {cog}\nException:\n{e}")
            return
        await ctx.respond(f"Loaded {cog}")

    @discord.slash_command()
    @discord.is_owner
    async def list_cogs(ctx):
        message = ""
        for cog in core.get_all_cogs():
            message.append(f"{cog}\n")
        await ctx.reply(message)


def setup(bot):
    bot.add_cog(core(bot))
