#!/usr/bin/env python3
import argparse
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


LABEL_TO_ID = {"none": 0, "review": 1, "urgent": 2}
ID_TO_LABEL = {value: key for key, value in LABEL_TO_ID.items()}


def parse_args():
    parser = argparse.ArgumentParser(description="Fine-tune a multilingual encoder for safety classification.")
    parser.add_argument("--model-name", default="google/muril-base-cased")
    parser.add_argument("--train-file", required=True)
    parser.add_argument("--eval-file", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--learning-rate", type=float, default=3e-5)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--max-length", type=int, default=256)
    parser.add_argument("--precision", choices=["auto", "bf16", "fp16", "fp32"], default="auto")
    return parser.parse_args()


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
    from training.runtime_utils import pick_precision

    args = parse_args()
    use_bf16, use_fp16 = pick_precision(torch, args.precision)
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

    dataset = dataset.map(preprocess, batched=True)
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

    training_args = TrainingArguments(
        output_dir=args.output_dir,
        learning_rate=args.learning_rate,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        logging_steps=5,
        bf16=use_bf16,
        fp16=use_fp16,
        report_to="none",
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset["train"],
        eval_dataset=dataset["eval"],
        tokenizer=tokenizer,
        data_collator=collator,
        compute_metrics=compute_metrics,
    )

    trainer.train()
    trainer.save_model(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)
    print(f"saved safety checkpoint to {Path(args.output_dir).resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
