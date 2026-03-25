#!/usr/bin/env python3
import os
import sys
from pathlib import Path

from huggingface_hub import InferenceClient
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env", override=False)
load_dotenv(PROJECT_ROOT / ".env.local", override=False)


def main() -> int:
    token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACEHUB_API_TOKEN")
    model = os.getenv("MANOVARTA_CHAT_MODEL", "Qwen/Qwen2.5-7B-Instruct")
    if not token:
        print("Missing HF_TOKEN or HUGGINGFACEHUB_API_TOKEN.")
        return 1

    client = InferenceClient(model=model, token=token, timeout=30)
    output = client.chat_completion(
        messages=[
            {"role": "system", "content": "You are a concise assistant."},
            {"role": "user", "content": "Reply with: ready"},
        ],
        temperature=0.0,
        max_tokens=12,
    )
    print(output.choices[0].message.content.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
