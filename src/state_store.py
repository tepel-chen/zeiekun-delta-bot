from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Dict, Tuple


ThreadStateRecord = Dict[str, int | str | list[int]]
STATE_DB_PATH = Path(__file__).resolve().parent.parent / "state.sqlite3"


def _connect() -> sqlite3.Connection:
    STATE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(STATE_DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_state_db() -> None:
    with _connect() as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS thread_state (
                challenge_key TEXT PRIMARY KEY,
                thread_id INTEGER,
                message_id INTEGER,
                challenge_hash TEXT
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS thread_state_tags (
                challenge_key TEXT NOT NULL,
                tag_id INTEGER NOT NULL,
                PRIMARY KEY (challenge_key, tag_id),
                FOREIGN KEY (challenge_key) REFERENCES thread_state(challenge_key) ON DELETE CASCADE
            )
            """
        )
        connection.commit()


def load_thread_state() -> Dict[str, ThreadStateRecord]:
    initialize_state_db()
    with _connect() as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        rows = connection.execute(
            """
            SELECT
                ts.challenge_key,
                ts.thread_id,
                ts.message_id,
                ts.challenge_hash,
                tst.tag_id
            FROM thread_state AS ts
            LEFT JOIN thread_state_tags AS tst
                ON ts.challenge_key = tst.challenge_key
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
    challenge_key: str,
    record: ThreadStateRecord,
) -> None:
    initialize_state_db()
    tag_ids = record.get("tag_ids", [])
    if not isinstance(tag_ids, list):
        tag_ids = []

    with _connect() as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            """
            INSERT INTO thread_state (challenge_key, thread_id, message_id, challenge_hash)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(challenge_key) DO UPDATE SET
                thread_id=excluded.thread_id,
                message_id=excluded.message_id,
                challenge_hash=excluded.challenge_hash
            """,
            (
                challenge_key,
                record.get("thread_id"),
                record.get("message_id"),
                record.get("hash"),
            ),
        )
        connection.execute(
            "DELETE FROM thread_state_tags WHERE challenge_key = ?",
            (challenge_key,),
        )
        for tag_id in tag_ids:
            if not isinstance(tag_id, int):
                continue
            connection.execute(
                """
                INSERT INTO thread_state_tags (challenge_key, tag_id)
                VALUES (?, ?)
                """,
                (challenge_key, int(tag_id)),
            )
        connection.commit()


def get_thread_state_by_thread_id(thread_id: int) -> Tuple[str, ThreadStateRecord] | None:
    state = load_thread_state()
    for challenge_key, record in state.items():
        if record.get("thread_id") == thread_id:
            return challenge_key, record
    return None
