from __future__ import annotations
from collections import defaultdict
from typing import Dict, List
import discord
from discord import Interaction, app_commands
from challenge import Challenge, choose_preferred_challenges
from info_helpers import challenge_state_key, format_challenge_line, sort_by_status_difficulty
from command.utils import ensure_in_category
from config import get_challenge_repo_path
from state_store import load_thread_state
from state_store import list_followed_branches


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
) -> None:
    @group.command(name="info_category", description="カテゴリ別チャレンジ一覧")
    async def info_category(interaction: Interaction) -> None:
        if not await ensure_in_category(interaction):
            return
        await interaction.response.defer(thinking=True)
        challenges: list[Challenge] = []
        for branch_name in list_followed_branches():
            repo_path = get_challenge_repo_path(branch_name)
            challenge_root = repo_path / "challenges"
            challenges.extend(Challenge.collect_from_repo(challenge_root, repo_path, branch_name))
        thread_state = load_thread_state()
        challenges = choose_preferred_challenges(challenges)
        if not challenges:
            await interaction.followup.send(
                "チャレンジが見つかりませんでした。`/chal pull`を実行してください。",
                ephemeral=True,
            )
            return
        groups = group_by_category(challenges)

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
                format_challenge_line(challenge, thread_state.get(challenge_state_key(challenge)))
                for challenge in entries
            )
            embed.add_field(name=f"{category} ({len(entries)})", value=value, inline=False)

        await interaction.followup.send(embed=embed)
