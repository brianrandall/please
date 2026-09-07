from please_cli.config import Config, load_config


def test_default_config_uses_qwen() -> None:
    config = Config()

    assert config.model == "qwen3:8b"
    assert config.fallback_model == "llama3.2:latest"


def test_load_config_defaults_when_missing(tmp_path) -> None:
    config = load_config(tmp_path / "missing.yaml")

    assert config.model == "qwen3:8b"
    assert config.fallback_model == "llama3.2:latest"
    assert config.timeout_seconds == 120.0