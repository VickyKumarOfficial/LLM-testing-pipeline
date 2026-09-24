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

- Phase 1: implemented and committed as `54c07cb`.
- Phase 2: implementation in progress. Stop for review before Phase 3.
- Phases remaining after Phase 2: 3.

## Phase 1 record

- Added `niera_api/main.py` with health, run listing/detail, paginated and
  filtered results, and per-test result routes.
- Data routes require `NIERA_API_TOKEN`. Prompt/profile artifacts default to
  disabled. Responses omit machine paths and raw exception messages.
- Added FastAPI/Uvicorn dependencies and local run instructions in `README.md`.
- Phase 1 commit: `54c07cb` (`Add protected read-only benchmark API`).

## Phase 2 record

- Started on 2026-09-24 after user review and direction to continue.
- Goal: create scoped, read-only links for chosen run IDs, with optional expiry
  and revocation. Keep owner operations protected by the existing API token.
- Scope excludes hosted persistence and public deployment. The first share
  store will be local SQLite for development and will need a storage adapter in
  Phase 3 before Vercel deployment.

## Issue log

| Date | Issue | Resolution / next action | Status |
|---|---|---|---|
| 2026-09-24 | Fine-tuning progress log included API work. | Removed API entries from `NIERA_FINETUNE_PROGRESS.md`; use this file for API work. | Resolved |
| 2026-09-24 | Phase 1 uses one owner bearer token and has no per-recipient access. | Phase 2 adds run-scoped, revocable, read-only share tokens. | In progress |
