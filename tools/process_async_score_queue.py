#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from manovarta_core.async_scoring import AsyncScoringStore
from manovarta_core.config import get_runtime_config
from manovarta_core.engine import RuntimeEngine
from manovarta_core.llm import HuggingFaceExtractor, HuggingFaceSafetyAssessor
from manovarta_core.safety import SafetyMonitor
from manovarta_core.safety_assessors import CompositeSafetyAssessor, LocalSafetyCheckpointAssessor
from manovarta_core.scoring import ConversationScorer
from manovarta_core.semantic_safety import SemanticSafetyConfig, SemanticSafetyMonitor


def build_engine() -> tuple[RuntimeEngine, HuggingFaceExtractor]:
    runtime_config = get_runtime_config()
    extractor = HuggingFaceExtractor(runtime_config)
    local_safety_assessor = LocalSafetyCheckpointAssessor(runtime_config.local_safety_checkpoint)
    hf_safety_assessor = None if local_safety_assessor.enabled else HuggingFaceSafetyAssessor(runtime_config)
    safety_assessor = CompositeSafetyAssessor([local_safety_assessor, hf_safety_assessor])
    engine = RuntimeEngine(
        scorer=ConversationScorer(),
        safety_monitor=SafetyMonitor(),
        semantic_safety_monitor=SemanticSafetyMonitor(
            SemanticSafetyConfig(
                model_name=runtime_config.semantic_safety_model,
                review_threshold=runtime_config.semantic_safety_review_threshold,
                urgent_threshold=runtime_config.semantic_safety_urgent_threshold,
            )
        ),
        safety_assessor=safety_assessor,
        extractor=extractor,
    )
    return engine, extractor


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Process queued async transcript scoring jobs.")
    parser.add_argument(
        "--queue-dir",
        default=None,
        help="Override queue directory. Defaults to MANOVARTA_ASYNC_SCORING_DIR/runtime config.",
    )
    parser.add_argument("--request-id", default=None, help="Process only one queued request id.")
    parser.add_argument("--max-jobs", type=int, default=10, help="Maximum pending jobs to process.")
    parser.add_argument(
        "--allow-heuristic-fallback",
        action="store_true",
        help="If LLM extraction is unavailable, process requests heuristically instead of failing them.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    runtime_config = get_runtime_config()
    queue_dir = args.queue_dir or runtime_config.async_scoring_dir
    store = AsyncScoringStore(Path(queue_dir))
    engine, extractor = build_engine()

    request_ids = [args.request_id] if args.request_id else list(store.iter_pending_ids())[: args.max_jobs]
    processed = 0
    for request_id in request_ids:
        payload = store.load_payload(request_id)
        store.mark_running(request_id)
        try:
            if payload.use_llm and not extractor.enabled and not args.allow_heuristic_fallback:
                raise RuntimeError("LLM extractor is not configured on this worker.")
            snapshot = engine.analyze(payload.turns, payload.language, use_llm=payload.use_llm)
            store.mark_completed(
                request_id,
                {
                    "mode": snapshot.mode,
                    "snapshot": snapshot.model_dump(mode="json"),
                    "provider": runtime_config.extraction_model_provider,
                    "model": runtime_config.extraction_model,
                },
            )
            processed += 1
        except Exception as exc:  # pragma: no cover - defensive worker path
            store.mark_failed(request_id, str(exc))
    return 0 if processed or not request_ids else 1


if __name__ == "__main__":
    raise SystemExit(main())
