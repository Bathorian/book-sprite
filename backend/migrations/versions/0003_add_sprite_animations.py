"""add sprite animations

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-16 22:24:32.962136

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sprite_animation",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sprite_id", sa.Integer(), nullable=False),
        sa.Column("kind", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("file_hash", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("durations", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("added_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.ForeignKeyConstraint(["sprite_id"], ["sprite.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sprite_id", "kind", name="uq_sprite_animation_kind"),
    )
    with op.batch_alter_table("sprite_animation", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_sprite_animation_sprite_id"), ["sprite_id"], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table("sprite_animation", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_sprite_animation_sprite_id"))

    op.drop_table("sprite_animation")
