from please_cli.cli import parse_request_args


def test_parses_flag_after_request() -> None:
    request, dry_run, yes, model = parse_request_args(["list", "running", "processes", "--dry-run"])

    assert request == ["list", "running", "processes"]
    assert dry_run is True
    assert yes is False
    assert model is None


def test_parses_flag_before_request() -> None:
    request, dry_run, yes, model = parse_request_args(["--dry-run", "delete", "node_modules"])

    assert request == ["delete", "node_modules"]
    assert dry_run is True
    assert yes is False
    assert model is None


def test_parses_yes_and_model() -> None:
    request, dry_run, yes, model = parse_request_args(
        ["-y", "--model", "llama3.2:latest", "list", "files"]
    )

    assert request == ["list", "files"]
    assert dry_run is False
    assert yes is True
    assert model == "llama3.2:latest"


def test_parses_model_equals_form() -> None:
    _, _, _, model = parse_request_args(["what", "is", "--model=qwen3:8b", "here"])

    assert model == "qwen3:8b"


def test_request_words_only() -> None:
    request, dry_run, yes, model = parse_request_args(["find", "every", "jpg"])

    assert request == ["find", "every", "jpg"]
    assert dry_run is False
    assert yes is False
    assert model is None