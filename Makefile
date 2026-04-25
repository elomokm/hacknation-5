.PHONY: install api backend frontend dev test test-api lint

PYTHON = .venv/bin/python
UV     = uv

install:
	$(UV) venv .venv --python 3.12
	$(UV) pip install -r backend/requirements.txt -r frontend/requirements.txt --python .venv/bin/python

api:
	cd backend && ../.venv/bin/uvicorn main:app --reload --port 8000

backend: api  # alias

frontend:
	.venv/bin/streamlit run frontend/app.py --server.port 8501

dev:
	@echo "Starting API on :8000 and Streamlit on :8501..."
	@trap 'kill 0' EXIT INT TERM; \
	(cd backend && ../.venv/bin/uvicorn main:app --reload --port 8000) & \
	(.venv/bin/streamlit run frontend/app.py --server.port 8501) & \
	wait

test:
	cd backend && PYTHONPATH=. ../.venv/bin/python tests/test_api.py

test-api: test  # alias

lint:
	.venv/bin/ruff check backend/ frontend/
