from datetime import datetime

from pydantic import BaseModel, Field

from booksprite.models import Book, BookFormat, Sprite, SpriteAnimation


class BookRead(BaseModel):
    id: int
    title: str
    author: str | None
    format: BookFormat
    original_filename: str
    file_size: int
    has_cover: bool
    sprite_id: int | None
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
            sprite_id=book.sprite_id,
            added_at=book.added_at,
            last_opened_at=book.last_opened_at,
        )


class BookUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    author: str | None = Field(default=None, max_length=500)


class BookSpriteUpdate(BaseModel):
    sprite_id: int | None


class AnimationRead(BaseModel):
    width: int
    height: int
    durations: list[int]
    frames: list[str]  # frame URLs, in order

    @classmethod
    def from_model(cls, animation: SpriteAnimation) -> "AnimationRead":
        base = f"/api/sprites/{animation.sprite_id}/animations/{animation.kind}"
        version = animation.file_hash[:12]  # new upload -> new URLs, so caching stays safe
        return cls(
            width=animation.width,
            height=animation.height,
            durations=animation.duration_list,
            frames=[f"{base}/{i}.png?v={version}" for i in range(len(animation.duration_list))],
        )


class SpriteRead(BaseModel):
    id: int
    name: str
    width: int
    height: int
    # direction -> frame URL
    frames: dict[str, str]
    # kind (e.g. "page_turn") -> animation
    animations: dict[str, AnimationRead]

    @classmethod
    def from_model(cls, sprite: Sprite, animations: list[SpriteAnimation]) -> "SpriteRead":
        return cls(
            id=sprite.id,
            name=sprite.name,
            width=sprite.width,
            height=sprite.height,
            frames={d: f"/api/sprites/{sprite.id}/{d}.png" for d in sprite.direction_list},
            animations={a.kind: AnimationRead.from_model(a) for a in animations},
        )
