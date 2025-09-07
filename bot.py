import os
import json
import logging
import aiohttp
import discord
from discord.ext import tasks

# === Logging ===
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)-8s] %(message)s')

# === Load environment variables ===
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", 0))

# === Load tracked players ===
TRACKED_PLAYERS_FILE = "tracked_players.json"
if os.path.exists(TRACKED_PLAYERS_FILE):
    with open(TRACKED_PLAYERS_FILE, "r") as f:
        tracked_data = json.load(f)
        TRACKED_PLAYERS = tracked_data.get("players", [])
else:
    TRACKED_PLAYERS = []
    logging.warning("⚠️ No tracked_players.json found, starting with empty list")

# === Database of seen events (avoid duplicates) ===
DB_FILE = "db.json"
if os.path.exists(DB_FILE):
    with open(DB_FILE, "r") as f:
        db = json.load(f)
else:
    db = {"seen_events": {}}

def save_db():
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=4)

# === Discord client ===
intents = discord.Intents.default()
client = discord.Client(intents=intents)

# === Helper functions ===
async def fetch_runemetrics(rsn):
    url = f"https://apps.runescape.com/runemetrics/profile/profile?user={rsn}&activities=20"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                return await resp.json()
            else:
                logging.warning(f"RuneMetrics API returned {resp.status} for {rsn}")
                return None

def format_level_message(player, skill, level):
    return f"🧱 {player} just reached level {level} in {skill}!"

def format_drop_message(player, item, quantity):
    return f"💎 {player} just received a rare drop: {quantity} x {item}!"

# === Main update check ===
@tasks.loop(seconds=60)
async def check_updates():
    await client.wait_until_ready()
    logging.info("Running update check...")

    for player in TRACKED_PLAYERS:
        logging.info(f"Checking RuneMetrics for {player}...")
        data = await fetch_runemetrics(player)

        if not data or "activities" not in data:
            logging.warning(f"No activity data for {player}")
            continue

        for activity in data["activities"]:
            text = activity.get("text", "")
            date = activity.get("date", "")

            if not text or not date:
                continue

            # Unique event key
            unique_id = f"{player}-{date}-{text}"

            if player not in db["seen_events"]:
                db["seen_events"][player] = []

            if unique_id not in db["seen_events"][player]:
                db["seen_events"][player].append(unique_id)

                # Level-up
                if "level" in text and "in" in text:
                    try:
                        parts = text.split(" ")
                        level = parts[5]
                        skill = parts[-1]
                        message = format_level_message(player, skill, level)
                    except Exception as e:
                        logging.error(f"Failed to parse level-up message: {text} ({e})")
                        continue

                # Rare drop
                elif "rare drop" in text.lower():
                    try:
                        drop_text = text.split("rare drop: ")[-1]
                        quantity, item = drop_text.split(" x ")
                        message = format_drop_message(player, item, quantity)
                    except Exception as e:
                        logging.error(f"Failed to parse drop message: {text} ({e})")
                        continue

                else:
                    continue

                logging.info(f"Sending message: {message}")
                save_db()

                if CHANNEL_ID != 0:
                    channel = client.get_channel(CHANNEL_ID)
                    if channel:
                        await channel.send(message)
                    else:
                        logging.warning(f"Channel ID {CHANNEL_ID} not found!")

# === Bot events ===
@client.event
async def on_ready():
    logging.info(f"✅ Logged in as {client.user}")
    check_updates.start()

# === Run bot ===
if not TOKEN:
    logging.error("❌ Discord token not set. Make sure DISCORD_TOKEN is in environment variables.")
else:
    client.run(TOKEN)




