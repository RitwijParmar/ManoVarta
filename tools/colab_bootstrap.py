#!/usr/bin/env python3
import importlib
import importlib.metadata
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
REQUIRED_IMPORTS = {
    "pydantic": "pydantic>=2.10,<=2.12.3",
    "huggingface_hub": "huggingface_hub>=0.34.0,<1.0",
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


def ensure_packaging():
    try:
        from packaging.requirements import Requirement
        from packaging.version import Version
    except ImportError:
        run([sys.executable, "-m", "pip", "install", "-q", "packaging>=24.0"])
        from packaging.requirements import Requirement
        from packaging.version import Version
    return Requirement, Version


def needs_install(module_name: str, package_spec: str, requirement_cls, version_cls) -> bool:
    try:
        importlib.import_module(module_name)
    except ImportError:
        return True

    requirement = requirement_cls(package_spec)
    try:
        installed = importlib.metadata.version(requirement.name)
    except importlib.metadata.PackageNotFoundError:
        return True
    return version_cls(installed) not in requirement.specifier


def main() -> int:
    requirement_cls, version_cls = ensure_packaging()
    missing = []
    for module_name, package_spec in REQUIRED_IMPORTS.items():
        if needs_install(module_name, package_spec, requirement_cls, version_cls):
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
