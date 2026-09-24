"""Authenticated, read-only API for completed benchmark run artifacts."""

import hmac
import json
import os
import time
import io
from pathlib import Path
import zipfile
from typing import Any, Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from niera_api import artifacts, publishing, shares

app = FastAPI(
    title="Niera benchmark API",
    version="1.0.0",
    description="Owner-managed publishing and read-only access to saved Niera benchmark runs.",
)


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "private, no-store"
    return response


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def reviewer_page() -> HTMLResponse:
    page = Path(__file__).resolve().parent / "static" / "index.html"
    try:
        return HTMLResponse(page.read_text(encoding="utf-8"))
    except OSError:
        raise HTTPException(status_code=404, detail="Reviewer page is unavailable") from None


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


def require_share(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "share" or not token:
        raise HTTPException(
            status_code=401,
            detail="Valid share credential required",
            headers={"WWW-Authenticate": "Share"},
        )
    share = shares.find_share_by_token(token)
    if share is None:
        raise HTTPException(status_code=401, detail="Share credential is invalid or expired")
    return share


class CreateShareRequest(BaseModel):
    run_ids: list[str] = Field(min_length=1, max_length=20)
    expires_in_hours: int | None = Field(default=168, ge=1, le=8760)
    allow_system_prompt: bool = False
    allow_profile: bool = False


class ComparisonRequest(BaseModel):
    run_ids: list[str] = Field(min_length=2, max_length=4)
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=10, ge=1, le=20)


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


def compare_runs(run_ids: list[str], offset: int, limit: int) -> dict[str, Any]:
    if len(set(run_ids)) != len(run_ids):
        raise HTTPException(status_code=422, detail="run_ids must not contain duplicates")
    manifests = {run_id: artifacts.get_manifest(run_id) for run_id in run_ids}
    normalized = {}
    for run_id, manifest in manifests.items():
        dataset = str(manifest.get("dataset", "")).replace("\\", "/").rsplit("/", 1)[-1]
        normalized[run_id] = {
            "benchmark_version": manifest.get("benchmark_version"),
            "dataset": dataset,
            "system_prompt_sha256": manifest.get("system_prompt_sha256"),
            "profile_id": manifest.get("profile_id"),
            "generation_config": manifest.get("generation_config"),
        }
    reference = normalized[run_ids[0]]
    mismatches = [
        field for field in reference
        if any(normalized[run_id].get(field) != reference.get(field) for run_id in run_ids[1:])
    ]

    result_maps = {}
    order = []
    for run_id in run_ids:
        rows = artifacts.get_results(run_id)
        result_maps[run_id] = {row.get("test_id"): row for row in rows if row.get("test_id")}
        for row in rows:
            test_id = row.get("test_id")
            if test_id and test_id not in order:
                order.append(test_id)

    aligned = []
    for test_id in order:
        present = [result_maps[run_id].get(test_id) for run_id in run_ids]
        first = next((row for row in present if row is not None), None)
        aligned.append({
            "test_id": test_id,
            "question": ((first or {}).get("test") or {}).get("question"),
            "runs": [
                None if row is None else {
                    "run_id": run_id,
                    "model": row.get("model"),
                    "output": row.get("output"),
                    "generation": row.get("generation", {}),
                    "error": {"type": row["error"].get("type", "Error")}
                    if isinstance(row.get("error"), dict) else None,
                }
                for run_id, row in zip(run_ids, present)
            ],
        })
    return {
        "run_ids": run_ids,
        "comparable": not mismatches,
        "comparison_mismatches": mismatches,
        "comparison_settings": normalized,
        "offset": offset,
        "limit": limit,
        "total_tests": len(aligned),
        "tests": aligned[offset : offset + limit],
    }


def make_export(run_id: str, include_prompt: bool, include_profile: bool) -> bytes:
    manifest = safe_run_summary(artifacts.get_manifest(run_id))
    bundle = artifacts.get_run_bundle(run_id)
    try:
        raw_rows = [
            json.loads(line)
            for line in bundle["results.jsonl"].decode("utf-8").splitlines()
            if line.strip()
        ]
    except (KeyError, UnicodeDecodeError, json.JSONDecodeError):
        raise HTTPException(status_code=500, detail="Run results are unreadable") from None
    rows = [public_result(row) for row in raw_rows]
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("run.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        archive.writestr(
            "results.jsonl",
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        )
        for name in ("performance.json", "performance.txt"):
            if name in bundle:
                archive.writestr(name, bundle[name])
        if include_prompt:
            if "system_prompt.rendered.txt" in bundle:
                archive.writestr("system_prompt.rendered.txt", bundle["system_prompt.rendered.txt"])
        if include_profile:
            if "student_profile.json" in bundle:
                archive.writestr("student_profile.json", bundle["student_profile.json"])
    return buffer.getvalue()


