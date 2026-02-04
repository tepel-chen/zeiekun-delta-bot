from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Optional
import discord
from discord import Interaction, app_commands
from challenge import Challenge
from forum_sync import load_thread_state, state_display
from info_helpers import (
    format_challenge_line,
    group_challenges_by_status,
    status_ordered_statuses,
)
from command.utils import ensure_in_category


def register_info_status_command(
    group: app_commands.Group,
    challenge_repo_path: Path,
    thread_state_file: Path,
    category_id: int,
) -> None:
    challenge_root = challenge_repo_path / "challenges"

    @group.command(name="info_status", description="ステータス別チャレンジ一覧")
    async def info_status(interaction: Interaction) -> None:
        if not await ensure_in_category(interaction, category_id):
            return
        await interaction.response.defer(thinking=True)
        challenges = Challenge.collect_from_repo(challenge_root, challenge_repo_path)
        if not challenges:
            await interaction.followup.send(
                "チャレンジが見つかりませんでした。`/chal pull`を実行してください。",
                ephemeral=True,
            )
            return
        groups = group_challenges_by_status(challenges)
        ordered_statuses = status_ordered_statuses(groups)
        thread_state = load_thread_state(thread_state_file)

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
