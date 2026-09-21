import argparse
import datetime as dt
import hashlib
import json
import uuid
from pathlib import Path

from niera_benchmark.backends.ollama import OllamaBackend
from niera_benchmark.evaluators import basic_evaluation
from niera_benchmark.io import read_jsonl, write_json
from niera_benchmark.models import GenerationConfig
from niera_benchmark.profile import load_profile, render_system_prompt
from niera_benchmark.stats import format_summary, summarize

ROOT = Path(__file__).resolve().parent

def load_generation_config(path: Path) -> GenerationConfig:
    values = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = [x.strip() for x in line.split(":", 1)]
        if value.lower() == "null":
            values[key] = None
        elif value.lower() in ("true", "false"):
            values[key] = value.lower() == "true"
        else:
            try:
                values[key] = float(value) if "." in value else int(value)
            except ValueError:
                values[key] = value
    return GenerationConfig(**values)

def test_identifier(test: dict) -> str:
    # The smoke set uses "id"; the sourced v1 set uses "test_id".
    return test.get("test_id") or test.get("id") or "UNKNOWN-ID"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--backend", choices=["ollama"], default="ollama")
    parser.add_argument("--dataset", default="datasets/smoke.jsonl")
    parser.add_argument("--profile", default="config/student_profile.json")
    parser.add_argument("--ollama-host", default="http://localhost:11434")
    parser.add_argument("--limit", type=int, default=None,
                        help="Run only the first N tests (for quick checks).")
    args = parser.parse_args()

    config = load_generation_config(ROOT / "config/generation.yaml")
    dataset_path = ROOT / args.dataset
    profile_path = ROOT / args.profile

    if args.backend == "ollama":
        backend = OllamaBackend(args.model, args.ollama_host)

    run_id = f"{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    run_dir = ROOT / "results" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    profile = load_profile(profile_path)
    system_template = (ROOT / "prompts/system.txt").read_text(encoding="utf-8")
    system_prompt = render_system_prompt(system_template, profile)
    user_template = (ROOT / "prompts/user_template.txt").read_text(encoding="utf-8")

    # Snapshot the exact prompt and profile used, so a run stays reproducible
    # even after the prompt files are edited.
    (run_dir / "system_prompt.rendered.txt").write_text(system_prompt, encoding="utf-8")
    write_json(run_dir / "student_profile.json", profile)
    prompt_hash = hashlib.sha256(system_prompt.encode("utf-8")).hexdigest()[:16]

    tests = list(read_jsonl(dataset_path))
    if args.limit:
        tests = tests[:args.limit]

    print("Niera Benchmark v1")
    print(f"Model:   {args.model}")
    print(f"Backend: {args.backend}")
    print(f"Dataset: {dataset_path.name}")
    print(f"Profile: {profile.get('profile_id', profile_path.name)}")
    print(f"Prompt:  sha256:{prompt_hash} ({len(system_prompt)} chars)")
    print(f"Tests:   {len(tests)}")
    print(f"Run dir: {run_dir}")
    print()

    results_path = run_dir / "results.jsonl"
    results = []
    ok_count = 0
    error_count = 0

    # Write incrementally: a failure partway through must not discard the
    # responses already collected.
    with open(results_path, "w", encoding="utf-8") as sink:
        for index, test in enumerate(tests, start=1):
            test_id = test_identifier(test)
            user_prompt = user_template.replace("{{question}}", test["question"])
            print(f"[{index}/{len(tests)}] {test_id} ...", end=" ", flush=True)

            base = {
                "run_id": run_id,
                "benchmark": "Niera Benchmark",
                "benchmark_version": "v1",
                "mode": "A_base_model",
                "model": args.model,
                "backend": args.backend,
                "test_id": test_id,
                "test": test,
                "prompt": {
                    "system_prompt_sha256": prompt_hash,
                    "profile_id": profile.get("profile_id"),
                    "user_prompt": user_prompt,
                },
            }

            try:
                response = backend.generate(system_prompt, user_prompt, config)
                result = {
                    **base,
                    "generation": {
                        "latency_ms": response.latency_ms,
                        "input_tokens": response.input_tokens,
                        "output_tokens": response.output_tokens,
                        "config": config.__dict__,
                    },
                    "output": response.text,
                    "evaluation": basic_evaluation(test, response.text),
                    "metadata": response.metadata,
                }
                ok_count += 1
                secs = (response.latency_ms or 0) / 1000
                print(f"OK ({secs:.1f}s)")
            except Exception as exc:
                result = {**base, "error": {"type": type(exc).__name__, "message": str(exc)}}
                error_count += 1
                print(f"ERROR: {exc}")

            results.append(result)
            sink.write(json.dumps(result, ensure_ascii=False) + "\n")
            sink.flush()

    stats = summarize(results)

    write_json(run_dir / "run.json", {
        "run_id": run_id,
        "benchmark_version": "v1",
        "mode": "A_base_model",
        "model": args.model,
        "backend": args.backend,
        "dataset": str(dataset_path),
        "profile_id": profile.get("profile_id"),
        "profile_path": str(profile_path),
        "system_prompt_sha256": prompt_hash,
        "generation_config": config.__dict__,
        "test_count": len(tests),
        "ok_count": ok_count,
        "error_count": error_count,
        "stats": stats,
        "started_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
    })

    # Standalone performance artifacts, so a run's speed profile can be read
    # or diffed without re-parsing results.jsonl.
    summary_text = format_summary(args.model, stats)
    write_json(run_dir / "performance.json", {
        "run_id": run_id,
        "model": args.model,
        "backend": args.backend,
        "dataset": dataset_path.name,
        "profile_id": profile.get("profile_id"),
        "generation_config": config.__dict__,
        "stats": stats,
    })
    (run_dir / "performance.txt").write_text(summary_text + "\n", encoding="utf-8")

    print(summary_text)
    print()
    print(f"Saved results to: {run_dir}")

if __name__ == "__main__":
    main()
