"""Extract title, author and cover image from ebook files."""

import logging
from dataclasses import dataclass
from pathlib import Path

import ebooklib
from ebooklib import epub
from pypdf import PdfReader

from booksprite.models import BookFormat

log = logging.getLogger(__name__)

IMAGE_EXTENSIONS = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/gif": "gif",
    "image/webp": "webp",
}


@dataclass
class Cover:
    data: bytes
    extension: str


@dataclass
class BookMetadata:
    title: str | None = None
    author: str | None = None
    cover: Cover | None = None


class InvalidBookError(ValueError):
    pass


def detect_format(path: Path) -> BookFormat:
    """Identify the format from the file's magic bytes, not its name."""
    with path.open("rb") as f:
        head = f.read(64)
    if head.startswith(b"%PDF-"):
        return BookFormat.PDF
    # EPUB is a zip whose first entry is an uncompressed "mimetype" file.
    if head.startswith(b"PK\x03\x04") and b"mimetypeapplication/epub+zip" in head:
        return BookFormat.EPUB
    raise InvalidBookError("File is not a valid EPUB or PDF")


def extract_metadata(path: Path, fmt: BookFormat) -> BookMetadata:
    try:
        if fmt is BookFormat.EPUB:
            return _extract_epub(path)
        return _extract_pdf(path)
    except InvalidBookError:
        raise
    except Exception as exc:
        raise InvalidBookError(f"Could not read {fmt.upper()} file") from exc


def _clean(value: str | None) -> str | None:
    return value.strip() or None if value else None


def _extract_epub(path: Path) -> BookMetadata:
    book = epub.read_epub(str(path), {"ignore_ncx": True})
    titles = [t for v, _ in book.get_metadata("DC", "title") if (t := _clean(v))]
    authors = [a for v, _ in book.get_metadata("DC", "creator") if (a := _clean(v))]
    return BookMetadata(
        title=titles[0] if titles else None,
        author=", ".join(authors) or None,
        cover=_epub_cover(book),
    )


def _epub_cover(book: epub.EpubBook) -> Cover | None:
    candidates = []
    # EPUB 3: manifest item with properties="cover-image".
    candidates.extend(book.get_items_of_type(ebooklib.ITEM_COVER))
    # EPUB 2: <meta name="cover" content="item-id"/>.
    for _value, attrs in book.get_metadata("OPF", "cover"):
        if item := book.get_item_with_id(attrs.get("content", "")):
            candidates.append(item)
    # Fallback: an image whose id or filename mentions "cover".
    for item in book.get_items_of_type(ebooklib.ITEM_IMAGE):
        if "cover" in (item.get_id() or "").lower() or "cover" in item.get_name().lower():
            candidates.append(item)

    for item in candidates:
        ext = IMAGE_EXTENSIONS.get(item.media_type)
        if ext and item.get_content():
            return Cover(item.get_content(), ext)
    return None


def _extract_pdf(path: Path) -> BookMetadata:
    reader = PdfReader(path)
    if reader.is_encrypted:
        raise InvalidBookError("Encrypted PDFs are not supported")
    info = reader.metadata
    return BookMetadata(
        title=_clean(info.title) if info else None,
        author=_clean(info.author) if info else None,
        cover=_pdf_cover(reader),
    )


def _pdf_cover(reader: PdfReader) -> Cover | None:
    """Use the largest embedded image on the first page, if any.

    pypdf cannot render pages, so a text-only first page yields no cover.
    """
    if not reader.pages:
        return None
    try:
        images = list(reader.pages[0].images)
    except Exception:
        log.debug("Failed to read images from PDF first page", exc_info=True)
        return None
    best = None
    for image in images:
        ext = Path(image.name).suffix.lstrip(".").lower()
        ext = "jpg" if ext == "jpeg" else ext
        if ext in IMAGE_EXTENSIONS.values() and (best is None or len(image.data) > len(best.data)):
            best = Cover(image.data, ext)
    return best
