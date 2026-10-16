from datetime import datetime

from pydantic import BaseModel, Field

from booksprite.models import Book, BookFormat


class BookRead(BaseModel):
    id: int
    title: str
    author: str | None
    format: BookFormat
    original_filename: str
    file_size: int
    has_cover: bool
    added_at: datetime
    last_opened_at: datetime | None

    @classmethod
    def from_model(cls, book: Book) -> "BookRead":
        return cls(
            id=book.id,
            title=book.title,
            author=book.author,
            format=book.format,
            original_filename=book.original_filename,
            file_size=book.file_size,
            has_cover=book.cover_filename is not None,
            added_at=book.added_at,
            last_opened_at=book.last_opened_at,
        )


class BookUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    author: str | None = Field(default=None, max_length=500)
