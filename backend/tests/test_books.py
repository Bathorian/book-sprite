from pathlib import Path

from fastapi.testclient import TestClient

from booksprite.config import settings
from conftest import make_epub, make_pdf, make_png


def upload(client: TestClient, name: str, data: bytes):
    return client.post("/api/books", files={"file": (name, data, "application/octet-stream")})


def test_upload_epub_extracts_metadata_and_cover(client: TestClient, tmp_path: Path):
    response = upload(client, "test.epub", make_epub(tmp_path))
    assert response.status_code == 201, response.text
    book = response.json()
    assert book["title"] == "Test Book"
    assert book["author"] == "Jane Doe"
    assert book["format"] == "epub"
    assert book["has_cover"] is True

    cover = client.get(f"/api/books/{book['id']}/cover")
    assert cover.status_code == 200
    assert cover.content == make_png()


def test_upload_epub_without_cover(client: TestClient, tmp_path: Path):
    book = upload(client, "plain.epub", make_epub(tmp_path, cover=False)).json()
    assert book["has_cover"] is False
    assert client.get(f"/api/books/{book['id']}/cover").status_code == 404


def test_upload_pdf_extracts_metadata(client: TestClient):
    response = upload(client, "doc.pdf", make_pdf())
    assert response.status_code == 201, response.text
    book = response.json()
    assert book["title"] == "A PDF Book"
    assert book["author"] == "John Roe"
    assert book["format"] == "pdf"


def test_pdf_without_metadata_uses_filename(client: TestClient):
    book = upload(client, "My Notes.pdf", make_pdf(title=None, author=None)).json()
    assert book["title"] == "My Notes"
    assert book["author"] is None


def test_format_detected_from_content_not_extension(client: TestClient):
    book = upload(client, "misnamed.epub", make_pdf()).json()
    assert book["format"] == "pdf"


def test_rejects_non_ebook(client: TestClient):
    response = upload(client, "notes.txt", b"just some text")
    assert response.status_code == 422
    assert not any(settings.books_dir.iterdir())
    assert not any(settings.tmp_dir.iterdir())


def test_rejects_corrupt_epub(client: TestClient):
    data = b"PK\x03\x04" + b"\x00" * 26 + b"mimetypeapplication/epub+zip" + b"garbage"
    assert upload(client, "broken.epub", data).status_code == 422


def test_rejects_duplicate_upload(client: TestClient):
    first = upload(client, "doc.pdf", make_pdf()).json()
    response = upload(client, "copy.pdf", make_pdf())
    assert response.status_code == 409
    assert response.json()["detail"]["book_id"] == first["id"]


def test_rejects_oversized_upload(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "max_upload_mb", 0)
    assert upload(client, "doc.pdf", make_pdf()).status_code == 413


def test_list_search_and_sort(client: TestClient, tmp_path: Path):
    upload(client, "b.epub", make_epub(tmp_path, title="Zebra Tales", author="Alice"))
    upload(client, "a.epub", make_epub(tmp_path, title="apple pie", author="Bob"))

    titles = [b["title"] for b in client.get("/api/books", params={"sort": "title"}).json()]
    assert titles == ["apple pie", "Zebra Tales"]

    found = client.get("/api/books", params={"q": "alic"}).json()
    assert [b["title"] for b in found] == ["Zebra Tales"]


def test_update_book(client: TestClient):
    book = upload(client, "doc.pdf", make_pdf()).json()
    response = client.patch(f"/api/books/{book['id']}", json={"title": " New ", "author": ""})
    assert response.status_code == 200
    assert response.json()["title"] == "New"
    assert response.json()["author"] is None

    assert client.patch(f"/api/books/{book['id']}", json={"title": "  "}).status_code == 422


def test_download_file_marks_opened(client: TestClient):
    data = make_pdf()
    book = upload(client, "doc.pdf", data).json()
    assert book["last_opened_at"] is None

    response = client.get(f"/api/books/{book['id']}/file")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content == data
    assert client.get(f"/api/books/{book['id']}").json()["last_opened_at"] is not None


def test_delete_removes_record_and_files(client: TestClient, tmp_path: Path):
    book = upload(client, "test.epub", make_epub(tmp_path)).json()
    assert client.delete(f"/api/books/{book['id']}").status_code == 204
    assert client.get(f"/api/books/{book['id']}").status_code == 404
    assert not any(settings.books_dir.iterdir())
    assert not any(settings.covers_dir.iterdir())


def test_missing_book_returns_404(client: TestClient):
    assert client.get("/api/books/999").status_code == 404
    assert client.delete("/api/books/999").status_code == 404
