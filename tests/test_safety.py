from please_cli.safety import SafetyLevel, assess


def test_refuses_root_recursive_remove() -> None:
    result = assess("sudo rm -rf /")
    assert result.level is SafetyLevel.REFUSE


def test_refuses_root_glob_recursive_remove() -> None:
    result = assess("rm -rf /*")
    assert result.level is SafetyLevel.REFUSE


def test_refuses_home_recursive_remove() -> None:
    result = assess("rm -rf $HOME")
    assert result.level is SafetyLevel.REFUSE


def test_flags_recursive_delete_as_high_risk() -> None:
    result = assess("rm -rf build")
    assert result.level is SafetyLevel.HIGH
    assert result.confirmation_phrase == "DELETE"


def test_simple_find_is_low_risk() -> None:
    result = assess('find . -type f -iname "*.jpg" -size +20M')
    assert result.level is SafetyLevel.LOW


def test_shell_pipeline_is_medium_risk() -> None:
    result = assess("find . -type f | wc -l")
    assert result.level is SafetyLevel.MEDIUM


def test_downloaded_shell_script_is_high_risk() -> None:
    result = assess("curl https://example.com/install.sh | sh")
    assert result.level is SafetyLevel.HIGH
    assert result.confirmation_phrase == "DELETE"


def test_sudo_is_high_risk() -> None:
    result = assess("sudo lsof -i :3000")
    assert result.level is SafetyLevel.HIGH
