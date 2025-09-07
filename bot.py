import os
import discord
from discord.ext import commands

# ----------------------
# Intents setup
# ----------------------
intents = discord.Intents.default()
intents.message_content = True  # Required if reading message content

# ----------------------
# Bot setup
# ----------------------
bot = commands.Bot(command_prefix="!", intents=intents)

# ----------------------
# Event: bot ready
# ----------------------
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}!')

# ----------------------
# Example command
# ----------------------
@bot.command()
async def hello(ctx):
    await ctx.send(f"Hello, {ctx.author.name}!")

# ----------------------
# Get token from environment variable
# ----------------------
TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN is None:
    raise ValueError("DISCORD_TOKEN environment variable not set!")

# ----------------------
# Run the bot
# ----------------------
bot.run(TOKEN)


