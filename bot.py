import os
import discord
from discord.ext import tasks
from discord import app_commands
import json
import logging

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("rs3-bot")

# --- Load config.json ---
with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

INTERVAL = config.get("check_interval", 300)  # default 5 minutes
CHANNEL_ID = config.get("channel_id")  # must be set in config.json

# --- Load token from Railway env ---
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError("❌ DISCORD_TOKEN environment variable is not set!")

# --- Discord intents ---
intents = discord.Intents.default()

# --- Bot client ---
class RS3Bot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        # Start background tracker loop after bot is ready
        tracker_loop.start()
        await self.tree.sync()
        logger.info("✅ Slash commands synced.")

bot = RS3Bot()

# --- Background task ---
@tasks.loop(seconds=INTERVAL)
async def tracker_loop():
    """Background loop that checks for RS3 account updates."""
    try:
        logger.info("Running RS3 account check...")

        if CHANNEL_ID:
            channel = bot.get_channel(CHANNEL_ID)
            if channel is None:
                logger.error(
                    f"❌ Could not find channel with ID {CHANNEL_ID}. "
                    "Check if the bot is in the server and has permissions."
                )
                return

            # TODO: Replace with your RS3 tracking logic
            await channel.send("✅ Tracker loop executed.")
        else:
            logger.warning("⚠️ No channel_id set in config.json, skipping message send.")

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
    await interaction.response.send_message(f"📡 Now tracking **{username}**.", ephemeral=False)

@bot.tree.command(name="untrack", description="Stop tracking a RuneScape 3 account.")
async def untrack(interaction: discord.Interaction, username: str):
    await interaction.response.send_message(f"🛑 Stopped tracking **{username}**.", ephemeral=False)

@bot.tree.command(name="list", description="List all currently tracked accounts.")
async def list_accounts(interaction: discord.Interaction):
    tracked = ["gimseedspoon", "gim mythy"]  # placeholder until storage added
    msg = "📋 Currently tracked accounts:\n" + "\n".join(f"• {u}" for u in tracked)
    await interaction.response.send_message(msg, ephemeral=False)

# --- Run bot ---
if __name__ == "__main__":
    bot.run(TOKEN)


