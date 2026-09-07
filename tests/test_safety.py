from pathlib import Path

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


def test_ps_ef_is_low_risk() -> None:
    result = assess("ps -ef")
    assert result.level is SafetyLevel.LOW


def test_recursive_copy_is_high_risk() -> None:
    result = assess("cp -r src dest")
    assert result.level is SafetyLevel.HIGH
    assert result.confirmation_phrase == "DELETE"


def test_find_exec_nested_mv_is_high_risk() -> None:
    result = assess("find . -type f -name '*.txt' -exec bash -c 'mv \"${@}\" \"${@//.txt/.md}\"' _ {} +")
    assert result.level is SafetyLevel.HIGH
    assert result.confirmation_phrase == "DELETE"


def test_find_delete_is_high_risk() -> None:
    result = assess("find . -name '*.log' -delete")
    assert result.level is SafetyLevel.HIGH
    assert result.confirmation_phrase == "DELETE"


def test_mv_inside_pipeline_is_high_risk() -> None:
    result = assess("find . -name '*.bak' -print0 | xargs -0 mv -t backup/")
    assert result.level is SafetyLevel.HIGH


def test_read_only_for_loop_is_not_high_risk() -> None:
    result = assess("for f in *.txt; do echo \"$f\"; done")
    assert result.level in {SafetyLevel.LOW, SafetyLevel.MEDIUM}


def test_grep_for_word_rm_is_not_high_risk() -> None:
    result = assess("ls -1 | grep 'rm'")
    assert result.level is SafetyLevel.MEDIUM
    assert result.confirmation_phrase is None


def test_grep_for_word_cp_is_low_risk() -> None:
    result = assess("grep -rl 'cp' .")
    assert result.level is SafetyLevel.LOW


def test_shell_c_body_verbs_are_high_risk() -> None:
    result = assess("sh -c 'rm -rf target'")
    assert result.level is SafetyLevel.HIGH
    assert result.confirmation_phrase == "DELETE"


def test_pkill_is_medium_risk() -> None:
    result = assess("pkill -f 'firefox'")
    assert result.level is SafetyLevel.MEDIUM
    assert result.confirmation_phrase is None


def test_refuses_separate_r_and_f_flags_on_home() -> None:
    result = assess("rm -r -f ~/Downloads/node_modules")
    assert result.level is SafetyLevel.REFUSE


def test_refuses_literal_home_path() -> None:
    result = assess(f"rm -rf {Path.home()}/Downloads/cache")
    assert result.level is SafetyLevel.REFUSE


def test_refuses_home_expansion_variant() -> None:
    result = assess("rm -rf $HOME/./*")
    assert result.level is SafetyLevel.REFUSE


def test_refuses_find_exec_delete_into_home() -> None:
    result = assess("find . -name '*.log' -exec rm -rf ~/tmp {} +")
    assert result.level is SafetyLevel.REFUSE


def test_narrow_remove_outside_home_is_not_refused() -> None:
    result = assess("rm -rf build")
    assert result.level is SafetyLevel.HIGH
    assert result.confirmation_phrase == "DELETE"
