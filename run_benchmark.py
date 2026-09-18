import argparse
import datetime as dt
import uuid
from pathlib import Path

from niera_benchmark.backends.ollama import OllamaBackend
from niera_benchmark.evaluators import basic_evaluation
from niera_benchmark.io import read_jsonl, write_json, write_jsonl
from niera_benchmark.models import GenerationConfig

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

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--backend", choices=["ollama"], default="ollama")
    parser.add_argument("--dataset", default="datasets/smoke.jsonl")
    parser.add_argument("--ollama-host", default="http://localhost:11434")
    args = parser.parse_args()

    config = load_generation_config(ROOT / "config/generation.yaml")
    dataset_path = ROOT / args.dataset

    if args.backend == "ollama":
        backend = OllamaBackend(args.model, args.ollama_host)

    run_id = f"{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    run_dir = ROOT / "results" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    system_prompt = (ROOT / "prompts/system.txt").read_text(encoding="utf-8")
    user_template = (ROOT / "prompts/user_template.txt").read_text(encoding="utf-8")

    tests = list(read_jsonl(dataset_path))
    results = []

    print("Niera Benchmark v1")
    print(f"Model: {args.model}")
    print(f"Backend: {args.backend}")
    print(f"Tests: {len(tests)}")
    print()

    for index, test in enumerate(tests, start=1):
        user_prompt = user_template.replace("{{question}}", test["question"])
        print(f"[{index}/{len(tests)}] {test['id']} ...", end=" ", flush=True)

        try:
            response = backend.generate(system_prompt, user_prompt, config)
            result = {
                "run_id": run_id,
                "benchmark": "Niera Benchmark",
                "benchmark_version": "v1",
                "model": args.model,
                "backend": args.backend,
                "test": test,
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
            print("OK")
        except Exception as exc:
            result = {
                "run_id": run_id,
                "benchmark": "Niera Benchmark",
                "benchmark_version": "v1",
                "model": args.model,
                "backend": args.backend,
                "test": test,
                "error": {"type": type(exc).__name__, "message": str(exc)},
            }
            print(f"ERROR: {exc}")

        results.append(result)

    write_jsonl(run_dir / "results.jsonl", results)
    write_json(run_dir / "run.json", {
        "run_id": run_id,
        "model": args.model,
        "backend": args.backend,
        "dataset": str(dataset_path),
        "generation_config": config.__dict__,
        "test_count": len(tests),
    })

    print()
    print(f"Saved results to: {run_dir}")

if __name__ == "__main__":
    main()
