from datetime import UTC, datetime
from enum import StrEnum

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(UTC)


class BookFormat(StrEnum):
    EPUB = "epub"
    PDF = "pdf"


class Book(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    author: str | None = Field(default=None, index=True)
    format: BookFormat
    file_hash: str = Field(unique=True, index=True)
    original_filename: str
    file_size: int
    cover_filename: str | None = None
    added_at: datetime = Field(default_factory=utcnow)
    last_opened_at: datetime | None = None

    @property
    def filename(self) -> str:
        return f"{self.file_hash}.{self.format}"
