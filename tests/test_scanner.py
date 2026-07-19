from pathlib import Path

from ai_okf.core.scanner import scan_codebase


def test_scan_codebase(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('hello')")
    (tmp_path / "src" / "utils.py").write_text("def helper(): pass")
    (tmp_path / "README.md").write_text("# Project")
    files = scan_codebase(tmp_path)
    paths = [f.path for f in files]
    assert "src/main.py" in paths
    assert "src/utils.py" in paths
    assert "README.md" in paths


def test_scan_ignores_git_dir(tmp_path: Path):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("[core]")
    (tmp_path / "main.py").write_text("x = 1")
    files = scan_codebase(tmp_path)
    assert all(".git" not in f.path for f in files)


def test_scan_ignores_venv(tmp_path: Path):
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "lib.py").write_text("lib")
    (tmp_path / "main.py").write_text("x = 1")
    files = scan_codebase(tmp_path)
    assert all(".venv" not in f.path for f in files)
