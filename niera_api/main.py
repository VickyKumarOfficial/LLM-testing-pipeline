"""Authenticated, read-only API for completed benchmark run artifacts."""

import hmac
import json
import os
import re
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Response


ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "results"
RUN_ID_RE = re.compile(r"^[0-9]{8}_[0-9]{6}_[a-f0-9]{6}$")

app = FastAPI(
    title="Niera benchmark API",
    version="1.0.0",
    description="Read-only access to saved Niera benchmark runs.",
)


def require_api_token(authorization: str | None = Header(default=None)) -> None:
    """Require a configured bearer token. Missing configuration fails closed."""
    expected = os.environ.get("NIERA_API_TOKEN", "")
    if not expected:
        raise HTTPException(status_code=503, detail="API access is not configured")
    scheme, _, supplied = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not supplied or not hmac.compare_digest(
        supplied, expected
    ):
        raise HTTPException(
            status_code=401,
            detail="Valid bearer token required",
            headers={"WWW-Authenticate": "Bearer"},
        )


def run_directory(run_id: str) -> Path:
    if not RUN_ID_RE.fullmatch(run_id):
        raise HTTPException(status_code=404, detail="Run not found")
    path = RESULTS_DIR / run_id
    # Resolve and re-check containment so an unexpected symlink cannot escape
    # the results directory.
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(RESULTS_DIR.resolve(strict=True))
    except (FileNotFoundError, ValueError):
        raise HTTPException(status_code=404, detail="Run not found") from None
    if not resolved.is_dir() or not (resolved / "run.json").is_file():
        raise HTTPException(status_code=404, detail="Run not found")
    return resolved


def read_manifest(path: Path) -> dict[str, Any]:
    try:
        return json.loads((path / "run.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raise HTTPException(status_code=500, detail="Run manifest is unreadable") from None


def safe_run_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    """Return approved manifest fields and omit machine-specific paths."""
    allowed = (
        "run_id",
        "benchmark_version",
        "mode",
        "model",
        "backend",
        "profile_id",
        "system_prompt_sha256",
        "generation_config",
        "test_count",
        "ok_count",
        "error_count",
        "stats",
        "started_utc",
    )
    return {key: manifest[key] for key in allowed if key in manifest}


def read_results(path: Path) -> list[dict[str, Any]]:
    results_path = path / "results.jsonl"
    if not results_path.is_file():
        raise HTTPException(status_code=404, detail="Run results not found")
    rows: list[dict[str, Any]] = []
    try:
        with results_path.open(encoding="utf-8") as source:
            for line_number, line in enumerate(source, start=1):
                if line.strip():
                    row = json.loads(line)
                    if not isinstance(row, dict):
                        raise ValueError("result row is not an object")
                    rows.append(row)
    except (OSError, json.JSONDecodeError, ValueError):
        raise HTTPException(
            status_code=500, detail="Run results are unreadable"
        ) from None
    return rows


def public_result(row: dict[str, Any]) -> dict[str, Any]:
    """Keep response data useful while excluding internal paths/metadata."""
    test = row.get("test") or {}
    prompt = row.get("prompt") or {}
    generation = row.get("generation") or {}
    result = {
        "run_id": row.get("run_id"),
        "test_id": row.get("test_id"),
        "model": row.get("model"),
        "benchmark_version": row.get("benchmark_version"),
        "test": {
            key: test[key]
            for key in (
                "question", "track", "subject", "chapter", "class",
                "difficulty", "answer_type", "source", "source_reference",
            )
            if key in test
        },
        "prompt": {
            key: prompt[key]
            for key in ("system_prompt_sha256", "profile_id")
            if key in prompt
        },
        "generation": {
            key: generation[key]
            for key in ("latency_ms", "input_tokens", "output_tokens", "config")
            if key in generation
        },
        "output": row.get("output"),
    }
    if isinstance(row.get("error"), dict):
        # Do not return the raw exception message, which may contain host or
        # environment details.
        result["error"] = {"type": row["error"].get("type", "Error")}
    return result


@app.get("/api/v1/health")
def health() -> dict[str, str]:
    """Liveness only. Does not reveal configuration or require a token."""
    return {"status": "ok"}


@app.get("/api/v1/runs", dependencies=[Depends(require_api_token)])
def list_runs(
    model: str | None = None,
    benchmark_version: str | None = None,
) -> dict[str, Any]:
    runs = []
    if not RESULTS_DIR.is_dir():
        return {"runs": runs, "count": 0}
    for path in sorted(RESULTS_DIR.iterdir(), reverse=True):
        if not path.is_dir() or not RUN_ID_RE.fullmatch(path.name):
            continue
        manifest_path = path / "run.json"
        if not manifest_path.is_file():
            continue
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if model and manifest.get("model") != model:
            continue
        if benchmark_version and manifest.get("benchmark_version") != benchmark_version:
            continue
        runs.append(safe_run_summary(manifest))
    return {"runs": runs, "count": len(runs)}


@app.get("/api/v1/runs/{run_id}", dependencies=[Depends(require_api_token)])
def get_run(run_id: str) -> dict[str, Any]:
    return safe_run_summary(read_manifest(run_directory(run_id)))


@app.get("/api/v1/runs/{run_id}/results", dependencies=[Depends(require_api_token)])
def list_results(
    run_id: str,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=25, ge=1, le=100),
    test_id: str | None = None,
    track: str | None = None,
    subject: str | None = None,
    difficulty: str | None = None,
) -> dict[str, Any]:
    path = run_directory(run_id)
    rows = read_results(path)
    filtered = []
    for row in rows:
        test = row.get("test") or {}
        if test_id and row.get("test_id") != test_id:
            continue
        if track and test.get("track") != track:
            continue
        if subject and test.get("subject") != subject:
            continue
        if difficulty and test.get("difficulty") != difficulty:
            continue
        filtered.append(public_result(row))
    return {
        "run_id": run_id,
        "offset": offset,
        "limit": limit,
        "total": len(filtered),
        "results": filtered[offset : offset + limit],
    }


@app.get(
    "/api/v1/runs/{run_id}/results/{test_id}",
    dependencies=[Depends(require_api_token)],
)
def get_result(run_id: str, test_id: str) -> dict[str, Any]:
    for row in read_results(run_directory(run_id)):
        if row.get("test_id") == test_id:
            return public_result(row)
    raise HTTPException(status_code=404, detail="Result not found")


def artifact_enabled(name: str) -> bool:
    return os.environ.get(f"NIERA_API_EXPOSE_{name.upper()}", "false").lower() in {
        "1", "true", "yes",
    }


@app.get(
    "/api/v1/runs/{run_id}/artifacts/system-prompt",
    dependencies=[Depends(require_api_token)],
)
def get_system_prompt(run_id: str) -> Response:
    if not artifact_enabled("system_prompt"):
        raise HTTPException(status_code=403, detail="System prompt sharing is disabled")
    path = run_directory(run_id) / "system_prompt.rendered.txt"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Prompt artifact not found")
    return Response(path.read_text(encoding="utf-8"), media_type="text/plain; charset=utf-8")


@app.get(
    "/api/v1/runs/{run_id}/artifacts/profile",
    dependencies=[Depends(require_api_token)],
)
def get_profile(run_id: str) -> dict[str, Any]:
    if not artifact_enabled("profile"):
        raise HTTPException(status_code=403, detail="Profile sharing is disabled")
    path = run_directory(run_id) / "student_profile.json"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Profile artifact not found")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raise HTTPException(status_code=500, detail="Profile artifact is unreadable") from None
