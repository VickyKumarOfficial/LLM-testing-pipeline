# Niera Model Benchmark v1

Model-agnostic benchmark harness for comparing LLMs under identical prompts,
generation settings, evaluation logic and result schemas.

Current scope:
- Local inference: Ollama
- JSONL benchmark dataset
- Fixed generation configuration
- Raw response preservation
- Per-run JSONL results
- Placeholder smoke tests only

The locked Benchmark v1 question set is 56 tests:
20 NCERT + 20 JEE/NEET + 16 adversarial.

The real questions are intentionally not included yet.

## Setup

Install Ollama separately, then pull a model:

    ollama pull qwen3:8b

Create the Python environment:

    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt

Run the smoke benchmark:

    python run_benchmark.py --model qwen3:8b --backend ollama --dataset datasets/smoke.jsonl

Results are written under results/<run_id>/.

## Architecture rule

The benchmark core must remain independent of the inference backend.
Ollama is the first backend. A Colab/Transformers backend can be added later
without changing the dataset, prompts, evaluators or result schema.
