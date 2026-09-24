# Niera Qwen3 Fine-Tuning — Progress Log

This file tracks implementation of [the fine-tuning plan](NIERA_QWEN3_FINETUNE_PLAN.md).
Update it whenever work is completed, an issue is found, or a solution changes the
next step. Keep entries factual and dated.

## Current status

- **Plan phase:** Phase 0 — freeze the baseline.
- **Implementation status:** In progress; manual scoring has not started.
- **Training:** Not started. Do not rent GPU time until the baseline decision and
  Phase 1 dataset gate are complete.

## First step to do

Score the existing baseline outputs in `scoring/20260924_035340/sheet.csv`
blindly using `scoring/20260924_035340/RUBRIC.md`. The sheet has 168 rows (56
tests across three runs), and currently none of the score fields are filled.
For every row, enter the applicable 0–2 criterion scores; leave non-applicable
criteria blank. For every score of 0 or 1, assign a `failure_type` and add a
short note where useful. Do not open `key.json` while scoring. Once all rows are
scored, run:

```bash
python scripts/aggregate_scores.py scoring/20260924_035340
```

Record the aggregate baseline and failure-type mix here, then use it to decide
whether the dominant failures are behavioural (continue to dataset work) or
factual (prioritize the planned retrieval layer). Preserve the scored sheet and
results as the baseline record.

## Findings and decisions

### 2026-09-24 — Project and plan review

- Read the Qwen3 fine-tuning plan, benchmark README, and research/pipeline notes.
- Confirmed the plan's stated immediate first action is baseline scoring and
  diagnosis before building a training set or renting an A100.
- Found three completed benchmark result directories from 2026-09-22, each with
  56 result rows. The scoring rubric identifies these three runs, despite the
  plan's section 8 referring to "two existing runs"; use the three runs already
  included in the scoring key/sheet unless review of the key reveals otherwise.
- Found a new scoring package at `scoring/20260924_035340/`: blinded sheet,
  rubric, and unblinding key. The sheet currently contains 168 rows and zero
  scored rows, so no baseline conclusion can yet be drawn.
- A newer run directory, `results/20260924_134826_3d2d7f/`, contains only two
  result lines and uses `config/generation.qwen3_budget_rerun.yaml`. That config
  explicitly labels itself diagnostic-only and changes the token budget/context;
  keep it out of the matched baseline comparison unless the benchmark protocol
  is deliberately revised.
- Existing aggregate script supports the scoring sheet and prints per-model,
  per-track statistics and failure-type counts. No code or benchmark results
  were changed during this review.

### 2026-09-24 — Existing benchmark run comparison

- Compared manifests and performance statistics for all three complete 56-test
  runs. All used the same benchmark dataset, rendered system-prompt hash,
  student profile, and generation settings (`temperature=0.2`, `top_p=0.9`,
  `max_tokens=8192`, `seed=42`); all report 56/56 requests completed without
  backend errors.
- No manual answer-quality scores exist yet: all 168 rows in the blinded sheet
  are still blank. Therefore this review cannot validly declare a model the
  educational or scientific quality winner. The benchmark captures outputs;
  its rubric requires human scoring for correctness, intent, behavior,
  scientific reliability, and teaching quality.
- Operational comparison from run manifests:
  - `gemma3:12b` finished the full run fastest (3,147.9 s / 52.5 min), had no
    empty, thinking-only, or max-token-truncated outputs, and was the most
    consistent in total wall time. Its measured output rate was lower (9.7
    tokens/s), with shorter and tightly bounded outputs (median 581 tokens).
  - `llama3.1:8b` completed in 4,338.2 s / 72.3 min; it had no empty outputs,
    and had the highest median decoded-token rate of the three (11.7 tokens/s,
    narrowly below Qwen's 12.4). It produced the shortest median output (379
    tokens), but three answers hit the 8,192-token cap. It does not expose a
    reasoning channel in these runs.
  - `qwen3:8b` completed in 10,616.0 s / 176.9 min; it generated reasoning-mode
    responses on all 56 tests and had the highest median token rate (12.4
    tokens/s), but four tests exhausted the token budget in thinking without a
    visible answer, and four tests are listed as truncated. The stats list four
    thinking-only IDs, including one (`PHY-JEE-03`) not present in the
    `truncated_at_max_tokens` list; treat its response as needing review. Qwen
    produced the longest outputs (median 965 output tokens among 55 measured).
- Group timings show `llama3.1:8b` had the lowest median latency in each track
  (Adversarial 26.1s, JEE 66.2s, NCERT 34.9s, NEET 24.5s); Gemma was generally
  second-fastest. Qwen was particularly slow on JEE (median 349.3s), consistent
  with its long reasoning outputs and budget exhaustion. These timings measure
  this Mac/Ollama setup and do not establish answer quality or hosted-GPU speed.
- Provisional area read: Gemma leads on complete, concise, consistent responses;
  Llama leads on practical latency and concise direct answers; Qwen leads on
  explicit reasoning and decoded-token throughput but has a serious visible
  answer / latency weakness under the current token cap. Quality-specific
  strengths remain unknown until the blinded sheet is scored.
- The Sep 24 Qwen diagnostic rerun has only two result lines and uses a changed
  token budget/context. It is not included in this matched comparison.

## Issue log

| Date | Issue | Resolution / next action | Status |
|---|---|---|---|
| 2026-09-24 | Baseline has not been scored, so the plan's key go/no-go decision cannot be made. | Score the 168 blinded rows with the rubric, then aggregate and log results. | Open |
| 2026-09-24 | Plan says two existing runs, while the rubric includes three complete runs (168 rows total). | Follow the prepared scoring package and include its three keyed runs; verify the key before unblinding. | Open |
| 2026-09-24 | Latest Qwen rerun is incomplete and uses a changed generation budget. | Treat it as diagnostic only; do not mix with the original matched 56-test comparison. | Resolved for baseline handling |
| 2026-09-24 | User asked which model is better by subject/behavior, but there are no human quality scores yet. | Report operational differences from manifests and defer educational-quality ranking until blinded scoring is complete. | Open |

## Progress history

| Date | Work completed | Outcome |
|---|---|---|
| 2026-09-24 | Inspected repository structure, fine-tuning plan, benchmark README, scoring artifacts, result directories, and generation configs. | Phase 0 is the first active task; baseline scoring is prepared but untouched. |
| 2026-09-24 | Compared all three complete benchmark run manifests and performance summaries. | Gemma is the operational completion/consistency leader; Llama is the latency/conciseness leader; Qwen shows reasoning but has four thinking-only responses. Quality ranking awaits manual scoring. |
