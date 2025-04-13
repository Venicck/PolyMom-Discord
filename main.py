import discord, os
from discord.ext import commands, tasks

# 初期変数
TOKEN = ""

bot = commands.Bot(command_prefix="+", intents=discord.Intents.all(), help_command=None)

@bot.event
def on_ready():
    print("Bot is ready!")


TOKEN = os.getenv("DISCORD_TOKEN")
Bot.run(TOKEN)