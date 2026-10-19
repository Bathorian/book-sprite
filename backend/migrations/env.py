from alembic import context
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine
from sqlmodel import SQLModel

from booksprite import models  # noqa: F401  (registers tables on SQLModel.metadata)
from booksprite.config import settings

config = context.config
target_metadata = SQLModel.metadata


def _database_url() -> str:
    return config.get_main_option("sqlalchemy.url") or settings.database_url


def _number_revisions(context, revision, directives) -> None:
    """Name new migrations 0001, 0002, ... instead of random hashes."""
    script = directives[0]
    if config.cmd_opts and getattr(config.cmd_opts, "rev_id", None):
        return  # an explicit --rev-id wins
    head = ScriptDirectory.from_config(config).get_current_head()
    script.rev_id = f"{int(head) + 1 if head else 1:04d}"
    if getattr(config.cmd_opts, "autogenerate", False) and script.upgrade_ops.is_empty():
        directives[:] = []
        print("No schema changes detected; no migration generated.")


def _configure(**kwargs) -> None:
    context.configure(
        target_metadata=target_metadata,
        # SQLite can't ALTER most things in place; batch mode recreates the table.
        render_as_batch=True,
        compare_type=True,
        process_revision_directives=_number_revisions,
        **kwargs,
    )


def run_migrations_offline() -> None:
    _configure(url=_database_url(), literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connection = config.attributes.get("connection")
    if connection is not None:
        _configure(connection=connection)
        with context.begin_transaction():
            context.run_migrations()
        return

    engine = create_engine(_database_url())
    with engine.connect() as connection:
        _configure(connection=connection)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
