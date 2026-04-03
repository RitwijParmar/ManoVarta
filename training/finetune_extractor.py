#!/usr/bin/env python3
from __future__ import annotations

import argparse
import inspect
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def parse_args():
    parser = argparse.ArgumentParser(description="LoRA fine-tune a chat model for structured evidence extraction.")
    parser.add_argument("--model-name", default="Qwen/Qwen2.5-7B-Instruct")
    parser.add_argument(
        "--init-adapter",
        default=None,
        help="Optional path to an existing LoRA adapter checkpoint to continue training from.",
    )
    parser.add_argument("--train-file", required=True)
    parser.add_argument("--eval-file", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--grad-accum", type=int, default=8)
    parser.add_argument("--max-length", type=int, default=2048)
    parser.add_argument("--lora-r", type=int, default=16)
    parser.add_argument("--lora-alpha", type=int, default=32)
    parser.add_argument("--target-modules", default=None)
    parser.add_argument("--use-4bit", action="store_true")
    parser.add_argument("--device", choices=["auto", "cuda", "mps", "cpu"], default="auto")
    parser.add_argument("--precision", choices=["auto", "bf16", "fp16", "fp32"], default="auto")
    parser.add_argument("--model-dtype", choices=["auto", "bf16", "fp16", "fp32"], default="auto")
    parser.add_argument("--gradient-checkpointing", action="store_true")
    parser.add_argument("--save-strategy", choices=["epoch", "steps"], default="epoch")
    parser.add_argument("--save-steps", type=int, default=50)
    parser.add_argument("--save-total-limit", type=int, default=4)
    parser.add_argument("--eval-strategy", choices=["epoch", "steps", "no"], default="epoch")
    parser.add_argument("--eval-steps", type=int, default=50)
    parser.add_argument("--resume-from-checkpoint", default=None)
    parser.add_argument(
        "--save-only-model",
        action="store_true",
        help="Save smaller checkpoints without trainer state. Not recommended when resuming interrupted runs.",
    )
    return parser.parse_args()


def resolve_target_modules(model_name: str, target_modules_arg: str | None) -> list[str] | None:
    if target_modules_arg:
        return [part.strip() for part in target_modules_arg.split(",") if part.strip()]

    lowered = model_name.lower()
    if "aya-expanse" in lowered or "command-r" in lowered:
        return [
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ]
    return None


def resolve_adapter_base_model(init_adapter: str | None) -> str | None:
    if not init_adapter:
        return None
    adapter_path = Path(init_adapter)
    config_path = adapter_path / "adapter_config.json"
    if not config_path.exists():
        raise FileNotFoundError(f"Missing adapter_config.json under {adapter_path}")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    base_model = config.get("base_model_name_or_path")
    if not base_model:
        raise ValueError(f"adapter_config.json under {adapter_path} is missing base_model_name_or_path")
    return str(base_model)


def resolve_tokenizer_source(model_name: str, init_adapter: str | None) -> str:
    if not init_adapter:
        return model_name
    adapter_path = Path(init_adapter)
    if (adapter_path / "tokenizer_config.json").exists():
        return str(adapter_path)
    base_model = resolve_adapter_base_model(init_adapter)
    return base_model or model_name


def resolve_resume_checkpoint(output_dir: str, resume_arg: str | None) -> str | None:
    if not resume_arg:
        return None
    if resume_arg != "last":
        return resume_arg

    root = Path(output_dir)
    checkpoints = []
    for path in root.glob("checkpoint-*"):
        if not (path / "trainer_state.json").exists():
            continue
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
        import torch
        from datasets import load_dataset
        from peft import LoraConfig, PeftModel
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, TrainingArguments
        from trl import SFTConfig, SFTTrainer
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(f"Install training extras first. Missing dependency: {exc.name}") from exc
    from training.runtime_utils import detect_device, pick_model_dtype, pick_precision

    args = parse_args()
    dataset = load_dataset(
        "json",
        data_files={"train": args.train_file, "eval": args.eval_file},
    )
    for split_name in dataset.keys():
        drop_cols = [col for col in dataset[split_name].column_names if col != "text"]
        if drop_cols:
            dataset[split_name] = dataset[split_name].remove_columns(drop_cols)

    base_model_name = resolve_adapter_base_model(args.init_adapter) or args.model_name
    tokenizer_source = resolve_tokenizer_source(args.model_name, args.init_adapter)

    tokenizer = AutoTokenizer.from_pretrained(tokenizer_source, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    device = detect_device(torch, args.device)
    use_bf16, use_fp16 = pick_precision(torch, args.precision, device=device)
    quantization_config = None
    if args.use_4bit and device == "cuda":
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16 if use_bf16 else torch.float16,
        )

    model_kwargs = {
        "trust_remote_code": True,
        "quantization_config": quantization_config,
    }
    if quantization_config is not None:
        model_kwargs["device_map"] = "auto"
    else:
        model_kwargs["torch_dtype"] = pick_model_dtype(torch, device, requested=args.model_dtype)
        model_kwargs["low_cpu_mem_usage"] = True

    model = AutoModelForCausalLM.from_pretrained(base_model_name, **model_kwargs)
    if quantization_config is None and device != "cpu":
        model.to(device)
    if args.init_adapter:
        model = PeftModel.from_pretrained(model, args.init_adapter, is_trainable=True)
    if args.gradient_checkpointing:
        model.gradient_checkpointing_enable()

    peft_config = None
    if not args.init_adapter:
        target_modules = resolve_target_modules(args.model_name, args.target_modules)
        peft_config = LoraConfig(
            r=args.lora_r,
            lora_alpha=args.lora_alpha,
            lora_dropout=0.05,
            bias="none",
            task_type="CAUSAL_LM",
            target_modules=target_modules,
        )

    training_kwargs = {
        "output_dir": args.output_dir,
        "learning_rate": args.learning_rate,
        "num_train_epochs": args.epochs,
        "per_device_train_batch_size": args.batch_size,
        "per_device_eval_batch_size": args.batch_size,
        "gradient_accumulation_steps": args.grad_accum,
        "logging_steps": 5,
        "save_strategy": args.save_strategy,
        "save_total_limit": args.save_total_limit,
        "bf16": use_bf16,
        "fp16": use_fp16,
        "report_to": "none",
        "gradient_checkpointing": args.gradient_checkpointing,
        "dataloader_pin_memory": device == "cuda",
        "optim": "adamw_torch",
    }
    if device == "cpu":
        training_kwargs["no_cuda"] = True
    elif device == "mps" and "use_mps_device" in inspect.signature(TrainingArguments.__init__).parameters:
        training_kwargs["use_mps_device"] = True
    if args.save_strategy == "steps":
        training_kwargs["save_steps"] = args.save_steps
    if "save_only_model" in inspect.signature(TrainingArguments.__init__).parameters and args.save_only_model:
        training_kwargs["save_only_model"] = True
    strategy_key = "evaluation_strategy"
    if strategy_key not in inspect.signature(TrainingArguments.__init__).parameters:
        strategy_key = "eval_strategy"
    training_kwargs[strategy_key] = args.eval_strategy
    if args.eval_strategy == "steps":
        training_kwargs["eval_steps"] = args.eval_steps
    trainer_signature = inspect.signature(SFTTrainer.__init__).parameters
    config_cls = TrainingArguments
    config_kwargs = dict(training_kwargs)
    if "processing_class" in trainer_signature and "dataset_text_field" not in trainer_signature:
        config_cls = SFTConfig
        config_kwargs["dataset_text_field"] = "text"
        if "max_length" in inspect.signature(SFTConfig.__init__).parameters:
            config_kwargs["max_length"] = args.max_length
    training_args = config_cls(**config_kwargs)

    trainer_kwargs = {
        "model": model,
        "train_dataset": dataset["train"],
        "eval_dataset": dataset["eval"],
        "args": training_args,
    }
    if peft_config is not None:
        trainer_kwargs["peft_config"] = peft_config
    if "processing_class" in trainer_signature:
        trainer_kwargs["processing_class"] = tokenizer
    elif "tokenizer" in trainer_signature:
        trainer_kwargs["tokenizer"] = tokenizer
    if "dataset_text_field" in trainer_signature:
        trainer_kwargs["dataset_text_field"] = "text"
    if "max_seq_length" in trainer_signature:
        trainer_kwargs["max_seq_length"] = args.max_length

    trainer = SFTTrainer(**trainer_kwargs)

    resume_checkpoint = resolve_resume_checkpoint(args.output_dir, args.resume_from_checkpoint)
    trainer.train(resume_from_checkpoint=resume_checkpoint)
    trainer.save_model(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)
    print(f"saved extractor checkpoint to {Path(args.output_dir).resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
