# BookSprite

A self-hosted ebook reader for EPUB and PDF, with a pixel-art reading companion.
Python (FastAPI) backend, Vue 3 + TypeScript frontend.

## Features

- **Library** – upload EPUB/PDF files (button or drag and drop), with title, author and cover
  read from the file. Search, sort, edit metadata and delete. Duplicate uploads are detected.
- **Reader** – paper-coloured reading view. EPUBs are paginated (two-page spread on wide
  screens) with adjustable text size; PDFs fit the screen with zoom. Table of contents,
  keyboard navigation (←/→, Space, PageUp/PageDown) and a progress bar.
- **Reading companion** – a sprite that walks along the progress bar, follows the mouse,
  turns to face it in 8 directions and hops when you turn a page. Toggle it from the
  reader's top bar.

## Requirements

- [uv](https://docs.astral.sh/uv/) (Python 3.11+)
- Node.js 22.18+ or 24.12+

## Setup

```sh
uv sync                       # backend deps into .venv
cd frontend && npm install    # frontend deps
```

## Development

Run the two servers in separate terminals from the repo root:

```sh
uv run uvicorn booksprite.main:app --reload    # API on http://127.0.0.1:8000
cd frontend && npm run dev                     # UI on http://localhost:5173 (proxies /api)
```

API docs: http://127.0.0.1:8000/docs

## Production

```sh
cd frontend && npm run build                   # type-checks and outputs frontend/dist
uv run uvicorn booksprite.main:app             # serves UI + API on :8000
```

## Project layout

```
backend/
  src/booksprite/
    main.py              FastAPI app; serves the built frontend in production
    config.py            settings (BOOKSPRITE_* env vars)
    models.py            database tables
    routers/books.py     /api/books endpoints
    services/            file storage and EPUB/PDF metadata extraction
  migrations/            Alembic migrations (0001, 0002, ...)
frontend/src/
  views/                 LibraryView (library page), ReaderView (reader page)
  components/reader/     EPUB reader (epub.js), PDF reader (pdf.js), reading companion
  companions/            companion sprites, one folder per character
  stores/library.ts      library state (Pinia)
  api/                   backend API client
data/                    uploaded books, covers and the SQLite database (gitignored)
```

## API

| Method | Path | |
|---|---|---|
| `POST` | `/api/books` | upload a book (multipart field `file`) |
| `GET` | `/api/books?q=&sort=` | list books; `sort` is `added`, `opened`, `title` or `author` |
| `GET` | `/api/books/{id}` | book details |
| `PATCH` | `/api/books/{id}` | update `title` / `author` |
| `DELETE` | `/api/books/{id}` | delete the book and its files |
| `GET` | `/api/books/{id}/file` | download the book file (supports range requests) |
| `GET` | `/api/books/{id}/cover` | cover image |

## Database migrations

The schema is managed by [Alembic](https://alembic.sqlalchemy.org/). Migrations live in
`backend/migrations/versions/` and are numbered `0001`, `0002`, ... They are applied
automatically when the backend starts. Run these commands from the repo root.

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

## Adding a companion

Put 8 PNG frames named `north.png`, `north-east.png`, `east.png`, `south-east.png`,
`south.png`, `south-west.png`, `west.png` and `north-west.png` in
`frontend/src/companions/<name>/`, define it in `frontend/src/companions/index.ts` the same
way as `warrior`, and use it in place of `warrior` in `frontend/src/views/ReaderView.vue`.

## Linting and formatting

```sh
uv run ruff check . && uv run ruff format .
cd frontend && npm run lint && npm run format && npm run type-check
```

## Configuration

Environment variables (or a `.env` file), prefixed `BOOKSPRITE_`:

| Variable | Default |
|---|---|
| `BOOKSPRITE_DATA_DIR` | `./data` (books, covers, SQLite DB) |
| `BOOKSPRITE_MAX_UPLOAD_MB` | `500` |
