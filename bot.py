import discord
import json
import asyncio

# ---------- CONFIG ----------
TOKEN = "YOUR_DISCORD_BOT_TOKEN"
GUILD_ID = 154070238806147072  # replace with your server ID
CHANNEL_ID = 1133590077394649138  # replace with your target channel ID
CHECK_INTERVAL = 300  # 5 minutes

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
bot = discord.Client(intents=intents)

# ---------- LOAD PLAYERS ----------
with open("tracked_players.json") as f:
    tracked_players = json.load(f)["players"]

# ---------- TRACK LEVELS ----------
# Replace this with your method to get player skills
def get_player_levels(player):
    """
    Returns a dict of {skill_name: level}
    For example: {"Attack": 75, "Divination": 85}
    """
    # Your actual API or scraping code goes here
    return {}

# Memory store for old levels
player_old_levels = {player: get_player_levels(player) for player in tracked_players}

# Batch storage for pending level-ups
pending_level_ups = {}

# ---------- LEVEL-UP DETECTION ----------
def record_level_ups(player, old_levels, new_levels):
    """
    Compares old and new levels, records only real level-ups
    """
    for skill, new_lvl in new_levels.items():
        old_lvl = old_levels.get(skill, 0)
        if new_lvl > old_lvl:
            # Optional: skip fake events here
            if player not in pending_level_ups:
                pending_level_ups[player] = {}
            pending_level_ups[player][skill] = new_lvl

# ---------- POSTING LOOP ----------
async def post_pending_level_ups(channel):
    while True:
        if pending_level_ups:
            msg = "**Level-ups in the last 5 minutes:**\n"
            for player, skills in pending_level_ups.items():
                skill_str = ", ".join(f"{skill} {lvl}" for skill, lvl in skills.items())
                msg += f"- {player}: {skill_str}\n"
            
            await channel.send(msg)
            pending_level_ups.clear()  # reset after posting

        await asyncio.sleep(CHECK_INTERVAL)

# ---------- CHECK LOOP ----------
async def check_players_loop(channel):
    while True:
        for player in tracked_players:
            new_levels = get_player_levels(player)
            old_levels = player_old_levels[player]
            record_level_ups(player, old_levels, new_levels)
            player_old_levels[player] = new_levels
        await asyncio.sleep(CHECK_INTERVAL)

# ---------- BOT EVENTS ----------
@bot.event
async def on_ready():
    print(f"{bot.user} logged in")
    channel = bot.get_channel(CHANNEL_ID)
    bot.loop.create_task(post_pending_level_ups(channel))
    bot.loop.create_task(check_players_loop(channel))

# ---------- START BOT ----------
bot.run(TOKEN)


