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

Start Ollama in a separate terminal:

    ollama serve

Smoke check (3 questions):

    python run_benchmark.py --model qwen3:8b --dataset datasets/smoke.jsonl

Full benchmark (56 questions, roughly 25-35 min on an 8B model):

    python run_benchmark.py \
      --model qwen3:8b \
      --dataset datasets/niera_legitimate_questions_verified_v1.jsonl

Useful flags:

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
