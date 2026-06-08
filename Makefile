# Mizan — developer commands
# Usage: `make <target>`  (on Windows, use Git Bash / WSL, or run the raw commands)

PY ?= python
APP_DIR = backend

.PHONY: help install backend frontend seed test lint clean

help:
	@echo "Mizan targets:"
	@echo "  make install    Install backend + frontend deps into the active venv"
	@echo "  make backend    Run FastAPI on :8000 (docs at /docs)"
	@echo "  make frontend   Run the Streamlit workflow UI on :8501"
	@echo "  make seed       Load the 8 demo fixtures into SQLite"
	@echo "  make test       Run the pytest suite"
	@echo "  make clean      Remove caches and the local SQLite db"

install:
	$(PY) -m pip install -r backend/requirements.txt

backend:
	$(PY) -m uvicorn app.main:app --reload --app-dir $(APP_DIR) --host 0.0.0.0 --port 8000

frontend:
	$(PY) -m streamlit run streamlit_app/app.py

seed:
	cd $(APP_DIR) && $(PY) -m app.fixtures.loader

test:
	$(PY) -m pytest backend/tests -q

clean:
	rm -f mizan.db backend/mizan.db
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf .pytest_cache backend/.pytest_cache
