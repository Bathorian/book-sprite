# BookSprite

A self-hosted ebook reader for EPUB and PDF. Python (FastAPI) backend, Vue 3 + TypeScript frontend.

## Requirements

- [uv](https://docs.astral.sh/uv/) (Python 3.11+)
- Node.js 22.18+ or 24.12+

## Setup

```sh
uv sync                       # backend deps into .venv
cd frontend && npm install    # frontend deps
```

## Development

Run the two servers in separate terminals:

```sh
uv run uvicorn booksprite.main:app --reload    # API on http://127.0.0.1:8000
cd frontend && npm run dev                     # UI on http://localhost:5173 (proxies /api)
```

API docs: http://127.0.0.1:8000/docs

## Production

```sh
cd frontend && npm run build                   # outputs frontend/dist
uv run uvicorn booksprite.main:app             # serves UI + API on :8000
```

## Database migrations

The schema is managed by [Alembic](https://alembic.sqlalchemy.org/). Migrations live in
`backend/migrations/versions/` and are numbered `0001`, `0002`, ... They are applied
automatically when the backend starts.

After changing a model in `backend/src/booksprite/models.py`:

```sh
uv run alembic revision --autogenerate -m "add series column"   # creates 0002_add_series_column.py
# review the generated file, then restart the backend (or run the next line)
uv run alembic upgrade head
```

Other useful commands:

```sh
uv run alembic current          # revision the database is at
uv run alembic history          # list all migrations
uv run alembic downgrade -1     # undo the latest migration
uv run alembic revision -m "backfill data"   # empty migration for hand-written changes
```

A test (`backend/tests/test_migrations.py`) fails if the models and migrations drift apart.

## Checks

```sh
uv run pytest
uv run ruff check . && uv run ruff format --check .
cd frontend && npm run lint && npx vitest run && npm run type-check
```

## Configuration

Environment variables (or a `.env` file), prefixed `BOOKSPRITE_`:

| Variable | Default |
|---|---|
| `BOOKSPRITE_DATA_DIR` | `./data` (books, covers, SQLite DB) |
| `BOOKSPRITE_MAX_UPLOAD_MB` | `500` |
