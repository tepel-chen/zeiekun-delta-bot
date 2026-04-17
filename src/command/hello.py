from discord import app_commands, Interaction
from command.utils import ensure_in_category


def register_hello_command(group: app_commands.Group) -> None:
    @group.command(name="hello", description="say hello")
    async def hello(interaction: Interaction) -> None:
        """Respond with a personalized greeting."""
        if not await ensure_in_category(interaction):
            return
        await interaction.response.send_message(f"Hello {interaction.user.display_name}")
