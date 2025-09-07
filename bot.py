import os
import asyncio
import discord
from discord.ext import commands, tasks

# ----------------------
# Intents setup
# ----------------------
intents = discord.Intents.default()
intents.message_content = True  # Needed if reading messages

# ----------------------
# Bot setup
# ----------------------
bot = commands.Bot(command_prefix="!", intents=intents)

# ----------------------
# Get token from Railway environment variable
# ----------------------
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN or len(TOKEN) < 50:
    raise ValueError(
        "DISCORD_TOKEN is missing or invalid! "
        "Please add your bot token in Railway settings under Environment Variables."
    )

# ----------------------
# RS3 notification config
# ----------------------
CHECK_INTERVAL = 20 * 60  # 20 minutes
# Map event types to Discord channels (adjust as needed)
EVENT_CHANNELS = {
    "general": 123456789012345678,  # Replace with your channel ID
}

# ----------------------
# Example v1.3-style RS3 data fetching
# ----------------------
async def fetch_rs3_updates():
    """
    Replace this function with your old v1.3 logic.
    For example, scrape RS3 website, parse feed, or check in-game events.
    Return a dictionary mapping event_type -> list of messages.
    """
    # Example mock data
    updates = {
        "general": [
            "RS3 Event: Boss X has spawned!",
            "RS3 Event: Minigame Y is live!"
        ]
    }
    return updates

# ----------------------
# Background task: send notifications
# ----------------------
@tasks.loop(seconds=CHECK_INTERVAL)
async def rs3_notifications_task():
    await bot.wait_until_ready()
    updates = await fetch_rs3_updates()
    for event_type, messages in updates.items():
        channel_id = EVENT_CHANNELS.get(event_type)
        if not channel_id:
            print(f"No channel configured for event type '{event_type}'")
            continue
        channel = bot.get_channel(channel_id)
        if not channel:
            print(f"Channel ID {channel_id} not found")
            continue
        for msg in messages:
            await channel.send(msg)

# ----------------------
# Event: bot ready
# ----------------------
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}!')
    if not rs3_notifications_task.is_running():
        rs3_notifications_task.start()

# ----------------------
# Example command
# ----------------------
@bot.command()
async def hello(ctx):
    await ctx.send(f"Hello, {ctx.author.name}!")

# ----------------------
# Run the bot
# ----------------------
try:
    bot.run(TOKEN)
except discord.errors.LoginFailure:
    raise ValueError(
        "Failed to login: DISCORD_TOKEN is invalid. "
        "Double-check the token in Railway settings."
    )




