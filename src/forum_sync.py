from __future__ import annotations

import urllib.parse
from typing import List, Tuple

import discord
from challenge import Challenge
from state_store import load_thread_state, upsert_thread_state


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


def format_thread_name(challenge: Challenge) -> str:
    display = challenge.display_name or challenge.folder_name
    return f"[{challenge.category}/{challenge.difficulty}] {display}"


def build_challenge_embed(challenge: Challenge, repo_base: str) -> discord.Embed:
    title = challenge.display_name or challenge.folder_name or challenge.key
    colour = status_color.get(challenge.status, 0x8a8a8a)
    url = f"{repo_base}/tree/{urllib.parse.quote(challenge.branch_name)}/{urllib.parse.quote(challenge.challenge_path)}"

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
    embed.set_footer(text=f"Branch: {challenge.branch_name} | Challenge path: {challenge.challenge_path}")
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


def resolve_forum_tags_by_ids(
    forum: discord.ForumChannel, tag_ids: List[int]
) -> List[discord.ForumTag]:
    tags_by_id = {tag.id: tag for tag in forum.available_tags}
    return [tags_by_id[tag_id] for tag_id in tag_ids if tag_id in tags_by_id]


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
    repo_base: str,
) -> Tuple[List[str], List[str]]:
    if not challenges:
        return [], []

    state = load_thread_state()
    created: List[str] = []
    updated: List[str] = []

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
            upsert_thread_state(challenge.branch_name, state_key, state[state_key])
            created.append(state_key)
            continue

        if current_hash is not None and current_hash != cached_hash:
            message_target_id = message_id or thread.id
            message = await thread.fetch_message(message_target_id)
            await message.edit(embed=build_challenge_embed(challenge, repo_base))
            previous_tag_ids = record.get("tag_ids", [])
            if not isinstance(previous_tag_ids, list):
                previous_tag_ids = []
            previous_tags = resolve_forum_tags_by_ids(
                forum_channel,
                [tag_id for tag_id in previous_tag_ids if isinstance(tag_id, int)],
            )
            next_tag_ids = [tag.id for tag in tags]
            tags_to_remove = [tag for tag in previous_tags if tag.id not in next_tag_ids]
            tags_to_add = [tag for tag in tags if tag.id not in previous_tag_ids]
            if tags_to_remove:
                await thread.remove_tags(*tags_to_remove)
            if tags_to_add:
                await thread.add_tags(*tags_to_add)
            record["message_id"] = message.id
            record["hash"] = current_hash
            record["tag_ids"] = next_tag_ids
            state[state_key] = record
            upsert_thread_state(challenge.branch_name, state_key, record)
            updated.append(state_key)
        else:
            record.setdefault("thread_id", thread.id)
            if message_id:
                record.setdefault("message_id", message_id)
            record.setdefault("tag_ids", [tag.id for tag in tags])
            state[state_key] = record
            upsert_thread_state(challenge.branch_name, state_key, record)

    return created, updated
