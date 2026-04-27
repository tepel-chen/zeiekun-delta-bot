# ゼイエくんΔ

ゼイエくんΔはCTF問題作成管理Discord BOTです

1. 依存パッケージをインストールします。
   ```bash
   python -m pip install -r requirements.txt
   ```
2. `.env.example` を `.env` にコピーし、必要な値を記入します。
   ```bash
   cp .env.example .env
   ```
   `DISCORD_TOKEN`、`GUILD_ID`、`FORUM_CHANNEL_ID`、`GITHUB_REPO_URL` など、Bot と対象フォーラム／リポジトリ用の環境変数を設定してください。`GITHUB_REPO_URL` は `git@github.com:owner/repo.git` 形式を前提にしています。
   スレッド状態は `branch_state.sqlite3` に保存され、ブランチごとの checkout は `challenge_repos/` 以下に作られます。
3. Discord デベロッパーポータルでアプリケーションを作成し、**bot** スコープで以下を有効化してください。
* Manage Channels
* Send Messages
* Read Message History
* Use Slash Commands
4. Bot を起動します。
   ```bash
   python src/main.py
   ```
