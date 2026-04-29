#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.request import Request, urlopen


FULL_COVERAGE_EN_TURNS = [
    "Sleep has been broken for the last two weeks. I wake around 3 or 4, drag through the day, skip lunch, and reread the same paragraph at work.",
    "Mostly waking during the night and too early, about five nights a week.",
    "Things I used to enjoy feel flat now and I mostly go through the motions.",
    "My mood stays heavy most of the day and basic tasks make me feel like I am failing at things that should be easy.",
    "I move slower than usual and it takes real effort just to get started.",
    "My mind also keeps looping about work, rent, and family even when I try to stop it.",
    "It spreads across all of them, around five days a week, and I feel on edge before calls.",
    "It feels like both a busy mind and a tense body, especially at night when I cannot relax.",
    "I pace around, get snappy with people, and feel like something bad is about to happen with work or money.",
    "No, I have not had thoughts of hurting myself or not wanting to be alive.",
]

PRESETS = {
    "full-coverage-en": {
        "language": "en",
        "turns": FULL_COVERAGE_EN_TURNS,
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a production chat session and report PHQ/GAD completion progress.")
    parser.add_argument(
        "--base-url",
        default="https://manovarta-runtime-ciiiagnzaq-uk.a.run.app",
        help="Runtime base URL exposing /chat/sessions.",
    )
    parser.add_argument(
        "--preset",
        choices=sorted(PRESETS.keys()),
        default="full-coverage-en",
        help="Built-in scripted transcript to replay.",
    )
    parser.add_argument(
        "--output-json",
        help="Optional path to write the full report JSON.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=120.0,
        help="HTTP timeout in seconds per request.",
    )
    return parser.parse_args()


def post_json(base_url: str, path: str, payload: dict, timeout: float) -> dict:
    request = Request(
        base_url.rstrip("/") + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
        method="POST",
    )
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def get_json(base_url: str, path: str, timeout: float) -> dict:
    request = Request(
        base_url.rstrip("/") + path,
        headers={"User-Agent": "Mozilla/5.0"},
        method="GET",
    )
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    args = parse_args()
    preset = PRESETS[args.preset]
    start = post_json(args.base_url, "/chat/sessions", {"language": preset["language"]}, timeout=args.timeout)
    session_id = start["session_id"]

    turn_reports = []
    for index, text in enumerate(preset["turns"], start=1):
        response = post_json(
            args.base_url,
            f"/chat/sessions/{session_id}/turns",
            {"text": text},
            timeout=args.timeout,
        )
        snapshot = response["snapshot"]
        dialogue = snapshot["coverage"]["dialogue"]
        turn_reports.append(
            {
                "turn_index": index,
                "user_text": text,
                "assistant_text": response["assistant_turn"]["text"],
                "assistant_notes": response["assistant_turn"].get("notes"),
                "touched_items": snapshot["coverage"]["touched_items"],
                "completion_ratio": snapshot["coverage"]["completion_ratio"],
                "resolved_items": list(snapshot["coverage"]["resolved_items"]),
                "phq_queue": list(dialogue["phq_queue"]),
                "gad_queue": list(dialogue["gad_queue"]),
                "target_topic": dialogue["target_topic"],
                "target_item": dialogue["target_item"],
                "active_domain": dialogue["active_domain"],
                "domain_locked": dialogue["domain_locked"],
                "summary_ready": dialogue["summary_ready"],
            }
        )

    summary = get_json(args.base_url, f"/chat/sessions/{session_id}/summary", timeout=args.timeout)
    summary_snapshot = summary["snapshot"]
    dialogue = summary_snapshot["coverage"]["dialogue"]
    report = {
        "base_url": args.base_url.rstrip("/"),
        "session_id": session_id,
        "preset": args.preset,
        "language": preset["language"],
        "turn_count": len(preset["turns"]),
        "sources": [turn["assistant_notes"] for turn in turn_reports],
        "turns": turn_reports,
        "final": {
            "summary_ready": dialogue["summary_ready"],
            "completion_ratio": summary_snapshot["coverage"]["completion_ratio"],
            "touched_items": summary_snapshot["coverage"]["touched_items"],
            "resolved_items": list(summary_snapshot["coverage"]["resolved_items"]),
            "unresolved_items": list(summary_snapshot["unresolved_items"]),
            "phq_queue": list(dialogue["phq_queue"]),
            "gad_queue": list(dialogue["gad_queue"]),
            "totals": summary_snapshot["totals"],
            "summary_text": summary["summary"],
        },
    }

    if args.output_json:
        output_path = Path(args.output_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"session_id: {session_id}")
    print(f"preset: {args.preset}")
    print(f"turn_count: {len(preset['turns'])}")
    print(f"final_completion_ratio: {report['final']['completion_ratio']}")
    print(f"final_touched_items: {report['final']['touched_items']}")
    print(f"final_phq_queue: {report['final']['phq_queue']}")
    print(f"final_gad_queue: {report['final']['gad_queue']}")
    print(f"summary_ready: {report['final']['summary_ready']}")
    print(json.dumps(report["final"], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
