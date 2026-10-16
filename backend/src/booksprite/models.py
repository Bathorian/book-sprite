from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(UTC)


class BookFormat(StrEnum):
    EPUB = "epub"
    PDF = "pdf"


class Sprite(SQLModel, table=True):
    """A reading companion: one PNG frame per direction it can face."""

    id: int | None = Field(default=None, primary_key=True)
    name: str
    file_hash: str = Field(unique=True, index=True)
    width: int
    height: int
    # Comma-separated directions that have a frame, e.g. "south,east,west".
    directions: str
    added_at: datetime = Field(default_factory=utcnow)

    @property
    def direction_list(self) -> list[str]:
        return self.directions.split(",")


class SpriteAnimation(SQLModel, table=True):
    """A one-shot animation a sprite plays on an event, e.g. turning the page."""

    __tablename__ = "sprite_animation"
    __table_args__ = (UniqueConstraint("sprite_id", "kind", name="uq_sprite_animation_kind"),)

    id: int | None = Field(default=None, primary_key=True)
    sprite_id: int = Field(foreign_key="sprite.id", ondelete="CASCADE", index=True)
    kind: str  # e.g. "page_turn"
    file_hash: str
    width: int
    height: int
    # Comma-separated frame durations in milliseconds, one per frame.
    durations: str
    added_at: datetime = Field(default_factory=utcnow)

    @property
    def duration_list(self) -> list[int]:
        return [int(d) for d in self.durations.split(",")]


class Book(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    author: str | None = Field(default=None, index=True)
    format: BookFormat
    file_hash: str = Field(unique=True, index=True)
    original_filename: str
    file_size: int
    cover_filename: str | None = None
    sprite_id: int | None = Field(default=None, foreign_key="sprite.id", ondelete="SET NULL")
    added_at: datetime = Field(default_factory=utcnow)
    last_opened_at: datetime | None = None

    @property
    def filename(self) -> str:
        return f"{self.file_hash}.{self.format}"
