import json
import subprocess
import sys
from pathlib import Path

from manovarta_core.daic_woz import load_daic_conversations


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _build_daic_fixture(root: Path) -> Path:
    _write_text(
        root / "train_split_Depression_AVEC2017.csv",
        "\n".join(
            [
                "Participant_ID,PHQ8_Binary,PHQ8_Score,Gender,Q1,Q2,Q3,Q4,Q5,Q6,Q7,Q8",
                "300,1,13,male,1,2,2,1,1,2,1,1",
            ]
        ),
    )
    _write_text(
        root / "dev_split_Depression_AVEC2017.csv",
        "\n".join(
            [
                "Participant_ID,PHQ8_Binary,PHQ8_Score,Gender,Q1,Q2,Q3,Q4,Q5,Q6,Q7,Q8",
                "301,0,5,female,1,1,0,1,0,0,1,0",
            ]
        ),
    )
    _write_text(
        root / "test_split.csv",
        "\n".join(
            [
                "Participant_ID,Gender",
                "302,female",
            ]
        ),
    )
    _write_text(
        root / "300_P" / "300_TRANSCRIPT.csv",
        "\n".join(
            [
                "start_time\tstop_time\tspeaker\tvalue",
                "0.00\t1.00\tEllie\tq1 (How have you been feeling lately?)",
                "1.01\t2.00\tParticipant\tMostly low and tired.",
            ]
        ),
    )
    _write_text(
        root / "301_P" / "301_TRANSCRIPT.csv",
        "\n".join(
            [
                "start_time\tstop_time\tspeaker\tvalue",
                "0.00\t1.00\tEllie\tq2 (How is your sleep?)",
                "1.01\t2.00\tParticipant\tIt has been okay, just a bit restless.",
            ]
        ),
    )
    _write_text(
        root / "302_P" / "302_TRANSCRIPT.csv",
        "\n".join(
            [
                "start_time\tstop_time\tspeaker\tvalue",
                "0.00\t1.00\tEllie\tq3 (Tell me about your week.)",
                "1.01\t2.00\tParticipant\tBusy, but manageable.",
            ]
        ),
    )
    return root


def test_load_daic_conversations_maps_phq8_and_turns(tmp_path: Path):
    root = _build_daic_fixture(tmp_path / "daic")
    grouped = load_daic_conversations(root)

    assert len(grouped["train"]) == 1
    assert len(grouped["dev"]) == 1
    assert len(grouped["test"]) == 1

    train_record = grouped["train"][0]
    assert train_record["conversation_id"] == "DAIC-300"
    assert train_record["language"] == "en"
    assert train_record["phq9_item_labels"]["phq_q2_low_mood"] == 2
    assert "How have you been feeling lately?" in train_record["conversation_turns"][0]["text"]
    assert train_record["conversation_turns"][0]["speaker"] == "assistant"
    assert train_record["conversation_turns"][1]["speaker"] == "user"

    test_record = grouped["test"][0]
    assert test_record["phq9_item_labels"] == {}


def test_export_training_sets_writes_daic_auxiliary_files(tmp_path: Path):
    root = _build_daic_fixture(tmp_path / "daic")
    output_dir = tmp_path / "processed"

    subprocess.run(
        [
            sys.executable,
            "tools/export_training_sets.py",
            "--output-dir",
            str(output_dir),
            "--daic-root",
            str(root),
        ],
        check=True,
        cwd=Path(__file__).resolve().parent.parent,
    )

    assert (output_dir / "extractor_daic_train.jsonl").exists()
    assert (output_dir / "extractor_daic_dev.jsonl").exists()
    assert (output_dir / "extractor_daic_test.jsonl").exists()
    assert (output_dir / "extractor_train_augmented_daic.jsonl").exists()

    train_row = json.loads((output_dir / "extractor_daic_train.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert train_row["language"] == "en"
    assert "DAIC-WOZ auxiliary supervision" in train_row["response"]
