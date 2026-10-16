from collections import defaultdict
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlmodel import Session, col, select

from booksprite.config import settings
from booksprite.db import get_session
from booksprite.models import Sprite, SpriteAnimation
from booksprite.schemas import SpriteRead
from booksprite.services import storage
from booksprite.services.sprites import (
    DIRECTIONS,
    InvalidSpriteError,
    parse_animation,
    parse_sprite,
)

router = APIRouter(prefix="/sprites", tags=["sprites"])

SessionDep = Annotated[Session, Depends(get_session)]
AnimationKind = Literal["page_turn"]

# Frames never change for a given URL, so browsers can keep them.
IMMUTABLE = {"Cache-Control": "public, max-age=31536000, immutable"}


def get_sprite_or_404(session: Session, sprite_id: int) -> Sprite:
    sprite = session.get(Sprite, sprite_id)
    if sprite is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sprite not found")
    return sprite


def _animations(session: Session, sprite_id: int) -> list[SpriteAnimation]:
    return list(session.exec(select(SpriteAnimation).where(SpriteAnimation.sprite_id == sprite_id)))


def _read(session: Session, sprite: Sprite) -> SpriteRead:
    return SpriteRead.from_model(sprite, _animations(session, sprite.id))


def _drop_unused_frames(session: Session, file_hash: str) -> None:
    """Delete stored animation frames once no animation uses them any more."""
    in_use = session.exec(select(SpriteAnimation).where(SpriteAnimation.file_hash == file_hash))
    if in_use.first() is None:
        storage.delete_animation_frames(file_hash)


@contextmanager
def _uploaded(file: UploadFile) -> Iterator[tuple[Path, str]]:
    """Save an upload to a temp file; yields (path, sha256) and cleans up afterwards."""
    try:
        tmp_path, file_hash, _size = storage.save_to_temp(
            file.file, settings.max_sprite_upload_mb * 1024 * 1024
        )
    except storage.FileTooLargeError as exc:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, str(exc)) from exc
    try:
        yield tmp_path, file_hash
    except InvalidSpriteError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    finally:
        tmp_path.unlink(missing_ok=True)


@router.post("", status_code=status.HTTP_201_CREATED)
def upload_sprite(file: UploadFile, response: Response, session: SessionDep) -> SpriteRead:
    with _uploaded(file) as (tmp_path, file_hash):
        existing = session.exec(select(Sprite).where(Sprite.file_hash == file_hash)).first()
        if existing is not None:
            response.status_code = status.HTTP_200_OK
            return _read(session, existing)

        parsed = parse_sprite(tmp_path)
        storage.store_sprite_frames(file_hash, parsed.frames)
        sprite = Sprite(
            name=Path(file.filename or "Companion").stem.replace("_", " ").strip() or "Companion",
            file_hash=file_hash,
            width=parsed.width,
            height=parsed.height,
            directions=",".join(d for d in DIRECTIONS if d in parsed.frames),
        )
        session.add(sprite)
        session.commit()
        session.refresh(sprite)
        return _read(session, sprite)


@router.get("")
def list_sprites(session: SessionDep) -> list[SpriteRead]:
    sprites = session.exec(select(Sprite).order_by(col(Sprite.added_at).desc())).all()
    by_sprite: dict[int, list[SpriteAnimation]] = defaultdict(list)
    for animation in session.exec(select(SpriteAnimation)):
        by_sprite[animation.sprite_id].append(animation)
    return [SpriteRead.from_model(s, by_sprite[s.id]) for s in sprites]


@router.get("/{sprite_id}")
def get_sprite(sprite_id: int, session: SessionDep) -> SpriteRead:
    return _read(session, get_sprite_or_404(session, sprite_id))


@router.get("/{sprite_id}/{direction}.png")
def get_sprite_frame(sprite_id: int, direction: str, session: SessionDep) -> FileResponse:
    sprite = get_sprite_or_404(session, sprite_id)
    if direction not in sprite.direction_list:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No frame for that direction")
    return FileResponse(
        storage.sprite_frame_path(sprite.file_hash, direction),
        media_type="image/png",
        headers=IMMUTABLE,
    )


@router.put("/{sprite_id}/animations/{kind}")
def upload_animation(
    sprite_id: int, kind: AnimationKind, file: UploadFile, session: SessionDep
) -> SpriteRead:
    sprite = get_sprite_or_404(session, sprite_id)
    with _uploaded(file) as (tmp_path, file_hash):
        parsed = parse_animation(tmp_path)
        storage.store_animation_frames(file_hash, parsed.frames)

        animation = session.exec(
            select(SpriteAnimation).where(
                SpriteAnimation.sprite_id == sprite_id, SpriteAnimation.kind == kind
            )
        ).first() or SpriteAnimation(sprite_id=sprite_id, kind=kind)
        replaced_hash = animation.file_hash if animation.id is not None else None
        animation.file_hash = file_hash
        animation.width = parsed.width
        animation.height = parsed.height
        animation.durations = ",".join(str(d) for d in parsed.durations)
        session.add(animation)
        session.commit()
        if replaced_hash and replaced_hash != file_hash:
            _drop_unused_frames(session, replaced_hash)
        return _read(session, sprite)


@router.delete("/{sprite_id}/animations/{kind}")
def delete_animation(sprite_id: int, kind: AnimationKind, session: SessionDep) -> SpriteRead:
    sprite = get_sprite_or_404(session, sprite_id)
    removed = [a for a in _animations(session, sprite_id) if a.kind == kind]
    removed_hashes = {a.file_hash for a in removed}
    for animation in removed:
        session.delete(animation)
    session.commit()
    for file_hash in removed_hashes:
        _drop_unused_frames(session, file_hash)
    return _read(session, sprite)


@router.get("/{sprite_id}/animations/{kind}/{index}.png")
def get_animation_frame(
    sprite_id: int, kind: AnimationKind, index: int, session: SessionDep
) -> FileResponse:
    animation = next((a for a in _animations(session, sprite_id) if a.kind == kind), None)
    if animation is None or not 0 <= index < len(animation.duration_list):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such animation frame")
    return FileResponse(
        storage.animation_frame_path(animation.file_hash, index),
        media_type="image/png",
        headers=IMMUTABLE,
    )
