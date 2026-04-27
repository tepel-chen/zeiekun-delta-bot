from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote

from dotenv import load_dotenv


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
GITHUB_REPO_URL = require_env_variable("GITHUB_REPO_URL")
CATEGORY_ID = require_env_int("CATEGORY_ID")
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CHALLENGE_REPOS_PATH = PROJECT_ROOT / "challenge_repos"

if not GITHUB_REPO_URL.startswith("git@github.com:"):
    raise SystemExit("GITHUB_REPO_URL must use git@github.com:<owner>/<repo>.git")


def get_challenge_repo_path(branch_name: str) -> Path:
    return CHALLENGE_REPOS_PATH / quote(branch_name, safe="")
