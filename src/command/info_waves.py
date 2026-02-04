from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional

import discord
from discord import Interaction, app_commands

from challenge import Challenge
from forum_sync import load_thread_state
from info_helpers import format_challenge_line, sort_by_status_difficulty


def wave_key(value: Optional[str]) -> int:
    if not value:
        return 999
    try:
        return int(value)
    except ValueError:
        return 900 + hash(value) % 50


def group_by_wave(challenges: List[Challenge]) -> Dict[str, List[Challenge]]:
    allowed_statuses = {"playtest", "done"}
    groups: Dict[str, List[Challenge]] = defaultdict(list)
    for challenge in challenges:
        if (challenge.status or "").lower() not in allowed_statuses:
            continue
        wave = challenge.wave or "未割当"
        groups[wave].append(challenge)
    for wave in list(groups.keys()):
        groups[wave] = sort_by_status_difficulty(groups[wave])
    return groups


def register_info_waves_command(
    group: app_commands.Group,
    challenge_repo_path: Path,
    thread_state_file: Path,
) -> None:
    challenge_root = challenge_repo_path / "challenges"

    @group.command(name="info_waves", description="Wave別チャレンジ一覧")
    async def info_waves(interaction: Interaction) -> None:
        await interaction.response.defer(thinking=True)
        challenges = Challenge.collect_from_repo(challenge_root, challenge_repo_path)
        if not challenges:
            await interaction.followup.send(
                "チャレンジが見つかりませんでした。`/chal pullrepo`を実行してください。",
                ephemeral=True,
            )
            return
        groups = group_by_wave(challenges)
        thread_state = load_thread_state(thread_state_file)

        embed = discord.Embed(
            title="/chal info_waves",
            description="Waveごとのチャレンジ",
            colour=0xFFA500,
        )

        for wave in sorted(groups.keys(), key=wave_key):
            entries = groups[wave]
            if not entries:
                continue
            value = "\n".join(
                format_challenge_line(challenge, thread_state.get(challenge.key))
                for challenge in entries
            )
            embed.add_field(
                name=f"Wave {wave} ({len(entries)})", value=value, inline=False
            )

        await interaction.followup.send(embed=embed)
