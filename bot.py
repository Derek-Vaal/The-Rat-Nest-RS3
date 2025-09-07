import os
import json
import discord
from discord.ext import commands, tasks

TOKEN = os.environ.get('TOKEN')
if not TOKEN:
    raise ValueError("Discord bot token not set in environment variables!")

CHANNEL_ID = YOUR_CHANNEL_ID  # replace with your Discord channel ID

intents = discord.Intents.default()
intents.messages = True
bot = commands.Bot(command_prefix='!', intents=intents)

# JSON files
PLAYERS_FILE = 'tracked_players.json'
LEVELS_FILE = 'tracked_levels.json'

# Load tracked players
if os.path.exists(PLAYERS_FILE):
    with open(PLAYERS_FILE, 'r') as f:
        tracked_players = json.load(f)
else:
    tracked_players = []
    with open(PLAYERS_FILE, 'w') as f:
        json.dump(tracked_players, f)

# Load previous levels
if os.path.exists(LEVELS_FILE):
    with open(LEVELS_FILE, 'r') as f:
        previous_levels = json.load(f)
else:
    previous_levels = {}

def save_levels():
    with open(LEVELS_FILE, 'w') as f:
        json.dump(previous_levels, f, indent=4)

# Replace this with your actual level-fetching logic
def get_current_levels():
    return {
        "GIM Mythy": {"Divination": 85, "Constitution": 85},
        "GIMSeedSpoon": {"Divination": 60}
    }

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    update_loop.start()

@tasks.loop(minutes=20)
async def update_loop():
    channel = bot.get_channel(CHANNEL_ID)
    current_levels = get_current_levels()
    messages = []

    for player in tracked_players:
        skills = current_levels.get(player, {})
        leveled_up_skills = {}

        if player not in previous_levels:
            previous_levels[player] = {}

        for skill, level in skills.items():
            last_level = previous_levels[player].get(skill, 0)
            if level > last_level:
                leveled_up_skills[skill] = level
                previous_levels[player][skill] = level

        if leveled_up_skills:
            skill_updates = ', '.join(f"{skill} to {lvl}" for skill, lvl in leveled_up_skills.items())
            messages.append(f"{player} has leveled up {skill_updates}!")

    if messages:
        await channel.send("\n".join(messages))
        save_levels()

bot.run(TOKEN)


