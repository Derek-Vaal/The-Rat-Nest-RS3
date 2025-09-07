# bot.py - RS3 RuneMetrics Notifications with Slash Commands
import os
import json
import requests
import discord
from discord.ext import tasks
from discord import app_commands
from datetime import datetime, timedelta, timezone

# ----------------------
# Config
# ----------------------
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN or len(TOKEN) < 50:
    raise ValueError("DISCORD_TOKEN missing or invalid. Set it in Railway env vars.")

INTERVAL = int(os.getenv("CHECK_INTERVAL", 600))  # default 10 min
DB_FILE = "db.json"
SEEN_FILE = "seen_events.json"

# ----------------------
# Bot Setup
# ----------------------
intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# ----------------------
# Database
# ----------------------
if not os.path.exists(DB_FILE):
    with open(DB_FILE, "w") as f:
        json.dump({"players": {}, "channel": None, "xp_history": {}}, f)

with open(DB_FILE) as f:
    db = json.load(f)

seen_events = set()
if os.path.exists(SEEN_FILE):
    with open(SEEN_FILE, "r") as f:
        try:
            seen_events = set(json.load(f))
        except Exception:
            seen_events = set()

def save_db():
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=2)

def save_seen():
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen_events), f)

# ----------------------
# RuneMetrics Helpers
# ----------------------
def fetch_runemetrics(rsn):
    url = f"https://apps.runescape.com/runemetrics/profile/profile?user={rsn}"
    try:
        r = requests.get(url, timeout=10)
        return r.json()
    except Exception:
        return {}

def get_skill_level(profile, skill_name):
    try:
        skills = profile.get("skillvalues", [])
        skill_map = {
            0: "Attack", 1: "Defence", 2: "Strength", 3: "Constitution",
            4: "Ranged", 5: "Prayer", 6: "Magic", 7: "Cooking",
            8: "Woodcutting", 9: "Fletching", 10: "Fishing", 11: "Firemaking",
            12: "Crafting", 13: "Smithing", 14: "Mining", 15: "Herblore",
            16: "Agility", 17: "Thieving", 18: "Slayer", 19: "Farming",
            20: "Runecrafting", 21: "Hunter", 22: "Construction", 23: "Summoning",
            24: "Dungeoneering", 25: "Divination", 26: "Invention", 27: "Archaeology"
        }
        for skill in skills:
            if skill_map.get(skill.get("id"), "").lower() == skill_name.lower():
                return skill.get("level", "?")
    except Exception:
        return "?"
    return "?"

skill_emojis = {
    "Attack": "⚔️", "Defence": "🛡️", "Strength": "💪", "Constitution": "❤️",
    "Ranged": "🏹", "Prayer": "🙏", "Magic": "✨", "Cooking": "🍳",
    "Woodcutting": "🌲", "Fletching": "🏹", "Fishing": "🎣", "Firemaking": "🔥",
    "Crafting": "🎨", "Smithing": "⚒️", "Mining": "⛏️", "Herblore": "🧪",
    "Agility": "🤸", "Thieving": "🕵️", "Slayer": "💀", "Farming": "🌱",
    "Runecrafting": "🌀", "Hunter": "🐾", "Construction": "🏠", "Summoning": "🔮",
    "Dungeoneering": "🗝️", "Divination": "🔆", "Invention": "💡", "Archaeology": "🏺"
}

async def post_update(channel, text):
    embed = discord.Embed(description=text, color=0xff9900)
    await channel.send(embed=embed)

# ----------------------
# Slash Commands
# ----------------------
@tree.command(name="setchannel", description="Set this channel for RS3 updates")
async def setchannel(interaction: discord.Interaction):
    db["channel"] = interaction.channel.id
    save_db()
    await interaction.response.send_message("✅ This channel is now set for RS3 updates.")

@tree.command(name="track", description="Track a RuneScape player")
async def track(interaction: discord.Interaction, rsn: str):
    rsn = rsn.strip()
    db["players"][rsn] = True
    if rsn not in db["xp_history"]:
        db["xp_history"][rsn] = []
    save_db()
    await interaction.response.send_message(f"✅ Now tracking **{rsn}**.")

@tree.command(name="untrack", description="Stop tracking a RuneScape player")
async def untrack(interaction: discord.Interaction, rsn: str):
    rsn = rsn.strip()
    if rsn in db["players"]:
        del db["players"][rsn]
        db["xp_history"].pop(rsn, None)
        save_db()
        await interaction.response.send_message(f"🛑 Stopped tracking **{rsn}**.")
    else:
        await interaction.response.send_message("⚠️ That player isn’t being tracked.")

@tree.command(name="list", description="List all tracked RuneScape players")
async def list_players(interaction: discord.Interaction):
    if db["players"]:
        players = ", ".join(db["players"].keys())
        await interaction.response.send_message(f"📋 Currently tracking: {players}")
    else:
        await interaction.response.send_message("⚠️ No players are being tracked.")

# ----------------------
# Background Task
# ----------------------
@tasks.loop(seconds=INTERVAL)
async def check_updates():
    if not db["channel"]:
        return
    channel = client.get_channel(db["channel"])
    if not channel:
        return

    cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=10)

    for rsn in list(db["players"].keys()):
        profile = fetch_runemetrics(rsn)
        if not profile:
            continue

        events = profile.get("activities", [])
        for event in events:
            text = event.get("text", "")
            date_str = event.get("date", "")
            unique_id = f"{rsn}-{text}-{date_str}"

            if unique_id in seen_events:
                continue

            try:
                event_time = datetime.strptime(date_str, "%d-%b-%Y %H:%M").replace(tzinfo=timezone.utc)
            except Exception:
                event_time = datetime.now(timezone.utc)

            if event_time < cutoff_time:
                continue

            seen_events.add(unique_id)

            if "level" in text.lower():
                if text.lower().startswith("reached level"):
                    parts = text.split(" ")
                    new_level = parts[2]
                    skill_name = parts[3].replace(".", "")
                elif text.lower().startswith("levelled up"):
                    skill_name = text.split(" ")[2].replace(".", "")
                    new_level = get_skill_level(profile, skill_name)
                else:
                    skill_name, new_level = "Unknown", "?"

                emoji = skill_emojis.get(skill_name, "🎉")
                msg = f"{emoji} **{rsn}** just reached **level {new_level} in {skill_name}!**"
                await post_update(channel, msg)
            else:
                await post_update(channel, f"📜 {text}")

    save_seen()

# ----------------------
# Events
# ----------------------
@client.event
async def on_ready():
    await tree.sync()
    print(f"✅ Logged in as {client.user}")
    if not check_updates.is_running():
        check_updates.start()

# ----------------------
# Run
# ----------------------
try:
    client.run(TOKEN)
except discord.errors.LoginFailure:
    raise ValueError("❌ Failed to login: DISCORD_TOKEN invalid. Double-check Railway variable.")

