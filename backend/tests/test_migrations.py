from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect
from sqlmodel import SQLModel

from booksprite import models  # noqa: F401
from booksprite.migrations import alembic_config, upgrade_to_head


def _url(tmp_path: Path) -> str:
    return f"sqlite:///{tmp_path / 'test.db'}"


def test_migrations_match_models(tmp_path: Path):
    """Fails if a model changed without a matching migration."""
    engine = create_engine(_url(tmp_path))
    upgrade_to_head(engine)
    with engine.connect() as connection:
        diff = compare_metadata(MigrationContext.configure(connection), SQLModel.metadata)
    assert diff == [], (
        f"Models and migrations differ; run `alembic revision --autogenerate`: {diff}"
    )


def test_downgrade_to_base_and_back(tmp_path: Path):
    url = _url(tmp_path)
    engine = create_engine(url)
    upgrade_to_head(engine)
    command.downgrade(alembic_config(url), "base")
    assert "book" not in inspect(engine).get_table_names()
    command.upgrade(alembic_config(url), "head")
    assert "book" in inspect(engine).get_table_names()


def test_revisions_are_numbered_sequentially():
    script = ScriptDirectory.from_config(alembic_config("sqlite://"))
    revisions = [r.revision for r in reversed(list(script.walk_revisions()))]
    assert revisions == [f"{i:04d}" for i in range(1, len(revisions) + 1)]


def test_pre_migration_database_is_stamped(tmp_path: Path):
    """A database created with create_all() before Alembic was added is adopted."""
    engine = create_engine(_url(tmp_path))
    SQLModel.metadata.create_all(engine)
    upgrade_to_head(engine)
    with engine.connect() as connection:
        assert MigrationContext.configure(connection).get_current_revision() is not None
