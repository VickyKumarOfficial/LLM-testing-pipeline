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
- Phase 3: implemented and committed as `228b747`.
- Phase 4: implemented in the working tree and stopped for review.
- Phases remaining after Phase 4: 1.

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

- Added PostgreSQL support to the share metadata store when `DATABASE_URL` is
  configured, while keeping SQLite for local development.
- Added a published-run catalog with upload status, safe run metadata, private
  Blob pathname, artifact list, archive digest, and timestamp.
- Added `scripts/publish_run.py`. It validates the run ID, manifest, result JSON,
  unique test IDs, and completeness before publishing a ZIP to private Vercel
  Blob storage. Prompt/profile artifacts are excluded unless explicitly enabled.
- Added `vercel` and `psycopg` dependencies and documented dry-run/publish usage.
- Nothing was uploaded because storage credentials were not configured.
- Phase 3 commit: `228b747` (`Add hosted benchmark artifact publishing`).

## Phase 4 record

- Switched local and shared read routes to a storage adapter that can read either
  local artifacts or published archives. Remote mode checks catalog status and
  verifies the downloaded archive SHA-256 before serving it.
- Added owner and share-scoped comparison endpoints aligned by test ID. The API
  reports config mismatches and does not infer a quality winner.
- Added JSONL/ZIP exports and a browser review page. Share credentials travel in
  the URL fragment, then in an authorization header, not in the HTTP path.
- The page lets owners select runs, compare them, create/revoke shares, and
  download archives. Reviewers can compare/download only runs on their share.
- Remote mode requires `NIERA_API_STORAGE_BACKEND=remote`, persistent
  `DATABASE_URL`, and private Blob access. Local mode remains the default.
- No tests were added or run and no external storage was accessed. Stopped here
  for review before Vercel deployment.

- Phase 4 code is uncommitted pending the requested review checkpoint.

## Issue log

| Date | Issue | Resolution / next action | Status |
|---|---|---|---|
| 2026-09-24 | Fine-tuning progress log included API work. | Removed API entries from `NIERA_FINETUNE_PROGRESS.md`; use this file for API work. | Resolved |
| 2026-09-24 | Share credentials could leak if placed in request paths or query strings. | Reviewer UI keeps them in the URL fragment and sends them in an authorization header. | Resolved in Phase 4 |
| 2026-09-24 | Hosted catalog/blob artifacts were not used by read endpoints after Phase 3. | Added remote read adapter in Phase 4; Vercel deployment is still pending. | Resolved for API reads |
