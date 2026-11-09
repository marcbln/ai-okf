from pathlib import Path

from ai_okf.commands.config_cmd import collect_effective_config, config_file_paths


def test_collect_effective_config_defaults(tmp_path: Path) -> None:
    entries = {
        entry.name: entry for entry in collect_effective_config(tmp_path, env={})
    }
    assert entries["profile"].value == "code"
    assert entries["profile"].source == "default"
    assert entries["privacy"].value == "local-only (cloud blocked)"
    assert entries["workers"].value == "4"


def test_collect_effective_config_from_file(tmp_path: Path) -> None:
    (tmp_path / ".okf.yaml").write_text(
        "profile: notes\n"
        "model: local/qwen3-14b\n"
        "api_base: http://127.0.0.1:11434/v1\n"
        "workers: 1\n"
    )
    entries = {
        entry.name: entry for entry in collect_effective_config(tmp_path, env={})
    }
    assert entries["profile"].value == "notes"
    assert entries["profile"].source == "file"
    assert entries["api_base"].value == "http://127.0.0.1:11434/v1"
    assert entries["workers"].value == "1"
    assert entries["workers"].source == "file"


def test_env_overrides_file(tmp_path: Path) -> None:
    (tmp_path / ".okf.yaml").write_text("model: file/model\n")
    entries = {
        entry.name: entry
        for entry in collect_effective_config(tmp_path, env={"OKF_MODEL": "env/model"})
    }
    assert entries["model"].value == "env/model"
    assert entries["model"].source == "env"


def test_config_file_paths_marks_missing(tmp_path: Path) -> None:
    paths = config_file_paths(tmp_path)
    assert paths
    assert all(isinstance(path, Path) for path, _ in paths)
    assert all(isinstance(exists, bool) for _, exists in paths)
