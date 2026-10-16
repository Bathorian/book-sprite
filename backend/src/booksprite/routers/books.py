from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func
from sqlmodel import Session, col, or_, select

from booksprite.config import settings
from booksprite.db import get_session
from booksprite.models import Book, BookFormat, utcnow
from booksprite.routers.sprites import get_sprite_or_404
from booksprite.schemas import BookRead, BookSpriteUpdate, BookUpdate
from booksprite.services import storage
from booksprite.services.metadata import InvalidBookError, detect_format, extract_metadata

router = APIRouter(prefix="/books", tags=["books"])

SessionDep = Annotated[Session, Depends(get_session)]

MEDIA_TYPES = {BookFormat.EPUB: "application/epub+zip", BookFormat.PDF: "application/pdf"}
SORT_ORDER = {
    "added": col(Book.added_at).desc(),
    "title": func.lower(Book.title),
    "author": func.lower(func.coalesce(Book.author, "")),
    "opened": col(Book.last_opened_at).desc().nulls_last(),
}


def _get_book(session: Session, book_id: int) -> Book:
    book = session.get(Book, book_id)
    if book is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Book not found")
    return book


@router.post("", status_code=status.HTTP_201_CREATED)
def upload_book(file: UploadFile, session: SessionDep) -> BookRead:
    original_name = Path(file.filename or "book").name
    try:
        tmp_path, file_hash, size = storage.save_to_temp(
            file.file, settings.max_upload_mb * 1024 * 1024
        )
    except storage.FileTooLargeError as exc:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, str(exc)) from exc

    try:
        existing = session.exec(select(Book).where(Book.file_hash == file_hash)).first()
        if existing is not None:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                {"message": "This book is already in your library", "book_id": existing.id},
            )
        try:
            fmt = detect_format(tmp_path)
            meta = extract_metadata(tmp_path, fmt)
        except InvalidBookError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc

        book = Book(
            title=meta.title or Path(original_name).stem,
            author=meta.author,
            format=fmt,
            file_hash=file_hash,
            original_filename=original_name,
            file_size=size,
        )
        if meta.cover is not None:
            book.cover_filename = f"{file_hash}.{meta.cover.extension}"
            storage.store_cover(meta.cover.data, book.cover_filename)
        storage.store_book(tmp_path, book.filename)
        session.add(book)
        session.commit()
        session.refresh(book)
        return BookRead.from_model(book)
    finally:
        tmp_path.unlink(missing_ok=True)


@router.get("")
def list_books(
    session: SessionDep,
    q: Annotated[str | None, Query(max_length=200)] = None,
    sort: Literal["added", "title", "author", "opened"] = "added",
) -> list[BookRead]:
    query = select(Book)
    if q:
        pattern = f"%{q}%"
        query = query.where(or_(col(Book.title).ilike(pattern), col(Book.author).ilike(pattern)))
    query = query.order_by(SORT_ORDER[sort])
    return [BookRead.from_model(b) for b in session.exec(query)]


@router.get("/{book_id}")
def get_book(book_id: int, session: SessionDep) -> BookRead:
    return BookRead.from_model(_get_book(session, book_id))


@router.patch("/{book_id}")
def update_book(book_id: int, changes: BookUpdate, session: SessionDep) -> BookRead:
    book = _get_book(session, book_id)
    data = changes.model_dump(exclude_unset=True)
    if "title" in data:
        title = (data["title"] or "").strip()
        if not title:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Title cannot be empty")
        book.title = title
    if "author" in data:
        book.author = (data["author"] or "").strip() or None
    session.add(book)
    session.commit()
    session.refresh(book)
    return BookRead.from_model(book)


@router.put("/{book_id}/sprite")
def set_book_sprite(book_id: int, body: BookSpriteUpdate, session: SessionDep) -> BookRead:
    book = _get_book(session, book_id)
    if body.sprite_id is not None:
        get_sprite_or_404(session, body.sprite_id)
    book.sprite_id = body.sprite_id
    session.add(book)
    session.commit()
    session.refresh(book)
    return BookRead.from_model(book)


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book(book_id: int, session: SessionDep) -> None:
    book = _get_book(session, book_id)
    paths = [storage.book_path(book.filename)]
    if book.cover_filename:
        paths.append(storage.cover_path(book.cover_filename))
    session.delete(book)
    session.commit()
    storage.delete_files(*paths)


@router.get("/{book_id}/file")
def get_book_file(book_id: int, session: SessionDep) -> FileResponse:
    book = _get_book(session, book_id)
    path = storage.book_path(book.filename)
    if not path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Book file is missing")
    book.last_opened_at = utcnow()
    session.add(book)
    session.commit()
    return FileResponse(path, media_type=MEDIA_TYPES[book.format], filename=book.original_filename)


@router.get("/{book_id}/cover")
def get_book_cover(book_id: int, session: SessionDep) -> FileResponse:
    book = _get_book(session, book_id)
    if not book.cover_filename:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Book has no cover")
    path = storage.cover_path(book.cover_filename)
    if not path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Book has no cover")
    return FileResponse(path, headers={"Cache-Control": "public, max-age=86400"})
