from pathlib import Path

from ai_okf.core.git_scanner import get_changes_since, get_git_summary


def test_get_git_summary_empty_dir(tmp_path: Path):
    result = get_git_summary(tmp_path)
    assert result == ""


def test_get_changes_since_empty_dir(tmp_path: Path):
    result = get_changes_since(tmp_path)
    assert result == ""
