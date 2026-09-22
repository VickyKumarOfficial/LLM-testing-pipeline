# Niera — Qwen3-8B Fine-Tuning Plan v1

Target model: **`Qwen/Qwen3-8B`**
Method: **LoRA SFT (supervised fine-tuning)**
Status: plan, not yet executed
Date: 2026-09-22

---

## 0. Locked decisions

These are decided. Do not re-open them mid-build.

| Item | Decision |
|---|---|
| Base model | `unsloth/Qwen3-8B` (bf16, not the 4-bit build) |
| Method | LoRA SFT. Not full fine-tune, not pretraining, not RLHF (yet) |
| Trainer | Unsloth + TRL `SFTTrainer` |
| Hardware | Rented A100 80GB. **Not** the 16 GB Mac |
| Dataset size | ~3,000 rows, hand-curated. Not 1M |
| System prompt | The real `prompts/system.txt`, included in every training row |
| Thinking mode | Mixed 75% reasoning / 25% direct, per Qwen3's own guidance |
| Evaluation | Existing `run_benchmark.py` + the 56-test set, unchanged |

**Why not the Mac.** A 16 GB Mac can QLoRA an 8B model, but Niera's rendered system prompt is ~4,000 tokens. Every training row needs ~6k token sequence length. That does not fit in 16 GB at any usable batch size. Renting an A100 for 4 hours costs under $10 — cheaper than a week of fighting OOM errors.

**Why Qwen3 and not Llama.** Called by you. Note the one consequence: Qwen3 has a thinking mode, and naive SFT on direct-answer data will suppress it. Section 4 handles this.

---

## 1. What this fine-tune will and will not fix

Be clear-eyed. Your system prompt is already doing enormous work.

**Will improve:**
- Style consistency — LaTeX conventions, no filler endings, no leaked headings
- Adversarial detection — catching false premises reliably instead of ~half the time
- Implicit intent — answering `"rotational"` correctly without a clarifying question
- Latency — you can eventually shrink the inference-time system prompt

**Will not fix:**
- Factual gaps in physics/chemistry. LoRA teaches *behaviour*, not new knowledge. If the base model doesn't know a formula, 3,000 rows will not teach it — that needs RAG, which your architecture already plans for
- Arithmetic errors
- Anything your benchmark hasn't measured yet

If the base-model benchmark shows failures that are mostly *factual*, fine-tuning is the wrong lever and you should build the KB retrieval layer first. Check the two runs in `results/` before spending the GPU money.

---

## 2. The dataset — read this section twice

This is 80% of the work and 100% of the outcome. The training code is a weekend; the dataset is the project.

### 2.1 Can we use the HuggingFace datasets?

**Yes for the questions. No for the answers.**

Take the questions from HF. Throw the answers away and write new ones.

Here is why, in plain terms. Your `prompts/system.txt` defines a very specific way of answering:

- Use `$x^2$`, never `$ x^2 $`
- Never end with generic encouragement
- If the student states a wrong premise, correct it before answering
- Adapt depth to the student's knowledge graph
- Stay under ~400 words unless genuinely multi-concept
- Never say "based on your profile"

The HF NCERT datasets contain none of this. `lokeshe09/mathematics_ncert` is generic ChatGPT-style QA. `Henit007/Ncert` is 1M rows of synthetic tutoring text with a completely different system prompt baked in.

If you fine-tune on those answers, you are explicitly training the model that **the correct response to Niera's system prompt is to ignore it**. The fine-tune will make your benchmark scores go *down*. This is the single most common way domain fine-tunes fail.

So:

| Source | Use it for | Don't use it for |
|---|---|---|
| `lokeshe09/mathematics_ncert` (1,388 rows) | Question bank, topic coverage | Target answers |
| `Henit007/Ncert` (1M rows) | Question bank only, heavily sampled | Target answers — this is synthetic and unverified |
| Your other ~8 links | Same — mine for questions | Same |

### 2.2 What one training row must look like

Every row is a three-part conversation. Exactly this shape:

```json
{
  "messages": [
    {"role": "system",    "content": "<the FULL rendered system.txt, profile filled in>"},
    {"role": "user",      "content": "why negative here"},
    {"role": "assistant", "content": "<the ideal Niera answer, in Niera's house style>"}
  ]
}
```

