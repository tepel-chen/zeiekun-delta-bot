from __future__ import annotations

import json
import urllib.parse
from pathlib import Path
from typing import Dict, List, Tuple

import discord
from challenge import Challenge


state_display = {
    "idea": "アイデア",
    "playtest": "プレイテスト",
    "done": "完成",
    "scrapped": "没",
}

status_color = {
    "idea": 0xed7ee9,
    "playtest": 0x3774e6,
    "done": 0x14f532,
}


def load_thread_state(state_file: Path) -> Dict[str, Dict[str, int]]:
    if not state_file.exists():
        return {}
    try:
        data = json.loads(state_file.read_text())
    except (json.JSONDecodeError, ValueError):
        return {}

    state: Dict[str, Dict[str, int]] = {}
    for key, value in data.items():
        if not isinstance(value, dict):
            continue
        state[str(key)] = value

    return state


def save_thread_state(state_file: Path, state: Dict[str, Dict[str, int]]) -> None:
    state_file.write_text(json.dumps(state, indent=2))


def format_thread_name(challenge: Challenge) -> str:
    display = challenge.display_name or challenge.folder_name
    return f"[{challenge.category}] {display}"


def build_challenge_embed(challenge: Challenge, repo_base: str) -> discord.Embed:
    title = challenge.display_name or challenge.folder_name or challenge.key
    colour = status_color.get(challenge.status, 0x8a8a8a)
    url = f"{repo_base}/tree/main/{urllib.parse.quote(challenge.challenge_path)}"

    embed = discord.Embed(
        title=title,
        description=challenge.description or "_No description provided yet._",
        colour=colour,
        url=url,
    )
    if challenge.difficulty:
        embed.add_field(name="Difficulty", value=challenge.difficulty, inline=True)
    if challenge.status:
        embed.add_field(
            name="Status",
            value=state_display.get(challenge.status, "不明"),
            inline=True,
        )
    if challenge.wave:
        embed.add_field(name="Wave", value=challenge.wave, inline=True)
    if challenge.authors:
        embed.add_field(
            name="Authors", value=", ".join(challenge.authors), inline=False
        )
    if challenge.tags:
        embed.add_field(name="Tags", value=", ".join(challenge.tags), inline=False)
    embed.set_footer(text=f"Challenge path: {challenge.challenge_path}")
    return embed


async def assure_tag(tag_name: str, forum: discord.ForumChannel) -> discord.ForumTag:
    for tag in forum.available_tags:
        if tag.name == tag_name:
            return tag
    return await forum.create_tag(name=tag_name)


async def build_challenge_tags(
    challenge: Challenge, forum: discord.ForumChannel
) -> List[discord.ForumTag]:
    res: List[discord.ForumTag] = []
    if challenge.category:
        res.append(await assure_tag(challenge.category, forum))
    status_label = state_display.get(challenge.status)
    if status_label:
        res.append(await assure_tag(status_label, forum))
    return res


def calculate_repo_base(repo_url: str) -> str:
    base = repo_url[:-4] if repo_url.endswith(".git") else repo_url
    return base.rstrip("/")


async def get_forum_channel(bot: discord.Client, forum_channel_id: int) -> discord.ForumChannel:
    channel = bot.get_channel(forum_channel_id)
    if channel is None:
        channel = await bot.fetch_channel(forum_channel_id)
    if not isinstance(channel, discord.ForumChannel):
        raise RuntimeError("FORUM_CHANNEL_ID must point to a Discord forum channel")
    return channel


async def ensure_challenge_threads(
    forum_channel: discord.ForumChannel,
    challenges: List[Challenge],
    state_file: Path,
    repo_base: str,
) -> Tuple[List[str], List[str]]:
    state = load_thread_state(state_file)
    created: List[str] = []
    updated: List[str] = []
    state_dirty = False

    for challenge in challenges:
        state_key = challenge.key
        record = state.get(state_key, {})
        thread_id = record.get("thread_id")
        message_id = record.get("message_id")
        cached_hash = record.get("hash")
        current_hash = challenge.file_hash

        tags = await build_challenge_tags(challenge, forum_channel)
        thread = forum_channel.get_thread(thread_id) if thread_id else None
        if thread is None:
            thread_name = format_thread_name(challenge)
            embed = build_challenge_embed(challenge, repo_base)
            thread, message = await forum_channel.create_thread(
                name=thread_name, embed=embed, applied_tags=tags
            )
            state[state_key] = {
                "thread_id": thread.id,
                "message_id": message.id,
                "hash": current_hash,
                "tag_ids": [tag.id for tag in tags],
            }
            created.append(state_key)
            state_dirty = True
            continue

        if current_hash is not None and current_hash != cached_hash:
            message_target_id = message_id or thread.id
            message = await thread.fetch_message(message_target_id)
            await message.edit(embed=build_challenge_embed(challenge, repo_base))
            if tags:
                await thread.add_tags(*tags)
            record["message_id"] = message.id
            record["hash"] = current_hash
            record["tag_ids"] = [tag.id for tag in tags]
            state[state_key] = record
            updated.append(state_key)
            state_dirty = True
        else:
            record.setdefault("thread_id", thread.id)
            if message_id:
                record.setdefault("message_id", message_id)
            record.setdefault("tag_ids", [tag.id for tag in tags])
            state[state_key] = record

    if state_dirty:
        save_thread_state(state_file, state)

    return created, updated
