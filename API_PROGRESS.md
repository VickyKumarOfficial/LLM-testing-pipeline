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
- Phase 4: implemented and committed as `48a1105`.
- Phase 5: Vercel project and stores are configured; the production reviewer
  page is live. Hosted benchmark records still need publishing.
- Phases complete: 4/5. Phase 5 remains in progress.

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
  before Vercel deployment.

- Phase 4 commit: `48a1105` (`Add hosted run comparison and reviewer UI`).

## Phase 5 record

- Added root `index.py` as the Vercel FastAPI entry point.
- Added `.vercelignore` so the deployment omits benchmark results, datasets,
  prompts, scoring sheets/key, fine-tuning files, and local SQLite data.
- Added `API_DEPLOYMENT.md` with required environment variables and Preview to
  Production rollout steps.
- Vercel project `llm-testing-pipeline` was created from the GitHub repository.
- Connected a Neon PostgreSQL database to Production and Preview using the
  `DATABASE` prefix, which provides the required `DATABASE_URL` variable.
- Created a private Vercel Blob store in `iad1` and enabled its read-write
  token for the project. The user confirmed creation; secret values were not
  inspected or recorded.
- The production reviewer page and API schema load at the deployed URL. The
  owner page reports zero runs after token setup, so the owner credential is
  accepted; the hosted catalog still needs published records.
- User provided production URL `https://llm-testing-pipeline.vercel.app/`.
  Inspected the live page and OpenAPI document; the reviewer UI and API routes
  are being served. The page asks for Owner or Shared review access and a
  credential. Owner share controls include expiry hours (default 168) and
  optional system-prompt/profile access. Run availability has not been
  confirmed because no credential was used and no runs have been published.
- User reports the owner page now loads but shows zero runs. Found three
  completed local runs: Qwen3 8B (`20260922_104435_c7a061`), Llama 3.1 8B
  (`20260922_140247_243752`), and Gemma 3 12B (`20260922_172853_2f88de`),
  each with 56 tests. These have not been published to hosted storage, which
  explains the empty catalog if remote mode is enabled. No upload was made.
  Initially the local publisher dry-run could not start because FastAPI was
  missing from the active `.venv`; installed the declared project requirements
  in that environment and reran the dry-run successfully for all three full
  runs plus the Qwen retry subset. Archives include the normal benchmark
  question and final response data. They omit the separate system prompt and
  profile files, and the publisher now strips `metadata.thinking`.
  Next: confirm remote mode is active in Production, then publish approved run
  IDs to the linked Postgres and private Blob store.
  Vercel CLI 60.0.0 was available through `npm exec`; user has since linked the
  project. Sensitive Production values remain unavailable to local CLI env
  commands, so no artifacts have been uploaded.
- User identified a Qwen retry folder (`20260924_134826_3d2d7f`) for two of the
  original empty cases. `MATH-JEE-02` has a 1,897-character answer;
  `PHY-NC-03` remains empty. The other original empty cases,
  `PHY-JEE-03` and `CHEM-JEE-03`, were not retried. The retry has a higher
  token limit/context than the original run, so a `run.json` now labels it as a
  two-test retry subset rather than merging it into the original 56-test run.
- Publisher review found raw `metadata.thinking` was present inside
  `results.jsonl`, despite the separate system-prompt/profile artifacts being
  excluded by default. Updated the publisher to remove that field from the
  uploaded archive and documented the behavior. Local source results remain
  untouched. No upload has happened; this change needs review before any
  publishing.

## Issue log

| Date | Issue | Resolution / next action | Status |
|---|---|---|---|
| 2026-09-24 | Fine-tuning progress log included API work. | Removed API entries from `NIERA_FINETUNE_PROGRESS.md`; use this file for API work. | Resolved |
| 2026-09-24 | Share credentials could leak if placed in request paths or query strings. | Reviewer UI keeps them in the URL fragment and sends them in an authorization header. | Resolved in Phase 4 |
| 2026-09-24 | Hosted catalog/blob artifacts were not used by read endpoints after Phase 3. | Added remote read adapter in Phase 4; Vercel deployment is still pending. | Resolved for API reads |
| 2026-09-24 | Local CLI cannot read Vercel's sensitive database/Blob environment values. | Added an owner-token-protected upload endpoint. Vercel's deployed function writes with its own secrets; share links remain read-only. | Implemented locally; deployment pending |
| 2026-09-24 | User needed help interpreting the deployed review page fields. | Inspected the production page and API schema; documented owner/share credential use and optional share fields. No credential values were accessed. | Resolved |
| 2026-09-24 | Owner credential was reported as invalid/expired and its Vercel value is hidden. | The Vercel value is hidden by design. User replaced the value and the owner page now accepts it. | Resolved |
| 2026-09-24 | Hosted review page reports 0 runs. | Identified that run artifacts are still local. Validated three completed runs and one Qwen retry subset in dry-run. No data was uploaded; publishing remains. | In progress |
| 2026-09-24 | Publisher dry-run initially lacked FastAPI in the active virtualenv. | Installed `requirements.txt` into the existing `.venv`; dry-run then validated all four publish records. Upload has not been performed. | Resolved |
| 2026-09-24 | The local publisher cannot access hosted database and Blob secrets even after CLI linking. | Confirmed Vercel withholds sensitive values from local environment commands. Added browser upload through the deployed API, which uses Vercel's runtime credentials. | Implemented locally; deploy pending |
| 2026-09-24 | Qwen rerun covered only two of four empty outputs and used a different token/context configuration. | Kept the original run unchanged and added a two-test partial-retry manifest. It records one recovered response and one remaining empty response, with the changed configuration visible. | Prepared locally |
| 2026-09-24 | Raw result archives would have included model `metadata.thinking`. | Publisher strips this field from upload archives while preserving local originals and fields needed for review. | Resolved |
| 2026-09-25 | Downloading a published run returned HTTP 500 because the API expected a `.stream` attribute on the Vercel Blob SDK result. | Updated remote archive reads to use the SDK's `content` bytes, validate the response type and archive size, and close the async client. Deployed commit `5c2c5eb`; production page and API schema return HTTP 200. No post-deploy download request is present in Vercel logs yet, so the browser download still needs confirmation. | Fixed and deployed; awaiting user confirmation |

