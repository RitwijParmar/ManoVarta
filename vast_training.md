# Vast Training

This path is for finishing the heavier GPU work on a rented Vast instance.

## Recommended model plan

- extractor fine-tune: `CohereLabs/aya-expanse-8b`
- fallback extractor: `Qwen/Qwen3-8B`
- runtime safety model: `Qwen/Qwen3Guard-Gen-8B`
- optional trainable safety classifier: `ai4bharat/IndicBERTv2-MLM-only`

Why this split:

- `Aya Expanse 8B` is a better fit for English + Hindi symptom extraction than the small local Qwen model.
- `Qwen3-8B` is the clean fallback if Aya access or VRAM becomes a problem.
- `Qwen3Guard-Gen-8B` is better suited for product safety gating than the weak local safety checkpoint.

## Connection

Vast instances are typically reached over SSH. This machine now has a dedicated public key:

```text
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIG4c0+6Przf4lGeb2rygMit8jAQTcZrGUkZjmMiAfIcu manovarta-vast
```

Attach that key in Vast or provide the SSH command shown in the instance panel.

## Remote setup

Clone the repo on the instance, then run:

```bash
chmod +x tools/vast_bootstrap.sh tools/run_vast_training.sh
./tools/vast_bootstrap.sh
```

Set your Hugging Face token on the instance:

```bash
export HF_TOKEN=...
```

## Launch training

Run in a persistent shell like `tmux` or `screen`:

```bash
./tools/run_vast_training.sh
```

This path is resumable:

- extractor checkpoints: `outputs/vast_remote/extractor/checkpoint-*`
- safety checkpoints: `outputs/vast_remote/safety/checkpoint-*`
- resume behavior: `--resume-from-checkpoint last`

## If Aya is blocked

Switch to Qwen3 before launching:

```bash
export MANOVARTA_REMOTE_EXTRACTOR_MODEL=Qwen/Qwen3-8B
./tools/run_vast_training.sh
```

## Suggested persistence

Keep logs and outputs on an attached volume or sync them off-instance after training:

```bash
tar -czf manovarta_vast_outputs.tgz outputs reports artifacts logs
```
