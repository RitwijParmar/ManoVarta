# Colab Workbench

Use this path when you want GPU-backed experiments without bloating the local runtime.

## Suggested Colab flow

```bash
git clone https://github.com/RitwijParmar/ManoVarta.git
cd ManoVarta
pip install -e .[dev,gpu]
```

Optional environment setup:

```bash
export HF_TOKEN=...
export MANOVARTA_CHAT_MODEL=Qwen/Qwen2.5-7B-Instruct
export MANOVARTA_EXTRACTION_MODEL=CohereLabs/aya-expanse-32b
```

## Useful Colab commands

Baseline evaluation:

```bash
python tools/evaluate_seed_runtime.py --mode heuristic
python tools/evaluate_seed_runtime.py --mode llm --model CohereLabs/aya-expanse-32b
python tools/evaluate_seed_runtime.py --mode llm --model moonshotai/Kimi-K2-Instruct
```

Semantic safety encoder:

```bash
python tools/semantic_safety_eval.py --model ai4bharat/IndicBERT-v3-1B
```

Annotation packet export:

```bash
python tools/build_annotation_packets.py
```

## What this is for

- batch model comparison without local CPU bottlenecks
- trying the IndicBERT-style encoder path on Hindi and Hinglish cases
- exporting seed packets for annotation cleanup or second-pass review

Keep the local app lightweight and use Colab for the heavier evaluation loops.
