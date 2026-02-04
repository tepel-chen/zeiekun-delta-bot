from __future__ import annotations

import discord


async def ensure_in_category(interaction: discord.Interaction, category_id: int) -> bool:
    channel = interaction.channel
    actual_category = None
    if isinstance(channel, discord.Thread):
        parent = channel.parent
        if parent:
            actual_category = parent.category_id
    else:
        actual_category = getattr(channel, "category_id", None)

    if actual_category != category_id:
        await interaction.response.send_message(
            "このコマンドは指定されたカテゴリ内でのみ利用可能です。", ephemeral=True
        )
        return False

    return True
