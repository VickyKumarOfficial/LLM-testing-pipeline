"""Validate and publish owner-supplied run archives to hosted storage."""

import hashlib
import io
import json
import os
import zipfile
from pathlib import PurePath
from typing import Any

from fastapi import HTTPException

from niera_api import artifacts, catalog
from niera_api.main_paths import RUN_ID_RE


MAX_UPLOAD_BYTES = 4 * 1024 * 1024
MAX_ARCHIVE_BYTES = 100 * 1024 * 1024
ALLOWED_ARTIFACTS = {
    "run.json",
    "results.jsonl",
    "performance.json",
    "performance.txt",
    "system_prompt.rendered.txt",
    "student_profile.json",
}


def sanitize_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    safe = dict(manifest)
    safe.pop("profile_path", None)
    dataset = safe.get("dataset")
    if isinstance(dataset, str):
        safe["dataset"] = PurePath(dataset.replace("\\", "/")).name
    return safe


def sanitize_results(content: bytes, run_id: str, test_count: int) -> bytes:
    seen: set[str] = set()
    rows = []
    try:
        for line_no, line in enumerate(content.decode("utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict) or row.get("run_id") != run_id:
                raise ValueError(f"invalid run_id at result row {line_no}")
            test_id = row.get("test_id")
            if not isinstance(test_id, str) or not test_id or test_id in seen:
                raise ValueError(f"missing or duplicate test_id at result row {line_no}")
            seen.add(test_id)
            metadata = row.get("metadata")
            if isinstance(metadata, dict):
                metadata = dict(metadata)
                metadata.pop("thinking", None)
                row["metadata"] = metadata
            rows.append(json.dumps(row, ensure_ascii=False))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("results.jsonl is not valid UTF-8 JSONL") from exc
    if len(seen) != test_count:
        raise ValueError(
            f"run is incomplete: manifest has {test_count} tests, results have {len(seen)}"
        )
    return ("\n".join(rows) + "\n").encode("utf-8")


def sanitize_archive(content: bytes) -> tuple[bytes, dict[str, Any], list[str], str]:
    if not content or len(content) > MAX_UPLOAD_BYTES:
        raise ValueError("ZIP upload must be no larger than 4 MB")
    try:
        source = zipfile.ZipFile(io.BytesIO(content))
    except (OSError, zipfile.BadZipFile) as exc:
        raise ValueError("upload is not a valid ZIP archive") from exc

    with source:
        infos = source.infolist()
        names = [info.filename for info in infos]
        if len(names) != len(set(names)):
            raise ValueError("ZIP archive contains duplicate filenames")
        for info in infos:
            if info.is_dir() or "\\" in info.filename or PurePath(info.filename).name != info.filename:
                raise ValueError("ZIP archive contains an invalid filename")
            if info.filename not in ALLOWED_ARTIFACTS:
                raise ValueError("ZIP archive contains an unsupported artifact")
        if not {"run.json", "results.jsonl"}.issubset(names):
            raise ValueError("ZIP archive must include run.json and results.jsonl")
        if sum(info.file_size for info in infos) > MAX_ARCHIVE_BYTES:
            raise ValueError("ZIP archive expands beyond the 100 MB limit")

        try:
            manifest = json.loads(source.read("run.json"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("run.json is missing or invalid") from exc
        run_id = manifest.get("run_id") if isinstance(manifest, dict) else None
        test_count = manifest.get("test_count") if isinstance(manifest, dict) else None
        if not isinstance(run_id, str) or not RUN_ID_RE.fullmatch(run_id):
            raise ValueError("run.json has an invalid run_id")
        if not isinstance(test_count, int) or test_count < 1:
            raise ValueError("run.json test_count must be a positive integer")

        sanitized_manifest = sanitize_manifest(manifest)
        sanitized_rows = sanitize_results(source.read("results.jsonl"), run_id, test_count)
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as output:
            output.writestr(
                "run.json",
                json.dumps(sanitized_manifest, ensure_ascii=False, indent=2) + "\n",
            )
            output.writestr("results.jsonl", sanitized_rows)
            if "system_prompt.rendered.txt" in names:
                output.writestr(
                    "system_prompt.rendered.txt",
                    source.read("system_prompt.rendered.txt"),
                )
            if "student_profile.json" in names:
                output.writestr("student_profile.json", source.read("student_profile.json"))
            for name in ("performance.json", "performance.txt"):
                if name in names:
                    data = source.read(name)
                    if name == "performance.json":
                        try:
                            performance = json.loads(data)
                        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                            raise ValueError("performance.json is invalid") from exc
                        if isinstance(performance, dict):
                            performance = sanitize_manifest(performance)
                            data = json.dumps(performance, ensure_ascii=False, indent=2).encode()
                    output.writestr(name, data)

    sanitized = buffer.getvalue()
    digest = hashlib.sha256(sanitized).hexdigest()
    return sanitized, sanitized_manifest, [name for name in names if name in ALLOWED_ARTIFACTS], digest


def publish_archive(content: bytes) -> dict[str, Any]:
    sanitized, manifest, artifact_names, digest = sanitize_archive(content)
    if not artifacts.remote_mode():
        raise HTTPException(status_code=503, detail="Remote storage is not enabled")
    if not os.environ.get("DATABASE_URL"):
        raise HTTPException(status_code=503, detail="Remote database is not configured")
    run_id = manifest["run_id"]
    blob_path = f"benchmark-runs/{run_id}.zip"
    catalog.stage_run(run_id, manifest, blob_path, artifact_names, digest)
    try:
        from vercel.blob import BlobClient

        token = os.environ.get("BLOB_READ_WRITE_TOKEN")
        client = BlobClient()
        client.put(
            blob_path,
            sanitized,
            access="private",
            content_type="application/zip",
            overwrite=True,
            token=token,
        )
        catalog.mark_published(run_id)
    except Exception as exc:
        catalog.mark_failed(run_id)
        raise HTTPException(status_code=502, detail="Run archive upload failed") from exc
    return {"run_id": run_id, "test_count": manifest["test_count"], "status": "published"}
