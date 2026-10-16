from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from booksprite.config import settings
from booksprite.db import init_db
from booksprite.routers import books, health


@asynccontextmanager
async def lifespan(app: FastAPI):
    for d in (settings.data_dir, settings.books_dir, settings.covers_dir):
        d.mkdir(parents=True, exist_ok=True)
    init_db(settings.database_url)
    yield


app = FastAPI(title="BookSprite", lifespan=lifespan)
app.include_router(health.router, prefix="/api")
app.include_router(books.router, prefix="/api")

# In production, serve the built Vue app from the same process.
if settings.frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=settings.frontend_dist, html=True), name="frontend")
