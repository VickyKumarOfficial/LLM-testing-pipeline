"""Speed and output-shape statistics for a benchmark run.

Deliberately descriptive only: nothing here judges whether an answer is
educationally good. That stays with human review.
"""
import statistics
from collections import defaultdict
from typing import Any, Dict, List


def _pct(values: List[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    k = (len(ordered) - 1) * p
    lo, hi = int(k), min(int(k) + 1, len(ordered) - 1)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (k - lo)


def _num(values: List[float]) -> Dict[str, float]:
    if not values:
        return {"n": 0}
    return {
        "n": len(values),
        "mean": round(statistics.fmean(values), 1),
        "median": round(statistics.median(values), 1),
        "p95": round(_pct(values, 0.95), 1),
        "min": round(min(values), 1),
        "max": round(max(values), 1),
    }


def summarize(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    ok = [r for r in rows if "error" not in r]
    errors = [r for r in rows if "error" in r]

    latencies, out_tokens, in_tokens, tps, lengths = [], [], [], [], []
    truncated, empty, thinking_only = [], [], []
    reasoning_runs = 0
    by_group = defaultdict(lambda: {"latency": [], "out_tokens": []})

    for r in ok:
        gen = r.get("generation", {})
        meta = r.get("metadata", {})
        text = r.get("output", "") or ""
        test = r.get("test", {})

        lat = gen.get("latency_ms")
        ot = gen.get("output_tokens")
        it = gen.get("input_tokens")

        if lat is not None:
            latencies.append(lat)
        if ot is not None:
            out_tokens.append(ot)
        if it is not None:
            in_tokens.append(it)

        # Prefer Ollama's own eval_duration for tokens/sec; it excludes model
        # load and prompt processing, so it measures real decode speed.
        eval_ns = meta.get("eval_duration_ns")
        if ot and eval_ns:
            tps.append(ot / (eval_ns / 1e9))
        elif ot and lat:
            tps.append(ot / (lat / 1000))

        lengths.append(len(text))
        if meta.get("has_thinking"):
            reasoning_runs += 1
        if not text.strip():
            empty.append(r.get("test_id"))
            # Empty answer but the model did think: the token budget ran out
            # before it began writing. A harness problem, not a refusal.
            if meta.get("has_thinking"):
                thinking_only.append(r.get("test_id"))
        # max_tokens reached: the answer was cut off mid-thought.
        if ot and ot >= gen.get("config", {}).get("max_tokens", 10**9):
            truncated.append(r.get("test_id"))

        for key in ("track", "subject", "difficulty"):
            val = test.get(key)
            if val:
                g = by_group[f"{key}={val}"]
                if lat is not None:
                    g["latency"].append(lat)
                if ot is not None:
                    g["out_tokens"].append(ot)

    groups = {
        name: {
            "n": len(vals["latency"]),
            "median_latency_s": round(statistics.median(vals["latency"]) / 1000, 1)
            if vals["latency"] else None,
            "median_out_tokens": round(statistics.median(vals["out_tokens"]))
            if vals["out_tokens"] else None,
        }
        for name, vals in sorted(by_group.items())
    }

    return {
        "tests": len(rows),
        "ok": len(ok),
        "errors": len(errors),
        "error_ids": [r.get("test_id") for r in errors],
        "wall_clock_s": round(sum(latencies) / 1000, 1),
        "latency_ms": _num(latencies),
        "output_tokens": _num([float(x) for x in out_tokens]),
        "input_tokens": _num([float(x) for x in in_tokens]),
        "tokens_per_sec": _num(tps),
        "response_chars": _num([float(x) for x in lengths]),
        "truncated_at_max_tokens": truncated,
        "empty_responses": empty,
        "thinking_only_no_answer": thinking_only,
        "reasoning_model_responses": reasoning_runs,
        "by_group": groups,
    }


def format_summary(model: str, s: Dict[str, Any]) -> str:
    lat, tps, ot = s["latency_ms"], s["tokens_per_sec"], s["output_tokens"]
    lines = [
        "",
        "=" * 58,
        f" SPEED & OUTPUT PROFILE - {model}",
        "=" * 58,
        f" Completed          {s['ok']}/{s['tests']}  ({s['errors']} errors)",
        f" Total generation   {s['wall_clock_s'] / 60:.1f} min",
        "",
        f" Latency/question   median {lat.get('median', 0) / 1000:.1f}s"
        f"   p95 {lat.get('p95', 0) / 1000:.1f}s"
        f"   max {lat.get('max', 0) / 1000:.1f}s",
        f" Decode speed       median {tps.get('median', 0):.1f} tok/s"
        f"   min {tps.get('min', 0):.1f}",
        f" Output length      median {ot.get('median', 0):.0f} tok"
        f"   max {ot.get('max', 0):.0f} tok",
        f" Prompt size        median {s['input_tokens'].get('median', 0):.0f} tok",
    ]
    if s["truncated_at_max_tokens"]:
        lines.append(
            f" ! TRUNCATED        {len(s['truncated_at_max_tokens'])} answers hit max_tokens: "
            + ", ".join(s["truncated_at_max_tokens"][:5])
        )
    if s["empty_responses"]:
        lines.append(f" ! EMPTY            {', '.join(s['empty_responses'][:5])}")
    if s.get("thinking_only_no_answer"):
        lines.append(
            f" ! THOUGHT, NO ANSWER  {len(s['thinking_only_no_answer'])} ran out of"
            " budget mid-reasoning - raise max_tokens"
        )
    if s.get("reasoning_model_responses"):
        lines.append(
            f" i Reasoning model     {s['reasoning_model_responses']}/{s['ok']}"
            " responses included a thinking block"
        )
    if s["error_ids"]:
        lines.append(f" ! ERRORS           {', '.join(s['error_ids'][:5])}")

    lines += ["", " Median latency / output length by group:"]
    for name, g in s["by_group"].items():
        if name.startswith("track=") or name.startswith("difficulty="):
            lines.append(
                f"   {name:<28} n={g['n']:<3} {g['median_latency_s']}s"
                f"   {g['median_out_tokens']} tok"
            )
    lines.append("=" * 58)
    return "\n".join(lines)
