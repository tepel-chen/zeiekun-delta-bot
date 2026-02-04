# Discord Bot Starter

Simple Python/discord.py bot whose source lives under `src/` (`src/main.py` plus commands in `src/command/`). `/chal hello` and `/chal pullrepo` are defined as slash commands that rely on the `.env` configuration; git interactions are centralized in `src/git.py`.

## Setup

1. Install dependencies:
   ```bash
   python -m pip install -r requirements.txt
   ```
2. Copy `.env.example` to `.env` and fill in the values:
   ```bash
   cp .env.example .env
   ```
   Then set `DISCORD_TOKEN`, `GITHUB_REPO_URL`, `GUILD_ID` (a test guild makes slash commands appear immediately after starting the bot), and `FORUM_CHANNEL_ID` (the Discord forum channel where challenge threads should be created).

3. Create the bot application in the Discord Developer Portal, enable the **bot** and **applications.commands** scopes, invite it to a server, and grant it the `applications.commands` and `send messages` permissions.

## Running

Start the bot with:

```bash
python src/main.py
```

After it logs in you can run `/chal hello` to receive `Hello {username}` and `/chal pullrepo` to sync the configured GitHub repo into `challenge_repo` and to populate a forum thread per challenge.

## Pulling a GitHub Repository via the Bot

In `.env`, set `GITHUB_REPO_URL`. The bot exposes `/chal pullrepo`, which clones the repository into the fixed `challenge_repo` directory if it is missing or runs `git pull` when that directory already contains the repository. After the sync, `/chal pullrepo` parses each `challenge.yml` in `challenge_repo/challenges`, opens a dedicated forum thread in the channel referenced by `FORUM_CHANNEL_ID`, and records the thread IDs plus a SHA-256 digest inside the local `challenge_threads.json` cache so reruns skip creating duplicates. When a challenge’s `challenge.yml` hash differs from the cached value, the command edits that thread’s first post so the content stays up to date.

### Private repositories

`/chal pullrepo` simply forwards to Git, so private repositories work as long as the host user is already authenticated. For HTTPS repositories you can either cache a Personal Access Token (PAT) with `git config --global credential.helper cache` or embed the PAT in the URL (`https://<PAT>@github.com/owner/repo.git`) provided `.env` stays secret. For SSH repositories, set `GITHUB_REPO_URL=git@github.com:owner/repo.git` and make sure the machine running the bot has the corresponding private key available (e.g., via `ssh-agent` and a configured `~/.ssh/config` entry).

Run `/chal pullrepo` from Discord (after inviting the bot with `applications.commands`) and the bot replies with success/failure feedback in the channel or as an ephemeral error message. The command always targets `challenge_repo`, and because `FORUM_CHANNEL_ID` is set it also keeps the configured forum channel up to date (thread IDs, tag assignments, and content hashes are cached in `challenge_threads.json`). Each thread’s first message is now sent as an embed (with tags mirrored in the embed and as forum tags), and when you rerun `/chal pullrepo` the embed plus forum tags are re-applied whenever the `challenge.yml` hash changes. Because `GUILD_ID` is required, the slash command syncs into that guild right away instead of waiting for global propagation.

## Notes

- `.env` is ignored by Git (see `.gitignore`), so never commit your token.
- `challenge_threads.json` tracks which forum thread belongs to which challenge, as well as the hashed `challenge.yml` digest used to detect updates, so it is ignored as well.
- For local testing, make sure the bot is invited to at least one server so it can register the slash command.
