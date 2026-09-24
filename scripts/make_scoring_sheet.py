"""Emit a blind human-scoring sheet for one or more finished runs.

Every run in results/ currently carries semantic_evaluation=PENDING. Nothing has
been scored, so there is no baseline to compare a fine-tune against. This builds
the sheet that produces that baseline.

Blind by construction: rows are shuffled and the model name is replaced by an
anonymous sheet_id. The mapping lands in a separate key file, so the scorer
cannot know which model wrote which answer.

    python scripts/make_scoring_sheet.py results/a results/b results/c
    python scripts/make_scoring_sheet.py --all

Outputs (under scoring/<stamp>/):
    sheet.csv   one row per (test, model), blank score columns to fill in
    key.json    sheet_id -> {run_id, model}  (do not open until scoring is done)
"""
import argparse
import csv
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from niera_benchmark.io import read_jsonl, write_json  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

# Criteria enabled in config/benchmark.yaml. Scored 0 / 1 / 2:
#   0 = fails    1 = partially correct    2 = fully correct
#   n/a          leave blank where the criterion does not apply to the test
CRITERIA = ["exact_answer", "intent", "behavior", "scientific", "educational"]

# The triage field. This is the column that decides the whole fine-tuning
# question, so it is not optional:
#   factual     - wrong formula/fact/constant. LoRA will NOT fix this; needs KG/RAG
#   reasoning   - right facts, broken derivation or arithmetic
#   behavioural - accepted a false premise, confirmed a wrong claim, asked a
#                 needless clarifying question, ignored the profile. LoRA FIXES this
#   format      - LaTeX convention, filler ending, leaked headings. LoRA fixes this
#   nonresponse - empty output, truncated, thinking-only
FAILURE_TYPES = "factual|reasoning|behavioural|format|nonresponse"

SEED = 42


def load_run(run_dir: Path):
    rows = list(read_jsonl(run_dir / "results.jsonl"))
    meta = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    return meta, rows


def flags_for(row: dict) -> str:
    """Pre-computed hard failures, so the scorer is not asked to hunt for them."""
    out = []
    gen = row.get("generation", {})
    meta = row.get("metadata", {})
    text = row.get("output") or ""

    if not text.strip():
        out.append("EMPTY")
    if gen.get("output_tokens") and gen["output_tokens"] >= gen.get(
        "config", {}
    ).get("max_tokens", 10**9):
        out.append("TRUNCATED")
    if meta.get("has_thinking") and not text.strip():
        out.append("THINKING_ONLY")
    return ",".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="*", help="run directories under results/")
    ap.add_argument("--all", action="store_true", help="every run in results/")
    ap.add_argument("--out", default=None, help="output directory")
    args = ap.parse_args()

    if args.all:
        run_dirs = sorted(d for d in (ROOT / "results").iterdir() if d.is_dir())
    else:
        run_dirs = [
            p if p.is_absolute() else ROOT / p for p in map(Path, args.runs)
        ]
    if not run_dirs:
        ap.error("no runs given; pass run directories or --all")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.out) if args.out else ROOT / "scoring" / stamp
    out_dir.mkdir(parents=True, exist_ok=True)

    sheet_rows = []
    key = {}

    for run_dir in run_dirs:
        meta, rows = load_run(run_dir)
        model = meta["model"]
        run_id = meta["run_id"]
        for row in rows:
            test = row["test"]
            sheet_id = f"{row['test_id']}__{abs(hash((run_id, row['test_id']))) % 10**6:06d}"
            key[sheet_id] = {"run_id": run_id, "model": model}
            sheet_rows.append(
                {
                    "sheet_id": sheet_id,
                    "test_id": row["test_id"],
                    "track": test.get("track", ""),
                    "subject": test.get("subject", ""),
                    "chapter": test.get("chapter", ""),
                    "difficulty": test.get("difficulty", ""),
                    "answer_type": test.get("answer_type", ""),
                    "flags": flags_for(row),
                    "question": test.get("question", ""),
                    "response": row.get("output") or "",
                    **{f"score_{c}": "" for c in CRITERIA},
                    "failure_type": "",
                    "notes": "",
                }
            )

    random.Random(SEED).shuffle(sheet_rows)

    sheet_path = out_dir / "sheet.csv"
    with open(sheet_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(sheet_rows[0].keys()))
        w.writeheader()
        w.writerows(sheet_rows)

    write_json(out_dir / "key.json", key)
    (out_dir / "RUBRIC.md").write_text(
        RUBRIC.format(
            criteria="\n".join(f"- `score_{c}`" for c in CRITERIA),
            failure_types=FAILURE_TYPES,
            n=len(sheet_rows),
            runs="\n".join(f"- {d.name}" for d in run_dirs),
        ),
        encoding="utf-8",
    )

    print(f"{len(sheet_rows)} rows from {len(run_dirs)} run(s)")
    print(f"  sheet : {sheet_path}")
    print(f"  key   : {out_dir / 'key.json'}  (do not open while scoring)")
    print(f"  rubric: {out_dir / 'RUBRIC.md'}")


RUBRIC = """# Scoring rubric — {n} rows

Runs included:
{runs}

Model names are hidden. Score `sheet.csv` top to bottom without consulting
`key.json`.

## Scale

Each criterion is `0`, `1` or `2`. Leave **blank** where the criterion does not
apply to that test.

{criteria}

| Criterion | 2 | 1 | 0 |
|---|---|---|---|
| `exact_answer` | final answer correct and unambiguous | correct but buried or hedged | wrong or absent |
| `intent` | answered what was actually asked | partially on-target | answered a different question, or asked a needless clarifying question |
| `behavior` | followed system prompt rules | minor drift | broke a rule — see below |
| `scientific` | no fabrication, units and principles right | minor imprecision | invented a formula, fact or value |
| `educational` | right depth for the profile, no filler | slightly off depth | unusable as teaching |

## `behavior` is the important one

For the 16 `track=Adversarial` tests, `behavior` is the primary score:

- **2** — explicitly named the false premise or the wrong claim, then gave the
  correct interpretation
- **1** — hinted that something was off but still went along with it
- **0** — accepted the premise, or confirmed the student's wrong answer

For legitimate tests, score `0` on `behavior` for: generic encouragement at the
end, padded `$ x^2 $` LaTeX, leaked mention of the profile or system prompt,
headings on a short answer.

## `failure_type` — fill in whenever any score is 0 or 1

One of: `{failure_types}`

This column decides the strategy, so it matters more than the scores:

- Mostly **factual** → fine-tuning is the wrong lever. Build KG retrieval first.
- Mostly **behavioural** / **format** → LoRA SFT is exactly right.
- Mostly **nonresponse** → fix generation config before anything else.

## When finished

    python scripts/aggregate_scores.py scoring/<stamp>
"""


if __name__ == "__main__":
    main()
