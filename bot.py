import os
import asyncio
import logging
import aiohttp
import discord
from discord.ext import tasks

# Logging setup
logging.basicConfig(level=logging.INFO)

# Discord setup
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", "0"))

intents = discord.Intents.default()
client = discord.Client(intents=intents)

# Players to track
PLAYERS = ["GIM Mythy", "GIM Seedpsoon"]

# RuneMetrics API URL
API_URL = "https://apps.runescape.com/runemetrics/profile/profile?user={}&activities=20"

# Track last seen events to avoid duplicates
last_seen = {player: set() for player in PLAYERS}


# -------- Message Formatters --------
def format_level_message(player, skill, level):
    return f"🎉 {player} just reached **level {level}** in **{skill}**!"


def format_drop_message(player, drop_text):
    return f"💎 {player} just received a rare drop: **{drop_text}**!"


# -------- Fetch RuneMetrics --------
async def fetch_activities(player):
    url = API_URL.format(player.replace(" ", "%20"))
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as resp:
                if resp.status != 200:
                    logging.error(f"Failed to fetch {player}: HTTP {resp.status}")
                    return []
                data = await resp.json()
                return data.get("activities", [])
        except Exception as e:
            logging.error(f"Error fetching {player}: {e}")
            return []


# -------- Check Updates --------
async def check_updates():
    channel = client.get_channel(CHANNEL_ID)
    if not channel:
        logging.error("Channel not found. Check DISCORD_CHANNEL_ID.")
        return

    for player in PLAYERS:
        activities = await fetch_activities(player)

        for act in activities:
            text = act.get("text", "").strip()
            if not text or text in last_seen[player]:
                continue

            message = None

            # ✅ Legit level-up
            if text.startswith("Reached level") and "in" in text:
                try:
                    parts = text.split(" ")
                    level = parts[2]
                    skill = parts[-1].replace(".", "")
                    message = format_level_message(player, skill, level)
                except Exception as e:
                    logging.error(f"Failed to parse level-up: {text} ({e})")

            # ✅ Legit rare drop
            elif text.lower().startswith("received a rare drop:"):
                try:
                    drop_text = text.split("rare drop: ")[-1].strip().replace(".", "")
                    message = format_drop_message(player, drop_text)
                except Exception as e:
                    logging.error(f"Failed to parse drop: {text} ({e})")

            if message:
                await channel.send(message)
                logging.info(f"Posted: {message}")

            # Mark as seen
            last_seen[player].add(text)


# -------- Task Loop --------
@tasks.loop(minutes=1)
async def run_check():
    await check_updates()


@client.event
async def on_ready():
    logging.info(f"Logged in as {client.user}")
    run_check.start()


# -------- Start Bot --------
if __name__ == "__main__":
    if not TOKEN or CHANNEL_ID == 0:
        logging.error("Missing DISCORD_TOKEN or DISCORD_CHANNEL_ID in environment.")
    else:
        client.run(TOKEN)


