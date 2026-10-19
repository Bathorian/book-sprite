"""Store uploaded ebook files on disk, keyed by content hash."""

import hashlib
import shutil
import uuid
from pathlib import Path
from typing import BinaryIO

from booksprite.config import settings

CHUNK_SIZE = 1024 * 1024


class FileTooLargeError(ValueError):
    pass


def save_to_temp(source: BinaryIO, max_bytes: int) -> tuple[Path, str, int]:
    """Stream an upload to a temp file, returning (path, sha256, size)."""
    tmp_path = settings.tmp_dir / uuid.uuid4().hex
    digest = hashlib.sha256()
    size = 0
    try:
        with tmp_path.open("wb") as out:
            while chunk := source.read(CHUNK_SIZE):
                size += len(chunk)
                if size > max_bytes:
                    raise FileTooLargeError(f"File exceeds {max_bytes // (1024 * 1024)} MB")
                digest.update(chunk)
                out.write(chunk)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise
    return tmp_path, digest.hexdigest(), size


def book_path(filename: str) -> Path:
    return settings.books_dir / filename


def cover_path(filename: str) -> Path:
    return settings.covers_dir / filename


def sprite_frame_path(file_hash: str, direction: str) -> Path:
    return settings.sprites_dir / file_hash / f"{direction}.png"


def store_sprite_frames(file_hash: str, frames: dict[str, bytes]) -> None:
    for direction, data in frames.items():
        path = sprite_frame_path(file_hash, direction)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def animation_frame_path(file_hash: str, index: int) -> Path:
    return settings.sprites_dir / "animations" / file_hash / f"{index}.png"


def store_animation_frames(file_hash: str, frames: list[bytes]) -> None:
    for index, data in enumerate(frames):
        path = animation_frame_path(file_hash, index)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def delete_animation_frames(file_hash: str) -> None:
    shutil.rmtree(animation_frame_path(file_hash, 0).parent, ignore_errors=True)


def store_book(tmp_path: Path, filename: str) -> None:
    shutil.move(tmp_path, book_path(filename))


def store_cover(data: bytes, filename: str) -> None:
    cover_path(filename).write_bytes(data)


def delete_files(*paths: Path) -> None:
    for path in paths:
        path.unlink(missing_ok=True)
