PYTHON=.venv/bin/python
PIP=.venv/bin/pip

.PHONY: install test api migrate seed stats eval-seed

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
