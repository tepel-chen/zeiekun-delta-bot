from discord import app_commands, Interaction


def register_hello_command(group: app_commands.Group) -> None:
    @group.command(name="hello", description="say hello")
    async def hello(interaction: Interaction) -> None:
        """Respond with a personalized greeting."""
        await interaction.response.send_message(f"Hello {interaction.user.display_name}")
