from pathlib import Path

from git import Repo

from ai_okf.core.git_scanner import (
    get_changed_files,
    get_changes_since,
    get_git_summary,
)


def test_get_git_summary_empty_dir(tmp_path: Path):
    result = get_git_summary(tmp_path)
    assert result == ""


def test_get_changes_since_empty_dir(tmp_path: Path):
    result = get_changes_since(tmp_path)
    assert result == ""


def test_get_changes_since_clean_repo(tmp_path: Path):
    repo = Repo.init(tmp_path)
    (tmp_path / "a.txt").write_text("x")
    repo.index.add(["a.txt"])
    repo.index.commit("init")
    assert get_changes_since(tmp_path, "HEAD") == ""


def test_get_changes_since_dirty_repo(tmp_path: Path):
    repo = Repo.init(tmp_path)
    (tmp_path / "a.txt").write_text("x")
    repo.index.add(["a.txt"])
    repo.index.commit("init")
    (tmp_path / "a.txt").write_text("y")
    assert "a.txt" in get_changes_since(tmp_path, "HEAD")


def test_get_changed_files_clean_repo(tmp_path: Path):
    repo = Repo.init(tmp_path)
    (tmp_path / "a.txt").write_text("x")
    repo.index.add(["a.txt"])
    repo.index.commit("init")
    assert get_changed_files(tmp_path, "HEAD") == []


def test_get_changed_files_dirty_repo(tmp_path: Path):
    repo = Repo.init(tmp_path)
    (tmp_path / "a.txt").write_text("x")
    repo.index.add(["a.txt"])
    repo.index.commit("init")
    (tmp_path / "a.txt").write_text("y")
    assert get_changed_files(tmp_path, "HEAD") == ["a.txt"]
