from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

PHOTO_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".heic",
    ".heif",
    ".png",
    ".gif",
    ".tif",
    ".tiff",
    ".dng",
    ".raw",
    ".cr2",
    ".nef",
    ".arw",
    ".mov",
    ".mp4",
    ".m4v",
}

FILENAME_DATE_PATTERNS = (
    re.compile(r"(?P<year>20\d{2})[-_:.]?(?P<month>0[1-9]|1[0-2])[-_:.]?(?P<day>0[1-9]|[12]\d|3[01])"),
    re.compile(r"(?P<month>0[1-9]|1[0-2])[-_](?P<day>0[1-9]|[12]\d|3[01])[-_](?P<year>20\d{2})"),
)

MDLS_DATE_KEYS = (
    "kMDItemContentCreationDate",
    "kMDItemFSCreationDate",
    "kMDItemCreationDate",
)


@dataclass(frozen=True)
class PhotoMove:
    source: Path
    destination: Path
    taken_date: datetime


@dataclass(frozen=True)
class PhotoOrganizePlan:
    source_root: Path
    destination_root: Path
    moves: list[PhotoMove]
    skipped: list[Path]


def build_photo_organize_plan(root: Path, destination_root: Path | None = None) -> PhotoOrganizePlan:
    root = root.expanduser().resolve()
    destination_root = (destination_root.expanduser().resolve() if destination_root else root)
    moves: list[PhotoMove] = []
    skipped: list[Path] = []

    for source in sorted(root.iterdir()):
        if not source.is_file() or source.suffix.lower() not in PHOTO_EXTENSIONS:
            continue

        taken = date_from_filename(source.name) or date_from_mdls(source)
        if taken is None:
            skipped.append(source)
            continue

        destination_dir = destination_root / f"{taken:%Y}" / f"{taken:%m_%y}"
        destination = unique_destination(destination_dir / source.name)
        if source.resolve() == destination.resolve():
            continue
        moves.append(PhotoMove(source=source, destination=destination, taken_date=taken))

    return PhotoOrganizePlan(source_root=root, destination_root=destination_root, moves=moves, skipped=skipped)


def apply_photo_organize_plan(plan: PhotoOrganizePlan) -> None:
    for move in plan.moves:
        move.destination.parent.mkdir(parents=True, exist_ok=True)
        move.source.rename(move.destination)


def date_from_filename(name: str) -> datetime | None:
    for pattern in FILENAME_DATE_PATTERNS:
        if match := pattern.search(name):
            try:
                return datetime(
                    int(match.group("year")),
                    int(match.group("month")),
                    int(match.group("day")),
                    tzinfo=UTC,
                )
            except ValueError:
                return None
    return None


def date_from_mdls(path: Path) -> datetime | None:
    args = ["mdls", "-raw"]
    for key in MDLS_DATE_KEYS:
        args.extend(["-name", key])
    args.append(str(path))

    try:
        result = subprocess.run(
            args,
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None

    if result.returncode != 0:
        return None

    for line in result.stdout.splitlines():
        value = line.strip()
        if not value or value == "(null)":
            continue
        if parsed := parse_mdls_date(value):
            return parsed
    return None


def parse_mdls_date(value: str) -> datetime | None:
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S %z")
    except ValueError:
        pass

    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
    except ValueError:
        return None


def unique_destination(destination: Path) -> Path:
    if not destination.exists():
        return destination

    stem = destination.stem
    suffix = destination.suffix
    parent = destination.parent
    counter = 1
    while True:
        candidate = parent / f"{stem}-{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1
