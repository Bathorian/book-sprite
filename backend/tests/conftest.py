import io
import struct
import zlib
from collections.abc import Iterator
from pathlib import Path

import pytest
from ebooklib import epub
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from booksprite.config import settings
from booksprite.main import app


def make_png() -> bytes:
    """A valid 1x1 PNG."""

    def chunk(kind: bytes, data: bytes) -> bytes:
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    idat = zlib.compress(b"\x00\xff\x00\x00")
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


def make_epub(
    tmp_path: Path, title: str = "Test Book", author: str = "Jane Doe", cover: bool = True
) -> bytes:
    book = epub.EpubBook()
    book.set_identifier(f"id-{title}")
    book.set_title(title)
    book.set_language("en")
    book.add_author(author)
    if cover:
        book.set_cover("cover.png", make_png())
    chapter = epub.EpubHtml(title="One", file_name="ch1.xhtml", lang="en")
    chapter.content = "<h1>One</h1><p>Hello.</p>"
    book.add_item(chapter)
    book.toc = [chapter]
    book.spine = ["nav", chapter]
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    path = tmp_path / f"{title}.epub"
    epub.write_epub(str(path), book)
    return path.read_bytes()


def make_pdf(title: str | None = "A PDF Book", author: str | None = "John Roe") -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    metadata = {}
    if title:
        metadata["/Title"] = title
    if author:
        metadata["/Author"] = author
    if metadata:
        writer.add_metadata(metadata)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setattr(settings, "data_dir", tmp_path / "data")
    with TestClient(app) as test_client:
        yield test_client
