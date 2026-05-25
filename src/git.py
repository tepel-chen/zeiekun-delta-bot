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
    return await sync_repository_branch(repo_url, repo_path, "main")


async def local_branch_exists(repo_path: Path, branch_name: str) -> bool:
    try:
        await run_git_command(
            ["git", "-C", str(repo_path), "rev-parse", "--verify", branch_name]
        )
    except RuntimeError:
        return False
    return True


async def sync_repository_branch(repo_url: str, repo_path: Path, branch_name: str) -> str:
    git_dir = repo_path / ".git"
    if git_dir.is_dir():
        await run_git_command(["git", "-C", str(repo_path), "fetch", "origin", branch_name])
        if await local_branch_exists(repo_path, branch_name):
            await run_git_command(["git", "-C", str(repo_path), "checkout", branch_name])
        else:
            await run_git_command(
                [
                    "git",
                    "-C",
                    str(repo_path),
                    "checkout",
                    "-b",
                    branch_name,
                    "--track",
                    f"origin/{branch_name}",
                ]
            )
        await run_git_command(
            ["git", "-C", str(repo_path), "reset", "--hard", f"origin/{branch_name}"]
        )
        return f"`{branch_name}` ブランチの最新状態を取得しました。"

    repo_path.parent.mkdir(parents=True, exist_ok=True)
    await run_git_command(
        ["git", "clone", "--branch", branch_name, "--single-branch", repo_url, str(repo_path)]
    )
    return f"`{branch_name}` ブランチを `{repo_path.name}` にクローンしました。"


async def stage_commit_push(
    repo_path: Path, files: List[str], message: str, branch_name: str
) -> None:
    await run_git_command(["git", "-C", str(repo_path), "add", *files])
    await run_git_command(["git", "-C", str(repo_path), "commit", "-m", message])
    await run_git_command(["git", "-C", str(repo_path), "push", "origin", branch_name])