## Owner upload phase (in progress)

- User confirmed the Vercel CLI link is complete. CLI link alone does not make
  sensitive Production values readable locally, so the CLI publisher cannot
  connect directly to hosted PostgreSQL/Blob without exposing secrets.
- Added `POST /api/v1/publish`, protected by the owner bearer token. It accepts
  an `application/zip` body up to 4 MB, validates archive names/run ID/count,
  strips `metadata.thinking` and machine-specific paths, and writes via the
  deployment's configured private Blob and PostgreSQL credentials.
- Added an owner-only upload control to the review page. Share credentials
  cannot publish. Student profiles remain excluded; prompts are opt-in.
- Added `--write-archive PATH` to `scripts/publish_run.py` to create sanitized
  ZIPs for the page. Updated API plan/deployment/README docs and corrected this
  file's record of Vercel CLI linking and secret limitations.
- Code and docs compiled cleanly and `git diff --check` passed. Prepared four
  ignored local ZIPs: three full runs and the two-question Qwen retry subset;
  each is below the 4 MB upload cap. Nothing has been uploaded.
- Committed this development phase as `14324b9` (`Add owner upload flow for
  hosted benchmark runs`). After review, deployed to Vercel Production at
  `https://llm-testing-pipeline.vercel.app/`; deployment ID
  `dpl_EAbYgpxECe2rbePucbarEwoxysmj` is READY. Verified the review page and
  OpenAPI return HTTP 200, the publish route is present, and unauthenticated
  publish returns HTTP 401. The four archives remain local and no run has been
  uploaded because the owner token is intentionally hidden from local CLI and
  is available only to the user in the browser/Vercel dashboard. Next: user
  enters owner token in the deployed page and uploads archives.

## Review UI clarity phase (in progress)

- User reported that model output Markdown was shown as raw text and the
  comparison pagination did not make the current and upcoming tests clear.
- Added a progress banner showing the test range on the current page and the
  next test ID/question. Renamed paging controls to say they move by 10 tests.
- Added safe browser-side formatting for common Markdown: headings, bold,
  italics, ordered/unordered lists, inline code, and visibly separated math
  notation. Uses DOM text nodes/elements rather than injecting model HTML.
- Clarified the owner share controls: a share is a selected-run, read-only link;
  168 hours is seven days; other reviewers use the generated link and do not
  need the owner's OpenSSL token.
- System prompts and profiles are currently absent from existing hosted runs.
  Added opt-in support for `--include-system-prompt` and `--include-profile`;
  each stays private to the owner unless selected in the share options.
- Changes are local and awaiting review. No deployment or additional prompt
  upload has occurred.

## Run context display and share repair (in progress)

- User reported that Create share did not work and asked to display system
  prompts/profiles directly using the review page space. The previous screenshot
  had prompt/profile sharing selected, but existing hosted archives excluded
  both, so the API rejects creating a share that requests unavailable files.
- Added owner-authenticated and share-scoped context routes for prompts and
  profiles, plus full question-set endpoints. Replaced the inline details
  panels with three buttons: View system prompts, View student profiles, and
  View full question sets. Each button opens a scrollable popup grouped by
  selected run. Profiles render as readable labeled fields; question sets show
  all questions used by that run and omit answer keys.
- Enabled opt-in `--include-profile` archive publishing alongside prompts.
  Existing hosted runs need replacement ZIPs to include either artifact.
- Prepared four ignored replacement ZIPs in
  `.api-data/publish-ready/context/` with prompt and profile included. Each is
  below 60 KB. No upload occurred.
- Share creation now checks that selected artifact files exist and provides a
  direct re-upload instruction instead of making an opaque failing request.
- Changes are local and awaiting review. No deployment or share was created.

## Direct context popups (2026-09-25)

- Removed the review-share creation, expiry, existing-share management, and ZIP
  upload controls from the reviewer page. This display flow no longer creates
  sharing links or asks for file uploads.
- Kept three direct popup buttons for selected runs: system prompts, student
  profiles, and the full question sets. These read through owner-authenticated
  API routes; the owner API key is required to view benchmark data.
- Vercel excludes the `results/` tree, so copied only the four selected runs'
  existing `system_prompt.rendered.txt` and `student_profile.json` files into
  `niera_api/context_data/`. The function reads those bounded, allowlisted
  files when the published archive does not contain them. No Blob upload is
  required for prompt/profile display.
- Removed stale share-link and upload JavaScript paths from the page. The share
  API routes remain available to preserve the existing API contract; they are
  no longer exposed as controls in this reviewer page.
- JavaScript syntax check, Python bytecode compilation, and `git diff --check`
  passed. Committed as `f98fa8a` (`Show run context directly in review page`).
- The first Vercel deploy attempt returned `Not authorized`; the authenticated
  CLI still identified the linked project. Retried with CLI diagnostics and the
  Production deployment completed successfully as
  `dpl_Aups8vyzWgFdvx98xQ8GTRYgYpqJ`.
- Checked the production page: all three popup buttons are present and the
  share creation and ZIP upload controls are gone. Unauthenticated context
  requests return HTTP 401, so the owner API key remains required.
- Deployment is complete. A separate viewer must use the owner API key; this
  direct-popup setup does not create an independent read-only access link.
