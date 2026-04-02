#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from manovarta_core.dialogue import DialoguePlanner
from manovarta_core.reporting import build_summary
from manovarta_core.safety import SafetyMonitor
from manovarta_core.scoring import ConversationScorer
from manovarta_core.sessions import SessionStore


def run_cli(language: str) -> None:
    store = SessionStore()
    planner = DialoguePlanner()
    scorer = ConversationScorer()
    safety_monitor = SafetyMonitor()

    session = store.create(language)
    opening = store.add_turn(session.session_id, "assistant", planner.opening_prompt(language), language)
    print(f"\nAssistant: {opening.text}\n")

    while True:
        user_text = input("You: ").strip()
        if not user_text:
            continue
        if user_text.lower() in {"quit", "exit"}:
            break

        store.add_turn(session.session_id, "user", user_text, language)
        safety_flag = safety_monitor.assess(session.turns)
        snapshot = scorer.analyze(session.turns, language, safety_flag)
        reply, asked_item = planner.next_reply(snapshot, session)
        if asked_item and asked_item not in session.asked_items:
            session.asked_items.append(asked_item)
        store.add_turn(session.session_id, "assistant", reply, language)

        print(f"\nAssistant: {reply}")
        print(f"Safety: {snapshot.safety.level}")
        print(f"Observed totals: PHQ-9={snapshot.totals['PHQ9']} | GAD-7={snapshot.totals['GAD7']}")
        print(f"Unresolved items: {', '.join(snapshot.unresolved_items[:6]) or 'none'}\n")

        if snapshot.safety.level == "urgent":
            break

    final_snapshot = scorer.analyze(session.turns, language, safety_monitor.assess(session.turns))
    final_snapshot.coverage = planner.build_plan(final_snapshot, session)
    print("Summary:")
    print(build_summary(session, final_snapshot))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a local ManoVarta text demo.")
    parser.add_argument("--language", choices=["en", "hi", "hinglish"], default="en")
    args = parser.parse_args()
    run_cli(args.language)


if __name__ == "__main__":
    main()
