PYTHON=.venv/bin/python
PIP=.venv/bin/pip

.PHONY: install test api migrate seed stats eval-seed compare-baselines splits export-train ship-bundle assignment-report

install:
	$(PIP) install -e .[dev]

test:
	$(PYTHON) -m pytest

api:
	.venv/bin/uvicorn manovarta_core.api:app --reload

migrate:
	$(PYTHON) manage.py migrate

seed:
	$(PYTHON) manage.py load_seed_data

stats:
	$(PYTHON) tools/dataset_stats.py

eval-seed:
	$(PYTHON) tools/evaluate_seed_runtime.py --mode heuristic

compare-baselines:
	$(PYTHON) tools/compare_llm_baselines.py

splits:
	$(PYTHON) tools/create_data_splits.py

export-train:
	$(PYTHON) tools/export_training_sets.py

ship-bundle:
	$(PYTHON) tools/package_shipped_baseline.py

assignment-report:
	$(PYTHON) tools/generate_assignment_completion_report.py
