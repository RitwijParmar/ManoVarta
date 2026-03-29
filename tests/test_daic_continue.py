from argparse import Namespace

from tools.run_colab_daic_continue import DEFAULT_EXTRACTOR_OUTPUT, DEFAULT_REPORTS_DIR, configure_storage_paths
from training.finetune_extractor import resolve_adapter_base_model, resolve_tokenizer_source


def test_daic_continue_configure_storage_paths_redirects_defaults_into_drive_dir():
    args = Namespace(
        drive_dir="/tmp/drive-root",
        reports_dir=str(DEFAULT_REPORTS_DIR),
        extractor_output=str(DEFAULT_EXTRACTOR_OUTPUT),
    )

    configure_storage_paths(args)

    assert args.reports_dir == "/tmp/drive-root/reports/colab_daic_continue"
    assert args.extractor_output.endswith("/tmp/drive-root/outputs/colab/extractor-qwen25-7b-compact-daic-continue")


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
