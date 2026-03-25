#!/usr/bin/env python3
import importlib
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
REQUIRED_IMPORTS = {
    "pydantic": "pydantic>=2.10,<3.0",
    "huggingface_hub": "huggingface_hub>=1.3.0,<2.0",
    "dotenv": "python-dotenv>=1.0,<2.0",
    "torch": "torch>=2.2",
    "transformers": "transformers>=4.45",
    "datasets": "datasets>=3.0.0",
    "accelerate": "accelerate>=1.0.0",
    "trl": "trl>=0.11.0",
    "peft": "peft>=0.12.0",
    "bitsandbytes": "bitsandbytes>=0.45.0",
    "numpy": "numpy>=1.26.0",
    "sentencepiece": "sentencepiece>=0.2.0",
}


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def main() -> int:
    missing = []
    for module_name, package_spec in REQUIRED_IMPORTS.items():
        try:
            importlib.import_module(module_name)
        except ImportError:
            missing.append(package_spec)

    run([sys.executable, "-m", "pip", "install", "-q", "-e", str(PROJECT_ROOT), "--no-deps"])
    if missing:
        run([sys.executable, "-m", "pip", "install", "-q", *missing])
    else:
        print("Training stack already present.", flush=True)

    print("Colab bootstrap complete.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
