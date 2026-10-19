# Run each in its own terminal: `make backend`, then `make frontend`.

.PHONY: backend frontend

# API on http://127.0.0.1:8000 (reloads on code changes; applies database migrations on start).
backend:
	uv run uvicorn booksprite.main:app --reload

# UI on http://localhost:5173 (proxies /api to the backend).
frontend:
	npm --prefix frontend run dev
