"""add sprites

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-16 21:40:21.621691

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sprite",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("file_hash", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("directions", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("added_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("sprite", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_sprite_file_hash"), ["file_hash"], unique=True)

    with op.batch_alter_table("book", schema=None) as batch_op:
        batch_op.add_column(sa.Column("sprite_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_book_sprite_id_sprite", "sprite", ["sprite_id"], ["id"], ondelete="SET NULL"
        )


def downgrade() -> None:
    with op.batch_alter_table("book", schema=None) as batch_op:
        batch_op.drop_constraint("fk_book_sprite_id_sprite", type_="foreignkey")
        batch_op.drop_column("sprite_id")

    with op.batch_alter_table("sprite", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_sprite_file_hash"))

    op.drop_table("sprite")
