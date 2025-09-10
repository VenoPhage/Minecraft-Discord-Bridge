import discord


def discordInit(token):
    bot = discord.Bot()
    bot.run(token)

    return bot