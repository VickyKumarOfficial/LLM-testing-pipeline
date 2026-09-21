"""Print speed/output stats for finished runs, or compare several side by side.

    python scripts/report.py                      # latest run
    python scripts/report.py results/<run_id>     # one run
    python scripts/report.py results/a results/b  # compare models
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from niera_benchmark.io import read_jsonl          # noqa: E402
from niera_benchmark.stats import format_summary, summarize  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def load(run_dir: Path):
    rows = list(read_jsonl(run_dir / "results.jsonl"))
    meta = {}
    run_json = run_dir / "run.json"
    if run_json.exists():
        meta = json.loads(run_json.read_text(encoding="utf-8"))
    model = meta.get("model") or (rows[0].get("model") if rows else "unknown")
    return model, rows


def main():
    args = sys.argv[1:]
    if not args:
        runs = sorted(d for d in (ROOT / "results").iterdir() if d.is_dir())
        if not runs:
            print("No runs found in results/")
            return
        args = [str(runs[-1])]

    summaries = []
    for arg in args:
        run_dir = Path(arg)
        if not run_dir.is_absolute():
            run_dir = ROOT / run_dir
        model, rows = load(run_dir)
        s = summarize(rows)
        summaries.append((model, run_dir.name, s))
        print(format_summary(f"{model}  [{run_dir.name}]", s))

    if len(summaries) > 1:
        print("\n" + "=" * 78)
        print(" COMPARISON")
        print("=" * 78)
        head = f" {'model':<22}{'ok':>7}{'med lat':>10}{'p95 lat':>10}{'tok/s':>9}{'med out':>10}"
        print(head)
        print("-" * 78)
        for model, _, s in summaries:
            print(
                f" {model:<22}"
                f"{s['ok']}/{s['tests']:<4}"
                f"{s['latency_ms'].get('median', 0) / 1000:>9.1f}s"
                f"{s['latency_ms'].get('p95', 0) / 1000:>9.1f}s"
                f"{s['tokens_per_sec'].get('median', 0):>9.1f}"
                f"{s['output_tokens'].get('median', 0):>10.0f}"
            )
        print("=" * 78)


if __name__ == "__main__":
    main()
