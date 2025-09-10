import discord, os


def discordInit(token):
    bot = discord.Bot(intents=discord.Intents.all())
    bot.run(token)

    
    cog_list = [f[:-3] for f in os.listdir("./discordCogs") if f.endswith(".py")]
    
    for cog in cog_list:
        bot.load_extension(f"discordCogs.{cog}")
    
    @bot.event
    async def on_ready():
        print('We have logged in as {0.user}'.format(bot))

    return bot
