import os
from pathlib import Path

import discord
from discord import app_commands
from dotenv import load_dotenv

from command.hello import register_hello_command
from command.pull import register_pull_command
from command.setmeta import register_set_command
from command.info_status import register_info_status_command
from command.info_category import register_info_category_command
from command.info_waves import register_info_waves_command


def require_env_variable(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise SystemExit(f"{name} is not set in .env")
    return value


def require_env_int(name: str) -> int:
    value = require_env_variable(name)
    try:
        return int(value)
    except ValueError as exc:
        raise SystemExit(f"{name} must be an integer") from exc


load_dotenv(".env")

DISCORD_TOKEN = require_env_variable("DISCORD_TOKEN")
GUILD_ID = require_env_int("GUILD_ID")
FORUM_CHANNEL_ID = require_env_int("FORUM_CHANNEL_ID")
GITHUB_REPO_URL = require_env_variable("GITHUB_REPO_URL")
CATEGORY_ID = require_env_int("CATEGORY_ID")

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
CHALLENGE_REPO_PATH = PROJECT_ROOT / "challenge_repo"
THREAD_STATE_FILE = PROJECT_ROOT / "challenge_threads.json"

intents = discord.Intents.default()
intents.guilds = True
intents.members = True

bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)
guild_obj = discord.Object(id=GUILD_ID)
chal_commands = app_commands.Group(name="chal", description="チャレンジ制作関連")
tree.add_command(chal_commands, guild=guild_obj)

register_hello_command(
    chal_commands,
    category_id=CATEGORY_ID,
)
register_pull_command(
    chal_commands,
    bot,
    forum_channel_id=FORUM_CHANNEL_ID,
    challenge_repo_path=CHALLENGE_REPO_PATH,
    thread_state_file=THREAD_STATE_FILE,
    repo_url=GITHUB_REPO_URL,
    category_id=CATEGORY_ID,
)
register_set_command(
    chal_commands,
    bot,
    forum_channel_id=FORUM_CHANNEL_ID,
    challenge_repo_path=CHALLENGE_REPO_PATH,
    thread_state_file=THREAD_STATE_FILE,
    repo_url=GITHUB_REPO_URL,
    category_id=CATEGORY_ID,
)
register_info_status_command(
    chal_commands,
    challenge_repo_path=CHALLENGE_REPO_PATH,
    thread_state_file=THREAD_STATE_FILE,
    category_id=CATEGORY_ID,
)
register_info_category_command(
    chal_commands,
    challenge_repo_path=CHALLENGE_REPO_PATH,
    thread_state_file=THREAD_STATE_FILE,
    category_id=CATEGORY_ID,
)
register_info_waves_command(
    chal_commands,
    challenge_repo_path=CHALLENGE_REPO_PATH,
    thread_state_file=THREAD_STATE_FILE,
    category_id=CATEGORY_ID,
)


@bot.event
async def on_ready() -> None:
    try:
        await tree.sync(guild=guild_obj)
        print(f"Synced commands to guild {guild_obj.id}")
    except Exception:
        print("Failed to sync commands")

    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("Ready to receive / commands.")


if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
