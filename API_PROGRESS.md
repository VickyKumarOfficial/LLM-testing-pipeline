# Benchmark API progress

This log tracks only the benchmark sharing API. Fine-tuning work is tracked in
`NIERA_FINETUNE_PROGRESS.md` and is unrelated to this project.

## Scope and phases

1. Local, protected read-only API for completed runs.
2. Scoped share links with expiry and revocation.
3. Hosted metadata/artifact storage and a controlled publish flow.
4. Remote reads, run comparison, and reviewer UI, including exports.
5. Vercel deployment and end-to-end remote access.

## Status

- Phase 1: implemented and committed as `de2e4a6`.
- Phase 2: implemented and committed as `bfdf2d3`.
- Phase 3: implemented in the working tree and stopped for review.
- Phases remaining after Phase 3: 2.

## Phase 1 record

- Added `niera_api/main.py` with health, run listing/detail, paginated and
  filtered results, and per-test result routes.
- Data routes require `NIERA_API_TOKEN`. Prompt/profile artifacts default to
  disabled. Responses omit machine paths and raw exception messages.
- Added FastAPI/Uvicorn dependencies and local run instructions in `README.md`.
- Phase 1 commit: `de2e4a6` (`Add protected read-only benchmark API`).

## Phase 2 record

- Added local SQLite share records with SHA-256 hashes of high-entropy random
  credentials. Raw credentials are returned once when created and are not stored.
- Added owner-only create/list/revoke endpoints. Shares allow up to 20 completed
  runs, default to seven days, and can separately allow prompt/profile artifacts.
- Added share-authenticated routes for listing allowed runs and reading their
  metadata/results/artifacts. Scope violations return not found. Expired or
  revoked credentials no longer authorize access.
- Added `.api-data/` to `.gitignore`, usage instructions to `README.md`, and
  updated `API_ACCESS_PLAN.md`.
- Local SQLite is not durable Vercel storage. Hosted persistence and a publish
  flow remained Phase 3. No tests were added or run.
- Phase 2 commit: `bfdf2d3` (`Add scoped benchmark share credentials`).

## Phase 3 record

- Started after committing Phase 2 as `bfdf2d3`.
- Added PostgreSQL support to the share metadata store when `DATABASE_URL` is
  configured, keeping SQLite for local development.
- Added a PostgreSQL published-run catalog with upload status, manifest, Blob
  pathname, artifact list, SHA-256 digest, and timestamp.
- Added `scripts/publish_run.py`. It validates run identity, JSONL integrity,
  unique test IDs, and completeness before creating an archive. It uploads only
  allowlisted artifacts to private Vercel Blob storage, with prompt/profile
  snapshots excluded unless explicitly requested.
- Added Vercel SDK and psycopg dependencies and documented the publish workflow.
- No credentials were supplied, so nothing was uploaded to external storage.
  No tests were added or run. The current API still serves local run files;
  Phase 4 will switch reads to the hosted catalog and blobs. Stopped for review.

## Issue log

| Date | Issue | Resolution / next action | Status |
|---|---|---|---|
| 2026-09-24 | Fine-tuning progress log included API work. | Removed API entries from `NIERA_FINETUNE_PROGRESS.md`; use this file for API work. | Resolved |
| 2026-09-24 | Share credentials are headers rather than clickable browser URLs in this phase. | Keep secrets out of request paths/logs; add a browser UI that reads a token from URL fragment in Phase 4. | Open |
| 2026-09-24 | Hosted catalog/blob artifacts are not yet used by read endpoints. | Add a storage-backed read adapter in Phase 4 before deploying to Vercel. | Open |
