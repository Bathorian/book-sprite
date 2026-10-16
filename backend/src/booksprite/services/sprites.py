"""Read companion sprites (direction frames) and their animations from uploads."""

import io
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from PIL import Image, ImageSequence, UnidentifiedImageError

DIRECTIONS = (
    "south",
    "south-east",
    "east",
    "north-east",
    "north",
    "north-west",
    "west",
    "south-west",
)

MAX_FRAME_BYTES = 5 * 1024 * 1024
MAX_FRAME_SIDE = 1024
MAX_ANIMATION_FRAMES = 120
# Total decoded pixels across all frames, to bound memory for huge animations.
MAX_ANIMATION_PIXELS = 32_000_000
ANIMATION_FORMATS = {"GIF", "PNG", "WEBP"}


class InvalidSpriteError(ValueError):
    pass


@dataclass
class ParsedAnimation:
    frames: list[bytes]  # PNG bytes, in order
    durations: list[int]  # milliseconds per frame
    width: int
    height: int


@dataclass
class ParsedSprite:
    frames: dict[str, bytes]  # direction -> PNG bytes
    width: int
    height: int


def parse_sprite(path: Path) -> ParsedSprite:
    with path.open("rb") as f:
        head = f.read(8)
    if head.startswith(b"PK\x03\x04"):
        frames = _frames_from_zip(path)
    elif head.startswith(b"\x89PNG\r\n\x1a\n"):
        # A single image stands for every direction.
        frames = {"south": path.read_bytes()}
    else:
        raise InvalidSpriteError("Upload a sprite .zip or a .png image")

    normalized: dict[str, bytes] = {}
    sizes = set()
    for direction, data in frames.items():
        normalized[direction], size = _normalize_png(data)
        sizes.add(size)
    if len(sizes) > 1:
        raise InvalidSpriteError("All direction frames must be the same size")
    width, height = sizes.pop()
    return ParsedSprite(normalized, width, height)


def _frames_from_zip(path: Path) -> dict[str, bytes]:
    try:
        with zipfile.ZipFile(path) as zf:
            chosen: dict[str, zipfile.ZipInfo] = {}
            for info in zf.infolist():
                name = PurePosixPath(info.filename)
                direction = name.stem.lower()
                if info.is_dir() or name.suffix.lower() != ".png" or direction not in DIRECTIONS:
                    continue
                # Sprite exports may hold several frame sets; prefer the still "rotations".
                current = chosen.get(direction)
                if current is None or (
                    "rotations" in name.parts
                    and "rotations" not in PurePosixPath(current.filename).parts
                ):
                    chosen[direction] = info
            if not chosen:
                raise InvalidSpriteError(
                    "No direction frames (south.png, east.png, …) were found in the zip"
                )
            frames = {}
            for direction, info in chosen.items():
                # Check the declared size first so a zip bomb is never expanded.
                if info.file_size > MAX_FRAME_BYTES:
                    raise InvalidSpriteError(f"{info.filename} is too large")
                frames[direction] = zf.read(info)
            return frames
    except zipfile.BadZipFile as exc:
        raise InvalidSpriteError("The zip file is damaged") from exc


def _normalize_png(data: bytes) -> tuple[bytes, tuple[int, int]]:
    """Validate an image and re-encode it, so only clean PNG data is stored."""
    try:
        with Image.open(io.BytesIO(data)) as image:
            if image.format != "PNG":
                raise InvalidSpriteError("Sprite frames must be PNG images")
            width, height = image.size
            if max(width, height) > MAX_FRAME_SIDE:
                raise InvalidSpriteError(
                    f"Sprite frames can be at most {MAX_FRAME_SIDE}×{MAX_FRAME_SIDE} pixels"
                )
            out = io.BytesIO()
            image.convert("RGBA").save(out, "PNG")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise InvalidSpriteError("A sprite frame is not a valid PNG image") from exc
    return out.getvalue(), (width, height)


def parse_animation(path: Path) -> ParsedAnimation:
    """Split an animated GIF/PNG/WebP into PNG frames with their timings."""
    try:
        with Image.open(path) as image:
            if image.format not in ANIMATION_FORMATS:
                raise InvalidSpriteError("Upload an animated .gif (or animated .png / .webp)")
            width, height = image.size
            count = getattr(image, "n_frames", 1)
            if count < 2:
                raise InvalidSpriteError("That image isn't animated (it has only one frame)")
            if max(width, height) > MAX_FRAME_SIDE:
                raise InvalidSpriteError(
                    f"Animations can be at most {MAX_FRAME_SIDE}×{MAX_FRAME_SIDE} pixels"
                )
            if count > MAX_ANIMATION_FRAMES or count * width * height > MAX_ANIMATION_PIXELS:
                raise InvalidSpriteError("That animation has too many frames")

            frames, durations = [], []
            # Iterating composes each frame (GIF disposal etc.) into a full image.
            for frame in ImageSequence.Iterator(image):
                out = io.BytesIO()
                frame.convert("RGBA").save(out, "PNG")
                frames.append(out.getvalue())
                duration = frame.info.get("duration") or 100
                durations.append(min(max(int(duration), 20), 5000))
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise InvalidSpriteError("That file is not a valid animated image") from exc
    return ParsedAnimation(frames, durations, width, height)
