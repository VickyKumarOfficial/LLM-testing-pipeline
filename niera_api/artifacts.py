"""Read run files from the local repository or private published archives."""

import asyncio
import hashlib
import io
import json
import os
import zipfile
from typing import Any

from fastapi import HTTPException

from niera_api import catalog
from niera_api.main_paths import RESULTS_DIR, run_directory


ALLOWED_ARTIFACTS = {
    "run.json",
    "results.jsonl",
    "performance.json",
    "performance.txt",
    "system_prompt.rendered.txt",
    "student_profile.json",
}
MAX_ARCHIVE_BYTES = 100 * 1024 * 1024


def remote_mode() -> bool:
    return os.environ.get("NIERA_API_STORAGE_BACKEND", "local").lower() == "remote"


def require_remote_database() -> None:
    if remote_mode() and not os.environ.get("DATABASE_URL"):
        raise HTTPException(
            status_code=503,
            detail="Remote storage requires a persistent DATABASE_URL",
        )


def published_run(run_id: str) -> dict[str, Any]:
    item = catalog.get_published_run(run_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return item


def get_manifest(run_id: str) -> dict[str, Any]:
    if remote_mode():
        require_remote_database()
        return published_run(run_id)["manifest"]
    path = run_directory(run_id)
    try:
        return json.loads((path / "run.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raise HTTPException(status_code=500, detail="Run manifest is unreadable") from None


def list_manifests() -> list[dict[str, Any]]:
    if remote_mode():
        require_remote_database()
        return [item["manifest"] for item in catalog.list_published_runs()]
    manifests = []
    if not RESULTS_DIR.is_dir():
        return manifests
    for path in sorted(RESULTS_DIR.iterdir(), reverse=True):
        if not path.is_dir() or not (path / "run.json").is_file():
            continue
        try:
            manifests.append(json.loads((path / "run.json").read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            continue
    return manifests


def _fetch_remote_archive(blob_path: str) -> bytes:
    async def fetch() -> bytes:
        try:
            from vercel.blob import AsyncBlobClient
        except ImportError as exc:
            raise HTTPException(status_code=503, detail="Vercel Blob SDK is unavailable") from exc
        try:
            async with AsyncBlobClient() as client:
                result = await client.get(blob_path, access="private")
        except Exception:
            raise HTTPException(status_code=502, detail="Could not read published run") from None
        if result is None or result.status_code != 200:
            raise HTTPException(status_code=404, detail="Published run artifact not found")
        # Vercel Blob SDK returns the body in `content` bytes, not as a stream.
        content = getattr(result, "content", None)
        if not isinstance(content, bytes):
            raise HTTPException(status_code=502, detail="Published run artifact response is invalid")
        if len(content) > MAX_ARCHIVE_BYTES:
            raise HTTPException(status_code=413, detail="Published run archive is too large")
        return content

    return asyncio.run(fetch())


def get_run_bundle(run_id: str) -> dict[str, bytes]:
    if remote_mode():
        require_remote_database()
        item = published_run(run_id)
        bundle = _fetch_remote_archive(item["blob_path"])
        if hashlib.sha256(bundle).hexdigest() != item["archive_sha256"]:
            raise HTTPException(status_code=502, detail="Published run archive failed integrity check")
        try:
            with zipfile.ZipFile(io.BytesIO(bundle), "r") as archive:
                names = archive.namelist()
                output = {}
                for name in item["artifact_names"]:
                    if name not in ALLOWED_ARTIFACTS or name not in names:
                        raise HTTPException(status_code=502, detail="Published run archive is invalid")
                    output[name] = archive.read(name)
                return output
        except (zipfile.BadZipFile, KeyError):
            raise HTTPException(status_code=502, detail="Published run archive is invalid") from None

    path = run_directory(run_id)
    output = {}
    for name in ALLOWED_ARTIFACTS:
        artifact_path = path / name
        if artifact_path.is_file():
            try:
                output[name] = artifact_path.read_bytes()
            except OSError:
                raise HTTPException(status_code=500, detail="Artifact is unreadable") from None
    return output


def get_artifact_bytes(run_id: str, name: str) -> bytes:
    if name not in ALLOWED_ARTIFACTS:
        raise HTTPException(status_code=404, detail="Artifact not found")
    bundle = get_run_bundle(run_id)
    if name not in bundle:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return bundle[name]


def get_results(run_id: str) -> list[dict[str, Any]]:
    try:
        content = get_artifact_bytes(run_id, "results.jsonl").decode("utf-8")
        rows = []
        for line_no, line in enumerate(content.splitlines(), start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError(f"line {line_no} is not an object")
            rows.append(row)
        return rows
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=500, detail="Run results are unreadable") from None


def require_run(run_id: str) -> dict[str, Any]:
    """Ensure that a run is available in the configured backend."""
    return get_manifest(run_id)
