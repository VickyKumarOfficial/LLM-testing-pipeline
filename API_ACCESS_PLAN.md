# Niera benchmark sharing API plan

## Goal

Let an invited reviewer open benchmark runs over HTTPS, inspect the model
outputs and the exact prompts/configuration used, and compare selected runs.
The first release should be read-only. It should not start model inference or
expose the Ollama service.

## Where the service runs

The API code does not make a laptop reachable by itself. For another device on
another network to use it, the API must run on a public host with an HTTPS URL
and a route through that host's firewall or ingress.

- **Run it on this laptop:** the laptop must stay on, connected to the internet,
  and running the API process. A secure tunnel or router configuration is also
  needed, and sleep, changing networks, or a changing public IP can interrupt
  access. This is suitable for a short demo, not reliable sharing.
- **Deploy it on a cloud/app host:** the host runs the API continuously, so the
  laptop can be off. Store benchmark artifacts on that host or in private
  persistent object storage. Deploying the API does not require keeping Ollama
  running because the first version serves saved results only.

Use a managed host for ongoing reviewer access. Do not expose a development
server or the Ollama port directly to the public internet.

## Vercel fit

Vercel is a reasonable host for this read-only API and comparison page. Its
current Python Functions runtime supports FastAPI, although Vercel labels the
Python runtime beta. A Vercel deployment means the laptop can be off while
reviewers use the service.

Treat Vercel as the compute and web hosting layer, not as the writable home for
the run archive. Vercel Functions have a read-only filesystem, with `/tmp` only
for scratch data. Do not rely on edits or new results written beside the
function persisting between requests. Put run metadata in a hosted database
such as Postgres/SQLite-compatible hosted storage, and keep full output and
prompt/profile artifacts in private object storage. Vercel Blob private storage
is one option; serve it through authenticated functions. Check its current
availability and pricing before choosing it.

For a small static archive, files could be bundled with the deployment, but
that makes each data update a code deployment and risks publishing repository
artifacts unintentionally. Do not deploy the repository root as a public static
site. Explicitly exclude `results/`, scoring sheets, `key.json`, datasets, and
prompt/profile files from public static output. Serve allowed files only after
the API checks access.

Suggested Vercel layout: host the API and reviewer UI in Vercel Functions; use
an external/Marketplace database for run indexes and share permissions; store
the selected run artifacts in a private Blob store. Keep the existing runner
local and add a controlled publish/upload command that sends only approved
artifacts. Vercel supports Python functions, but for a new implementation we
should confirm that the beta runtime and the chosen auth/storage libraries meet
the project's needs before locking the stack.

## What the project already saves

Each completed `results/<run_id>/` has `run.json`, `results.jsonl`,
`system_prompt.rendered.txt`, `student_profile.json`, and performance summaries.
Each result row contains the test/question metadata, model output, per-question
timing/token data, and prompt hash. The repository also has a blinded scoring
sheet and a separate unblinding `key.json`.

The API should index these existing artifacts. It should not need the full
benchmark runner or a live model to serve a comparison.

## First version

Build a small FastAPI read-only service backed by SQLite metadata and the files
under `results/`. Import run artifacts through a controlled index/rebuild
command. Store run IDs, metadata, share permissions, and optional score records
in SQLite; keep large response text and prompt snapshots in the run files at
first. Resolve files only through validated run IDs from the index. Never accept
filesystem paths from API callers.

The first viewer can be a basic web page that calls this API, but the API is the
stable part. Support JSON responses and a downloadable JSONL export.

## Implementation checkpoints

- **Phase 1, local read-only API:** completed and committed. The API requires a
  bearer token and reads completed local runs. Prompt/profile downloads default
  to disabled.
- **Phase 2, scoped shares:** implemented locally for review. Owner creates
  per-run read-only credentials with expiry and optional prompt/profile access;
  owner can list and revoke them. Credentials are sent in the `Authorization:
  Share` header. SQLite is local development storage only.
- **Phase 3, persistent storage and publish flow:** implemented and committed as
  `228b747`.
  PostgreSQL stores the run catalog and share credentials; a controlled command
  publishes allowlisted run files to private Vercel Blob storage.
- **Phase 4, remote reads and comparison UI:** implemented and committed as
  `48a1105`. The API
  reads the published catalog/archives, compares by test ID, exports results,
  and serves a small reviewer page for owner and share credentials.
- **Phase 5, Vercel deployment:** entry point and safe deployment exclusions
  are prepared. Live deployment still requires an authenticated Vercel project
  and configured PostgreSQL/Blob storage.

## Proposed endpoints

All routes are under `/api/v1` and require HTTPS.

