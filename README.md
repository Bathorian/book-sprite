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
- **Any screen size** – from small phones (320px) to large monitors. Phones get touch-sized
  buttons, swipe/tap page turns and a compact layout when held sideways; large screens scale
  the interface and text up; long lines are capped at a comfortable book width.
- **Reading companion** – a pixel-art warrior patrols back and forth along the progress bar
  and does a flying kick each time you turn a page. Stay on a page for more than 5 seconds
  and he stops and turns to face you, waiting for you to move on — hover over him (or tap
  him on a phone) and he says "Move on!". The figure button in the reader's top bar shows or
  hides him.

## Requirements

- [uv](https://docs.astral.sh/uv/) (Python 3.11+)
- Node.js 22.18+ or 24.12+
- Optional: GNU Make, for the `make` shortcuts below

## Setup

```sh
uv sync                          # backend deps into .venv
npm --prefix frontend install    # frontend deps
```

## Development

Run the two servers in separate terminals from the repo root:

```sh
make backend     # API on http://127.0.0.1:8000 (reloads on changes, applies migrations)
make frontend    # UI on http://localhost:5173 (proxies /api to the backend)
```

Without `make`, the same commands are:

```sh
uv run uvicorn booksprite.main:app --reload
npm --prefix frontend run dev
```

API docs: http://127.0.0.1:8000/docs

### Opening it on your phone

Your phone must be on the same Wi-Fi network as your computer. Start the frontend with
`npm --prefix frontend run dev:lan` instead of `make frontend`; Vite prints a `Network:`
address such as `http://192.168.1.20:5173` — open that on the phone. (Windows may ask to
allow Node.js through the firewall.)

There is no login: anyone on the same network who knows the address can use the library,
so only do this on a network you trust.

## Production

From the repo root:

```sh
npm --prefix frontend run build                # type-checks and outputs frontend/dist
uv run uvicorn booksprite.main:app             # serves UI + API on http://127.0.0.1:8000
```

Add `--host 0.0.0.0` to the uvicorn command to reach it from other devices (same caveat
as above: there is no login yet).

## How it works

### EPUB page numbers

EPUB text reflows to the screen, so it has no fixed pages. BookSprite measures how much text
fits on one page at the current text size and screen size and splits the book into pages of
that size, so numbers advance one per page and the contents show where each chapter starts.
Changing the text size or rotating a phone recounts them. The first count of a long book
takes a few seconds (about 14 s for a 1,000-page novel); results are cached in the browser,
so reopening is instant.

### Companion sprite

The companion is built in: `frontend/src/companions/warrior/` holds one PNG per direction
(`south.png`, `east.png`, …) and `page-turn/0.png`, `1.png`, … for the kick, which is
defined in `frontend/src/companions/index.ts`. The animation's canvas may be larger than the
standing frame (room for the kick); both are aligned on their **centres**, which is how the
sprite tool exports them. Walking speed and the 5-second wait are constants at the top of
`frontend/src/components/reader/ReadingCompanion.vue`.

Uploading your own sprite per book is not in the UI yet. That work is saved on the
`feature/sprite-upload` branch; the backend part (`/api/sprites`, migrations 0002 and 0003)
is already here.

## Project layout

```
Makefile                 make backend / make frontend
alembic.ini              Alembic (migrations) config
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
  components/reader/     EPUB reader (epub.js), PDF reader (pdf.js), companion, swipe helpers
  companions/            built-in companion sprites (frames + page-turn animation)
  composables/           screen-size helpers (media queries, large-screen scaling)
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
uv run alembic revision --autogenerate -m "add series column"   # creates e.g. 0004_add_series_column.py
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

Never delete or edit a migration that has already been applied to a database; add a new one.

## Linting and formatting

```sh
uv run ruff check . && uv run ruff format .
cd frontend && npm run lint && npm run format && npm run type-check
```

## Configuration

Environment variables (or a `.env` file in the directory you start the backend from),
prefixed `BOOKSPRITE_`:

| Variable | Default |
|---|---|
| `BOOKSPRITE_DATA_DIR` | `data/` in the repo (books, covers, sprites, SQLite DB) |
| `BOOKSPRITE_MAX_UPLOAD_MB` | `500` (books) |
| `BOOKSPRITE_MAX_SPRITE_UPLOAD_MB` | `20` (sprites) |

## TODO

### Requested

- [ ] **More companion animations**
  - [ ] A real walk cycle (frames for east and west) to replace the stepping bob
  - [ ] East/west versions of the kick, so he kicks toward the page being turned
        (the current GIF only has the south-facing direction)
  - [ ] An idle/"waiting" animation for when he stops to face the reader (tapping foot,
        pointing at the next page)
  - [ ] Reactions to milestones: finishing a chapter, finishing the book
  - [ ] Bring back per-book sprites and uploads from the `feature/sprite-upload` branch, with
        animation slots for each of the above
- [ ] **Deploy online** (e.g. [Fly.io](https://fly.io); Railway, Render or a small VPS also work)
  - [ ] Add login first (see *Security* below) — the app is currently open to anyone who can
        reach it
  - [ ] Dockerfile: build the frontend with Node, then run the backend with uv, serving
        `frontend/dist` (the backend already does this when `dist` exists)
  - [ ] Persistent volume mounted at `BOOKSPRITE_DATA_DIR` for the SQLite DB and book files;
        run a single machine (SQLite doesn't share across machines)
  - [ ] Regular backups of the data volume
  - [ ] HTTPS comes with the platform; set a sensible upload size limit at the proxy too
- [ ] **Android app**
  - [ ] Step 1 – make it an installable PWA: web app manifest, app icons (replace the
        default Vite favicon), a service worker to cache the app shell. "Add to home screen"
        then gives a full-screen app on Android with no app store
  - [ ] Step 2 – Play Store: wrap the deployed PWA in a Trusted Web Activity (e.g. with
        Bubblewrap) or use Capacitor for a native shell
  - [ ] Either way the backend must be reachable from the phone, i.e. deployed online first
  - [ ] Optional: offline reading (cache opened books on the device)

### Fixes and improvements (from code review)

Highest impact first:

- [ ] **Save reading position** – books always reopen at the start. Store the position
      (EPUB CFI / PDF page) per book in the backend and restore it on open; show progress
      bars in the library
- [ ] **Security** – no authentication, so the app must not be exposed beyond a trusted
      network. Add login (single user is enough to start) before deploying
- [ ] **Bring back automated tests** – they were removed during cleanup. Cover at least:
      uploads (EPUB/PDF/invalid/duplicate), migrations matching the models, and the EPUB page
      counting
- [ ] **Upload robustness** – files are written to disk before the database record is
      committed, and two identical uploads at the same moment can hit the unique-hash
      constraint and return a 500. Catch the conflict, return 409, and clean up files if the
      commit fails
- [ ] **Reader font** – the reader asks for *Literata* but never loads it, so it falls back to
      Georgia (and to a generic serif on Android, which has no Georgia). Bundle Literata
      (SIL Open Font License) for a consistent look on every device
- [ ] **epub.js** – version 0.3.93 is unmaintained and pulls in `@xmldom/xmldom` with known
      advisories (`npm audit`). Evaluate epub.js 0.4.x or foliate-js. Page counting also reads
      epub.js's private `_locations` list, so re-test page numbers after any upgrade
- [ ] **Page counting speed** – the first count of a long book takes ~14 s in the browser.
      Options: count once on the server after upload, or show a progress indicator
- [ ] **Page-count cache** – stored in `localStorage` (~100 KB per book and layout); a large
      library could hit the browser's storage limit. Move to IndexedDB or prune old books
- [ ] **PDF covers** – only taken from images embedded on the first page (pypdf can't render
      pages), so text-only PDFs get a placeholder. Render page 1 with pypdfium2 instead
- [ ] **Unused backend code** – the `/api/sprites` endpoints aren't used by the UI until the
      upload branch is merged; merge it or keep them documented as such
- [ ] **Accessibility** – keyboard focus isn't trapped inside the contents drawer; the side
      tap zones have no visible hint on first use

### Ideas

- [ ] Night / sepia / light reading themes (the reader is paper-coloured only)
- [ ] Bookmarks, highlights and notes
- [ ] Full-text search inside a book and across the library (SQLite FTS5)
- [ ] Collections / shelves and reading statistics (time read, pages per day)
- [ ] More formats: MOBI/AZW3 (convert to EPUB on upload), CBZ comics
- [ ] Choose the companion's walking speed and wait time in a settings panel
