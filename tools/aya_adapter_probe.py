#!/usr/bin/env python3
from __future__ import annotations

import argparse
import traceback

import torch
from peft import PeftModel, prepare_model_for_kbit_training
from transformers import AutoModelForCausalLM, BitsAndBytesConfig


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-model", required=True)
    parser.add_argument("--adapter", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    print(f"[probe] base_model={args.base_model}")
    print(f"[probe] adapter={args.adapter}")
    quant = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
    )
    print("[probe] loading 4-bit base model...", flush=True)
    model = AutoModelForCausalLM.from_pretrained(
        args.base_model,
        trust_remote_code=True,
        quantization_config=quant,
        device_map="auto",
    )
    print("[probe] base loaded", flush=True)
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)
    print("[probe] k-bit prep done", flush=True)
    try:
        print("[probe] loading adapter...", flush=True)
        model = PeftModel.from_pretrained(model, args.adapter, is_trainable=True)
        print("[probe] adapter loaded OK", flush=True)
    except Exception as exc:  # pragma: no cover
        print(f"[probe] adapter load exception: {exc!r}", flush=True)
        traceback.print_exc()
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
