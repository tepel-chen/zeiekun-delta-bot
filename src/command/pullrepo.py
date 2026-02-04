from __future__ import annotations

from pathlib import Path

import discord
from discord import Interaction, app_commands

from challenge import Challenge
from forum_sync import calculate_repo_base, ensure_challenge_threads, get_forum_channel
from git import sync_repository


def register_pullrepo_command(
    group: app_commands.Group,
    bot: discord.Client,
    forum_channel_id: int,
    challenge_repo_path: Path,
    thread_state_file: Path,
    repo_url: str,
) -> None:
    challenge_root = challenge_repo_path / "challenges"
    repo_base = calculate_repo_base(repo_url)

    @group.command(
        name="pullrepo", description="Githubのレポジトリと同期してフォーラムスレッドを用意する"
    )
    async def pullrepo(interaction: Interaction) -> None:
        """Clone or update the repository and keep forum threads aligned."""
        await interaction.response.defer(thinking=True)

        try:
            action = await sync_repository(repo_url, challenge_repo_path)
        except RuntimeError as exc:
            await interaction.followup.send(f"Failed to sync repository: {exc}", ephemeral=True)
            return

        try:
            forum_channel = await get_forum_channel(bot, forum_channel_id)
            challenges = Challenge.collect_from_repo(challenge_root, challenge_repo_path)
            new_threads, updated_threads = await ensure_challenge_threads(
                forum_channel,
                challenges,
                thread_state_file,
                repo_base,
            )
        except RuntimeError as exc:
            await interaction.followup.send(
                f"Repository synced but thread creation failed: {exc}", ephemeral=True
            )
            return

        message_lines = [action]
        if new_threads:
            message_lines.append(f"Created threads for: {', '.join(new_threads)}.")
        if updated_threads:
            message_lines.append(f"Updated threads for: {', '.join(updated_threads)}.")
        if not new_threads and not updated_threads:
            message_lines.append("All challenge threads already existed and were current.")

        await interaction.followup.send("\n".join(message_lines))
