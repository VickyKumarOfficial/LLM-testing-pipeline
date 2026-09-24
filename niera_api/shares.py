"""Local SQLite store for scoped read-only share credentials.

This development store is intentionally replaceable. Serverless deployment
must use a persistent hosted database instead of the function filesystem.
"""

import hashlib
import json
import os
import secrets
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get("NIERA_API_DB_PATH", str(ROOT / ".api-data" / "shares.sqlite3")))


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 10000")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS shares (
            share_id TEXT PRIMARY KEY,
            token_hash TEXT NOT NULL UNIQUE,
            run_ids_json TEXT NOT NULL,
            allow_system_prompt INTEGER NOT NULL DEFAULT 0,
            allow_profile INTEGER NOT NULL DEFAULT 0,
            created_at REAL NOT NULL,
            expires_at REAL
        )"""
    )
    conn.commit()
    return conn


def metadata(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "share_id": row["share_id"],
        "run_ids": json.loads(row["run_ids_json"]),
        "artifacts": {
            "system_prompt": bool(row["allow_system_prompt"]),
            "profile": bool(row["allow_profile"]),
        },
        "created_at": row["created_at"],
        "expires_at": row["expires_at"],
    }


def create_share(
    run_ids: list[str],
    allow_system_prompt: bool,
    allow_profile: bool,
    expires_at: float | None,
) -> tuple[dict[str, Any], str]:
    share_id = str(uuid.uuid4())
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    created_at = time.time()
    conn = connect()
    try:
        conn.execute(
            """INSERT INTO shares
            (share_id, token_hash, run_ids_json, allow_system_prompt,
             allow_profile, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                share_id,
                token_hash,
                json.dumps(run_ids),
                int(allow_system_prompt),
                int(allow_profile),
                created_at,
                expires_at,
            ),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM shares WHERE share_id = ?", (share_id,)).fetchone()
        return metadata(row), token
    finally:
        conn.close()


def find_share_by_token(token: str) -> dict[str, Any] | None:
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    conn = connect()
    try:
        row = conn.execute(
            "SELECT * FROM shares WHERE token_hash = ?", (token_hash,)
        ).fetchone()
        if row is None:
            return None
        if row["expires_at"] is not None and row["expires_at"] <= time.time():
            return None
        return metadata(row)
    finally:
        conn.close()


def list_shares() -> list[dict[str, Any]]:
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT * FROM shares ORDER BY created_at DESC"
        ).fetchall()
        return [metadata(row) for row in rows]
    finally:
        conn.close()


def revoke_share(share_id: str) -> bool:
    conn = connect()
    try:
        cursor = conn.execute("DELETE FROM shares WHERE share_id = ?", (share_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()
