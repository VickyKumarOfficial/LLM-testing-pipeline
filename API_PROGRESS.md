# Benchmark API progress

This log tracks only the benchmark sharing API. Fine-tuning work is tracked in
`NIERA_FINETUNE_PROGRESS.md` and is unrelated to this project.

## Scope and phases

1. Local, protected read-only API for completed runs.
2. Scoped share links with expiry and revocation.
3. Hosted metadata/artifact storage and a controlled publish flow.
4. Run comparison and reviewer UI, including exports.
5. Vercel deployment and end-to-end remote access.

## Status

- Phase 1: implemented and committed as `de2e4a6`.
- Phase 2: implemented in the working tree and stopped for review.
- Phases remaining after Phase 2: 3.

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
  flow remain Phase 3. No tests were added or run. Stopped here for review.

## Issue log

| Date | Issue | Resolution / next action | Status |
|---|---|---|---|
| 2026-09-24 | Fine-tuning progress log included API work. | Removed API entries from `NIERA_FINETUNE_PROGRESS.md`; use this file for API work. | Resolved |
| 2026-09-24 | Share credentials are headers rather than clickable browser URLs in this phase. | Keep secrets out of request paths/logs; add a browser UI that reads a token from URL fragment in Phase 4. | Open |
