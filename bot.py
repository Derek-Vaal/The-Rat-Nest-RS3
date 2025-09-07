import discord
from discord.ext import tasks
import aiohttp
import asyncio
import os
import json
import logging
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] %(message)s')

# Discord intents
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Load settings
TOKEN = os.getenv("DISCORD_TOKEN")
INTERVAL = int(os.getenv("CHECK_INTERVAL", "300"))  # default = 300s
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))

# Load tracked players
with open("tracked_players.json", "r") as f:
    tracked_data = json.load(f)
    TRACKED_PLAYERS = tracked_data.get("players", [])

# Skill emojis
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

# In-memory db
db = {"seen_events": {}}

def format_level_message(rsn, skill, level):
    emoji = SKILL_EMOJIS.get(skill, "🎉")
    return f"{emoji} **{rsn}** just reached level {level} in **{skill}**!"

def format_drop_message(rsn, item, quantity):
    return f"💎 **{rsn}** just received a rare drop: {quantity} x **{item}**!"

@tasks.loop(seconds=INTERVAL)
async def check_updates():
    await client.wait_until_ready()
    logging.info("Running update check...")

    for player in TRACKED_PLAYERS:
        logging.info(f"Checking RuneMetrics for {player}...")

        # TODO: Replace with actual RuneMetrics API call
        # For now we just use a dummy event to test posting
        sample_events = [
            {"rsn": player, "type": "levelup", "skill": "Construction", "level": 85},
            {"rsn": player, "type": "drop", "item": "Armadyl Godsword", "quantity": 1}
        ]

        for event in sample_events:
            rsn = event["rsn"]
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

                logging.info(f"Sending message: {message}")

                if CHANNEL_ID != 0:
                    channel = client.get_channel(CHANNEL_ID)
                    if channel:
                        await channel.send(message)
                    else:
                        logging.warning(f"Channel ID {CHANNEL_ID} not found!")

@client.event
async def on_ready():
    logging.info(f"✅ Logged in as {client.user}")
    check_updates.start()

if TOKEN:
    client.run(TOKEN)
else:
    logging.error("❌ DISCORD_TOKEN not set in environment variables!")



