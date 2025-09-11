import discord, toml
from discord.ext import commands
from utils.functions import functions as utils
from mcrcon import MCRcon

class minecraft(commands.Cog): # create a class for our cog that inherits from commands.Cog
    # this class is used to create a cog, which is a module that can be added to the bot

    def __init__(self, bot): # this is a special method that is called when the cog is loaded
        self.bot = bot

    @discord.slash_command() # we can also add application commands
    async def list(self, ctx):
        with open ('config.toml') as f:
            config = toml.load(f)
        rcon_ip = config['minecraft']['rcon_ip']
        rcon_port = config['minecraft']['rcon_port']
        rcon_pass = config['minecraft']['rcon_password']
        with MCRcon(f'{rcon_ip}:{rcon_port}', rcon_port, rcon_pass) as mcr:
            list = mcr.command('list')
        
        await ctx.respond(list)

def setup(bot): # this is called by Pycord to setup the cog
    bot.add_cog(minecraft(bot)) # add the cog to the bot