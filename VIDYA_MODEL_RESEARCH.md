# Vidya — Model Research for the Niera Benchmark

Research date: 2026-09-22. All claims below are sourced from primary sources
(Hugging Face repo files and API, the Ollama registry, the publisher's own pages).
Secondary sources were not used. Anything unverifiable is marked as such.

---

**Both supplied URLs resolve and match the description.**
<https://huggingface.co/neo-saket/vidya-9b> and <https://ollama.com/neosaket/vidya> are both
live, and both describe an NCERT/JEE/NEET tutoring model as the user expected. One correction to
a working assumption: the "9B" does **not** indicate a Gemma-2-9B derivative. `config.json` says
Qwen3.5 (§4), and 8.95B is the actual parameter count. That flips which existing candidate it
duplicates — it overlaps `qwen3:8b`, not the `gemma3:12b` slot it would fill.

## Verdict

**Vidya exists.** It is a real, released family of NCERT/JEE/NEET tutoring models —
`neo-saket/vidya-2b`, `neo-saket/vidya-4b`, `neo-saket/vidya-9b` on Hugging Face, pullable
from Ollama as `neosaket/vidya:2b|4b|9b`. It is a chat/instruct model, Apache-2.0, and the
9B Q4_K_M weighs 5.6 GB, so it fits comfortably in 16 GB. **But it should not replace
gemma3:12b as the third benchmark candidate.** Two reasons, both structural. First, it is a
LoRA fine-tune of **Qwen3.5-9B** (or 4B), so it sits in the same model family as the already
benchmarked `qwen3:8b` — it is not an independent data point, it is a variant of an existing
one. Second, it is a solo hobby project by one individual: the only published evaluation is a
self-reported 30-sample LLM-as-judge "tutoring quality" score with no accuracy benchmark on
NCERT/JEE/NEET content, the two model cards contradict each other about whether continued
pre-training on NCERT text even happened, and the GitHub repo the card links as training code
returns 404. There is nothing here that would survive a reviewer asking "why this model".
Vidya is worth running as an *extra, fourth* curiosity run — a domain-tuned small model is
genuinely interesting against the adversarial false-premise set — but the third slot in a
base-model comparison should stay with a different architecture family, and gemma3:12b remains
the better occupant of it.

---

## 1. Does "Vidya" exist as a released LLM? Exact repo ids

Yes. Three sibling repos from one author, all created May 2026, all last touched 2026-06-30
(<https://huggingface.co/api/models/neo-saket/vidya-4b>,
`.../vidya-9b`, `.../vidya-2b`):

| Repo id | Created | Last modified | HF downloads | Likes |
|---|---|---|---|---|
| [`neo-saket/vidya-9b`](https://huggingface.co/neo-saket/vidya-9b) | 2026-05-18 | 2026-06-30 | 95 | 1 |
| [`neo-saket/vidya-4b`](https://huggingface.co/neo-saket/vidya-4b) | 2026-05-19 | 2026-06-30 | 817 | 1 |
| [`neo-saket/vidya-2b`](https://huggingface.co/neo-saket/vidya-2b) | 2026-05-21 | 2026-06-30 | 26 | 0 |

`vidya-2b` has no model card beyond four lines of sampler advice and no `config.json` — it is
a bare GGUF drop (file listing:
<https://huggingface.co/api/models/neo-saket/vidya-2b/tree/main?recursive=true>). Treat only
4B and 9B as documented releases.

**Name collisions — all unrelated to the above.** "Vidya" is both a common Indian given name
and the Sanskrit word for knowledge, so most HF hits are personal usernames
(`vidyavenkappa/*`, `vidyamdeveloper/*`, `vidyasagarbhargava/*` and dozens more) rather than a
model called Vidya. Distinct projects that do use the name:

- [`neo-saket/vidya-kisan-2b` / `-4b`](https://huggingface.co/neo-saket/vidya-kisan-4b) — same
  author, but an **agriculture** advisory model, not education. Its card explicitly says
  "research preview. NOT validated for field advisory use." Not relevant here.
- [`rajasingh012/vidya-gemma4-e2b-gguf`](https://huggingface.co/rajasingh012/vidya-gemma4-e2b-gguf)
  — a different, unrelated "Vidya — NCERT Socratic Learning Bot", Gemma-4-E2B (2.3B) fine-tune,
  Q4_K_M GGUF, 30 downloads. Card is 20 lines with no training data detail, no eval, no licence
  field. Too thin to consider.
- [`Abhisingh-18/Vidya-AI`](https://huggingface.co/Abhisingh-18/Vidya-AI) — not a model at all;
  a Next.js video-generation web app that calls OpenRouter. Repo contains no weights.
- [`animesh2005/Bharat-Vidya`](https://huggingface.co/animesh2005/Bharat-Vidya) — a StyleTTS2
  bilingual **text-to-speech** system. Unrelated.
- `gouthamsk/tinyllama-VidyaLeap-v0.1`, `yedurivishnuvardhan/vidyaai-gitam-llama3b`,
  `Sharathbeesu/Vidya`, `Lidya5/Vidya`, `Vidya123/vidya-1stmodel` — all auto-generated empty
  model cards, no documentation. Not releases.
- HF Spaces matching "vidya" are personal chatbot demos and Analytics Vidhya course-search
  projects (<https://huggingface.co/api/spaces?search=vidya>). None relate to this model.

There is **no** NCERT/CBSE/government-published model called Vidya. Searching HF for `ncert`
returns ~50 models, all individual hobby fine-tunes of Llama/Qwen/Gemma/Mistral
(<https://huggingface.co/api/models?search=ncert>).

## 2. Who published it?

**An individual.** HF author `neo-saket`; the card's citation block names the author as
**Saket Nayak** and gives contact `neoraspberrybi@gmail.com`
(<https://huggingface.co/neo-saket/vidya-4b/raw/main/README.md>). The Ollama publisher profile
<https://ollama.com/neosaket> carries the display name **"Readheights Technologies"**, with
only two model families published (vidya, vidya-kisan). No university, no company of record, no
government body, no connection to NCERT, CBSE, AI4Bharat, Sarvam or BharatGPT. The card states
training was done on a single **RTX 5090 (32 GB VRAM)** — a personal workstation.

The card links training code at `https://github.com/neo-saket/ncert_vidya`. **That URL returns
HTTP 404, and the GitHub user `neo-saket` also returns 404.** The training pipeline is therefore
not inspectable and the card's process claims cannot be independently checked.

## 3. Is the NCERT-training claim substantiated? Exact wording

Partially, and the publisher's own two cards contradict each other.

**`vidya-9b` card** (<https://huggingface.co/neo-saket/vidya-9b/raw/main/README.md>) claims a
three-stage pipeline including continued pre-training:

> "Fine-tuned via a 3-stage pipeline on an RTX 5090 (32 GB VRAM):
> 1. **CPT** — Continued pre-training on NCERT textbook content
> 2. **SFT** — Supervised fine-tuning on educational Q&A, exam problems, and tutoring conversations
> 3. **DPO** — Alignment for pedagogically effective responses"

**`vidya-4b` card** (<https://huggingface.co/neo-saket/vidya-4b/raw/main/README.md>) says the
opposite about CPT and is more specific about data provenance:

> "**Pipeline:** SFT → DPO (no CPT due to data constraints)"

and in its training table:

> "| SFT | NCERT synthetic Q&A (GPT-4o-mini generated), HuggingFace NCERT datasets, SATHEE exam papers |"
> "| DPO | Preference pairs on NCERT content; beta=0.1 |"

**So:** it is **fine-tuning, not pretraining, and not RAG** — LoRA (r=16, alpha=16, DoRA +
rsLoRA) SFT followed by DPO. Crucially, the 4B's SFT data is largely **synthetic Q&A generated
by GPT-4o-mini**, not NCERT textbook text itself; "HuggingFace NCERT datasets" is unnamed and
unlinked, and "SATHEE exam papers" is unlinked. The `datasets:` metadata field lists
`AI4Bharat/sangraha` and `uonlp/CulturaX` — general Indic web corpora, neither of which is
NCERT content and neither of which appears anywhere in the card's own training table. **No
training dataset is published**, so none of this is verifiable. The CPT-on-NCERT-textbooks
claim exists only on the 9B card and is contradicted by the 4B card; treat it as unverified.

## 4. Parameters, architecture, base model

**It is not a Gemma-2-9B derivative and not a Llama derivative. It is Qwen3.5.** The "9B" in the
name is a rounding of 8.95B actual parameters, not a signal of Gemma-2-9B lineage.

Evidence used, in order of authority — `config.json` over any prose claim
(<https://huggingface.co/neo-saket/vidya-9b/raw/main/config.json>):

1. `"architectures": ["Qwen3_5ForConditionalGeneration"]`, `"model_type": "qwen3_5"`, inner
   `"model_type": "qwen3_5_text"`. Neither `Gemma2ForCausalLM` nor `LlamaForCausalLM` appears
   anywhere in the repo.
2. `"vocab_size": 248320` — the Qwen3.5 vocabulary. Gemma-2-9B is 256000 and Llama-3.1-8B is
   128256, so vocab size alone rules both out.
3. `"model_name": "models/dpo_ncert_9b/_merged_sft"` — the author's own training artifact path,
   left in the config. Independent corroboration that this checkpoint is a DPO stage applied over
   a merged SFT checkpoint of an "ncert_9b" run.
4. `"unsloth_version": "2026.5.2"` — confirms the card's claim of Unsloth LoRA tuning.
5. README front matter declares `base_model: Qwen/Qwen3.5-9B`, and the HF tags carry
   `base_model:Qwen/Qwen3.5-9B` / `base_model:quantized:Qwen/Qwen3.5-9B`. That base repo exists
   and is Apache-2.0 (<https://huggingface.co/Qwen/Qwen3.5-9B>).
6. The Ollama registry independently reports `arch qwen35 · parameters 8.95B · quantization
   Q4_K_M` (<https://ollama.com/neosaket/vidya:9b>).

Architecture detail from `config.json` worth knowing: it is the Qwen3.5 **hybrid-attention**
design — 32 layers with `full_attention_interval: 4`, i.e. three `linear_attention` layers for
every one `full_attention` layer, hidden size 4096, intermediate 12288, 16 attention heads /
4 KV heads, head_dim 256, partial rotary factor 0.25, rope_theta 1e7. It also carries a
`vision_config` (27-layer SigLIP-style tower) because the Qwen3.5-9B base is multimodal —
irrelevant to the GGUF, which is text-only, but it explains the `ForConditionalGeneration`
class name. And `"mtp_num_hidden_layers": 1` — a multi-token-prediction layer, which matters for
GGUF loading (see §7).

**Consequence for the benchmark: it overlaps `qwen3:8b`, not `gemma3:12b`.** So it does not
inherit llama3.1:8b's failure modes, and it does *not* collide with the gemma3:12b slot it would
replace — but it collides with the Qwen candidate already benchmarked. Swapping gemma3:12b for
Vidya would leave the comparison two-thirds Qwen and drop the only Gemma-family data point
entirely, narrowing the architectural spread rather than widening it.

Summary table, verified from `config.json` and the Ollama registry, not just the card:

| | vidya-4b | vidya-9b |
|---|---|---|
| Base model | `Qwen/Qwen3.5-4B` | `Qwen/Qwen3.5-9B` |
| Architecture | `Qwen3_5ForCausalLM`, `model_type: qwen3_5_text` | `Qwen3_5ForConditionalGeneration` |
| Layers / hidden | 32 / 2560 | 32 / 4096 |
| Parameters (Ollama-reported) | — | **8.95B** |
| BF16 safetensors size | 8.41 GB | 18.8 GB |

Sources: <https://huggingface.co/neo-saket/vidya-4b/raw/main/config.json>,
<https://huggingface.co/neo-saket/vidya-9b/raw/main/config.json>,
<https://ollama.com/neosaket/vidya:9b>.

On the 16 adversarial false-premise items in particular, shared-lineage models tend to share
refusal and sycophancy behaviour, so a Vidya-vs-qwen3 delta measures the fine-tune, not the base
model. That is a legitimate experiment, but it is a different experiment from the one this
harness is set up to run.

## 5. Licence and usage restrictions

**Apache-2.0**, declared in both the 4B and 9B card front matter
(<https://huggingface.co/neo-saket/vidya-4b/raw/main/README.md>) and in the HF model tags. The
base models are themselves Apache-2.0, so the declaration is coherent. No usage restrictions
beyond Apache-2.0 terms. The cards add non-binding limitations: "Not suitable for medical
advice, legal guidance, or safety-critical applications" and "Primary training language is
English; Hindi support is limited" (4B card).

One consistency flag: the same author's `vidya-kisan-4b` card declares `license: other /
qwen-research` and links it to the Qwen3.5-4B LICENSE file, which is Apache-2.0
(<https://huggingface.co/neo-saket/vidya-kisan-4b/raw/main/README.md>). The author's licence
metadata is not applied carefully across repos. It does not change the Apache-2.0 declaration on
the tutoring models, but it is a signal about card rigour.

## 6. Context window

Two different numbers, and the difference is load-bearing.

- **Architectural**: `max_position_embeddings: 262144` in both `config.json` files, and
  `model_max_length: 262144` in `tokenizer_config.json`, inherited from Qwen3.5. Ollama's tag
  listing consequently shows **256K** context for all three tags
  (<https://ollama.com/neosaket/vidya>).
- **Trained / claimed**: the 9B card's Model Details table says "**Context length | 4096
  tokens**", and the 4B card's training table says "**Max seq length | 4096**".

So the file will *accept* a long context, but the fine-tune was only ever trained at 4096. For
the Niera harness — ~3.3k-token system prompt plus a question plus up to 8192 output tokens —
**the total (~11.5k) is roughly 3x the 4096 window the fine-tune was trained at**. The model
will not error, but generation past ~4k tokens is outside the tuned regime and its tutoring
behaviour there is uncharacterised.

**Two Modelfile parameters must be overridden explicitly, and one of them is a silent-truncation
risk.** The shipped Modelfile (<https://huggingface.co/neo-saket/vidya-9b/raw/main/Modelfile>)
sets **`PARAMETER num_predict 1024`** — so output is capped at 1024 tokens, not 8192, unless the
harness sends `num_predict` in `options` on every request. And the Modelfile sets **no `num_ctx`
at all**, so the context window falls back to the Ollama server default. Given the earlier
observation on this machine that the effective default can be as low as 2048, a ~3.3k-token
system prompt would be **silently truncated from the left before the model ever sees it** —
which in a ChatML layout means losing the start of the Niera system prompt. `num_ctx` must be
set explicitly per request (≥12288 to cover prompt + 8192 output), and at that setting the
KV cache grows accordingly — still well within 16 GB (see §8).

## 7. Ollama availability

**Yes, directly pullable from the Ollama registry** — verified on the registry page itself,
<https://ollama.com/neosaket/vidya>:

| Tag | Size | Quantization | Listed context | Last updated |
|---|---|---|---|---|
| `neosaket/vidya:2b` | 1.3 GB | Q4_K_M | 256K | ~4 months ago |
| `neosaket/vidya:4b` | 2.7 GB | Q4_K_M | 256K | ~2 months ago |
| `neosaket/vidya:9b` | 5.6 GB | Q4_K_M | 256K | ~2 months ago |

Pull command: `ollama run neosaket/vidya:9b`. The registry reports **69 total pulls** across all
three tags (<https://ollama.com/neosaket/vidya:9b>) — near-zero adoption.

Only **one quantisation, Q4_K_M**, is published anywhere; there is no Q5/Q6/Q8/F16 GGUF. GGUF
file sizes from the HF file tree:

- `neo-saket/vidya-4b/vidya-Q4_K_M.gguf` — 2,708,796,384 bytes (2.7 GB)
- `neo-saket/vidya-9b/gguf/vidya-Q4_K_M.gguf` — 5,629,101,056 bytes (5.6 GB)
- `neo-saket/vidya-2b/vidya-Q4_K_M.gguf` — 1,274,388,544 bytes (1.3 GB)

Running from HF directly (`ollama run hf.co/neo-saket/vidya-4b`) is possible since the 4B GGUF
sits at the repo root, but **prefer the registry tag**: each repo ships a `Modelfile` carrying
the ChatML template, the tutoring system prompt and the samplers, and a raw GGUF pull picks up
none of that. The 9B's GGUF is under a `gguf/` subdirectory, which is a further reason to use
the registry tag rather than the HF path.

The published Modelfile (identical across 2B/4B/9B) is:

```
TEMPLATE """{{- range .Messages }}
<|im_start|>{{ .Role }}
{{ .Content }}<|im_end|>
{{ end }}
<|im_start|>assistant
"""
SYSTEM You are Vidya, an expert tutor for Indian students preparing for NCERT Classes 6-12, IIT-JEE, and NEET. Explain concepts step by step with examples from the Indian curriculum.
PARAMETER stop "<|im_end|>"
PARAMETER num_predict 1024
PARAMETER repeat_penalty 1.1
PARAMETER repeat_last_n 64
PARAMETER temperature 0.3
```

**The baked-in SYSTEM prompt and samplers are a benchmark hazard.** Ollama's `/api/chat` will
replace the Modelfile SYSTEM when the request supplies a system message, so the Niera prompt
does land — but the baked-in `temperature 0.3`, `repeat_penalty 1.1`, `repeat_last_n 64` and
`num_predict 1024` otherwise apply, and differ from whatever qwen3:8b and llama3.1:8b were run
at. Identical generation settings across candidates is the stated premise of this benchmark
(see `NIERA_BENCHMARK_RESEARCH_AND_PIPELINE_README.md` §2), so each would have to be overridden
per request. The author's own `vidya-kisan-4b` card documents exactly this trap: "Ollama's
OpenAI-compatible endpoint **ignores the Modelfile temperature when a request omits it**".

Also note the Modelfile's TEMPLATE is a **hand-written simplification** of the repo's real
ChatML template — it iterates `.Messages` emitting `<|im_start|>{{ .Role }}` with no special
handling at all, whereas the repo's `chat_template.jinja` has tool-call, vision and
system-position logic. For plain system+user chat the two agree, so this is not a blocker, but
it means the Ollama build is not running the model's own template.

**GGUF-loading risk, unverified.** `config.json` contains `"mtp_num_hidden_layers": 1` — a
multi-token-prediction layer. The same author's `vidya-kisan-4b` card documents that exactly
this layer broke their GGUFs on Ollama 0.32+ with `key qwen35.attention.recurrent_layers has
wrong array length; expected 32, got 33`, and that they had to reconvert with `--no-mtp` in
September 2026. **The vidya tutoring GGUFs were uploaded 2026-06-30 and have not been rebuilt
since**, so they predate that fix and may hit the same error on a current Ollama. I did not pull
to test. If `ollama run neosaket/vidya:9b` fails with that message, that is why — and the only
remedy would be reconverting from the BF16 safetensors yourself.

## 8. Will it fit in 16 GB unified memory?

**Yes, easily — memory is not the constraint here.**

`neosaket/vidya:9b` is 5.6 GB of Q4_K_M weights. Sizing the KV cache for `num_ctx 12288`
(covering a ~3.3k prompt plus 8192 output): from `config.json`, 32 layers, 4 KV heads,
head_dim 256 — but only 8 of the 32 are `full_attention` layers (`full_attention_interval: 4`),
the other 24 being `linear_attention`, which carries a fixed-size recurrent state rather than a
length-proportional cache. So the length-scaling cache is roughly 8 layers x 2 x 4 heads x 256
dims x 12288 tokens x 2 bytes ≈ **0.4 GB at F16** — the hybrid architecture makes this
unusually cheap. Peak resident size lands around **6.5–7 GB**, leaving ~9 GB free on a 16 GB M4.

**Verdict: comfortable, with more headroom than gemma3:12b**, which is 8.1 GB of weights before
any cache (<https://ollama.com/library/gemma3:12b>). `vidya:4b` at 2.7 GB is trivial.

Memory is genuinely not the constraint. The real constraints are elsewhere: the 4096-token
training window (§6), the `num_ctx` default that must be raised to avoid truncating the system
prompt (§6/§7), and the unverified MTP GGUF-loading risk (§7).

## 9. Published evaluation results

Thin, self-reported, and not a curriculum-accuracy benchmark.

The **only** numbers published are an LLM-as-judge "tutoring quality" score. From the 4B card:

> "**Tutoring score: 4.1 / 5.0** (Gemini 2.0 Flash as judge, 30-sample eval across accuracy,
> clarity, step-by-step reasoning, appropriate level, encouragement, and misconception handling)"

with the per-dimension breakdown: Overall 4.1, Accuracy 3.8, Clarity 4.4, Step-by-step 4.5,
Appropriate level 4.5, Encouragement 4.5, Misconception handling 4.8. The 9B card reports
**4.60 / 5.0** overall, and registers it as a `model-index` metric with `"verified": false`
(<https://huggingface.co/api/models/neo-saket/vidya-9b>). The 9B card gives no per-dimension
breakdown and does not state its sample size.

Assessment:

- **n = 30.** Far too small to separate 4.1 from 4.6 with any confidence.
- **Self-reported**, by the author, with a judge model and no published rubric, prompts or
  outputs. The eval set is not released, and the linked GitHub repo that would contain it is 404.
- **No accuracy benchmark on NCERT/JEE/NEET content.** There is no MMLU, no JEE/NEET MCQ
  accuracy, no Indian-curriculum benchmark of any kind. "Accuracy 3.8/5" is a judge's opinion of
  answer quality, not a measured correct-answer rate.
- **No adversarial / false-premise evaluation**, which is 16 of the harness's 56 items. The
  closest proxy is "Misconception handling 4.8" but that measures correcting a *student's* stated
  misconception, not resisting a false premise embedded in the question.
- The card concedes the weakness itself: "The accuracy score (3.8) reflects the 4B model's
  smaller factual recall capacity" and, under Limitations, "may occasionally hallucinate specific
  NCERT facts."

Notably, the same author's `vidya-kisan-4b` card is far more rigorous — held-out sets,
leakage disclosure ("53 of this set's 60 items are verbatim training data"), tiered safety
adjudication, temperature-controlled repeat runs. None of that discipline was applied to the
tutoring models, and the tutoring cards have not been updated since 2026-06-30. So the eval
quality gap is not a matter of the author being unable to do it; the tutoring numbers simply
predate that practice.

## 10. Chat/instruct or base completion?

**Chat/instruct, and the system role is fully supported — not a blocker.** This was checked
directly against `tokenizer_config.json` / `chat_template.jinja` rather than inferred, because
a dropped system prompt would invalidate the whole run.

The repo ships a 7,756-character ChatML Jinja template, present both as `chat_template` inside
`tokenizer_config.json` and as a standalone `chat_template.jinja`
(<https://huggingface.co/neo-saket/vidya-9b/raw/main/chat_template.jinja>). Its system handling:

```jinja
{%- if messages[0].role == 'system' %}
    {{- '<|im_start|>system\n' + content + '<|im_end|>\n' }}
```

with a guard later in the loop:

```jinja
{%- if message.role == "system" %}
    {{- raise_exception('System message must be at the beginning.') }}
```

So a system turn is emitted verbatim into its own `<|im_start|>system … <|im_end|>` block. **The
~3.3k-token Niera system prompt will be delivered intact, not dropped and not merged into the
user turn** — provided it is the *first* message (the harness's system+user ordering satisfies
this) and `num_ctx` is large enough that it is not truncated (§6 — that is the real risk, not
the template). Two other template constraints, neither of which the harness hits: the system
message must not contain images or videos (`raise_exception` on both), and there must be only
one system message.

`<|im_end|>` (token 248044) is the EOS, declared in `tokenizer_config.json` and as
`eos_token_id` in `config.json` / `generation_config.json`, and repeated as a `stop` parameter
in the Modelfile — so generation terminates cleanly. The Ollama registry page shows an
`/api/chat` cURL example as canonical usage.

One runtime wrinkle to plan for: Qwen3.5 emits a `<think>…</think>` block. The card says the
GGUF "ships a **plain ChatML** chat template (Qwen3 *thinking mode disabled*)" and advises
pre-filling `<think>\n\n</think>\n\n` on the assistant turn to suppress reasoning output. If the
harness stores raw responses for human grading, reasoning blocks may or may not appear depending
on template handling — the same issue already faced with `qwen3:8b`.

## 11. Release date and maintenance status

Full commit history of `neo-saket/vidya-9b`
(<https://huggingface.co/api/models/neo-saket/vidya-9b/commits/main>) — eight commits, all
`huggingface_hub` uploads:

| Date | Commit |
|---|---|
| 2026-06-30 | Upload README.md |
| 2026-06-30 | Upload gguf/vidya-Q4_K_M.gguf |
| 2026-06-29 | Upload Modelfile |
| 2026-05-19 | Rename model-Q4_K_M.gguf to vidya-Q4_K_M.gguf |
| 2026-05-18 | Upload gguf/model-Q4_K_M.gguf |
| 2026-05-18 | Upload folder |
| 2026-05-18 | Upload README.md |
| 2026-05-18 | initial commit |

- Created 2026-05-18 (9B), 2026-05-19 (4B), 2026-05-21 (2B). **Last commit 2026-06-30** on all
  three; Ollama tags last updated ~2 months ago, matching.
- Nearly three months with no update as of 2026-09-22.
- **Open discussions: 0** — the HF discussions API returns `count: 0`
  (<https://huggingface.co/api/models/neo-saket/vidya-9b/discussions>). No community issues, but
  equally no community scrutiny: nobody has ever filed anything against this model.
- The author **is** active — `neosaket/vidya-kisan` was updated one week ago
  (<https://ollama.com/neosaket>) and its GGUF was rebuilt 2026-09-12 to fix an Ollama 0.32+
  loading failure. But that attention went to the agriculture line, not the tutoring line.
- The training-code GitHub repo is 404 and the GitHub account does not exist.
- Adoption: 69 Ollama pulls, 938 HF downloads across three repos, 2 likes total.

**Verdict: published, not abandoned outright, but not actively maintained.** Worth noting: the
`vidya-kisan` GGUFs had to be rebuilt because a converter bug made them fail to load on Ollama
0.32+. The tutoring GGUFs were built by the same pipeline in the same period and **have not been
rebuilt**. Whether they load on a current Ollama is unverified — the only way to know is to pull
one, which is out of scope for this research.

---

## Recommendation: Vidya vs gemma3:12b as the third candidate

**Keep gemma3:12b.** Reasoning, in priority order:

1. **The swap would narrow the architectural spread, not widen it.** The existing pair is
   qwen3:8b and llama3.1:8b — two families. gemma3:12b (Google, Gemma-3, 12.2B,
   <https://ollama.com/library/gemma3:12b>) is a genuine third family. vidya:9b is Qwen3.5-9B
   with a LoRA on top, so substituting it would simultaneously add a second Qwen and delete the
   only Gemma data point — leaving two of three candidates sharing a lineage, tokenizer,
   template and pretraining corpus. Since the point is to choose a *base* model for Niera, that
   is backwards.
2. **The provenance will not survive scrutiny.** Choosing a base model for a product means
   defending the choice. Vidya's defence is: one individual, no institution, one RTX 5090, a
   30-sample self-judged eval, a 404 training repo, two model cards that disagree about whether
   CPT happened, and unnamed training datasets. gemma3:12b's defence is a Google model card, a
   tech report and public benchmark numbers.
3. **The fine-tune is on synthetic data of unknown quality.** Per the 4B card, the SFT set is
   "NCERT synthetic Q&A (GPT-4o-mini generated)". A model tuned on GPT-4o-mini output largely
   inherits GPT-4o-mini's NCERT errors — and the card admits it "may occasionally hallucinate
   specific NCERT facts". For a benchmark whose 16 adversarial items are specifically about not
   confidently asserting false things, training on unreviewed synthetic data is the wrong prior.
4. **Category error.** Vidya is a *finished tutoring product*, already carrying its own tutor
   system prompt, temperature and persona. Niera's benchmark is evaluating *base* models onto
   which Niera's own ~3.3k-token system prompt and pedagogy will be layered. Benchmarking Vidya
   measures someone else's fine-tune, not the substrate Niera would build on.
5. **Context.** Vidya was tuned at 4096 tokens; the harness's prompt-plus-output budget exceeds
   that. gemma3 has a 128K window as shipped.

Vidya wins on exactly one axis: it is 5.6 GB against gemma3:12b's 8.1 GB, so it runs faster and
cooler on a 16 GB M4. That is not a reason to choose a base model.

**Suggested use of Vidya instead:** run it as an unofficial **fourth** run, outside the
three-way comparison, specifically against the 16 adversarial items. It is cheap (5.6 GB, 69
pulls of prior art means nobody has done this), and "does an NCERT-tuned 9B resist false
premises better or worse than a general 9B?" is a genuinely useful question for Niera's
pedagogy design. Just do not let it occupy the third base-model slot, and if you run it,
override `temperature`, `repeat_penalty` and `num_predict` explicitly so it matches the other
runs' generation settings.

### Alternatives checked (Indian-curriculum / Indian-language, ≤14B, Ollama-runnable)

None of these is a better third candidate than gemma3:12b either. Summarised so the option is
closed rather than left open:

| Model | Publisher | Size / base | Licence | Ollama | Verdict |
|---|---|---|---|---|---|
| [`sarvamai/sarvam-m`](https://huggingface.co/sarvamai/sarvam-m) | Sarvam AI | 24B, Mistral-Small-3.1-24B-Base | apache-2.0 | no official tag; community re-uploads only (`mashriram/sarvam-m`) | **Over budget.** 24B exceeds the ≤14B constraint; Q4 would be ~14 GB of weights on a 16 GB machine. The only official GGUF is `sarvam-m-bf16.gguf` at 47 GB. |
| [`sarvamai/sarvam-30b`](https://huggingface.co/sarvamai/sarvam-30b) | Sarvam AI | 30B MoE (`SarvamMoEForCausalLM`, 128 experts, 6 active), 128K ctx | apache-2.0 | community only (`predictivemanish/sarvam-30b`) | **Over budget.** Official Q4_K_M GGUF is 6 shards totalling ~19.6 GB. Most-downloaded Indian LLM found (304k HF downloads) but does not fit. |
| [`sarvamai/sarvam-1`](https://huggingface.co/sarvamai/sarvam-1) | Sarvam AI | 2B, Llama arch | not declared in card metadata | no official tag | Small enough, but it is a **base/pretrained** model for Indic languages, not an instruct tutor, and last touched 2024-11. Wrong shape for `/api/chat`. |
| [`krutrim-ai-labs/Krutrim-2-instruct`](https://huggingface.co/krutrim-ai-labs/Krutrim-2-instruct) | Ola Krutrim | 12B (Mistral arch, 40 layers / 5120 hidden) | **`other` — Krutrim Community License v1.0**, not OSI | no official tag; third-party GGUFs exist (`bartowski/…-GGUF`) | Closest in spirit — right size, Indian publisher, instruct-tuned. But last updated 2025-03, 470 downloads, no official GGUF or Ollama tag, custom non-standard licence, and **no NCERT/JEE/NEET-specific training or eval**. Would be a general Indian-language model, not a curriculum model. |
| [`ai4bharat/Airavata`](https://huggingface.co/ai4bharat/Airavata) | AI4Bharat (IIT Madras) | 7B, Llama-2 derived | llama2 | no | **Stale and wrong lineage.** Last updated 2024-03. Llama-2-based, so it is architecturally *behind* llama3.1:8b rather than independent of it. AI4Bharat's current HF output is translation/ASR/TTS (IndicTrans3, Cadence, IndicBERT-v3, Bhili models) — they are not shipping a current general LLM. |
| `sarvamai/OpenHathi-7B-Hi-v0.1-Base` | Sarvam AI | 7B base | — | no | Base completion model, Hindi-focused, superseded by the Sarvam line. Not usable with `/api/chat`. |
| [`CoRover/BharatGPT-3B-Indic`](https://huggingface.co/CoRover/BharatGPT-3B-Indic) | CoRover | 3B, Llama arch | `other` | no official tag; community GGUFs (`mradermacher/…`) | Too small to compare against 8–12B candidates, and licence is unspecified "other". |
| [`nickmalhotra/ProjectIndus`](https://huggingface.co/nickmalhotra/ProjectIndus) | Tech Mahindra | **GPT-2 architecture**, ~1.2B | osl-3.0 | no | Not competitive. GPT-2-class model, last updated 2024-07. |
| [`MBZUAI/Llama-3-Nanda-10B-Chat`](https://huggingface.co/MBZUAI/Llama-3-Nanda-10B-Chat) | MBZUAI (UAE) | 10B, Llama-3 derived | llama3 | no | **Wrong lineage** — Llama-3 derivative, so it overlaps llama3.1:8b. 14 downloads, no GGUF, Hindi-general rather than curriculum. |

**Conclusion on alternatives:** there is currently **no** Indian-curriculum or Indian-language
model that is simultaneously (a) ≤14B, (b) instruct-tuned, (c) officially available on Ollama,
(d) from a credible publisher with real evaluations, and (e) architecturally independent of both
Qwen and Llama-3. The closest miss is Krutrim-2-instruct (12B, right size, Indian publisher) and
it fails on official Ollama availability, licence, maintenance and the absence of any curriculum
eval. gemma3:12b remains the right third candidate.

---

## Sources

All primary. Accessed 2026-09-22.

**Vidya**
- <https://huggingface.co/neo-saket/vidya-9b> — read in full, plus these repo files directly:
  `README.md`, `config.json`, `tokenizer_config.json`, `chat_template.jinja`, `Modelfile`,
  the recursive file tree, the commit history (`/api/models/neo-saket/vidya-9b/commits/main`)
  and the discussions endpoint (`count: 0`)
- <https://huggingface.co/neo-saket/vidya-4b> (card: <https://huggingface.co/neo-saket/vidya-4b/raw/main/README.md>, config, Modelfile, file tree)
- <https://huggingface.co/neo-saket/vidya-2b>
- <https://huggingface.co/neo-saket/vidya-kisan-4b> (same author; used for publisher-practice comparison)
- <https://ollama.com/neosaket> — publisher profile
- <https://ollama.com/neosaket/vidya> — tag listing, sizes, context
- <https://ollama.com/neosaket/vidya:9b> — arch/params/quantisation details, pull count
- `https://github.com/neo-saket/ncert_vidya` — **HTTP 404**; `https://github.com/neo-saket` — **HTTP 404**
- HF API: `https://huggingface.co/api/models/neo-saket/vidya-{2b,4b,9b}`, `.../tree/main?recursive=true`

**Base models**
- <https://huggingface.co/Qwen/Qwen3.5-4B>, <https://huggingface.co/Qwen/Qwen3.5-9B>

**Comparison and alternatives**
- <https://ollama.com/library/gemma3:12b>
- <https://huggingface.co/sarvamai/sarvam-m>, `sarvam-m-gguf`, `sarvam-30b`, `sarvam-30b-gguf`, `sarvam-1`, `OpenHathi-7B-Hi-v0.1-Base`
- <https://huggingface.co/krutrim-ai-labs/Krutrim-2-instruct>
- <https://huggingface.co/ai4bharat/Airavata> and the `ai4bharat` HF author listing
- <https://huggingface.co/CoRover/BharatGPT-3B-Indic>
- <https://huggingface.co/nickmalhotra/ProjectIndus>
- <https://huggingface.co/MBZUAI/Llama-3-Nanda-10B-Chat>
- Ollama registry search (`https://ollama.com/search?q=…`) for sarvam, airavata, openhathi, krutrim, indus, bharatgpt, nanda, ai4bharat
- HF name-collision checks: `https://huggingface.co/api/models?search=vidya`, `?search=ncert`, `https://huggingface.co/api/datasets?search=vidya`, `https://huggingface.co/api/spaces?search=vidya`

**Explicitly unverified**
- Whether continued pre-training on NCERT textbooks happened (the two cards contradict each other).
- The composition, size and quality of every training dataset — none is published.
- The 4.1/5.0 and 4.60/5.0 tutoring scores — self-reported, `verified: false`, n=30 for the 4B and unstated for the 9B, eval set unpublished, judge prompts unpublished.
- Whether the tutoring GGUFs load on current Ollama versions. `config.json` shows the MTP layer (`mtp_num_hidden_layers: 1`) that broke the sibling `vidya-kisan` GGUFs on Ollama 0.32+; those were rebuilt with `--no-mtp` in Sept 2026, the tutoring GGUFs (uploaded 2026-06-30) were not. Not tested here — no pulls performed.
- The effective default `num_ctx` Ollama will apply to these tags — the Modelfile sets none, so it is server-dependent. Must be set explicitly by the harness regardless.
