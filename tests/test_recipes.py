from please_cli.recipes import match_recipe


def test_numbered_text_files_recipe() -> None:
    proposal = match_recipe(
        "make 25 new files in this folder that are .txt files and "
        "in each file have an increasing number, 1 - 25"
    )

    assert proposal is not None
    assert proposal.command == (
        "for i in {1..25}; do printf '%s\\n' \"$i\" > \"$(printf '%02d.txt' \"$i\")\"; done"
    )
    assert "25" in proposal.explanation


def test_numbered_text_files_recipe_ignores_missing_content_request() -> None:
    assert match_recipe("make 25 new txt files here") is None