| Endpoint | Purpose |
|---|---|
| `GET /runs` | List runs the caller can access. Filter by model, date, and benchmark version. Return summary metadata and completion counts. |
| `GET /runs/{run_id}` | Run manifest, generation settings, prompt hash, counts, and performance summary. |
| `GET /runs/{run_id}/results` | Paginated test results. Filter by `test_id`, track, subject, and difficulty. Include question, answer, token counts, latency, and error state. |
| `GET /runs/{run_id}/results/{test_id}` | Full question and response record for one test. |
| `GET /runs/{run_id}/artifacts/system-prompt` | Exact rendered system prompt snapshot, with content type text/plain and hash metadata. |
| `GET /runs/{run_id}/artifacts/profile` | Student profile snapshot used for the run. |
| `GET /runs/{run_id}/export` | Download sanitized JSONL or a ZIP with run metadata, outputs, and performance summaries. Owner prompt/profile inclusion is controlled by server settings. |
| `POST /publish` | Owner-only upload of a sanitized run ZIP (maximum 4 MB) into private Blob storage and the hosted catalog. An exact system prompt is allowed only when explicitly included in the local archive; profiles remain excluded. Share credentials cannot publish. |
| `POST /comparisons` | Compare two to four accessible runs, aligned by test ID. Reports mismatched settings and does not choose a quality winner. |
| `POST /shares` | Owner creates a read-only share for selected run IDs. Return a high-entropy share link/token with optional expiry. |
| `DELETE /shares/{share_id}` | Owner revokes a share. |

Share credentials use matching read routes under `/api/v1/shared/runs`,
`POST /api/v1/shared/comparisons`, and
`GET /api/v1/shared/runs/{run_id}/export`. Comparison responses are paginated
in batches of at most 20 test IDs to keep response bodies bounded.

Owner share management currently uses `GET`, `POST`, and `DELETE
/api/v1/shares...` with the owner bearer token. Shared reads use
`Authorization: Share <token>` on `/api/v1/shared/runs...` routes. They expose
only the run IDs and artifact classes recorded on that share.

The first implementation uses `/api/v1/shares` and
`/api/v1/shared/runs/...`. It returns a one-time share credential rather than a
browser URL. The reviewer UI can place the credential in a URL fragment and
send it in the authorization header; the secret should not be sent as a query
parameter or path segment where server logs may capture it.

Keep score access out of the first release until the rubric is filled and the
team agrees that scores and evaluator notes may be shared. When added, expose
only aggregate scores by default. Keep `key.json`, blinded mapping, private
reviewer identity, and unblinding details owner-only.

## Authentication and sharing

- Require an owner account for run listing, indexing, creating links, and
  revoking links. Use an established identity provider or signed session.
- A share link grants read-only access to only the selected run IDs. Use a
  cryptographically random token, store only its hash, and support expiry and
  revocation. Do not make run IDs themselves act as secrets.
- Allow the owner to choose whether a share includes full outputs, prompt
  snapshots, profiles, and exports. Default sharing should include run metadata
  and outputs but require a deliberate choice to include prompt/profile files.
- Add pagination, request-size limits, rate limits, and access logs. Never
  expose stack traces, machine paths, environment variables, or provider keys.

## Data handling decisions before deployment

1. Confirm that the system prompt is approved for external sharing. It is a
   12 KB product prompt and may contain internal teaching rules.
2. Review student profiles for personal or sensitive learning information.
   Replace real identifiers with pseudonyms or exclude profile snapshots.
3. Review benchmark questions and source licenses before allowing public
   downloads. A private reviewer share is safer than an anonymous public API.
4. Decide whether individual response exports may be retained by recipients.
   The API cannot prevent a recipient from copying content once shared.
5. Never serve the unblinding key or reviewer-only notes to a shared-link user.

## Deployment shape

1. Add the API and its dependencies in a separate service module. Keep the
   benchmark runner and Ollama backend unchanged.
2. Add an index/rebuild command that validates manifests and JSONL rows, records
   valid completed runs, and reports partial runs without publishing them by
   default.
3. Implement authentication, ownership, and read-only share tokens before
   opening the service to the internet.
4. Build the run list, run detail, result comparison, and export views.
5. Deploy the API and artifact storage on an always-available host behind a
   managed HTTPS reverse proxy or platform ingress. Keep storage private, back
   up the index and run artifacts, and configure access logs without recording
   share tokens.
6. Start with invited reviewers. Consider public access only after content
   rights and prompt/profile sharing choices are settled.

## Comparison rules

- Align results by stable `test_id`, and show missing/error results explicitly.
- Show measured runtime, response length, token rate, and truncation alongside
  outputs. These metrics do not establish answer quality.
- Label a run as comparable only when benchmark version, dataset, rendered
  prompt hash, profile, and generation settings match. Diagnostic reruns with a
  different token budget must be marked separately.
- Do not present an automatic quality winner until human scoring is recorded.

## Suggested build order

1. Agree on private invited access and which artifacts a share may include.
2. Define response schemas and run-index validation against current artifacts.
3. Build run listing, details, and paginated results endpoints.
4. Add prompt/profile artifact endpoints and safe exports with explicit share
   permissions.
5. Add comparison endpoint and a minimal browser UI.
6. Deploy with authentication, HTTPS, backups, and revocable share links.

## Acceptance checks for implementation

- A reviewer can open an authorized share and compare two complete runs without
  access to this repository or machine.
- A reviewer cannot access unshared runs, arbitrary files, the scoring key, or
  the Ollama endpoint.
- Revoked and expired links stop working.
- Incomplete or diagnostic runs carry clear labels and cannot be mistaken for a
  matched comparison.
- Question, response, prompt, profile, and export downloads work only when the
  share grants those artifact classes.
