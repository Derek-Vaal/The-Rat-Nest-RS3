import discord
from discord.ext import tasks, commands
import aiohttp
import asyncio
import os
import json
from datetime import datetime, timedelta

# -----------------------------
# Discord bot setup
# -----------------------------
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

# Environment variables
TOKEN = os.getenv("DISCORD_TOKEN")
INTERVAL = int(os.getenv("CHECK_INTERVAL", "300"))
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))

# Skill emojis mapping
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

# -----------------------------
# Persistent storage
# -----------------------------
DB_FILE = "tracked_players.json"
EVENTS_FILE = "seen_events.json"

# Load tracked players
if os.path.exists(DB_FILE):
    with open(DB_FILE, "r") as f:
        db = json.load(f)
else:
    db = {"players": []}

# Load seen events
if os.path.exists(EVENTS_FILE):
    with open(EVENTS_FILE, "r") as f:
        seen_events = json.load(f)
else:
    seen_events = {}

# -----------------------------
# Helpers
# -----------------------------
def save_db():
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=2)

def save_events():
    with open(EVENTS_FILE, "w") as f:
        json.dump(seen_events, f, indent=2)

def format_level_message(rsn, skill, level):
    emoji = SKILL_EMOJIS.get(skill, "🎉")
    return f"{emoji} **{rsn}** just reached level {level} in **{skill}**!"

def format_drop_message(rsn, item, quantity):
    return f"💎 **{rsn}** just received a rare drop: {quantity} x **{item}**!"

# -----------------------------
# RuneMetrics API placeholder
# -----------------------------
async def fetch_player_events(rsn):
    # TODO: Replace this with real RuneMetrics API call
    # Example response structure:
    # [{"type": "levelup", "skill": "Construction", "level": 54}, {"type": "drop", "item": "Armadyl Godsword", "quantity": 1}]
    return []

# -----------------------------
# Background task
# -----------------------------
@tasks.loop(seconds=INTERVAL)
async def check_updates():
    await bot.wait_until_ready()
    channel = bot.get_channel(CHANNEL_ID) if CHANNEL_ID != 0 else None

    for rsn in db["players"]:
        events = await fetch_player_events(rsn)

        if rsn not in seen_events:
            seen_events[rsn] = []

        for event in events:
            unique_id = str(event)
            if unique_id not in seen_events[rsn]:
                seen_events[rsn].append(unique_id)
                save_events()

                # Format message
                if event["type"] == "levelup":
                    message = format_level_message(rsn, event["skill"], event["level"])
                elif event["type"] == "drop":
                    message = format_drop_message(rsn, event["item"], event["quantity"])
                else:
                    continue

                # Send message
                if channel:
                    await channel.send(message)

# -----------------------------
# Commands
# -----------------------------
@bot.command(name="track")
async def track(ctx, player: str):
    player = player.strip()
    if player in db["players"]:
        await ctx.send(f"⚠️ **{player}** is already being tracked.")
    else:
        db["players"].append(player)
        save_db()
        await ctx.send(f"✅ Now tracking **{player}**!")

@bot.command(name="tracked")
async def tracked(ctx):
    if not db["players"]:
        await ctx.send("No players are currently being tracked.")
    else:
        players_list = ", ".join(db["players"])
        await ctx.send(f"Currently tracking: {players_list}")

# -----------------------------
# Bot events
# -----------------------------
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    if not check_updates.is_running():
        check_updates.start()

# -----------------------------
# Run bot
# -----------------------------
if TOKEN:
    bot.run(TOKEN)
else:
    print("❌ DISCORD_TOKEN not set in environment variables!")



