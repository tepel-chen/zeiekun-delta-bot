from __future__ import annotations

from discord import Interaction, app_commands

from command.utils import ensure_in_category
from state_store import unfollow_branch


def register_unfollow_command(group: app_commands.Group) -> None:
    @group.command(name="unfollow", description="ブランチのフォローを解除")
    @app_commands.describe(branch_name="フォローを外すブランチ名")
    async def unfollow(interaction: Interaction, branch_name: str) -> None:
        if not await ensure_in_category(interaction):
            return

        removed = unfollow_branch(branch_name.strip())
        if removed:
            await interaction.response.send_message(
                f"`{branch_name}` のフォローを解除しました。"
            )
            return

        await interaction.response.send_message(
            f"`{branch_name}` はフォローされていません。", ephemeral=True
        )
