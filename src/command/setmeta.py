from __future__ import annotations

from pathlib import Path
from typing import List

import discord
import yaml
from discord import Interaction, app_commands

from challenge import Challenge
from forum_sync import (
    calculate_repo_base,
    ensure_challenge_threads,
    get_forum_channel,
    load_thread_state,
)
from git import stage_commit_push, sync_repository


def register_set_command(
    group: app_commands.Group,
    bot: "discord.Client",
    forum_channel_id: int,
    challenge_repo_path: Path,
    thread_state_file: Path,
    repo_url: str,
) -> None:
    challenge_root = challenge_repo_path / "challenges"
    repo_base = calculate_repo_base(repo_url)

    @group.command(
        name="set", description="このスレッドに紐づくチャレンジのメタ情報を更新"
    )
    @app_commands.describe(
        status="新しいステータス",
        wave="新しいウェーブ",
        difficulty="新しい難易度",
        name="表示名の上書き",
    )
    async def set_metadata(
        interaction: Interaction,
        status: str | None = None,
        wave: str | None = None,
        difficulty: str | None = None,
        name: str | None = None,
    ) -> None:
        """Edit challenge metadata, push changes, and update the forum thread."""
        await interaction.response.defer(thinking=True)

        try:
            await sync_repository(repo_url, challenge_repo_path)
        except RuntimeError as exc:
            await interaction.followup.send(
                f"編集前のリポジトリ同期に失敗しました: {exc}", ephemeral=True
            )
            return

        if not isinstance(interaction.channel, discord.Thread):
            await interaction.followup.send(
                "このコマンドはチャレンジのフォーラムスレッド内で実行してください。", ephemeral=True
            )
            return

        state = load_thread_state(thread_state_file)
        challenge_key = next(
            (key for key, record in state.items() if record.get("thread_id") == interaction.channel.id),
            None,
        )
        if not challenge_key:
            await interaction.followup.send(
                "このスレッドに対応するチャレンジがキャッシュにありません。", ephemeral=True
            )
            return

        challenges = Challenge.collect_from_repo(challenge_root, challenge_repo_path)
        target = next((c for c in challenges if c.key == challenge_key), None)
        if not target:
            await interaction.followup.send(
                f"チャレンジ `{challenge_key}` が同期後に見つかりませんでした。", ephemeral=True
            )
            return

        challenge_file = challenge_repo_path / target.challenge_path / "challenge.yml"
        try:
            metadata = yaml.safe_load(challenge_file.read_text()) or {}
        except yaml.YAMLError as exc:
            await interaction.followup.send(
                f"{challenge_file} の解析に失敗しました: {exc}", ephemeral=True
            )
            return

        changed_fields: List[str] = []
        if status:
            metadata["status"] = status
            changed_fields.append("status")
        if wave:
            metadata["wave"] = int(wave)
            changed_fields.append("wave")
        if difficulty:
            metadata["difficulty"] = difficulty
            changed_fields.append("difficulty")
        if name:
            metadata["name"] = name
            changed_fields.append("name")

        if not changed_fields:
            await interaction.followup.send(
                "更新対象のフィールドが指定されていません。", ephemeral=True
            )
            return

        challenge_file.write_text(yaml.safe_dump(metadata, sort_keys=False))

        relative_path = Path(target.challenge_path) / "challenge.yml"
        try:
            await stage_commit_push(
                challenge_repo_path,
                [str(relative_path)],
                f"Update metadata for {challenge_key}",
            )
        except RuntimeError as exc:
            await interaction.followup.send(
                f"コミット／プッシュに失敗しました: {exc}", ephemeral=True
            )
            return

        updated_challenges = Challenge.collect_from_repo(challenge_root, challenge_repo_path)
        updated = next((c for c in updated_challenges if c.key == challenge_key), None)
        if not updated:
            await interaction.followup.send(
                f"編集後にチャレンジ `{challenge_key}` が見つかりませんでした。", ephemeral=True
            )
            return

        try:
            forum_channel = await get_forum_channel(bot, forum_channel_id)
            await ensure_challenge_threads(
                forum_channel, [updated], thread_state_file, repo_base
            )
        except RuntimeError as exc:
            await interaction.followup.send(
                f"スレッド更新に失敗しました: {exc}", ephemeral=True
            )
            return

        await interaction.followup.send(
            f"チャレンジ `{challenge_key}` の {', '.join(changed_fields)} を更新しました。"
        )
