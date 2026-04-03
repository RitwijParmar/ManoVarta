from argparse import Namespace

from tools.run_colab_daic_continue import (
    DEFAULT_EXTRACTOR_OUTPUT,
    DEFAULT_REPORTS_DIR,
    configure_storage_paths,
    pick_best_extractor_report,
)
from training.finetune_extractor import resolve_adapter_base_model, resolve_tokenizer_source


def test_daic_continue_configure_storage_paths_redirects_defaults_into_drive_dir():
    args = Namespace(
        drive_dir="/tmp/drive-root",
        reports_dir=str(DEFAULT_REPORTS_DIR),
        extractor_output=str(DEFAULT_EXTRACTOR_OUTPUT),
    )

    configure_storage_paths(args)

    assert args.reports_dir == "/tmp/drive-root/reports/colab_daic_continue"
    assert args.extractor_output.endswith("/tmp/drive-root/outputs/colab/extractor-aya-8b-compact-daic-continue")


def test_resolve_adapter_helpers_use_adapter_tokenizer_when_present(tmp_path):
    adapter_dir = tmp_path / "adapter"
    adapter_dir.mkdir()
    (adapter_dir / "adapter_config.json").write_text(
        '{"base_model_name_or_path":"Qwen/Qwen2.5-7B-Instruct"}',
        encoding="utf-8",
    )
    (adapter_dir / "tokenizer_config.json").write_text("{}", encoding="utf-8")

    assert resolve_adapter_base_model(str(adapter_dir)) == "Qwen/Qwen2.5-7B-Instruct"
    assert resolve_tokenizer_source("ignored-model", str(adapter_dir)) == str(adapter_dir)


def test_resolve_tokenizer_source_falls_back_to_base_model_without_tokenizer(tmp_path):
    adapter_dir = tmp_path / "adapter"
    adapter_dir.mkdir()
    (adapter_dir / "adapter_config.json").write_text(
        '{"base_model_name_or_path":"Qwen/Qwen2.5-7B-Instruct"}',
        encoding="utf-8",
    )

    assert resolve_tokenizer_source("ignored-model", str(adapter_dir)) == "Qwen/Qwen2.5-7B-Instruct"


def test_pick_best_extractor_report_prefers_balanced_multilingual_macro_f1():
    reports = [
        {
            "checkpoint_name": "checkpoint-10",
            "step": 10,
            "result": {
                "overall": {"macro_f1": 0.31, "mae": 0.44},
                "languages": {
                    "en": {"macro_f1": 0.40, "exact_match_rate": 0.56, "coverage_completeness": 0.98},
                    "hi": {"macro_f1": 0.33, "exact_match_rate": 0.52, "coverage_completeness": 0.94},
                    "hinglish": {"macro_f1": 0.28, "exact_match_rate": 0.50, "coverage_completeness": 0.90},
                },
            },
        },
        {
            "checkpoint_name": "checkpoint-20",
            "step": 20,
            "result": {
                "overall": {"macro_f1": 0.32, "mae": 0.48},
                "languages": {
                    "en": {"macro_f1": 0.38, "exact_match_rate": 0.54, "coverage_completeness": 0.97},
                    "hi": {"macro_f1": 0.34, "exact_match_rate": 0.53, "coverage_completeness": 0.94},
                    "hinglish": {"macro_f1": 0.31, "exact_match_rate": 0.53, "coverage_completeness": 0.91},
                },
            },
        },
    ]

    best = pick_best_extractor_report(reports)

    assert best["checkpoint_name"] == "checkpoint-20"
