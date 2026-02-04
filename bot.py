import asyncio
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple
import discord
from discord import app_commands
from dotenv import load_dotenv
import yaml
import hashlib
import urllib.parse


def require_env_variable(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise SystemExit(f"{name} is not set in .env")
    return value


def require_env_int(name: str) -> int:
    value = require_env_variable(name)
    try:
        return int(value)
    except ValueError as exc:
        raise SystemExit(f"{name} must be an integer") from exc


load_dotenv(".env")

DISCORD_TOKEN = require_env_variable("DISCORD_TOKEN")
GUILD_ID = require_env_int("GUILD_ID")
FORUM_CHANNEL_ID = require_env_int("FORUM_CHANNEL_ID")

BASE_DIR = Path(__file__).resolve().parent
CHALLENGE_REPO_PATH = BASE_DIR / "challenge_repo"
CHALLENGE_ROOT = CHALLENGE_REPO_PATH / "challenges"
THREAD_STATE_FILE = BASE_DIR / "challenge_threads.json"

intents = discord.Intents.default()
intents.guilds = True
intents.members = True

bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)
guild_obj = discord.Object(id=GUILD_ID)
chal_commands = app_commands.Group(name="chal", description="チャレンジ制作関連")
tree.add_command(chal_commands, guild=guild_obj)

state_display = {
    "idea": "アイデア",
    "playtest": "プレイテスト",
    "done": "完成",
    "scrapped": "没"
}

def load_thread_state() -> Dict[str, Dict[str, int]]:
    if not THREAD_STATE_FILE.exists():
        return {}
    try:
        data = json.loads(THREAD_STATE_FILE.read_text())
    except (json.JSONDecodeError, ValueError):
        return {}

    state: Dict[str, Dict[str, int]] = {}
    for key, value in data.items():
        if isinstance(value, dict):
            thread_id = value.get("thread_id")
            message_id = value.get("message_id")
        else:
            thread_id = value
            message_id = None

        try:
            tid = int(thread_id)
        except (TypeError, ValueError):
            continue

        record: Dict[str, int] = {"thread_id": tid}
        if message_id is not None:
            try:
                record["message_id"] = int(message_id)
            except (TypeError, ValueError):
                pass

        state[str(key)] = record

    return state


def save_thread_state(state: Dict[str, Dict[str, int]]) -> None:
    THREAD_STATE_FILE.write_text(json.dumps(state, indent=2))


def collect_challenges() -> List[Dict[str, Any]]:
    challenges: List[Dict[str, Any]] = []
    if not CHALLENGE_ROOT.is_dir():
        return challenges

    for challenge_file in CHALLENGE_ROOT.rglob("challenge.yml"):
        try:
            metadata = yaml.safe_load(challenge_file.read_text())
        except yaml.YAMLError:
            continue

        if not isinstance(metadata, dict):
            continue

        relative = challenge_file.parent.relative_to(CHALLENGE_REPO_PATH)
        relative_parts = relative.parts
        if len(relative_parts) < 2:
            continue
        category = relative_parts[1]
        name = relative_parts[-1]

        key = metadata.get("key")
        if not key:
            continue

        description_value = metadata.get("description")
        description = description_value.strip() if isinstance(description_value, str) else None

        def to_list(value: Any) -> List[str]:
            if isinstance(value, list):
                return [str(item).strip() for item in value if item]
            if isinstance(value, str):
                item = value.strip()
                return [item] if item else []
            return []

        authors = to_list(metadata.get("authors"))
        tags = to_list(metadata.get("tags"))

        difficulty_value = metadata.get("difficulty")
        difficulty = str(difficulty_value).strip() if difficulty_value else None

        status_value = metadata.get("status")
        status = str(status_value).strip() if status_value else None

        wave_value = metadata.get("wave")
        wave = str(wave_value).strip() if wave_value else None

        challenges.append(
            {
                "key": key,
                "category": category,
                "name": name,
                "description": description,
                "difficulty": difficulty,
                "status": status,
                "wave": wave,
                "authors": authors,
                "tags": tags,
                "challenge_path": str(relative),
                "file_hash": hashlib.sha256(challenge_file.read_bytes()).hexdigest(),
            }
        )

    return challenges


def format_thread_name(challenge: Dict[str, Any]) -> str:
    return f"[{challenge.get('category', 'unknown')}] {challenge.get('name')}"


status_color = {
    "idea": 0xed7ee9,
    "playtest": 0x3774e6,
    "done": 0x14f532,
}
def build_challenge_embed(challenge: Dict[str, Any]) -> discord.Embed:
    title = challenge.get("name") or challenge["key"]
    colour = status_color.get(challenge.get("status"), 0x8a8a8a)

    repo_url = require_env_variable("GITHUB_REPO_URL")[:-4]
    url = f"{repo_url}/tree/main/{urllib.parse.quote(challenge['challenge_path'])}"

    embed = discord.Embed(
        title=title, 
        description=challenge.get("description") or "_No description provided yet._",
        colour=colour,
        url=url
    )
    if challenge.get("difficulty"):
        embed.add_field(name="Difficulty", value=challenge["difficulty"], inline=True)
    if challenge.get("status"):
        embed.add_field(name="Status", value=state_display.get(challenge["status"], "不明"), inline=True)
    if challenge.get("wave"):
        embed.add_field(name="Wave", value=challenge["wave"], inline=True)
    if challenge.get("authors"):
        embed.add_field(name="Authors", value=", ".join(challenge["authors"]), inline=False)
    if challenge.get("tags"):
        embed.add_field(name="Tags", value=", ".join(challenge["tags"]), inline=False)
    return embed

