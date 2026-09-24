# Niera Model Benchmark v1

Model-agnostic benchmark harness for comparing LLMs under identical prompts,
generation settings and result schemas.

Current scope:
- Local inference: Ollama
- JSONL benchmark dataset (56 tests)
- Fixed generation configuration
- Raw response preservation
- Per-run JSONL results + speed/performance profile
- Human evaluation (automated semantic scoring is intentionally out of scope)

## Benchmark set

`datasets/niera_legitimate_questions_verified_v1.jsonl` holds 56 tests in two
clearly headed sections:

    SET 1 - LEGITIMATE (40)    NCERT 20 | JEE 15 | NEET 5, source-linked
    SET 2 - ADVERSARIAL (16)   controlled false-premise / wrong-claim variants

`#` comment lines act as section headings and are skipped by the loader.

## Setup

Install Ollama separately, then pull a model:

    ollama pull qwen3:8b

Create the Python environment:

    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt

## Running

All three candidate models run through the same code path with the same
generation config. Only `--model` changes - that is what makes the comparison
valid. Never change `config/generation.yaml` for one model only.

Start Ollama in a separate terminal and leave it running:

    ollama serve

Activate the environment in your working terminal:

    source .venv/bin/activate

### Candidate models

| # | Model            | Size   | Reasoning | Expected full-run time |
|---|------------------|--------|-----------|------------------------|
| 1 | `qwen3:8b`       | 5.2 GB | yes       | ~2 h                   |
| 2 | `llama3.1:8b`    | ~4.9 GB| no        | ~40-60 min             |
| 3 | `gemma3:12b`     | ~8.1 GB| no        | ~1.5-2 h               |

Run them one at a time. 16 GB of unified memory cannot hold two of these at
once, and `gemma3:12b` uses most of it on its own.

### Model 1 - qwen3:8b

Already pulled.

    python run_benchmark.py --model qwen3:8b --dataset datasets/smoke.jsonl --limit 1

    python run_benchmark.py \
      --model qwen3:8b \
      --dataset datasets/niera_legitimate_questions_verified_v1.jsonl

    scripts/save_run.sh

### Model 2 - llama3.1:8b

    ollama pull llama3.1:8b

    python run_benchmark.py --model llama3.1:8b --dataset datasets/smoke.jsonl --limit 1

    python run_benchmark.py \
      --model llama3.1:8b \
      --dataset datasets/niera_legitimate_questions_verified_v1.jsonl

    scripts/save_run.sh

### Model 3 - gemma3:12b

    ollama pull gemma3:12b

    python run_benchmark.py --model gemma3:12b --dataset datasets/smoke.jsonl --limit 1

    python run_benchmark.py \
      --model gemma3:12b \
      --dataset datasets/niera_legitimate_questions_verified_v1.jsonl

    scripts/save_run.sh

This machine is a fanless MacBook Air. On a run this long, watch whether
per-question latency drifts upward from test 1 to test 56 - that is thermal
throttling, not the model being slow. `performance.json` holds the per-question
data needed to check it.

### After all three

    python scripts/report.py results/<qwen3_run> results/<llama_run> results/<gemma_run>

### Always do this

1. Run the `--limit 1` smoke first. It confirms the run writes cleanly in about
   a minute rather than failing two hours in.
2. Run `scripts/save_run.sh` the moment a run finishes. An uncommitted run is
   not recoverable if the directory is removed.
3. Check the printed profile for `! TRUNCATED` and `! THOUGHT, NO ANSWER`.
   Both should be empty at `max_tokens: 8192`. If either fires, raise the
   ceiling for *all* models and re-run *all* of them.

### Useful flags

    --limit 5              run only the first N tests
    --profile <path>       use a different student profile
    --ollama-host <url>    point at a non-default Ollama instance

## Model performance stats

Speed and output statistics print automatically at the end of every run.
No extra command is needed.

    ==========================================================
     SPEED & OUTPUT PROFILE - qwen3:8b
    ==========================================================
     Completed          56/56  (0 errors)
     Total generation   28.4 min

     Latency/question   median 28.8s   p95 42.4s   max 61.2s
     Decode speed       median 23.1 tok/s   min 4.7
     Output length      median 400 tok   max 2048 tok
     Prompt size        median 3900 tok

     Median latency / output length by group:
       difficulty=Hard              n=14  27.6s   900 tok
       track=JEE                    n=15  25.4s   900 tok
       ...
    ==========================================================

To re-print stats for a finished run, or compare models side by side:

    python scripts/report.py                          # latest run
    python scripts/report.py results/<run_id>         # a specific run
    python scripts/report.py results/<run_a> results/<run_b>   # comparison table

The comparison table reports ok/total, median and p95 latency, decode speed and
median output length per model - the cost side of the model decision.

Two warnings to watch for in the profile:

- `! TRUNCATED` - answers that hit `max_tokens` and were cut off mid-sentence.
  Those responses are not fairly reviewable; raise `max_tokens` in
  `config/generation.yaml` and re-run.
- `Prompt size` - the personalized system prompt costs ~4k tokens on every call.

Decode speed uses Ollama's `eval_duration`, so it excludes model load and prompt
processing and reflects real generation speed rather than first-call warmup.

## Run output

Each run writes to `results/<run_id>/`:

    results.jsonl              one record per test, written incrementally
    run.json                   run manifest, including the full stats block
    performance.json           speed/output stats on their own
    performance.txt            the printed profile, saved verbatim
    system_prompt.rendered.txt the exact system prompt sent to the model
    student_profile.json       the profile used for this run

