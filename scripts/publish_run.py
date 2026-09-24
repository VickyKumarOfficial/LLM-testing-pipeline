#!/usr/bin/env python3
"""Validate and publish one completed run to private Vercel Blob storage."""

import argparse
import hashlib
import io
import json
import os
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from niera_api import catalog  # noqa: E402
from niera_api.main_paths import RESULTS_DIR, RUN_ID_RE  # noqa: E402


MAX_ARCHIVE_BYTES = 100 * 1024 * 1024
BASE_ARTIFACTS = (
    "run.json",
    "results.jsonl",
    "performance.json",
    "performance.txt",
)


def validate_run(run_id: str, include_prompt: bool, include_profile: bool):
    if not RUN_ID_RE.fullmatch(run_id):
        raise ValueError("run_id has an invalid format")
    run_dir = (RESULTS_DIR / run_id).resolve(strict=True)
    run_dir.relative_to(RESULTS_DIR.resolve(strict=True))
    if not run_dir.is_dir():
        raise ValueError("run directory was not found")

    try:
        manifest = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("run.json is missing or invalid") from exc
    if manifest.get("run_id") != run_id:
        raise ValueError("run.json run_id does not match the directory")
    expected_rows = manifest.get("test_count")
    if not isinstance(expected_rows, int) or expected_rows < 1:
        raise ValueError("manifest test_count must be a positive integer")

    result_path = run_dir / "results.jsonl"
    seen_ids: set[str] = set()
    try:
        with result_path.open(encoding="utf-8") as source:
            for line_no, line in enumerate(source, start=1):
                if not line.strip():
                    continue
                row = json.loads(line)
                if not isinstance(row, dict) or row.get("run_id") != run_id:
                    raise ValueError(f"invalid run_id in results.jsonl line {line_no}")
                test_id = row.get("test_id")
                if not isinstance(test_id, str) or not test_id or test_id in seen_ids:
                    raise ValueError(f"missing or duplicate test_id at line {line_no}")
                seen_ids.add(test_id)
    except OSError as exc:
        raise ValueError("results.jsonl is missing or unreadable") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"results.jsonl contains invalid JSON: {exc}") from exc
    if len(seen_ids) != expected_rows:
        raise ValueError(
            f"run is incomplete: manifest has {expected_rows} tests, results have {len(seen_ids)}"
        )

    names = [name for name in BASE_ARTIFACTS if (run_dir / name).is_file()]
    if "results.jsonl" not in names:
        raise ValueError("results.jsonl is missing")
    if include_prompt:
        names.append("system_prompt.rendered.txt")
    if include_profile:
        names.append("student_profile.json")
    for name in names:
        path = run_dir / name
        if not path.is_file():
            raise ValueError(f"requested artifact is missing: {name}")
        path.resolve(strict=True).relative_to(run_dir)
    return run_dir, manifest, names