async def assure_tag(tag_name: str, forum: discord.ForumChannel) -> discord.ForumTag:
    for tag in forum.available_tags:
        if tag.name == tag_name:
            return tag
    
    return await forum.create_tag(name=tag_name)

async def build_challenge_tags(challenge: Dict[str, Any], forum: discord.ForumChannel) -> List[discord.ForumTag]:
    res = []
    res.append(await assure_tag(challenge["category"], forum))
    status_display = state_display.get(challenge["status"])
    if status_display:
        res.append(await assure_tag(status_display, forum))
    return res


async def run_git_command(cmd: List[str], cwd: str | None = None) -> bytes:
    process = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        raise RuntimeError(
            f"git command failed ({' '.join(cmd)}): "
            f"{stderr.decode().strip() or 'see server logs'}"
        )
    return stdout


async def get_forum_channel() -> discord.ForumChannel:
    channel = bot.get_channel(FORUM_CHANNEL_ID)
    if channel is None:
        channel = await bot.fetch_channel(FORUM_CHANNEL_ID)

    if not isinstance(channel, discord.ForumChannel):
        raise RuntimeError("FORUM_CHANNEL_ID must point to a Discord forum channel")

    return channel


async def ensure_challenge_threads(
    forum_channel: discord.ForumChannel, challenges: List[Dict[str, Any]]
) -> Tuple[List[str], List[str]]:
    state = load_thread_state()
    created: List[str] = []
    updated: List[str] = []
    state_dirty = False

    for challenge in challenges:
        state_key = challenge['key']
        record = state.get(state_key, {})
        thread_id = record.get("thread_id")
        message_id = record.get("message_id")
        cached_hash = record.get("hash")
        current_hash = challenge.get("file_hash")

        thread = forum_channel.get_thread(thread_id) if thread_id else None
        if thread is None:
            thread_name = format_thread_name(challenge)
            embed = build_challenge_embed(challenge)
            tags = await build_challenge_tags(challenge, forum_channel)
            thread, message = await forum_channel.create_thread(
                name=thread_name, embed=embed
            )
            await thread.add_tags(*tags)
            state[state_key] = {
                "thread_id": thread.id,
                "message_id": message.id,
                "hash": current_hash,
            }
            created.append(state_key)
            state_dirty = True
            continue

        if current_hash is not None and current_hash != cached_hash:
            message_target_id = message_id or thread.id
            message = await thread.fetch_message(message_target_id)
            await message.edit(embed=build_challenge_embed(challenge))

            tags = await build_challenge_tags(challenge, forum_channel)
            await thread.add_tags(*tags)

            record["message_id"] = message.id
            record["hash"] = current_hash
            state[state_key] = record
            updated.append(state_key)
            state_dirty = True
        else:
            record.setdefault("thread_id", thread.id)
            if message_id:
                record.setdefault("message_id", message_id)
            state[state_key] = record

    if state_dirty:
        save_thread_state(state)

    return created, updated


@chal_commands.command(name="hello", description="say hello")
async def hello(interaction: discord.Interaction) -> None:
    """Respond with a personalized greeting."""
    await interaction.response.send_message(f"Hello {interaction.user.display_name}")


@chal_commands.command(
    name="pullrepo", description="Githubのレポジトリと同期してフォーラムスレッドを用意する"
)
async def pullrepo(interaction: discord.Interaction) -> None:
    """Clone or update the repository referenced in `.env` and create archived threads for each challenge."""
    repo_url = require_env_variable("GITHUB_REPO_URL")
    clone_dir = CHALLENGE_REPO_PATH
    git_dir = clone_dir / ".git"

    await interaction.response.defer(thinking=True)

    try:
        if git_dir.is_dir():
            await run_git_command(["git", "-C", str(clone_dir), "pull"])
            action = f"Pulled latest changes into `{clone_dir.name}`."
        else:
            await run_git_command(["git", "clone", repo_url, str(clone_dir)])
            action = f"Cloned `{repo_url}` into `{clone_dir.name}`."
    except RuntimeError as exc:
        await interaction.followup.send(f"Failed to sync repository: {exc}", ephemeral=True)
        return

    try:
        forum_channel = await get_forum_channel()
        new_threads, updated_threads = await ensure_challenge_threads(
            forum_channel, collect_challenges()
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


@bot.event
async def on_ready() -> None:
    try:
        await tree.sync(guild=guild_obj)
        print(f"Synced commands to guild {guild_obj.id}")
    except Exception:
        print("Failed to sync commands")

    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("Ready to receive / commands.")


if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
