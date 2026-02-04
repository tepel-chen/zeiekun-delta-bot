from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import discord
from discord import Interaction, app_commands

from challenge import Challenge
from forum_sync import load_thread_state, state_display


DIFFICULTY_ORDER = {
    "welcome": 0,
    "beginner": 1,
    "easy": 2,
    "medium": 3,
    "hard": 4,
}

STATUS_ORDER = {
    "idea": 0,
    "playtest": 1,
    "done": 2
}


def difficulty_rank(value: str | None) -> int:
    if value is None:
        return 99
    return DIFFICULTY_ORDER.get(value.lower(), 50)


def format_challenge_line(
    challenge: Challenge,
    thread_record: Optional[Dict[str, int]],
) -> str:
    if thread_record:
        thread_id = thread_record.get("thread_id")
        if thread_id:
            return f"<#{thread_id}>"
    return f"[{challenge.category}] {challenge.display_name}"


def group_challenges_by_status(challenges: List[Challenge]) -> Dict[str, List[Challenge]]:
    groups: Dict[str, List[Challenge]] = {}
    for challenge in challenges:
        status = challenge.status
        if status == "scrapped" or status is None:
            continue
        groups.setdefault(status, []).append(challenge)
    for status_challenges in groups.values():
        status_challenges.sort(
            key=lambda challenge: (
                challenge.category.lower() if challenge.category else "",
                difficulty_rank(challenge.difficulty),
                challenge.display_name.lower() if challenge.display_name else "",
            )
        )
    return groups


def order_statuses(groups: Dict[str, List[Challenge]]) -> List[str]:
    ordered: List[str] = []
    for status, _ in sorted(STATUS_ORDER.items(), key=lambda item: item[1]):
        if status in groups:
            ordered.append(status)
    for status in sorted(groups.keys()):
        if status not in ordered and status != "scrapped":
            ordered.append(status)
    return ordered


def register_info_status_command(
    group: app_commands.Group,
    challenge_repo_path: Path,
    thread_state_file: Path,
) -> None:
    challenge_root = challenge_repo_path / "challenges"

    @group.command(name="info_status", description="ステータス別チャレンジ一覧")
    async def info_status(interaction: Interaction) -> None:
        await interaction.response.defer(thinking=True)
        challenges = Challenge.collect_from_repo(challenge_root, challenge_repo_path)
        if not challenges:
            await interaction.followup.send(
                "チャレンジが見つかりませんでした。`/chal pullrepo`を実行してください。",
                ephemeral=True,
            )
            return
        groups = group_challenges_by_status(challenges)
        ordered_statuses = order_statuses(groups)
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
                format_challenge_line(
                    challenge, thread_state.get(challenge.key), 
                )
                for challenge in entries
            )
            embed.add_field(name=f"{label} ({len(entries)})", value=value, inline=False)

        await interaction.followup.send(embed=embed)
