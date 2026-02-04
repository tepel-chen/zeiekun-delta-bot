from __future__ import annotations

from pathlib import Path

import discord
from discord import Interaction, app_commands

from challenge import Challenge
from command.utils import ensure_in_category
from forum_sync import calculate_repo_base, ensure_challenge_threads, get_forum_channel
from git import sync_repository


def register_pull_command(
    group: app_commands.Group,
    bot: discord.Client,
    forum_channel_id: int,
    challenge_repo_path: Path,
    thread_state_file: Path,
    repo_url: str,
    category_id: int,
) -> None:
    challenge_root = challenge_repo_path / "challenges"
    repo_base = calculate_repo_base(repo_url)

    @group.command(
        name="pull", description="Githubのレポジトリと同期してフォーラムスレッドを用意する"
    )
    async def pull(interaction: Interaction) -> None:
        if not await ensure_in_category(interaction, category_id):
            return
        """Clone or update the repository and keep forum threads aligned."""
        await interaction.response.defer(thinking=True)

        try:
            action = await sync_repository(repo_url, challenge_repo_path)
        except RuntimeError as exc:
            await interaction.followup.send(f"リポジトリの同期に失敗しました: {exc}", ephemeral=True)
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
            message_lines.append(f"新しいスレッドを作成しました: {', '.join(new_threads)}。")
        if updated_threads:
            message_lines.append(f"既存スレッドを更新しました: {', '.join(updated_threads)}。")
        if not new_threads and not updated_threads:
            message_lines.append("すべてのチャレンジスレッドはすでに最新です。")

        await interaction.followup.send("\n".join(message_lines))
