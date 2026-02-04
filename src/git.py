import asyncio
from pathlib import Path
from typing import List


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


async def sync_repository(repo_url: str, repo_path: Path) -> str:
    git_dir = repo_path / ".git"
    if git_dir.is_dir():
        await run_git_command(["git", "-C", str(repo_path), "pull"])
        return f"Pulled latest changes into `{repo_path.name}`."

    await run_git_command(["git", "clone", repo_url, str(repo_path)])
    return f"Cloned `{repo_url}` into `{repo_path.name}`."


async def stage_commit_push(repo_path: Path, files: List[str], message: str) -> None:
    await run_git_command(["git", "-C", str(repo_path), "add", *files])
    await run_git_command(["git", "-C", str(repo_path), "commit", "-m", message])
    await run_git_command(["git", "-C", str(repo_path), "push", "origin", "main"])
