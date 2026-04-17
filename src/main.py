import discord
from discord import app_commands

from command.hello import register_hello_command
from command.pull import register_pull_command
from command.setmeta import register_set_command
from command.info_status import register_info_status_command
from command.info_category import register_info_category_command
from command.info_waves import register_info_waves_command
from config import DISCORD_TOKEN, GUILD_ID
from state_store import initialize_state_db

initialize_state_db()

intents = discord.Intents.default()
intents.guilds = True
intents.members = True

bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)
guild_obj = discord.Object(id=GUILD_ID)
chal_commands = app_commands.Group(name="chal", description="チャレンジ制作関連")
tree.add_command(chal_commands, guild=guild_obj)

register_hello_command(chal_commands)
register_pull_command(
    chal_commands,
    bot,
)
register_set_command(
    chal_commands,
    bot,
)
register_info_status_command(
    chal_commands,
)
register_info_category_command(
    chal_commands,
)
register_info_waves_command(
    chal_commands,
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
