import discord, toml, pysftp, regex
from discord.ext import commands, tasks
from mcrcon import MCRcon
from utils.functions import getRconConfig, getSFTPConfig


class minecraft(commands.Cog): # create a class for our cog that inherits from commands.Cog
    # this class is used to create a cog, which is a module that can be added to the bot

    def __init__(self, bot): # this is a special method that is called when the cog is loaded
        self.bot = bot

    @discord.slash_command() # we can also add application commands
    async def list(self, ctx):
        rcon = getRconConfig()
        with MCRcon(rcon['host'], rcon['password'], rcon['port']) as mcr:
            list = mcr.command('list')
        
        
        await ctx.respond(list)

    
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return

        with open ('config.toml') as f:
            config = toml.load(f)
        if message.channel.id != config['discord']['channel_id']:
            return

        rconConf = getRconConfig()
        with MCRcon(rconConf['host'], rconConf['password'], rconConf['port']) as mcr:
            mcr.command(f'tell [DISCORD]{message.author.name}: {message.content}')


    @tasks.loop(seconds=5)
    async def fetchLogsLoop(self):
        sftpConf= getSFTPConfig()
        with pysftp.Connection(sftpConf['host'], username=sftpConf['username'], password=sftpConf['password'], port=sftpConf['port']) as sftp:
            with sftp.cd('logs') as f:
                with f.open('latest.log', 'r') as l:
                    for line in l:
                        match = regex.search(r'^ ]+]: <([^>]+)> (.*)$', line)
                        print(match)
                        # TODO send to discord with formatting, and fix the regex

def setup(bot): # this is called by Pycord to setup the cog
    bot.add_cog(minecraft(bot)) # add the cog to the bot