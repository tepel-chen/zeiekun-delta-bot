from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict, List, Tuple


ThreadStateRecord = Dict[str, int | str | list[int]]
STATE_DB_PATH = Path(__file__).resolve().parent.parent / "branch_state.sqlite3"


def _connect() -> sqlite3.Connection:
    STATE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(STATE_DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_state_db() -> None:
    with _connect() as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS followed_branches (
                branch_name TEXT PRIMARY KEY
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS thread_state (
                branch_name TEXT NOT NULL,
                challenge_key TEXT NOT NULL,
                thread_id INTEGER,
                message_id INTEGER,
                challenge_hash TEXT,
                PRIMARY KEY (branch_name, challenge_key)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS thread_state_tags (
                branch_name TEXT NOT NULL,
                challenge_key TEXT NOT NULL,
                tag_id INTEGER NOT NULL,
                PRIMARY KEY (branch_name, challenge_key, tag_id),
                FOREIGN KEY (branch_name, challenge_key) REFERENCES thread_state(branch_name, challenge_key)
                    ON DELETE CASCADE
            )
            """
        )
        connection.commit()


def list_followed_branches() -> List[str]:
    with _connect() as connection:
        rows = connection.execute(
            "SELECT branch_name FROM followed_branches ORDER BY branch_name"
        ).fetchall()
    return [str(row["branch_name"]) for row in rows]


def follow_branch(branch_name: str) -> bool:
    with _connect() as connection:
        cursor = connection.execute(
            "INSERT OR IGNORE INTO followed_branches (branch_name) VALUES (?)",
            (branch_name,),
        )
        connection.commit()
    return cursor.rowcount > 0


def unfollow_branch(branch_name: str) -> int:
    with _connect() as connection:
        connection.execute("DELETE FROM thread_state WHERE branch_name = ?", (branch_name,))
        cursor = connection.execute(
            "DELETE FROM followed_branches WHERE branch_name = ?",
            (branch_name,),
        )
        connection.commit()
    return cursor.rowcount


def load_thread_state() -> Dict[str, ThreadStateRecord]:
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT
                ts.branch_name,
                ts.challenge_key,
                ts.thread_id,
                ts.message_id,
                ts.challenge_hash,
                tst.tag_id
            FROM thread_state AS ts
            LEFT JOIN thread_state_tags AS tst
                ON ts.branch_name = tst.branch_name
               AND ts.challenge_key = tst.challenge_key
            ORDER BY ts.challenge_key, tst.tag_id
            """
        ).fetchall()

    state: Dict[str, ThreadStateRecord] = {}
    for row in rows:
        challenge_key = str(row["challenge_key"])
        if challenge_key not in state:
            state[challenge_key] = {
                "thread_id": row["thread_id"],
                "message_id": row["message_id"],
                "hash": row["challenge_hash"],
                "tag_ids": [],
            }
        if row["tag_id"] is not None:
            state[challenge_key]["tag_ids"].append(int(row["tag_id"]))

    return state


def upsert_thread_state(
    branch_name: str,
    challenge_key: str,
    record: ThreadStateRecord,
) -> None:
    tag_ids = record.get("tag_ids", [])
    if not isinstance(tag_ids, list):
        tag_ids = []

    with _connect() as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            "DELETE FROM thread_state_tags WHERE challenge_key = ?",
            (challenge_key,),
        )
        connection.execute(
            "DELETE FROM thread_state WHERE challenge_key = ?",
            (challenge_key,),
        )
        connection.execute(
            """
            INSERT INTO thread_state (
                branch_name, challenge_key, thread_id, message_id, challenge_hash
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                branch_name,
                challenge_key,
                record.get("thread_id"),
                record.get("message_id"),
                record.get("hash"),
            ),
        )
        for tag_id in tag_ids:
            if not isinstance(tag_id, int):
                continue
            connection.execute(
                """
                INSERT INTO thread_state_tags (branch_name, challenge_key, tag_id)
                VALUES (?, ?, ?)
                """,
                (branch_name, challenge_key, int(tag_id)),
            )
        connection.commit()


def get_thread_state_by_thread_id(
    thread_id: int,
) -> Tuple[str, str, ThreadStateRecord] | None:
    with _connect() as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        row = connection.execute(
            """
            SELECT branch_name, challenge_key, message_id, challenge_hash
            FROM thread_state
            WHERE thread_id = ?
            """,
            (thread_id,),
        ).fetchone()
        if row is None:
            return None
        tag_rows = connection.execute(
            """
            SELECT tag_id
            FROM thread_state_tags
            WHERE branch_name = ? AND challenge_key = ?
            ORDER BY tag_id
            """,
            (row["branch_name"], row["challenge_key"]),
        ).fetchall()

    return (
        str(row["branch_name"]),
        str(row["challenge_key"]),
        {
            "thread_id": thread_id,
            "message_id": row["message_id"],
            "hash": row["challenge_hash"],
            "tag_ids": [int(tag_row["tag_id"]) for tag_row in tag_rows],
        },
    )
