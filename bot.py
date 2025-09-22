import os
import discord
from discord.ext import tasks
from discord import app_commands
import json
import logging
import aiohttp
from datetime import datetime

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("rs3-bot")

# --- Load config.json ---
with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

INTERVAL = config.get("check_interval", 60)

# --- Load env vars ---
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError("❌ DISCORD_TOKEN environment variable is not set!")

CHANNEL_ID_RAW = os.getenv("DISCORD_CHANNEL_ID")
if not CHANNEL_ID_RAW:
    raise RuntimeError("❌ DISCORD_CHANNEL_ID environment variable is not set!")

try:
    CHANNEL_ID = int(CHANNEL_ID_RAW)
except ValueError:
    raise RuntimeError("❌ DISCORD_CHANNEL_ID must be a numeric channel ID!")

logger.info(f"✅ DISCORD_CHANNEL_ID loaded: {CHANNEL_ID}")

# --- Discord intents ---
intents = discord.Intents.default()

# --- Bot client ---
class RS3Bot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        # Store tracked accounts in memory for now
        self.tracked_accounts = ["gimseedspoon", "gim mythy"]

    async def setup_hook(self):
        tracker_loop.start()
        await self.tree.sync()
        logger.info("✅ Slash commands synced.")

bot = RS3Bot()

# --- Background tracker loop ---
@tasks.loop(seconds=INTERVAL)
async def tracker_loop():
    try:
        logger.info("Running RS3 account check...")

        channel = bot.get_channel(CHANNEL_ID)
        if channel is None:
            logger.error(
                f"❌ Could not find channel with ID {CHANNEL_ID}. "
                "Check if the bot is in the server and has permissions."
            )
            return

        async with aiohttp.ClientSession() as session:
            for username in bot.tracked_accounts:
                url = f"https://secure.runescape.com/m=hiscore_oldschool/index_lite.ws?player={username}"
                async with session.get(url) as resp:
                    if resp.status != 200:
                        logger.warning(f"Failed to fetch data for {username}: {resp.status}")
                        continue
                    data = await resp.text()
                    overall = data.splitlines()[0].split(",")
                    rank, level, xp = overall[0], overall[1], overall[2]

                    embed = discord.Embed(
                        title=f"RS3 Tracker Update: {username}",
                        description=f"**Overall:** Level {level} | XP {xp} | Rank #{rank}",
                        color=discord.Color.blue(),
                        timestamp=datetime.utcnow()
                    )
                    await channel.send(embed=embed)

    except Exception as e:
        logger.error(f"Error in tracker_loop: {e}")

@tracker_loop.before_loop
async def before_tracker_loop():
    await bot.wait_until_ready()
    logger.info("Tracker loop is starting...")

# --- Slash commands ---
@bot.tree.command(name="ping", description="Check if the bot is alive.")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("✅ Pong! Bot is running.", ephemeral=True)

@bot.tree.command(name="track", description="Start tracking a RuneScape 3 account.")
async def track(interaction: discord.Interaction, username: str):
    if username.lower() in [u.lower() for u in bot.tracked_accounts]:
        await interaction.response.send_message(f"⚠️ Already tracking **{username}**.", ephemeral=True)
        return
    bot.tracked_accounts.append(username)
    await interaction.response.send_message(f"📡 Now tracking **{username}**.", ephemeral=False)

@bot.tree.command(name="untrack", description="Stop tracking a RuneScape 3 account.")
async def untrack(interaction: discord.Interaction, username: str):
    for u in bot.tracked_accounts:
        if u.lower() == username.lower():
            bot.tracked_accounts.remove(u)
            await interaction.response.send_message(f"🛑 Stopped tracking **{username}**.", ephemeral=False)
            return
    await interaction.response.send_message(f"⚠️ Not currently tracking **{username}**.", ephemeral=True)

@bot.tree.command(name="list", description="List all currently tracked accounts.")
async def list_accounts(interaction: discord.Interaction):
    if not bot.tracked_accounts:
        await interaction.response.send_message("📋 No accounts are currently being tracked.", ephemeral=True)
        return
    msg = "📋 Currently tracked accounts:\n" + "\n".join(f"• {u}" for u in bot.tracked_accounts)
    await interaction.response.send_message(msg, ephemeral=False)

# --- Run bot ---
if __name__ == "__main__":
    bot.run(TOKEN)

