#!/usr/bin/env python3
from __future__ import annotations

import argparse
import inspect
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


LABEL_TO_ID = {"none": 0, "review": 1, "urgent": 2}
ID_TO_LABEL = {value: key for key, value in LABEL_TO_ID.items()}


def parse_args():
    parser = argparse.ArgumentParser(description="Fine-tune a multilingual encoder for safety classification.")
    parser.add_argument("--model-name", default="ai4bharat/IndicBERTv2-MLM-only")
    parser.add_argument("--train-file", required=True)
    parser.add_argument("--eval-file", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--learning-rate", type=float, default=3e-5)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--max-length", type=int, default=256)
    parser.add_argument("--device", choices=["auto", "cuda", "mps", "cpu"], default="auto")
    parser.add_argument("--precision", choices=["auto", "bf16", "fp16", "fp32"], default="auto")
    parser.add_argument("--save-strategy", choices=["epoch", "steps"], default="epoch")
    parser.add_argument("--save-steps", type=int, default=50)
    parser.add_argument("--save-total-limit", type=int, default=4)
    parser.add_argument("--eval-strategy", choices=["epoch", "steps", "no"], default="epoch")
    parser.add_argument("--eval-steps", type=int, default=50)
    parser.add_argument("--resume-from-checkpoint", default=None)
    return parser.parse_args()


def resolve_resume_checkpoint(output_dir: str, resume_arg: str | None) -> str | None:
    if not resume_arg:
        return None
    if resume_arg != "last":
        return resume_arg

    root = Path(output_dir)
    checkpoints = []
    for path in root.glob("checkpoint-*"):
        try:
            step = int(path.name.split("-")[-1])
        except ValueError:
            continue
        checkpoints.append((step, path))
    if not checkpoints:
        return None
    checkpoints.sort(key=lambda item: item[0])
    return str(checkpoints[-1][1])


def main() -> int:
    try:
        import numpy as np
        import torch
        from datasets import load_dataset
        from transformers import (
            AutoModelForSequenceClassification,
            AutoTokenizer,
            DataCollatorWithPadding,
            Trainer,
            TrainingArguments,
        )
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(f"Install training extras first. Missing dependency: {exc.name}") from exc
    from training.runtime_utils import detect_device, pick_precision

    args = parse_args()
    device = detect_device(torch, args.device)
    use_bf16, use_fp16 = pick_precision(torch, args.precision, device=device)
    dataset = load_dataset(
        "json",
        data_files={"train": args.train_file, "eval": args.eval_file},
    )
    tokenizer = AutoTokenizer.from_pretrained(args.model_name, trust_remote_code=True)

    def preprocess(batch):
        encoded = tokenizer(
            batch["text"],
            truncation=True,
            padding=False,
            max_length=args.max_length,
        )
        encoded["labels"] = [LABEL_TO_ID[label] for label in batch["label"]]
        return encoded

    original_columns = dataset["train"].column_names
    dataset = dataset.map(preprocess, batched=True, remove_columns=original_columns)
    collator = DataCollatorWithPadding(tokenizer=tokenizer)

    model = AutoModelForSequenceClassification.from_pretrained(
        args.model_name,
        trust_remote_code=True,
        num_labels=len(LABEL_TO_ID),
        id2label=ID_TO_LABEL,
        label2id=LABEL_TO_ID,
    )

    def compute_metrics(eval_pred):
        logits, labels = eval_pred
        preds = np.argmax(logits, axis=-1)
        accuracy = float((preds == labels).mean())
        return {"accuracy": round(accuracy, 4)}

    training_kwargs = {
        "output_dir": args.output_dir,
        "learning_rate": args.learning_rate,
        "num_train_epochs": args.epochs,
        "per_device_train_batch_size": args.batch_size,
        "per_device_eval_batch_size": args.batch_size,
        "save_strategy": args.save_strategy,
        "save_total_limit": args.save_total_limit,
        "logging_steps": 5,
        "bf16": use_bf16,
        "fp16": use_fp16,
        "report_to": "none",
        "dataloader_pin_memory": device == "cuda",
        "optim": "adamw_torch",
    }
    if device == "cpu":
        training_kwargs["no_cuda"] = True
    elif device == "mps" and "use_mps_device" in inspect.signature(TrainingArguments.__init__).parameters:
        training_kwargs["use_mps_device"] = True
    if args.save_strategy == "steps":
        training_kwargs["save_steps"] = args.save_steps
    strategy_key = "evaluation_strategy"
    if strategy_key not in inspect.signature(TrainingArguments.__init__).parameters:
        strategy_key = "eval_strategy"
    training_kwargs[strategy_key] = args.eval_strategy
    if args.eval_strategy == "steps":
        training_kwargs["eval_steps"] = args.eval_steps
    training_args = TrainingArguments(**training_kwargs)

    trainer_kwargs = {
        "model": model,
        "args": training_args,
        "train_dataset": dataset["train"],
        "eval_dataset": dataset["eval"],
        "data_collator": collator,
        "compute_metrics": compute_metrics,
    }
    trainer_signature = inspect.signature(Trainer.__init__).parameters
    if "processing_class" in trainer_signature:
        trainer_kwargs["processing_class"] = tokenizer
    elif "tokenizer" in trainer_signature:
        trainer_kwargs["tokenizer"] = tokenizer

    trainer = Trainer(**trainer_kwargs)

    resume_checkpoint = resolve_resume_checkpoint(args.output_dir, args.resume_from_checkpoint)
    trainer.train(resume_from_checkpoint=resume_checkpoint)
    trainer.save_model(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)
    print(f"saved safety checkpoint to {Path(args.output_dir).resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
