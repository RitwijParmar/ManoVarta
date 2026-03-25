#!/usr/bin/env python3
import os
import sys

from huggingface_hub import InferenceClient


def main() -> int:
    token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACEHUB_API_TOKEN")
    model = os.getenv("MANOVARTA_CHAT_MODEL", "mistralai/Mistral-Nemo-Instruct-2407")
    if not token:
        print("Missing HF_TOKEN or HUGGINGFACEHUB_API_TOKEN.")
        return 1

    client = InferenceClient(provider="hf-inference", api_key=token, timeout=30)
    output = client.chat_completion(
        model=model,
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
