from pathlib import Path

from tools.run_colab_full_pipeline import checkpoint_step, pick_best_safety_report


def test_checkpoint_step_sorts_named_checkpoints_and_final_dir():
    assert checkpoint_step(Path("checkpoint-10")) == 10
    assert checkpoint_step(Path("checkpoint-2")) == 2
    assert checkpoint_step(Path("final-model")) > checkpoint_step(Path("checkpoint-999"))


def test_pick_best_safety_report_prefers_macro_f1_then_accuracy_then_step():
    reports = [
        {
            "checkpoint_name": "checkpoint-10",
            "checkpoint_path": "/tmp/checkpoint-10",
            "step": 10,
            "result": {"macro_f1": 0.44, "accuracy": 0.70},
            "report_path": "/tmp/checkpoint-10.json",
        },
        {
            "checkpoint_name": "checkpoint-20",
            "checkpoint_path": "/tmp/checkpoint-20",
            "step": 20,
            "result": {"macro_f1": 0.52, "accuracy": 0.65},
            "report_path": "/tmp/checkpoint-20.json",
        },
        {
            "checkpoint_name": "checkpoint-25",
            "checkpoint_path": "/tmp/checkpoint-25",
            "step": 25,
            "result": {"macro_f1": 0.52, "accuracy": 0.66},
            "report_path": "/tmp/checkpoint-25.json",
        },
    ]

    best = pick_best_safety_report(reports)

    assert best["checkpoint_name"] == "checkpoint-25"
