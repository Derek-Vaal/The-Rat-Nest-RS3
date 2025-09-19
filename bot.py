import discord
from discord.ext import tasks, commands
import aiohttp
import asyncio
import json
import os
from datetime import datetime, timedelta

# Load config
with open("config.json") as f:
    config = json.load(f)

TOKEN = os.getenv("DISCORD_TOKEN", config.get("token"))
INTERVAL = config.get("check_interval", 300)

# JSON database
DB_FILE = "db.json"
if not os.path.exists(DB_FILE):
    with open(DB_FILE, "w") as f:
        json.dump({"players": {}, "channel": None, "xp_history": {}}, f)

with open(DB_FILE) as f:
    db = json.load(f)

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="/", intents=intents)

# Skill emoji map (includes Necromancy 🧟)
skill_emojis = {
    "Attack": "⚔️",
    "Strength": "💪",
    "Defence": "🛡️",
    "Constitution": "❤️",
    "Ranged": "🏹",
    "Prayer": "🙏",
    "Magic": "✨",
    "Cooking": "🍳",
    "Woodcutting": "🌲",
    "Fletching": "🏹",
    "Fishing": "🎣",
    "Firemaking": "🔥",
    "Crafting": "🎨",
    "Smithing": "⚒️",
    "Mining": "⛏️",
    "Herblore": "🌿",
    "Agility": "🤸",
    "Thieving": "🕵️",
    "Slayer": "💀",
    "Farming": "🌾",
    "Runecrafting": "🌀",
    "Hunter": "🎯",
    "Construction": "🏠",
    "Summoning": "🦄",
    "Dungeoneering": "🗝️",
    "Divination": "🔮",
    "Invention": "💡",
    "Archaeology": "🏺",
    "Necromancy": "🧟"
}

def save_db():
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=2)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    check_updates.start()

@bot.command()
async def setchannel(ctx):
    """Set the channel where updates will be posted"""
    db["channel"] = ctx.channel.id
    save_db()
    await ctx.send(f"✅ This channel has been set for RuneScape updates.")

async def fetch_rs3_data(player):
    """Stub — replace with real API scraping later"""
    return {
        "xp": {skill: 0 for skill in skill_emojis},  # all skills default
        "quests": [],
        "collection_log": []
    }

def group_levelups(events):
    """Group level-ups happening within 5 minutes"""
    grouped = {}
    for e in events:
        key = (e["player"], e["time"] // 300)  # group per 5-min block
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(e)
    return grouped.values()

@tasks.loop(seconds=INTERVAL)
async def check_updates():
    if not db.get("channel"):
        return

    channel = bot.get_channel(db["channel"])
    if not channel:
        return

    updates = []

    for player in db["players"].keys():
        try:
            new_data = await fetch_rs3_data(player)
            old_data = db["xp_history"].get(player, {})

            # Check for level-ups
            for skill, xp in new_data["xp"].items():
                old_xp = old_data.get(skill, 0)
                new_level = xp // 100000  # fake formula
                old_level = old_xp // 100000
                if new_level > old_level:
                    emoji = skill_emojis.get(skill, "❓")
                    updates.append({
                        "player": player,
                        "type": "level",
                        "skill": skill,
                        "level": new_level,
                        "emoji": emoji,
                        "time": int(datetime.utcnow().timestamp())
                    })

            # Check for quest completions
            for q in new_data["quests"]:
                if q not in old_data.get("quests", []):
                    updates.append({
                        "player": player,
                        "type": "quest",
                        "quest": q,
                        "time": int(datetime.utcnow().timestamp())
                    })

            # Check for collection log unlocks
            for item in new_data["collection_log"]:
                if item not in old_data.get("collection_log", []):
                    updates.append({
                        "player": player,
                        "type": "collection",
                        "item": item,
                        "time": int(datetime.utcnow().timestamp())
                    })

            db["xp_history"][player] = new_data
            save_db()

        except Exception as e:
            print(f"⚠️ Error fetching {player}: {e}")

    # Group and post updates
    for group in group_levelups(updates):
        if not group:
            continue
        if len(group) == 1:
            e = group[0]
            if e["type"] == "level":
                await channel.send(f"{e['emoji']} **{e['player']}** reached level {e['level']} in {e['skill']}!")
            elif e["type"] == "quest":
                await channel.send(f"📜 **{e['player']}** completed the quest *{e['quest']}*!")
            elif e["type"] == "collection":
                await channel.send(f"📦 **{e['player']}** unlocked *{e['item']}* in the collection log!")
        else:
            player = group[0]["player"]
            skills = [f"{e['emoji']} {e['skill']} {e['level']}" for e in group if e["type"] == "level"]
            await channel.send(f"🔥 **{player}** leveled up multiple times in 5 minutes:\n" + ", ".join(skills))

bot.run(TOKEN)


