from please_cli.commands import normalize_command


def test_quotes_raw_current_directory_with_spaces_and_parentheses() -> None:
    cwd = "/Users/brianrandall/Dropbox/Mac (2)/Desktop/pleasefolder"
    command = "for i in {1..25}; do touch /Users/brianrandall/Dropbox/Mac (2)/Desktop/pleasefolder/$i.txt; done"

    assert normalize_command(command, cwd) == (
        "for i in {1..25}; do touch '/Users/brianrandall/Dropbox/Mac (2)/Desktop/pleasefolder'/$i.txt; done"
    )


def test_leaves_already_single_quoted_current_directory_alone() -> None:
    cwd = "/Users/brianrandall/Dropbox/Mac (2)/Desktop/pleasefolder"
    command = "ls '/Users/brianrandall/Dropbox/Mac (2)/Desktop/pleasefolder'"

    assert normalize_command(command, cwd) == command


def test_leaves_relative_paths_alone() -> None:
    assert normalize_command("for i in {1..25}; do printf '%s\n' $i > $i.txt; done", "/tmp/example") == (
        "for i in {1..25}; do printf '%s\n' $i > $i.txt; done"
    )


def test_repairs_printf_loop_missing_value() -> None:
    command = 'for i in {1..25}; do printf "%d\n" > file$i.txt; done'

    assert normalize_command(command, "/tmp/example") == (
        'for i in {1..25}; do printf "%d\n" "$i" > file$i.txt; done'
    )
