#!/usr/bin/env bash
# Commit and push a benchmark run so the responses are backed up off-machine.
#
#   scripts/save_run.sh                  # save the newest run in results/
#   scripts/save_run.sh <run_id>         # save a specific run
#
# Run output is NOT gitignored, but it is easy to forget to commit. A run costs
# hours of generation; call this as soon as one finishes.
set -euo pipefail

cd "$(dirname "$0")/.."

RUN_ID="${1:-}"
if [ -z "$RUN_ID" ]; then
  RUN_ID=$(ls -t results/ | grep -v '^\.' | head -1)
fi

RUN_DIR="results/$RUN_ID"
if [ ! -d "$RUN_DIR" ]; then
  echo "No such run: $RUN_DIR" >&2
  exit 1
fi
if [ ! -f "$RUN_DIR/results.jsonl" ]; then
  echo "Refusing to save $RUN_ID: no results.jsonl (run may be incomplete)" >&2
  exit 1
fi

MODEL=$(python3 -c "import json;print(json.load(open('$RUN_DIR/run.json'))['model'])" 2>/dev/null || echo unknown)
COUNT=$(wc -l < "$RUN_DIR/results.jsonl" | tr -d ' ')

echo "Saving run $RUN_ID  (model=$MODEL, $COUNT responses)"
git add -f "$RUN_DIR"
git commit -q -m "Benchmark run $RUN_ID: $MODEL, $COUNT responses"
git push -q origin HEAD
echo "Pushed to origin. Backed up."