def make_archive(run_dir: Path, names: list[str]) -> tuple[bytes, str]:
    total_uncompressed = sum((run_dir / name).stat().st_size for name in names)
    if total_uncompressed > MAX_ARCHIVE_BYTES:
        raise ValueError("run artifacts exceed the 100 MB publish limit")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in names:
            path = run_dir / name
            if name == "results.jsonl":
                # Keep model-internal reasoning local. The review UI only needs
                # the final answer, test and timing fields from each result.
                sanitized_rows = []
                for line in path.read_text(encoding="utf-8").splitlines():
                    if not line.strip():
                        continue
                    row = json.loads(line)
                    metadata = row.get("metadata")
                    if isinstance(metadata, dict):
                        metadata = dict(metadata)
                        metadata.pop("thinking", None)
                        row["metadata"] = metadata
                    sanitized_rows.append(json.dumps(row, ensure_ascii=False))
                archive.writestr(name, "\n".join(sanitized_rows) + "\n")
            elif name == "run.json":
                manifest = json.loads(path.read_text(encoding="utf-8"))
                manifest.pop("profile_path", None)
                dataset = manifest.get("dataset")
                if isinstance(dataset, str):
                    manifest["dataset"] = Path(dataset.replace("\\", "/")).name
                archive.writestr(name, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
            elif name == "performance.json":
                performance = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(performance, dict):
                    performance.pop("profile_path", None)
                    dataset = performance.get("dataset")
                    if isinstance(dataset, str):
                        performance["dataset"] = Path(dataset.replace("\\", "/")).name
                archive.writestr(name, json.dumps(performance, ensure_ascii=False, indent=2) + "\n")
            else:
                archive.write(path, arcname=name)
    content = buffer.getvalue()
    if len(content) > MAX_ARCHIVE_BYTES:
        raise ValueError("run archive exceeds the 100 MB publish limit")
    return content, hashlib.sha256(content).hexdigest()


def publish(run_id: str, manifest: dict, names: list[str], archive: bytes, digest: str):
    token = os.environ.get("BLOB_READ_WRITE_TOKEN", "")
    if not token:
        raise RuntimeError("BLOB_READ_WRITE_TOKEN must be configured")
    if not os.environ.get("DATABASE_URL"):
        raise RuntimeError("DATABASE_URL must point to the hosted PostgreSQL database")

    try:
        from vercel.blob import BlobClient
    except ImportError as exc:
        raise RuntimeError("Install the Vercel Blob SDK with `pip install vercel`") from exc

    blob_path = f"benchmark-runs/{run_id}.zip"
    catalog.stage_run(run_id, manifest, blob_path, names, digest)
    try:
        client = BlobClient()
        client.put(
            blob_path,
            archive,
            access="private",
            content_type="application/zip",
            overwrite=True,
            token=token,
        )
        catalog.mark_published(run_id)
    except Exception:
        catalog.mark_failed(run_id)
        raise
    return blob_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_id", help="Completed run directory ID under results/")
    parser.add_argument("--include-system-prompt", action="store_true",
                        help="Include the rendered system prompt (sensitive; opt in)")
    parser.add_argument("--include-profile", action="store_true",
                        help="Include the student profile (sensitive; opt in)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Validate and report archive contents without uploading")
    parser.add_argument("--write-archive", type=Path,
                        help="Write a sanitized ZIP for upload through the hosted owner page")
    args = parser.parse_args()

    try:
        run_dir, manifest, names = validate_run(
            args.run_id, args.include_system_prompt, args.include_profile
        )
        archive, digest = make_archive(run_dir, names)
        if args.dry_run and args.write_archive:
            raise ValueError("choose either --dry-run or --write-archive")
        if args.write_archive:
            if args.include_profile:
                raise ValueError("hosted uploads do not accept student profiles")
            args.write_archive.parent.mkdir(parents=True, exist_ok=True)
            args.write_archive.write_bytes(archive)
            print(json.dumps({
                "run_id": args.run_id,
                "test_count": manifest["test_count"],
                "artifacts": names,
                "archive_bytes": len(archive),
                "sha256": digest,
                "archive": str(args.write_archive),
                "uploaded": False,
            }, indent=2))
            return
        if args.dry_run:
            print(json.dumps({
                "run_id": args.run_id,
                "test_count": manifest["test_count"],
                "artifacts": names,
                "archive_bytes": len(archive),
                "sha256": digest,
                "uploaded": False,
            }, indent=2))
            return
        blob_path = publish(args.run_id, manifest, names, archive, digest)
    except Exception as exc:
        parser.exit(1, f"publish failed: {exc}\n")

    print(json.dumps({
        "run_id": args.run_id,
        "test_count": manifest["test_count"],
        "artifacts": names,
        "archive_bytes": len(archive),
        "sha256": digest,
        "blob_path": blob_path,
        "uploaded": True,
    }, indent=2))


if __name__ == "__main__":
    main()
