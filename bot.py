import discord
from discord.ext import tasks, commands
import requests
import json
import os
from datetime import datetime, timedelta, timezone
import re
from collections import defaultdict

# === Load config ===
TOKEN = os.getenv("DISCORD_TOKEN")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 1200))  # default 20 minutes

# === Database (db.json) ===
if not os.path.exists("db.json"):
    with open("db.json", "w") as f:
        json.dump({"channel_id": 0, "tracked_players": []}, f)

with open("db.json", "r") as f:
    db = json.load(f)

def save_db():
    with open("db.json", "w") as f:
        json.dump(db, f, indent=4)

# === Bot Setup ===
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="/", intents=intents)

# === Safe message sender ===
async def send_update_message(message: str):
    if db.get("channel_id", 0) == 0:
        print("⚠️ No channel configured. Use /setchannel first.")
        return

    channel = bot.get_channel(db["channel_id"])
    if channel is None:
        print(f"⚠️ Could not find channel with ID {db['channel_id']}.")
        return

    try:
        await channel.send(message)
    except Exception as e:
        print(f"⚠️ Failed to send update: {e}")

# === Commands ===
@bot.command()
async def setchannel(ctx):
    db["channel_id"] = ctx.channel.id
    save_db()
    await ctx.send(f"✅ Updates will now post in {ctx.channel.mention}")

@bot.command()
async def track(ctx, *, player_name: str):
    if player_name not in db["tracked_players"]:
        db["tracked_players"].append(player_name)
        save_db()
        await ctx.send(f"✅ Now tracking **{player_name}**")
    else:
        await ctx.send(f"⚠️ Already tracking **{player_name}**")

@bot.command()
async def untrack(ctx, *, player_name: str):
    if player_name in db["tracked_players"]:
        db["tracked_players"].remove(player_name)
        save_db()
        await ctx.send(f"✅ Stopped tracking **{player_name}**")
    else:
        await ctx.send(f"⚠️ Not tracking **{player_name}**")

@bot.command()
async def listplayers(ctx):
    if not db["tracked_players"]:
        await ctx.send("⚠️ No players are being tracked.")
    else:
        players = ", ".join(db["tracked_players"])
        await ctx.send(f"👥 Tracking: {players}")

# === Background Task ===
last_checked = datetime.now(timezone.utc)

@tasks.loop(seconds=CHECK_INTERVAL)
async def check_updates():
    global last_checked
    now = datetime.now(timezone.utc)
    grouped_updates = defaultdict(lambda: defaultdict(int))
    latest_levels = defaultdict(dict)

    for player in db.get("tracked_players", []):
        url = f"https://apps.runescape.com/runemetrics/profile/profile?user={player}&activities=20"
        try:
            r = requests.get(url, timeout=10)
            data = r.json()
        except Exception as e:
            print(f"⚠️ Failed to fetch RuneMetrics for {player}: {e}")
            continue

        if "activities" not in data:
            continue

        for act in data["activities"]:
            ts = datetime.strptime(act["date"], "%d-%b-%Y %H:%M").replace(tzinfo=timezone.utc)
            if ts > last_checked:
                text = act["text"]

                # Check if it's a level-up
                match = re.match(r"(.+) levelled up (.+)\.", text)
                if match:
                    skill = match.group(2)
                    grouped_updates[player][skill] += 1

                    # Save highest level mentioned in this activity
                    level_match = re.search(r"to level (\d+)", text)
                    if level_match:
                        latest_levels[player][skill] = level_match.group(1)
                else:
                    # Non-level updates (quests, bosses, etc.)
                    grouped_updates[player][text]["raw"] = True

    last_checked = now

    if not grouped_updates:
        return

    # Format grouped message
    messages = []
    for player, updates in grouped_updates.items():
        for skill, count in updates.items():
            if isinstance(count, dict) and "raw" in count:
                # Raw text update
                messages.append(f"**{player}** → {skill}")
            else:
                # Grouped skill level-ups
                level = latest_levels[player].get(skill, "?")
                if count > 1:
                    messages.append(f"**{player}** gained {count} levels in **{skill}** (now {level})")
                else:
                    messages.append(f"**{player}** levelled up **{skill}** (now {level})")

    if messages:
        await send_update_message("\n".join(messages))

# === Startup ===
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    check_updates.start()

bot.run(TOKEN)



