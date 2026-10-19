from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import Scope

from booksprite.config import settings
from booksprite.db import init_db
from booksprite.routers import books, sprites


@asynccontextmanager
async def lifespan(app: FastAPI):
    for d in (
        settings.data_dir,
        settings.books_dir,
        settings.covers_dir,
        settings.sprites_dir,
        settings.tmp_dir,
    ):
        d.mkdir(parents=True, exist_ok=True)
    init_db(settings.database_url)
    yield


class SPAStaticFiles(StaticFiles):
    """Serve the built frontend; unknown non-API paths get index.html for client routing."""

    async def get_response(self, path: str, scope: Scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code != 404 or scope["path"].startswith("/api"):
                raise
            return await super().get_response("index.html", scope)


app = FastAPI(title="BookSprite", lifespan=lifespan)
app.include_router(books.router, prefix="/api")
app.include_router(sprites.router, prefix="/api")

# In production, serve the built Vue app from the same process.
if settings.frontend_dist.is_dir():
    app.mount("/", SPAStaticFiles(directory=settings.frontend_dist, html=True), name="frontend")
