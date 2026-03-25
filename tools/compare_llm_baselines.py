#!/usr/bin/env python3
import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

CANDIDATES = [
    "CohereLabs/aya-expanse-32b",
    "moonshotai/Kimi-K2-Instruct",
    "Qwen/Qwen2.5-7B-Instruct",
]


def run_eval(model: str):
    env = os.environ.copy()
    env["MANOVARTA_EXTRACTION_MODEL"] = model
    python_bin = PROJECT_ROOT / ".venv" / "bin" / "python"
    if not python_bin.exists():
        python_bin = Path(sys.executable)
    result = subprocess.run(
        [str(python_bin), str(PROJECT_ROOT / "tools" / "evaluate_seed_runtime.py"), "--mode", "llm"],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return {"model": model, "error": result.stderr.strip() or result.stdout.strip()}
    return json.loads(result.stdout)


def main() -> int:
    reports = [run_eval(model) for model in CANDIDATES]
    print(json.dumps(reports, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
