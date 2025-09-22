import discord
from discord.ext import tasks
from discord import app_commands
import json
import logging
import asyncio
from datetime import datetime

# --- Logging setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("rs3-bot")

# --- Load config ---
with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

TOKEN = config.get("token")
INTERVAL = config.get("check_interval", 300)  # default 5 minutes

# --- Discord intents ---
intents = discord.Intents.default()
intents.message_content = False  # only needed if you're reading msg text

# --- Bot client ---
class RS3Bot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        # Sync slash commands globally
        await self.tree.sync()
        logger.info("Slash commands synced.")

bot = RS3Bot()

# --- Background task ---
@tasks.loop(seconds=INTERVAL)
async def tracker_loop():
    """Background loop that checks for RS3 account updates."""
    try:
        # TODO: Replace with your actual tracking logic
        logger.info("Running RS3 account check...")
        # Example placeholder:
        # updates = check_accounts()
        # for channel_id, msg in updates:
        #     channel = bot.get_channel(channel_id)
        #     if channel:
        #         await channel.send(msg)
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
@app_commands.describe(username="RSN of the player to track")
async def track(interaction: discord.Interaction, username: str):
    # TODO: Hook into your storage logic
    await interaction.response.send_message(f"📡 Now tracking **{username}**.", ephemeral=False)

@bot.tree.command(name="untrack", description="Stop tracking a RuneScape 3 account.")
@app_commands.describe(username="RSN of the player to stop tracking")
async def untrack(interaction: discord.Interaction, username: str):
    # TODO: Hook into your storage logic
    await interaction.response.send_message(f"🛑 Stopped tracking **{username}**.", ephemeral=False)

@bot.tree.command(name="list", description="List all currently tracked accounts.")
async def list_accounts(interaction: discord.Interaction):
    # TODO: Pull from your storage
    tracked = ["gimseedspoon", "gim mythy"]  # placeholder
    if tracked:
        msg = "📋 Currently tracked accounts:\n" + "\n".join(f"• {u}" for u in tracked)
    else:
        msg = "No accounts are currently being tracked."
    await interaction.response.send_message(msg, ephemeral=False)

# --- Run bot ---
if __name__ == "__main__":
    try:
        tracker_loop.start()
        bot.run(TOKEN)
    except KeyboardInterrupt:
        logger.info("Bot shutting down...")
    except Exception as e:
        logger.error(f"Failed to run bot: {e}")