@app.get("/api/v1/health")
def health() -> dict[str, str]:
    """Liveness only. Does not reveal configuration or require a token."""
    return {"status": "ok"}


@app.post("/api/v1/publish", dependencies=[Depends(require_api_token)])
async def publish_run_archive(request: Request) -> dict[str, Any]:
    """Publish a validated ZIP archive using the deployment's private credentials."""
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > publishing.MAX_UPLOAD_BYTES:
                raise HTTPException(status_code=413, detail="Run archive exceeds the 4 MB upload limit")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid Content-Length") from None
    content = await request.body()
    if len(content) > publishing.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Run archive exceeds the 4 MB upload limit")
    if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() != "application/zip":
        raise HTTPException(status_code=415, detail="Content-Type must be application/zip")
    try:
        return publishing.publish_archive(content)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


@app.get("/api/v1/runs", dependencies=[Depends(require_api_token)])
def list_runs(
    model: str | None = None,
    benchmark_version: str | None = None,
) -> dict[str, Any]:
    runs = []
    for manifest in artifacts.list_manifests():
        if model and manifest.get("model") != model:
            continue
        if benchmark_version and manifest.get("benchmark_version") != benchmark_version:
            continue
        runs.append(safe_run_summary(manifest))
    return {"runs": runs, "count": len(runs)}


@app.get("/api/v1/runs/{run_id}", dependencies=[Depends(require_api_token)])
def get_run(run_id: str) -> dict[str, Any]:
    return safe_run_summary(artifacts.get_manifest(run_id))


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
    rows = artifacts.get_results(run_id)
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
    for row in artifacts.get_results(run_id):
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
    content = artifacts.get_artifact_bytes(run_id, "system_prompt.rendered.txt")
    return Response(content, media_type="text/plain; charset=utf-8")


@app.get(
    "/api/v1/runs/{run_id}/artifacts/profile",
    dependencies=[Depends(require_api_token)],
)
def get_profile(run_id: str) -> dict[str, Any]:
    if not artifact_enabled("profile"):
        raise HTTPException(status_code=403, detail="Profile sharing is disabled")
    try:
        return json.loads(artifacts.get_artifact_bytes(run_id, "student_profile.json"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise HTTPException(status_code=500, detail="Profile artifact is unreadable") from None


@app.get("/api/v1/runs/{run_id}/export", dependencies=[Depends(require_api_token)])
def export_run(
    run_id: str,
    export_format: Literal["jsonl", "zip"] = Query(default="zip", alias="format"),
) -> Response:
    if export_format == "jsonl":
        rows = [public_result(row) for row in artifacts.get_results(run_id)]
        content = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)
        return Response(
            content,
            media_type="application/x-ndjson",
            headers={"Content-Disposition": f'attachment; filename="{run_id}.jsonl"'},
        )
    content = make_export(
        run_id,
        include_prompt=artifact_enabled("system_prompt"),
        include_profile=artifact_enabled("profile"),
    )
    return Response(
        content,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{run_id}.zip"'},
    )


@app.get("/api/v1/shares", dependencies=[Depends(require_api_token)])
def list_shares() -> dict[str, Any]:
    return {"shares": shares.list_shares()}


@app.post("/api/v1/shares", dependencies=[Depends(require_api_token)])
def create_share(request: CreateShareRequest) -> dict[str, Any]:
    run_ids = list(dict.fromkeys(request.run_ids))
    if len(run_ids) != len(request.run_ids):
        raise HTTPException(status_code=422, detail="run_ids must not contain duplicates")
    for run_id in run_ids:
        artifacts.get_manifest(run_id)
        if request.allow_system_prompt:
            artifacts.get_artifact_bytes(run_id, "system_prompt.rendered.txt")
        if request.allow_profile:
            artifacts.get_artifact_bytes(run_id, "student_profile.json")
    expires_at = (
        time.time() + request.expires_in_hours * 3600
        if request.expires_in_hours is not None
        else None
    )
    record, token = shares.create_share(
        run_ids=run_ids,
        allow_system_prompt=request.allow_system_prompt,
        allow_profile=request.allow_profile,
        expires_at=expires_at,
    )
    # The raw credential is returned once. Only its hash is stored.
    return {**record, "share_token": token}


@app.delete("/api/v1/shares/{share_id}", dependencies=[Depends(require_api_token)])
def delete_share(share_id: str) -> dict[str, str]:
    if not shares.revoke_share(share_id):
        raise HTTPException(status_code=404, detail="Share not found")
    return {"status": "revoked"}


@app.post("/api/v1/comparisons", dependencies=[Depends(require_api_token)])
def owner_comparison(request: ComparisonRequest) -> dict[str, Any]:
    return compare_runs(request.run_ids, request.offset, request.limit)


@app.get("/api/v1/shared/runs/{run_id}/export")
def export_shared_run(
    run_id: str,
    export_format: Literal["jsonl", "zip"] = Query(default="zip", alias="format"),
    share: dict[str, Any] = Depends(require_share),
) -> Response:
    verify_run_scope(share, run_id)
    if export_format == "jsonl":
        rows = [public_result(row) for row in artifacts.get_results(run_id)]
        content = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)
        return Response(
            content,
            media_type="application/x-ndjson",
            headers={"Content-Disposition": f'attachment; filename="{run_id}.jsonl"'},
        )
    content = make_export(
        run_id,
        include_prompt=share["artifacts"]["system_prompt"],
        include_profile=share["artifacts"]["profile"],
    )
    return Response(
        content,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{run_id}.zip"'},
    )


