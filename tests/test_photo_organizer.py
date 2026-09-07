from pathlib import Path

from please_cli.photo_organizer import (
    apply_photo_organize_plan,
    build_photo_organize_plan,
    date_from_filename,
    unique_destination,
)


def test_date_from_filename_iso() -> None:
    assert date_from_filename("IMG_2026-08-17_123456.HEIC") is not None
    assert date_from_filename("IMG_2026-08-17_123456.HEIC").strftime("%Y/%m_%y") == "2026/08_26"


def test_date_from_filename_compact() -> None:
    assert date_from_filename("20260817_123456.jpg").strftime("%Y/%m_%y") == "2026/08_26"


def test_unique_destination_appends_counter(tmp_path: Path) -> None:
    destination = tmp_path / "2026" / "08_26" / "IMG.jpg"
    destination.parent.mkdir(parents=True)
    destination.write_text("existing")

    assert unique_destination(destination) == tmp_path / "2026" / "08_26" / "IMG-1.jpg"


def test_build_plan_only_moves_top_level_dated_media(tmp_path: Path) -> None:
    source = tmp_path / "IMG_2026-08-17_123456.jpg"
    source.write_text("photo")
    nested = tmp_path / "2026" / "08_26" / "IMG_2026-08-18_123456.jpg"
    nested.parent.mkdir(parents=True)
    nested.write_text("already organized")
    note = tmp_path / "notes.txt"
    note.write_text("nope")

    plan = build_photo_organize_plan(tmp_path)

    assert len(plan.moves) == 1
    assert plan.moves[0].source == source
    assert plan.moves[0].destination == tmp_path / "2026" / "08_26" / source.name


def test_apply_plan_creates_subdirectory_and_moves_file(tmp_path: Path) -> None:
    source = tmp_path / "IMG_2026-08-17.jpg"
    source.write_text("photo")
    plan = build_photo_organize_plan(tmp_path)

    apply_photo_organize_plan(plan)

    assert not source.exists()
    assert (tmp_path / "2026" / "08_26" / "IMG_2026-08-17.jpg").read_text() == "photo"


def test_build_plan_can_organize_to_parent(tmp_path: Path) -> None:
    source = tmp_path / "IMG_2026-08-17.jpg"
    source.write_text("photo")

    plan = build_photo_organize_plan(tmp_path, destination_root=tmp_path.parent)

    assert plan.destination_root == tmp_path.parent
    assert plan.moves[0].destination == tmp_path.parent / "2026" / "08_26" / source.name
