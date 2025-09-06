import discord
from discord.ext import tasks
import aiohttp
import asyncio
import os
import json
from datetime import datetime, timedelta

# Discord intents
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Load settings from environment variables
TOKEN = os.getenv("DISCORD_TOKEN")
INTERVAL = int(os.getenv("CHECK_INTERVAL", "300"))  # default = 300s (5 minutes)
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))  # optional, if you want to fix notifications to a single channel

# Skill emojis mapping (example, extend as needed)
SKILL_EMOJIS = {
    "Attack": "⚔️",
    "Strength": "💪",
    "Defence": "🛡️",
    "Ranged": "🏹",
    "Prayer": "🙏",
    "Magic": "✨",
    "Runecrafting": "🌀",
    "Construction": "🧱",
    "Dungeoneering": "🗝️",
    "Slayer": "🕷️",
    "Farming": "🌱",
    "Herblore": "🧪",
    "Mining": "⛏️",
    "Smithing": "⚒️",
    "Fishing": "🎣",
    "Cooking": "🍳",
    "Firemaking": "🔥",
    "Woodcutting": "🪓",
    "Agility": "🤸",
    "Thieving": "🕶️",
    "Fletching": "🏹",
    "Crafting": "🎨",
    "Hunter": "🐾",
    "Summoning": "🔮",
    "Divination": "🔷",
    "Invention": "💡",
    "Archaeology": "🏺"
}

# In-memory database
db = {
    "seen_events": {},
}

# Helper: Format level up message
def format_level_message(rsn, skill, level):
    emoji = SKILL_EMOJIS.get(skill, "🎉")
    return f"{emoji} **{rsn}** just reached level {level} in **{skill}**!"

# Helper: Format rare drop message
def format_drop_message(rsn, item, quantity):
    return f"💎 **{rsn}** just received a rare drop: {quantity} x **{item}**!"

# Background task
@tasks.loop(seconds=INTERVAL)
async def check_updates():
    await client.wait_until_ready()

    # (Dummy example – replace with your real RuneMetrics API logic)
    sample_events = [
        {"rsn": "GIM Mythy", "type": "levelup", "skill": "Construction", "level": 85},
        {"rsn": "GIM Mythy", "type": "drop", "item": "Armadyl Godsword", "quantity": 1}
    ]

    for event in sample_events:
        rsn = event["rsn"]

        # Initialize seen events store per RSN
        if rsn not in db["seen_events"]:
            db["seen_events"][rsn] = []

        unique_id = str(event)

        if unique_id not in db["seen_events"][rsn]:
            db["seen_events"][rsn].append(unique_id)

            if event["type"] == "levelup":
                message = format_level_message(rsn, event["skill"], event["level"])
            elif event["type"] == "drop":
                message = format_drop_message(rsn, event["item"], event["quantity"])
            else:
                continue

            # Send to channel
            if CHANNEL_ID != 0:
                channel = client.get_channel(CHANNEL_ID)
                if channel:
                    await channel.send(message)

# Events
@client.event
async def on_ready():
    print(f"✅ Logged in as {client.user}")
    check_updates.start()

# Run bot
if TOKEN:
    client.run(TOKEN)
else:
    print("❌ DISCORD_TOKEN not set in environment variables!")

