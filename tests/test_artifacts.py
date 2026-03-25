import subprocess
import sys
import zipfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_package_training_artifacts_includes_manifest_and_extra_dirs(tmp_path):
    outputs_dir = tmp_path / "outputs"
    reports_dir = tmp_path / "colab_run"
    artifacts_dir = tmp_path / "artifacts"

    outputs_dir.mkdir()
    reports_dir.mkdir()
    (outputs_dir / "model.bin").write_text("weights", encoding="utf-8")
    (reports_dir / "eval_bundle.json").write_text('{"status": "ok"}\n', encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "tools" / "package_training_artifacts.py"),
            "--source-dir",
            str(outputs_dir),
            "--include-dir",
            str(reports_dir),
            "--output-dir",
            str(artifacts_dir),
            "--archive-name",
            "bundle.zip",
        ],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    archive_path = artifacts_dir / "bundle.zip"
    assert archive_path.exists()

    with zipfile.ZipFile(archive_path) as archive:
        names = set(archive.namelist())

    assert "manifest.json" in names
    assert "outputs/model.bin" in names
    assert "colab_run/eval_bundle.json" in names