@app.post("/api/v1/shared/comparisons")
def shared_comparison(
    request: ComparisonRequest,
    share: dict[str, Any] = Depends(require_share),
) -> dict[str, Any]:
    for run_id in request.run_ids:
        verify_run_scope(share, run_id)
    return compare_runs(request.run_ids, request.offset, request.limit)


def verify_run_scope(share: dict[str, Any], run_id: str) -> dict[str, Any]:
    if run_id not in share["run_ids"]:
        raise HTTPException(status_code=404, detail="Run not found")
    return artifacts.get_manifest(run_id)


@app.get("/api/v1/shared/runs")
def list_shared_runs(share: dict[str, Any] = Depends(require_share)) -> dict[str, Any]:
    runs = []
    for run_id in share["run_ids"]:
        try:
            manifest = artifacts.get_manifest(run_id)
        except HTTPException as exc:
            if exc.status_code == 404:
                continue
            raise
        runs.append(safe_run_summary(manifest))
    return {"runs": runs, "count": len(runs)}


@app.get("/api/v1/shared/runs/{run_id}")
def get_shared_run(
    run_id: str, share: dict[str, Any] = Depends(require_share)
) -> dict[str, Any]:
    return safe_run_summary(verify_run_scope(share, run_id))


@app.get("/api/v1/shared/runs/{run_id}/results")
def list_shared_results(
    run_id: str,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=25, ge=1, le=100),
    test_id: str | None = None,
    track: str | None = None,
    subject: str | None = None,
    difficulty: str | None = None,
    share: dict[str, Any] = Depends(require_share),
) -> dict[str, Any]:
    verify_run_scope(share, run_id)
    rows = artifacts.get_results(run_id)
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


@app.get("/api/v1/shared/runs/{run_id}/results/{test_id}")
def get_shared_result(
    run_id: str,
    test_id: str,
    share: dict[str, Any] = Depends(require_share),
) -> dict[str, Any]:
    verify_run_scope(share, run_id)
    for row in artifacts.get_results(run_id):
        if row.get("test_id") == test_id:
            return public_result(row)
    raise HTTPException(status_code=404, detail="Result not found")


@app.get("/api/v1/shared/runs/{run_id}/artifacts/system-prompt")
def get_shared_system_prompt(
    run_id: str, share: dict[str, Any] = Depends(require_share)
) -> Response:
    if not share["artifacts"]["system_prompt"]:
        raise HTTPException(status_code=404, detail="Artifact not shared")
    verify_run_scope(share, run_id)
    content = artifacts.get_artifact_bytes(run_id, "system_prompt.rendered.txt")
    return Response(content, media_type="text/plain; charset=utf-8")


@app.get("/api/v1/shared/runs/{run_id}/artifacts/profile")
def get_shared_profile(
    run_id: str, share: dict[str, Any] = Depends(require_share)
) -> dict[str, Any]:
    if not share["artifacts"]["profile"]:
        raise HTTPException(status_code=404, detail="Artifact not shared")
    verify_run_scope(share, run_id)
    try:
        return json.loads(artifacts.get_artifact_bytes(run_id, "student_profile.json"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise HTTPException(status_code=500, detail="Profile artifact is unreadable") from None