Three rules that are not negotiable:

1. **The system prompt goes in every single row, fully rendered.** Whatever the model sees at inference, it must see in training. Any mismatch here silently wrecks the result.
2. **Rotate the student profile.** Build 4 different `student_profile.json` variants — a weak Class 10 NCERT student, a mid JEE student (the existing `JEE-2026-ARJUN-01`), a strong JEE Advanced student, a NEET student. Distribute rows across all four. If you train on one profile only, the model memorizes Arjun's weak areas and applies them to every student forever.
3. **The assistant answer is the product.** It must be something you would ship. If you would not show it to a paying student, it does not go in the training set.

### 2.3 Where the answers come from

Two sources, in this order:

- **Hand-written** for the high-leverage categories — adversarial, implicit-intent, out-of-scope. These are small (about 1,100 rows) and nobody on HuggingFace has them. This is Niera's actual moat.
- **Distilled** for the bulk academic set. Feed the question + your real `system.txt` to a strong teacher model, take the output, then have a subject expert verify and correct it. Budget roughly 30 seconds of human review per row.

Check the teacher model's terms of service before using its outputs to train a model you ship commercially. This is a real legal question, not a formality.

### 2.4 The exact mix — 3,000 rows

Do not scale this up until v1 is measured. 3,000 excellent rows beats 100,000 mediocre ones, every time.

| # | Category | Rows | Where from | Purpose |
|---|---|---|---|---|
| 1 | NCERT solved (Class 9–12, Phy/Chem/Math/Bio) | 1,000 | HF questions, answers regenerated | Core coverage |
| 2 | JEE Main / Advanced problems | 500 | PYQ papers | Multi-concept rigour |
| 3 | NEET problems | 200 | PYQ papers | NCERT-precision recall |
| 4 | **Adversarial — false premise** | 350 | **Hand-written** | The `SET 2` failure mode |
| 5 | **Adversarial — wrong student claim** | 250 | **Hand-written** | System prompt §9 |
| 6 | **Implicit intent** (`"rotational"`, `"solve this"`) | 300 | **Hand-written** | System prompt §4 |
| 7 | **Profile-adaptive pairs** (same Q, 2 profiles, 2 answers) | 200 | **Hand-written** | Teaches the model to *use* the knowledge graph |
| 8 | **Out-of-scope redirects** | 100 | **Hand-written** | System prompt §11 |
| 9 | Ambiguous / missing-information | 100 | Hand-written | System prompt §10 |
|  | **Total** | **3,000** | | |

Categories 4–9 are 1,300 rows — **43% of the set**. That ratio is deliberate. Those are the behaviours no public dataset contains and the ones your benchmark actually scores.

### 2.5 Cleaning rules

Apply in order, every source:

1. Normalize to the `messages` schema above
2. Deduplicate — exact match, then near-match (MinHash, threshold 0.85)
3. Drop any row where the answer is shorter than the question
4. Drop LLM artifacts — `"As an AI"`, `"I hope this helps"`, `"Great question!"`
5. Fix LaTeX to Niera's convention: `$x^2$`, no padded delimiters
6. Drop anything with broken Unicode or garbled math
7. **Contamination check** — no training row may match any of the 56 questions in `datasets/niera_legitimate_questions_verified_v1.jsonl`. Check by normalized-text fuzzy match, not exact. NCERT overlap here is very likely and will silently invalidate your entire evaluation
8. Split 95 / 5 into `train.jsonl` / `val.jsonl`

### 2.6 The Qwen3 thinking-mode split

Qwen3 supports thinking and non-thinking modes. Fine-tuning only on direct answers degrades its reasoning. Qwen3's own docs and Unsloth both recommend a **75% reasoning / 25% non-reasoning** mix.

For Niera, apply it by category:

- **Reasoning rows (~2,250):** JEE/NEET problems, derivations, multi-step NCERT, all adversarial rows. Assistant content includes a `<think>...</think>` block before the answer.
- **Direct rows (~750):** definitions, one-line recall, out-of-scope redirects, simple NCERT. No think block.

