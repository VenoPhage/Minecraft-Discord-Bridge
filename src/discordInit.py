import discord, os


def discordInit(token):
    bot = discord.Bot(intents=discord.Intents.all())

    cog_list = [f[:-3] for f in os.listdir("./discordCogs") if f.endswith(".py")]

    for cog in cog_list:
        bot.load_extension(f"discordCogs.{cog}")

    @bot.event
    async def on_ready():
        print("Logged in as {0.user}".format(bot))
        await bot.sync_commands()
        print("Synced commands!")

    bot.run(token)
    return bot