Results are flushed after every question, so an interrupted run keeps the
responses it already collected.

## Backing up a run

Run output is tracked by git (`results/` is not ignored), but committing is
manual. A full run costs 1-2 hours of generation, so save it as soon as it
finishes:

    scripts/save_run.sh              # commit + push the newest run
    scripts/save_run.sh <run_id>     # commit + push a specific run

The script refuses to save a run with no `results.jsonl`, and pushes to
`origin` so the responses exist off-machine. Runs left uncommitted are not
recoverable if the directory is removed.

## Prompt architecture

    prompts/system.txt          stable Niera teaching behaviour + {{placeholders}}
    config/student_profile.json student knowledge graph, fills the placeholders
    prompts/user_template.txt   the student query wrapper

`subject` and `current_topic` are deliberately left UNKNOWN in the profile so
that implicit-intent inference stays under test. A run fails fast if the prompt
contains a placeholder the profile does not supply.

## Evaluation

The harness collects data; it does not score answers. Human reviewers judge
correctness, reasoning quality, hallucination, instruction following and
pedagogical quality. Adversarial tests are scored on detection (did the model
challenge the false premise?) rather than on style.

## Architecture rule

The benchmark core must remain independent of the inference backend. Ollama is
the first backend. A Colab/Transformers backend, or the Niera Pipeline N
backend, can be added without changing the dataset, prompts or result schema.

## Read-only results API

The initial API serves saved runs only. It does not call Ollama or run inference.
Install the requirements above, set a private bearer token, and start the local
server:

    export NIERA_API_TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
    uvicorn niera_api.main:app --host 127.0.0.1 --port 8000

Send `Authorization: Bearer <token>` to protected routes. For example:

    curl -H "Authorization: Bearer $NIERA_API_TOKEN" \
      http://127.0.0.1:8000/api/v1/runs

Available routes are listed at `http://127.0.0.1:8000/docs`. The health route is
`GET /api/v1/health`; protected routes list runs, return run metadata, and
provide filtered/paginated outputs. System prompt and student profile downloads
are disabled unless the server owner explicitly sets
`NIERA_API_EXPOSE_SYSTEM_PROMPT=true` or `NIERA_API_EXPOSE_PROFILE=true`.

This local server is for development on this machine. It is not reachable from
the public internet by default. Do not bind it to a public interface or deploy
the repository as a public static site. Remote sharing needs the later hosting,
private storage, and share-link phases in `API_ACCESS_PLAN.md`.

### Create and use a scoped share credential

The owner can create a share for up to 20 completed run IDs. A share expires in
one week by default. Prompt and profile access are opt-in:

    curl -X POST http://127.0.0.1:8000/api/v1/shares \
      -H "Authorization: Bearer $NIERA_API_TOKEN" \
      -H "Content-Type: application/json" \
      -d '{"run_ids":["20260922_172853_2f88de"],"expires_in_hours":168}'

The response contains `share_token`. Save it when returned, since the service
stores only its hash. A reviewer uses it as an authorization credential, not
as a URL:

    curl -H "Authorization: Share <share_token>" \
      http://127.0.0.1:8000/api/v1/shared/runs

Reviewers can only see the selected runs. Prompt/profile artifact permission is
off unless `allow_system_prompt` or `allow_profile` is set when creating the
share. Owners can list share records at `GET /api/v1/shares` and revoke
one at `DELETE /api/v1/shares/{share_id}`. Expired or revoked credentials stop
authorizing requests. A browser-friendly share URL will be added with the
reviewer UI, and hosted persistence is required before Vercel deployment.

### Publish a run to hosted storage

Phase 3 adds a controlled publisher. Create a PostgreSQL database and a **private**
Vercel Blob store, then configure `DATABASE_URL` and
`BLOB_READ_WRITE_TOKEN` in the environment. First inspect exactly what would be
uploaded:

    python scripts/publish_run.py 20260922_172853_2f88de --dry-run

The publisher validates that the manifest and every result row match the run,
and that the result count equals `test_count`. It includes only run metadata,
results, and performance summaries by default. To deliberately include sensitive
snapshots, add `--include-system-prompt` or `--include-profile`.

After reviewing the dry-run report, publish with:

    python scripts/publish_run.py 20260922_172853_2f88de

The script stores the ZIP in private Blob storage and indexes its path, manifest,
artifact list, digest, and publish status in PostgreSQL. It never uploads the
scoring sheet/key or dataset directory. Set the API to remote mode to serve the
published runs through the catalog and private blobs.

### Serve published runs

The remote-read mode and reviewer page use published archives. To run the API
against a published archive, set `NIERA_API_STORAGE_BACKEND=remote` along with
`DATABASE_URL` and the Blob credentials available to the Vercel Python SDK, then
start the API as usual. The API reads only records marked `published`; failed or
in-progress uploads stay hidden. Keep `NIERA_API_STORAGE_BACKEND=local` for the
repository-backed development view.

Open `/` for the reviewer page. An owner enters the `NIERA_API_TOKEN` and can
compare runs, download a run archive, create scoped shares, and revoke existing
shares. A reviewer opens the generated link; its credential is in the URL
fragment and is sent to the API in an `Authorization: Share` header. The fragment
is not sent in the HTTP request path. The comparison page labels configuration
mismatches and does not declare an answer-quality winner.