The `<think>` content is internal reasoning — it must never leak into the visible answer, and `run_benchmark.py` should strip it before scoring.

---

## 3. Step-by-step execution

### Phase 0 — Freeze the baseline (1 day)

You cannot prove improvement without a locked "before".

```bash
ollama pull qwen3:8b
python run_benchmark.py --model qwen3:8b \
  --dataset datasets/niera_legitimate_questions_verified_v1.jsonl
scripts/save_run.sh
```

Score all 56 by hand against the 6 criteria in `config/benchmark.yaml`. Commit the scores. This number is the only thing the fine-tune is competing against.

Note the base model's Ollama quantization (`ollama show qwen3:8b`). You will need to match it in Phase 4.

### Phase 1 — Build the dataset (3–4 weeks, the real work)

```
finetune/
├── sources/              # raw HF pulls + PYQ dumps
├── profiles/             # 4 student_profile variants
├── scripts/
│   ├── 01_ingest.py      # HF → normalized questions
│   ├── 02_generate.py    # question + system.txt → teacher → draft answer
│   ├── 03_clean.py       # §2.5 rules
│   ├── 04_render.py      # attach system prompt + profile → messages format
│   └── 05_contamination.py
└── data/
    ├── train.jsonl
    └── val.jsonl
```

Gate: do not proceed until a human has reviewed 100% of categories 4–9 and a 10% sample of 1–3.

### Phase 2 — Environment (1 hour)

Rent an A100 80GB (RunPod, Lambda, or Vast). Then:

```bash
pip install unsloth trl peft accelerate bitsandbytes
```

Upload `train.jsonl`, `val.jsonl`, and `prompts/system.txt`.

### Phase 3 — Train (4–6 hours)

```python
from unsloth import FastLanguageModel
from unsloth.chat_templates import train_on_responses_only
from trl import SFTTrainer, SFTConfig
from datasets import load_dataset

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name     = "unsloth/Qwen3-8B",
    max_seq_length = 8192,
    load_in_4bit   = False,          # A100 80GB: bf16 LoRA, ~5% better than QLoRA
)

model = FastLanguageModel.get_peft_model(
    model,
    r                          = 32,
    lora_alpha                 = 32,
    lora_dropout               = 0.0,
    target_modules             = ["q_proj","k_proj","v_proj","o_proj",
                                  "gate_proj","up_proj","down_proj"],
    use_gradient_checkpointing = "unsloth",
    random_state               = 42,
)

ds = load_dataset("json", data_files={"train":"data/train.jsonl",
                                      "validation":"data/val.jsonl"})
ds = ds.map(lambda x: {"text": tokenizer.apply_chat_template(
    x["messages"], tokenize=False)})

trainer = SFTTrainer(
    model         = model,
    tokenizer     = tokenizer,
    train_dataset = ds["train"],
    eval_dataset  = ds["validation"],
    args = SFTConfig(
        max_seq_length              = 8192,
        per_device_train_batch_size = 1,
        gradient_accumulation_steps = 16,
        num_train_epochs            = 2,
        learning_rate               = 1e-4,
        lr_scheduler_type           = "cosine",
        warmup_ratio                = 0.05,
        optim                       = "adamw_8bit",
        weight_decay                = 0.01,
        logging_steps               = 5,
        eval_strategy               = "steps",
        eval_steps                  = 50,
        save_steps                  = 100,
        seed                        = 42,
        output_dir                  = "outputs",
    ),
)

# Train on the assistant's tokens only — never on the system prompt or question.
trainer = train_on_responses_only(
    trainer,
    instruction_part = "<|im_start|>user\n",
    response_part    = "<|im_start|>assistant\n",
)

trainer.train()
model.save_pretrained("niera-qwen3-8b-lora")
```

**Watch the eval loss.** If it stops falling and starts rising, you are overfitting — stop and drop to 1 epoch. On 3,000 rows this is a live risk.

### Phase 4 — Export to Ollama (1 hour)

```python
model.save_pretrained_gguf("niera-qwen3-8b",
                           tokenizer,
                           quantization_method="q4_k_m")
```

Match the base model's quantization exactly. If base `qwen3:8b` is Q4_K_M and you export Q8_0, your benchmark measures the quantization difference, not the fine-tune. That mistake will hand you a fake win.

