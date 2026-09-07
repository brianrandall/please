from please_cli.executor import shell_syntax_is_valid


def test_accepts_simple_command() -> None:
    assert shell_syntax_is_valid("ls -la") == (True, "")


def test_accepts_pipeline() -> None:
    assert shell_syntax_is_valid("ps -ef | grep python | head") == (True, "")


def test_rejects_broken_syntax() -> None:
    ok, error = shell_syntax_is_valid('for i in {1..5}; do echo "$i"')
    assert ok is False
    assert "done" in error or error