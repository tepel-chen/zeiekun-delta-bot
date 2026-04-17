from __future__ import annotations
from collections import defaultdict
from pathlib import Path
from typing import Dict, List
import discord
from discord import Interaction, app_commands
from challenge import Challenge
from info_helpers import format_challenge_line, sort_by_status_difficulty
from command.utils import ensure_in_category
from state_store import load_thread_state


def group_by_category(challenges: List[Challenge]) -> Dict[str, List[Challenge]]:
    groups: Dict[str, List[Challenge]] = defaultdict(list)
    for challenge in challenges:
        if challenge.status == "scrapped" or challenge.status is None:
            continue
        category = challenge.category or "未分類"
        groups[category].append(challenge)
    for category in list(groups.keys()):
        groups[category] = sort_by_status_difficulty(groups[category])
    return groups


def register_info_category_command(
    group: app_commands.Group,
    challenge_repo_path: Path,
    category_id: int,
) -> None:
    challenge_root = challenge_repo_path / "challenges"

    @group.command(name="info_category", description="カテゴリ別チャレンジ一覧")
    async def info_category(interaction: Interaction) -> None:
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
        groups = group_by_category(challenges)
        thread_state = load_thread_state()

        embed = discord.Embed(
            title="/chal info_category",
            description="カテゴリ別にチャレンジを集計",
            colour=0x3BA55C,
        )

        for category in sorted(groups.keys()):
            entries = groups[category]
            if not entries:
                continue
            value = "\n".join(
                format_challenge_line(challenge, thread_state.get(challenge.key))
                for challenge in entries
            )
            embed.add_field(name=f"{category} ({len(entries)})", value=value, inline=False)

        await interaction.followup.send(embed=embed)
