from pathlib import Path
from unittest.mock import patch

from ai_okf.agent.capabilities.code_analysis import (
    find_files_matching,
    read_file_content,
    search_text_in_files,
)
from ai_okf.models.okf import CodebaseFile


def _make_ctx(root: str) -> object:
    class FakeCtx:
        deps = {"root": root}
        model = None
        usage = None

    return FakeCtx()


@patch("ai_okf.agent.capabilities.code_analysis.scan_codebase")
def test_find_files_matching(mock_scan, tmp_path: Path):
    mock_scan.return_value = [
        CodebaseFile(path="src/auth.py", language="Python", size_bytes=20),
        CodebaseFile(path="src/main.py", language="Python", size_bytes=20),
        CodebaseFile(path="tests/test_auth.py", language="Python", size_bytes=25),
        CodebaseFile(path=".venv/lib.py", language="Python", size_bytes=10),
    ]

    ctx = _make_ctx(str(tmp_path))

    results_sub = find_files_matching(ctx, "auth")
    assert any("src/auth.py" in r for r in results_sub)
    assert any("tests/test_auth.py" in r for r in results_sub)
    assert not any("main.py" in r for r in results_sub)

    results_glob = find_files_matching(ctx, "*.py")
    paths = list(results_glob)
    assert "src/main.py" in paths
    assert "src/auth.py" in paths


@patch("ai_okf.agent.capabilities.code_analysis.scan_codebase")
def test_find_files_matching_substring(mock_scan, tmp_path: Path):
    mock_scan.return_value = [
        CodebaseFile(path="src/user_service.py", language="Python", size_bytes=15),
        CodebaseFile(path="src/order_service.py", language="Python", size_bytes=15),
    ]

    ctx = _make_ctx(str(tmp_path))

    results = find_files_matching(ctx, "user")
    assert len(results) == 1
    assert "user_service.py" in results[0]


@patch("ai_okf.agent.capabilities.code_analysis.scan_codebase")
def test_search_text_in_files(mock_scan, tmp_path: Path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "auth.py").write_text("class AuthService:\n    def login(self): pass")
    (src / "main.py").write_text("from auth import AuthService\n# todo: implementation")

    mock_scan.return_value = [
        CodebaseFile(path="src/auth.py", language="Python", size_bytes=40),
        CodebaseFile(path="src/main.py", language="Python", size_bytes=42),
    ]

    ctx = _make_ctx(str(tmp_path))

    results = search_text_in_files(ctx, "AuthService")
    assert len(results) == 2
    assert any("auth.py:1: class AuthService" in r for r in results)
    assert any("main.py:1: from auth import AuthService" in r for r in results)

    results_filtered = search_text_in_files(ctx, "AuthService", file_pattern="*main.py")
    assert len(results_filtered) == 1
    assert any("main.py:1: from auth import AuthService" in r for r in results_filtered)
    assert not any("auth.py" in r for r in results_filtered)


def test_read_file_content_edge_cases(tmp_path: Path):
    ctx = _make_ctx(str(tmp_path))

    assert read_file_content(ctx, "nonexistent.py") == ""

    large_file = tmp_path / "large.txt"
    large_file.write_text("a" * 105_000)
    content = read_file_content(ctx, "large.txt")
    assert "[truncated at 100KB]" in content
