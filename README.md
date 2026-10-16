# BookSprite

A self-hosted ebook reader for EPUB and PDF, with a pixel-art reading companion.
Python (FastAPI) backend, Vue 3 + TypeScript frontend.

## Features

- **Library** – upload EPUB/PDF files (button or drag and drop), with title, author and cover
  read from the file. Search, sort, edit metadata and delete. Duplicate uploads are detected.
- **Reader** – paper-coloured reading view. EPUBs are paginated (two-page spread on wide
  screens, always one page on phones) with adjustable text size; PDFs fit the screen with
  zoom. Page numbers under each page and next to each entry in the table of contents.
  Turn pages with the arrows, keyboard (←/→, Space, PageUp/PageDown), swiping, or tapping
  the left/right edge of the page.
- **Phones** – works in portrait and landscape: touch-sized buttons, swipe/tap page turns
  and a compact layout when the phone is held sideways.
- **Reading companion** – a pixel-art warrior patrols back and forth along the progress bar
  and does a flying kick each time you turn a page. The figure button in the reader's top
  bar shows or hides him.

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

### Opening it on your phone

Your phone must be on the same Wi-Fi network as your computer. Run the frontend with
`npm run dev:lan` instead of `npm run dev`; Vite prints a `Network:` address such as
`http://192.168.1.20:5173` — open that on the phone. (Windows may ask to allow Node.js
through the firewall.)

There is no login: anyone on the same network who knows the address can use the library,
so only do this on a network you trust.

## Production

```sh
cd frontend && npm run build                   # type-checks and outputs frontend/dist
uv run uvicorn booksprite.main:app             # serves UI + API on :8000
```

Add `--host 0.0.0.0` to the uvicorn command to reach it from other devices (same caveat
as above).

### EPUB page numbers

EPUB text reflows to the screen, so it has no fixed pages. BookSprite measures how much text
fits on one page at the current text size and screen size and splits the book into pages of
that size, so numbers advance one per page and the contents show where each chapter starts.
Changing the text size or rotating a phone recounts them. The first count of a long book
takes a few seconds (about 14 s for a 1,000-page novel); results are cached in the browser,
so reopening is instant.

## Project layout

```
backend/
  src/booksprite/
    main.py              FastAPI app; serves the built frontend in production
    config.py            settings (BOOKSPRITE_* env vars)
    models.py            database tables
    routers/             /api/books and /api/sprites endpoints
    services/            file storage, EPUB/PDF metadata, sprite upload parsing
  migrations/            Alembic migrations (0001, 0002, ...)
frontend/src/
  views/                 LibraryView (library page), ReaderView (reader page)
  components/reader/     EPUB reader (epub.js), PDF reader (pdf.js), reading companion
  companions/            built-in companion sprites (frames + page-turn animation)
  stores/library.ts      library state (Pinia)
  api/                   backend API client
data/                    uploaded books, covers, sprites and the SQLite database (gitignored)
```

## API

| Method | Path | |
|---|---|---|
| `POST` | `/api/books` | upload a book (multipart field `file`) |
| `GET` | `/api/books?q=&sort=` | list books; `sort` is `added`, `opened`, `title` or `author` |
| `GET` | `/api/books/{id}` | book details |
| `PATCH` | `/api/books/{id}` | update `title` / `author` |
| `DELETE` | `/api/books/{id}` | delete the book and its files |
| `PUT` | `/api/books/{id}/sprite` | set the book's companion (`{"sprite_id": 1}` or `null`) |
| `GET` | `/api/books/{id}/file` | download the book file (supports range requests) |
| `GET` | `/api/books/{id}/cover` | cover image |
| `POST` | `/api/sprites` | upload a companion sprite (multipart field `file`) |
| `GET` | `/api/sprites` | list uploaded sprites |
| `GET` | `/api/sprites/{id}` | sprite details with frame URLs |
| `GET` | `/api/sprites/{id}/{direction}.png` | one direction frame |
| `PUT` | `/api/sprites/{id}/animations/page_turn` | upload the page-turn animation (multipart `file`) |
| `DELETE` | `/api/sprites/{id}/animations/page_turn` | remove the page-turn animation |
| `GET` | `/api/sprites/{id}/animations/page_turn/{n}.png` | one animation frame |

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

## Companion sprite

The companion is built in: `frontend/src/companions/warrior/` holds one PNG per direction
(`south.png`, `east.png`, …) and `page-turn/0.png`, `1.png`, … for the kick, which is
defined in `frontend/src/companions/index.ts`. The animation's canvas may be larger than the
standing frame (room for the kick); both are aligned on their **centres**, which is how the
sprite tool exports them.

Uploading your own sprite per book is not in the UI yet. That work is saved on the
`feature/sprite-upload` branch; the backend part (`/api/sprites`, migrations 0002 and 0003)
is already here.

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
| `BOOKSPRITE_MAX_UPLOAD_MB` | `500` (books) |
| `BOOKSPRITE_MAX_SPRITE_UPLOAD_MB` | `20` (sprites) |
