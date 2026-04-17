from __future__ import annotations
import discord
from discord import Interaction, app_commands
from challenge import Challenge
from forum_sync import state_display
from info_helpers import (
    format_challenge_line,
    group_challenges_by_status,
    status_ordered_statuses,
)
from command.utils import ensure_in_category
from config import CHALLENGE_REPO_PATH
from state_store import load_thread_state


def register_info_status_command(
    group: app_commands.Group,
) -> None:
    challenge_root = CHALLENGE_REPO_PATH / "challenges"

    @group.command(name="info_status", description="ステータス別チャレンジ一覧")
    async def info_status(interaction: Interaction) -> None:
        if not await ensure_in_category(interaction):
            return
        await interaction.response.defer(thinking=True)
        challenges = Challenge.collect_from_repo(challenge_root, CHALLENGE_REPO_PATH)
        if not challenges:
            await interaction.followup.send(
                "チャレンジが見つかりませんでした。`/chal pull`を実行してください。",
                ephemeral=True,
            )
            return
        groups = group_challenges_by_status(challenges)
        ordered_statuses = status_ordered_statuses(groups)
        thread_state = load_thread_state()

        embed = discord.Embed(
            title="/chal info_status",
            description="ステータス別のチャレンジ一覧",
            colour=0x7289DA,
        )

        for status in ordered_statuses:
            label = state_display.get(status, status.capitalize())
            entries = groups.get(status, [])
            if not entries:
                continue
            value = "\n".join(
                format_challenge_line(challenge, thread_state.get(challenge.key))
                for challenge in entries
            )
            embed.add_field(name=f"{label} ({len(entries)})", value=value, inline=False)

        await interaction.followup.send(embed=embed)
