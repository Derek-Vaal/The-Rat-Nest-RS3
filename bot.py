import discord
from discord.ext import tasks
from discord import app_commands
import requests
import json
import os
from datetime import datetime

# Load config
try:
    with open("config.json") as f:
        config = json.load(f)
except FileNotFoundError:
    config = {}

TOKEN = os.getenv("DISCORD_TOKEN", config.get("token"))
CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", config.get("channel_id", 0)))
RSNS = config.get("rsns", [])

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# Track last seen data
last_quests = {}
last_levels = {}
last_collections = {}

# Icon map
skill_icons = {
    "Attack": "⚔️",
    "Defence": "🛡️",
    "Strength": "💪",
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
    "Herblore": "🧪",
    "Agility": "🤸",
    "Thieving": "🕵️",
    "Slayer": "👹",
    "Farming": "🌾",
    "Runecrafting": "🔮",
    "Hunter": "🏕️",
    "Construction": "🏠",
    "Summoning": "🦄",
    "Dungeoneering": "🏰",
    "Divination": "🌌",
    "Invention": "💡",
    "Archaeology": "🏺",
    "Necromancy": "🧟"
}

def fetch_runemetrics(rsn):
    url = f"https://apps.runescape.com/runemetrics/profile/profile?user={rsn}"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        if isinstance(data, dict):
            return data
        else:
            print(f"⚠️ RuneMetrics returned non-dict for {rsn}: {data}")
            return {}
    except Exception as e:
        print(f"⚠️ Error fetching {rsn}: {e}")
        return {}

@client.event
async def on_ready():
    print(f"✅ Logged in as {client.user}")
    await tree.sync()
    check_updates.start()

@tasks.loop(minutes=5)
async def check_updates():
    channel = client.get_channel(CHANNEL_ID)
    if not channel:
        print("❌ Channel not found")
        return

    for rsn in RSNS:
        profile = fetch_runemetrics(rsn)
        if not profile:
            continue

        # === Quest Completions ===
        if "quests" in profile:
            completed = [q["title"] for q in profile["quests"] if q.get("status") == "COMPLETED"]
            old_completed = last_quests.get(rsn, set())
            new_completed = set(completed) - old_completed
            for quest in new_completed:
                await channel.send(f"🎉 **{rsn}** has completed the quest **{quest}**!")
            last_quests[rsn] = set(completed)

        # === Level Ups ===
        if "skillvalues" in profile:
            skills = {s["level"]: s["id"] for s in profile["skillvalues"]}
            skill_map = {s["id"]: s for s in profile["skillvalues"]}

            old_levels = last_levels.get(rsn, {})
            new_levelups = []
            for skill in profile["skillvalues"]:
                skill_name = skill["skill"]
                level = skill["level"]
                old_level = old_levels.get(skill_name, 0)
                if level > old_level:
                    icon = skill_icons.get(skill_name, "⭐")
                    new_levelups.append(f"{icon} {skill_name} {level}")

            if new_levelups:
                levelup_msg = f"⬆️ **{rsn}** has leveled up!\n" + "\n".join(new_levelups)
                await channel.send(levelup_msg)

            last_levels[rsn] = {s["skill"]: s["level"] for s in profile["skillvalues"]}

        # === Collection Log Unlocks ===
        if "activities" in profile:
            new_logs = []
            old_logs = last_collections.get(rsn, set())
            for act in profile["activities"]:
                text = act.get("text", "")
                if "new collection log item" in text.lower() and text not in old_logs:
                    new_logs.append(text)

            if new_logs:
                for log in new_logs:
                    await channel.send(f"📜 **{rsn}** unlocked: {log}")
                last_collections[rsn] = old_logs.union(new_logs)

client.run(TOKEN)


