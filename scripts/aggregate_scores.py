"""Unblind a filled scoring sheet and print per-model, per-track results.

    python scripts/aggregate_scores.py scoring/<stamp>

Reports a Wilson 95% confidence interval on every pass rate. With only 16
adversarial tests the interval is roughly +/-24 points, which is wide enough to
swallow a real improvement -- so the interval is printed rather than hidden. If
two models' intervals overlap, the benchmark did not separate them and the
evaluation set needs to grow before it can decide anything.
"""
import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CRITERIA = ["exact_answer", "intent", "behavior", "scientific", "educational"]


def wilson(passes: int, n: int, z: float = 1.96):
    """Wilson score interval -- correct for small n, unlike the normal approx."""
    if n == 0:
        return 0.0, 0.0, 0.0
    p = passes / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return p, max(0.0, centre - half), min(1.0, centre + half)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    sc_dir = Path(sys.argv[1])
    if not sc_dir.is_absolute():
        sc_dir = ROOT / sc_dir

    key = json.loads((sc_dir / "key.json").read_text(encoding="utf-8"))
    rows = list(csv.DictReader(open(sc_dir / "sheet.csv", encoding="utf-8")))

    unscored = [r for r in rows if not any(r[f"score_{c}"].strip() for c in CRITERIA)]
    if unscored:
        print(f"WARNING: {len(unscored)}/{len(rows)} rows unscored; "
              f"reporting on the {len(rows) - len(unscored)} that are scored.\n")

    # model -> track -> criterion -> [scores]
    agg = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    failures = defaultdict(lambda: defaultdict(int))

    for r in rows:
        meta = key.get(r["sheet_id"])
        if not meta:
            continue
        model, track = meta["model"], r["track"] or "?"
        scored = False
        for c in CRITERIA:
            v = r[f"score_{c}"].strip()
            if v == "":
                continue
            scored = True
            agg[model][track][c].append(int(v))
            agg[model]["ALL"][c].append(int(v))
        if scored and r["failure_type"].strip():
            failures[model][r["failure_type"].strip()] += 1

    for model in sorted(agg):
        print("=" * 72)
        print(f"  {model}")
        print("=" * 72)
        for track in sorted(agg[model], key=lambda t: (t != "ALL", t)):
            per = agg[model][track]
            n = max((len(v) for v in per.values()), default=0)
            if not n:
                continue
            print(f"\n  {track}  (n={n})")
            for c in CRITERIA:
                vals = per.get(c, [])
                if not vals:
                    continue
                # "pass" = 2. A 1 is a partial credit and does not count as a pass.
                p, lo, hi = wilson(sum(1 for v in vals if v == 2), len(vals))
                mean = sum(vals) / len(vals)
                print(f"    {c:<14} pass {p*100:5.1f}%  "
                      f"[{lo*100:4.1f}, {hi*100:4.1f}]   mean {mean:.2f}")
        if failures[model]:
            total = sum(failures[model].values())
            print(f"\n  failure types (n={total})")
            for ft, cnt in sorted(failures[model].items(), key=lambda x: -x[1]):
                print(f"    {ft:<14} {cnt:>3}  ({cnt/total*100:.0f}%)")
        print()

    print("-" * 72)
    print("Strategy read-off, from the failure-type mix of the chosen model:")
    print("  mostly factual      -> build KG retrieval first; LoRA will not help")
    print("  mostly behavioural  -> LoRA SFT is the right lever; proceed")
    print("  mostly nonresponse  -> fix generation config before fine-tuning")


if __name__ == "__main__":
    main()
