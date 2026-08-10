from __future__ import annotations

import discord
from discord import Interaction, app_commands

from challenge import Challenge, choose_preferred_challenges
from command.utils import ensure_in_category
from config import FORUM_CHANNEL_ID, GITHUB_REPO_URL, get_challenge_repo_path
from forum_sync import calculate_repo_base, ensure_challenge_threads, get_forum_channel
from git import sync_repository_branch
from state_store import follow_branch, list_followed_branches


def register_pull_command(
    group: app_commands.Group,
    bot: discord.Client,
) -> None:
    repo_base = calculate_repo_base(GITHUB_REPO_URL)

    @group.command(
        name="pull", description="Githubのレポジトリと同期してフォーラムスレッドを用意する"
    )
    @app_commands.describe(branch_name="更新するブランチ名。未指定ならフォロー中の全ブランチ")
    async def pull(interaction: Interaction, branch_name: str | None = None) -> None:
        if not await ensure_in_category(interaction):
            return
        """Clone or update the repository and keep forum threads aligned."""
        await interaction.response.defer(thinking=True)

        branches = [branch_name] if branch_name else list_followed_branches()
        normalized_branches: list[str] = []
        for target_branch in branches + ["main"]:
            normalized_branch = target_branch.strip()
            if normalized_branch and normalized_branch not in normalized_branches:
                normalized_branches.append(normalized_branch)

        try:
            forum_channel = await get_forum_channel(bot, FORUM_CHANNEL_ID)
            message_lines: list[str] = []
            created_branches: list[str] = []
            all_challenges: list[Challenge] = []

            for normalized_branch in normalized_branches:
                repo_path = get_challenge_repo_path(normalized_branch)
                challenge_root = repo_path / "challenges"
                action = await sync_repository_branch(
                    GITHUB_REPO_URL, repo_path, normalized_branch
                )
                was_followed = follow_branch(normalized_branch)
                if was_followed:
                    created_branches.append(normalized_branch)

                all_challenges.extend(Challenge.collect_from_repo(
                    challenge_root, repo_path, normalized_branch
                ))

                branch_lines = [action]
                message_lines.append("\n".join(branch_lines))

            selected_challenges = choose_preferred_challenges(all_challenges)
            new_threads, updated_threads = await ensure_challenge_threads(
                forum_channel,
                selected_challenges,
                repo_base,
            )
        except RuntimeError as exc:
            await interaction.followup.send(
                f"リポジトリ同期またはスレッド更新に失敗しました: {exc}", ephemeral=True
            )
            return

        if created_branches:
            message_lines.insert(
                0,
                f"フォローを追加しました: {', '.join(created_branches)}。",
            )
        if new_threads:
            message_lines.append(f"新しいスレッドを作成しました: {', '.join(new_threads)}。")
        if updated_threads:
            message_lines.append(f"既存スレッドを更新しました: {', '.join(updated_threads)}。")
        if not new_threads and not updated_threads:
            message_lines.append("すべてのチャレンジスレッドはすでに最新です。")

        await interaction.followup.send("\n".join(message_lines))
