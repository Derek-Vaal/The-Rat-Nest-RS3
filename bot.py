import os
import discord
from discord.ext import tasks
from discord import app_commands
import aiohttp
import json
from datetime import datetime, timedelta, timezone

# -------------------
# Config & Env
# -------------------
with open("config.json") as f:
    config = json.load(f)

INTERVAL = config.get("check_interval", 60)
TOKEN = os.getenv("DISCORD_TOKEN") or config.get("token")
CHANNEL_ID_ENV = os.getenv("DISCORD_CHANNEL_ID")

if not TOKEN:
    raise RuntimeError("❌ DISCORD_TOKEN environment variable is not set!")

# -------------------
# Discord Setup
# -------------------
intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

DB_FILE = "db.json"
if not os.path.exists(DB_FILE):
    with open(DB_FILE, "w") as f:
        json.dump({"players": {}, "channel": None, "xp_history": {}, "seen_events": {}}, f)

with open(DB_FILE) as f:
    db = json.load(f)

seen_events = set(db.get("seen_events", []))

def save_db():
    db["seen_events"] = list(seen_events)
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=2)

# -------------------
# Skill Emojis
# -------------------
skill_emojis = {
    "Attack": "⚔️", "Defence": "🛡️", "Strength": "💪", "Constitution": "❤️",
    "Ranged": "🏹", "Prayer": "🙏", "Magic": "✨", "Cooking": "🍳",
    "Woodcutting": "🌲", "Fletching": "🏹", "Fishing": "🎣", "Firemaking": "🔥",
    "Crafting": "🎨", "Smithing": "⚒️", "Mining": "⛏️", "Herblore": "🧪",
    "Agility": "🤸", "Thieving": "🕵️", "Slayer": "💀", "Farming": "🌱",
    "Runecrafting": "🌀", "Hunter": "🐾", "Construction": "🏠", "Summoning": "🔮",
    "Dungeoneering": "🗝️", "Divination": "🔆", "Invention": "💡", "Archaeology": "🏺"
}

# -------------------
# Helper Functions
# -------------------
async def fetch_runemetrics(session, rsn):
    url = f"https://apps.runescape.com/runemetrics/profile/profile?user={rsn}"
    try:
        async with session.get(url, timeout=10) as r:
            return await r.json()
    except Exception:
        return {}

async def post_update(channel, text):
    embed = discord.Embed(description=text, color=0xff9900)
    await channel.send(embed=embed)

def get_skill_level(profile, skill_name):
    try:
        skills = profile.get("skillvalues", [])
        skill_map = {i: name for i, name in enumerate(skill_emojis.keys())}
        for skill in skills:
            if skill_map.get(skill.get("id"), "").lower() == skill_name.lower():
                return skill.get("level", "?")
    except Exception:
        return "?"
    return "?"

# -------------------
# Slash Commands
# -------------------
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

# -------------------
# Background Loop
# -------------------
@tasks.loop(seconds=INTERVAL)
async def check_updates():
    channel_id = CHANNEL_ID_ENV or db.get("channel")
    if not channel_id:
        return
    channel = client.get_channel(int(channel_id))
    if not channel:
        return

    cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=10)

    async with aiohttp.ClientSession() as session:
        for rsn in db["players"].keys():
            profile = await fetch_runemetrics(session, rsn)
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
                        skill_name = "Unknown"
                        new_level = "?"
                    emoji = skill_emojis.get(skill_name, "🎉")
                    msg = f"{emoji} **{rsn}** just reached **level {new_level} in {skill_name}!**"
                    await post_update(channel, msg)
                else:
                    await post_update(channel, f"📜 {text}")
    save_db()

@check_updates.before_loop
async def before_check_updates():
    await client.wait_until_ready()

# -------------------
# Events
# -------------------
@client.event
async def on_ready():
    await tree.sync()
    print(f"✅ Logged in as {client.user}")
    check_updates.start()

# -------------------
# Run Bot
# -------------------
client.run(TOKEN)
