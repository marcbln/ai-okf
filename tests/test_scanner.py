from pathlib import Path

from ai_okf.config import MAX_FILE_BYTES
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


def test_scan_excludes_protected_files(tmp_path: Path):
    (tmp_path / ".secrets.md").write_text("password=123")
    (tmp_path / ".env").write_text("API_KEY=x")
    (tmp_path / ".env.local").write_text("X=1")
    (tmp_path / "auth.json").write_text("{}")
    (tmp_path / "token.json").write_text("{}")
    (tmp_path / "credentials.yaml").write_text("x: 1")
    (tmp_path / "notes.md").write_text("# Notes")

    paths = [f.path for f in scan_codebase(tmp_path)]

    assert "notes.md" in paths
    for blocked in (
        ".secrets.md",
        ".env",
        ".env.local",
        "auth.json",
        "token.json",
        "credentials.yaml",
    ):
        assert blocked not in paths


def test_scan_skips_binary_and_unknown_files(tmp_path: Path):
    (tmp_path / "image.png").write_bytes(b"\x89PNG\r\n")
    (tmp_path / "blob.bin").write_bytes(b"\x00\x01")
    (tmp_path / "main.py").write_text("x = 1")
    (tmp_path / "notes.md").write_text("# Notes")

    paths = [f.path for f in scan_codebase(tmp_path)]

    assert "main.py" in paths
    assert "notes.md" in paths
    assert "image.png" not in paths
    assert "blob.bin" not in paths


def test_scan_skips_oversized_files(tmp_path: Path):
    (tmp_path / "big.md").write_text("a" * (MAX_FILE_BYTES + 1))
    (tmp_path / "small.md").write_text("ok")

    paths = [f.path for f in scan_codebase(tmp_path)]

    assert "big.md" not in paths
    assert "small.md" in paths


def test_scan_skips_excluded_output_dir(tmp_path: Path):
    out = tmp_path / "wiki"
    out.mkdir()
    (out / "generated.md").write_text("# generated")
    (tmp_path / "notes.md").write_text("# notes")

    paths = [f.path for f in scan_codebase(tmp_path, exclude_dirs={out.resolve()})]

    assert "notes.md" in paths
    assert "wiki/generated.md" not in paths
