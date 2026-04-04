from pathlib import Path

from manovarta_core.config import discover_local_safety_checkpoint


def test_discover_local_safety_checkpoint_prefers_explicit_env(monkeypatch, tmp_path):
    explicit = tmp_path / "custom-checkpoint"
    monkeypatch.setenv("MANOVARTA_LOCAL_SAFETY_CHECKPOINT", str(explicit))

    resolved = discover_local_safety_checkpoint(project_root=tmp_path)

    assert resolved == str(explicit)


def test_discover_local_safety_checkpoint_autodetects_promoted_fp16_dir(monkeypatch, tmp_path):
    monkeypatch.delenv("MANOVARTA_LOCAL_SAFETY_CHECKPOINT", raising=False)
    checkpoint = tmp_path / "outputs" / "local_safety_boost" / "safety-indicbert-best-infer-fp16"
    checkpoint.mkdir(parents=True)
    (checkpoint / "config.json").write_text("{}", encoding="utf-8")
    (checkpoint / "model.safetensors.index.json").write_text("{}", encoding="utf-8")

    resolved = discover_local_safety_checkpoint(project_root=tmp_path)

    assert resolved == str(checkpoint)


def test_discover_local_safety_checkpoint_returns_none_without_valid_dir(monkeypatch, tmp_path):
    monkeypatch.delenv("MANOVARTA_LOCAL_SAFETY_CHECKPOINT", raising=False)
    incomplete = tmp_path / "outputs" / "local_safety_boost" / "safety-indicbert-best"
    incomplete.mkdir(parents=True)
    (incomplete / "config.json").write_text("{}", encoding="utf-8")

    resolved = discover_local_safety_checkpoint(project_root=tmp_path)

    assert resolved is None
