"""Persistent catalog for benchmark runs published to private object storage."""

import json
import os
import time
from typing import Any

from niera_api.shares import connect

DATABASE_URL = os.environ.get("DATABASE_URL")
PARAM = "%s" if DATABASE_URL else "?"


def ensure_catalog_table() -> None:
    conn = connect()
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS published_runs (
                run_id TEXT PRIMARY KEY,
                manifest_json TEXT NOT NULL,
                blob_path TEXT NOT NULL,
                artifact_names_json TEXT NOT NULL,
                archive_sha256 TEXT NOT NULL,
                status TEXT NOT NULL,
                published_at DOUBLE PRECISION NOT NULL
            )"""
        )
        conn.commit()
    finally:
        conn.close()


def stage_run(
    run_id: str,
    manifest: dict[str, Any],
    blob_path: str,
    artifact_names: list[str],
    archive_sha256: str,
) -> None:
    ensure_catalog_table()
    conn = connect()
    param = "%s" if os.environ.get("DATABASE_URL") else "?"
    try:
        conn.execute(
            f"""INSERT INTO published_runs
            (run_id, manifest_json, blob_path, artifact_names_json,
             archive_sha256, status, published_at)
            VALUES ({param}, {param}, {param}, {param}, {param}, 'uploading', {param})
            ON CONFLICT (run_id) DO UPDATE SET
                manifest_json = excluded.manifest_json,
                blob_path = excluded.blob_path,
                artifact_names_json = excluded.artifact_names_json,
                archive_sha256 = excluded.archive_sha256,
                status = 'uploading',
                published_at = excluded.published_at""",
            (
                run_id,
                json.dumps(manifest, ensure_ascii=False),
                blob_path,
                json.dumps(artifact_names),
                archive_sha256,
                time.time(),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def mark_published(run_id: str) -> None:
    ensure_catalog_table()
    conn = connect()
    param = "%s" if os.environ.get("DATABASE_URL") else "?"
    try:
        conn.execute(
            f"UPDATE published_runs SET status = 'published' WHERE run_id = {param}",
            (run_id,),
        )
        conn.commit()
    finally:
        conn.close()


def mark_failed(run_id: str) -> None:
    ensure_catalog_table()
    conn = connect()
    param = "%s" if os.environ.get("DATABASE_URL") else "?"
    try:
        conn.execute(
            f"UPDATE published_runs SET status = 'failed' WHERE run_id = {param}",
            (run_id,),
        )
        conn.commit()
    finally:
        conn.close()


def get_published_run(run_id: str) -> dict[str, Any] | None:
    ensure_catalog_table()
    conn = connect()
    try:
        row = conn.execute(
            f"SELECT * FROM published_runs WHERE run_id = {PARAM} AND status = 'published'",
            (run_id,),
        ).fetchone()
        if row is None:
            return None
        return {
            "run_id": row["run_id"],
            "manifest": json.loads(row["manifest_json"]),
            "blob_path": row["blob_path"],
            "artifact_names": json.loads(row["artifact_names_json"]),
            "archive_sha256": row["archive_sha256"],
            "status": row["status"],
            "published_at": row["published_at"],
        }
    finally:
        conn.close()


def list_published_runs() -> list[dict[str, Any]]:
    ensure_catalog_table()
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT * FROM published_runs WHERE status = 'published' ORDER BY published_at DESC"
        ).fetchall()
        return [
            {
                "run_id": row["run_id"],
                "manifest": json.loads(row["manifest_json"]),
                "blob_path": row["blob_path"],
                "artifact_names": json.loads(row["artifact_names_json"]),
                "archive_sha256": row["archive_sha256"],
                "status": row["status"],
                "published_at": row["published_at"],
            }
            for row in rows
        ]
    finally:
        conn.close()
