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
    settings.tmp_dir.mkdir(parents=True, exist_ok=True)
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


def store_book(tmp_path: Path, filename: str) -> None:
    settings.books_dir.mkdir(parents=True, exist_ok=True)
    shutil.move(tmp_path, book_path(filename))


def store_cover(data: bytes, filename: str) -> None:
    settings.covers_dir.mkdir(parents=True, exist_ok=True)
    cover_path(filename).write_bytes(data)


def delete_files(*paths: Path) -> None:
    for path in paths:
        path.unlink(missing_ok=True)