```bash
# Modelfile
FROM ./niera-qwen3-8b.Q4_K_M.gguf
PARAMETER temperature 0.2
PARAMETER top_p 0.9

ollama create niera-qwen3-8b -f Modelfile
```

### Phase 5 — Evaluate (1 day)

Same harness, same config, same profile, same seed. Only `--model` changes.

```bash
python run_benchmark.py --model niera-qwen3-8b \
  --dataset datasets/niera_legitimate_questions_verified_v1.jsonl
scripts/save_run.sh
```

Score by hand, blind if you can — shuffle base and tuned outputs so the scorer doesn't know which is which.

### Phase 6 — Decide

| Result | Action |
|---|---|
| Adversarial up, legitimate flat or up | Ship it. Start v2 dataset |
| Adversarial up, legitimate down | Overfit on adversarial. Rebalance to ~25%, retrain |
| Both flat | Dataset too small or too generic. Do not add rows — improve answer quality |
| Both down | Train/inference mismatch. Check the system prompt is byte-identical in both |

---

## 4. Hyperparameters — locked

| Parameter | Value | Reason |
|---|---|---|
| `r` | 32 | Behaviour change needs capacity; 16 is too small for style + adversarial |
| `lora_alpha` | 32 | alpha = r |
| `lora_dropout` | 0.0 | Unsloth's optimized path |
| `target_modules` | all 7 | Attention-only won't shift output style |
| `learning_rate` | 1e-4 | Standard for r=32 LoRA |
| `num_train_epochs` | 2 | 3+ memorizes at this dataset size |
| `max_seq_length` | 8192 | 4k system + question + answer + think block |
| effective batch | 16 | 1 × 16 grad accum |
| `seed` | 42 | Matches `config/generation.yaml` |
| loss masking | responses only | Never train on the system prompt |

---

## 5. Success criteria

Set before you look at results.

- **Adversarial (`SET 2`, 16 tests):** base score → target **+25 percentage points** on premise detection
- **Legitimate (`SET 1`, 40 tests):** no regression greater than 5%
- **Format compliance:** LaTeX convention violations and filler endings → near zero
- **Implicit intent:** zero unnecessary clarifying questions on short queries

If adversarial improves but legitimate regresses more than 5%, the run failed. Say so and rebalance.

---

## 6. Timeline and cost

| Phase | Time | Cost |
|---|---|---|
| 0 — Baseline | 1 day | $0 |
| 1 — Dataset | 3–4 weeks | teacher API + expert review time |
| 2 — Environment | 1 hour | — |
| 3 — Training | 4–6 h | ~$10 (A100 80GB) |
| 4 — Export | 1 hour | — |
| 5 — Evaluate | 1 day | $0 |

GPU cost is trivial. Dataset construction is the entire budget. Plan accordingly.

---

## 7. Risks

| Risk | Mitigation |
|---|---|
| Training answers contradict `system.txt` | Regenerate all answers under the real system prompt. Never use HF answers raw |
| Benchmark contamination from NCERT overlap | Phase 1 script `05_contamination.py`, fuzzy match |
| Single-profile memorization | 4 rotating profiles |
| Thinking mode suppressed | 75/25 reasoning split |
| Quantization confound | Match base model's quant exactly |
| Overfitting on 3k rows | 2 epochs max, watch eval loss, 5% val split |
| Dataset licensing | Audit all ~10 HF licenses + teacher-model ToS before shipping |

---

## 8. Immediate next steps

1. Score the two existing runs in `results/` and commit the baseline numbers
2. Confirm the base-model failures are behavioural, not factual — if factual, build RAG first
3. Send the remaining 8 HF dataset links; run the license audit
4. Write the 4 student profile variants
5. Hand-write the first 50 adversarial rows as a format template before scaling

---

*References: [Unsloth Qwen3 fine-tuning docs](https://unsloth.ai/docs/models/tutorials/qwen3-how-to-run-and-fine-tune) · [Qwen3 official Unsloth guide](https://qwen.readthedocs.io/en/latest/training/unsloth.html) · [Qwen3 Technical Report](https://arxiv.org/pdf/2505.09388)*
