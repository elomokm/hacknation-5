.PHONY: install backend frontend test lint

PYTHON = .venv/bin/python
UV     = uv

install:
	$(UV) venv .venv --python 3.12
	$(UV) pip install -r backend/requirements.txt -r frontend/requirements.txt --python .venv/bin/python

backend:
	cd backend && ../.venv/bin/uvicorn main:app --reload --port 8000

frontend:
	cd frontend && ../.venv/bin/streamlit run app.py --server.port 8501

test:
	cd backend && ../.venv/bin/pytest tests/ -v

lint:
	.venv/bin/ruff check backend/ frontend/
