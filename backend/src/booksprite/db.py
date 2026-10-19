from collections.abc import Iterator

from sqlalchemy import Engine
from sqlmodel import Session, create_engine

from booksprite.migrations import upgrade_to_head

_engine: Engine | None = None


def init_db(database_url: str) -> Engine:
    global _engine
    if _engine is not None:
        _engine.dispose()
    _engine = create_engine(database_url, connect_args={"check_same_thread": False})
    upgrade_to_head(_engine)
    return _engine


def get_session() -> Iterator[Session]:
    if _engine is None:
        raise RuntimeError("Database not initialised")
    with Session(_engine) as session:
        yield session
