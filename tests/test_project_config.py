from pathlib import Path

import pytest

from ai_okf.project_config import (
    ConfigError,
    ProjectConfig,
    load_project_config,
    resolve_value,
)


def test_load_missing_config(tmp_path: Path) -> None:
    config, path = load_project_config(tmp_path)
    assert config == ProjectConfig()
    assert path is None


def test_load_valid_config(tmp_path: Path) -> None:
    (tmp_path / ".okf.yaml").write_text(
        "profile: notes\n"
        "model: local/qwen3-14b\n"
        "api_base: http://127.0.0.1:11434/v1\n"
        "output: wiki\n"
        "workers: 1\n"
    )
    config, path = load_project_config(tmp_path)
    assert path == tmp_path / ".okf.yaml"
    assert config.profile == "notes"
    assert config.model == "local/qwen3-14b"
    assert config.api_base == "http://127.0.0.1:11434/v1"
    assert config.output == "wiki"
    assert config.workers == 1


def test_unknown_key_raises(tmp_path: Path) -> None:
    (tmp_path / ".okf.yaml").write_text("profil: notes\n")
    with pytest.raises(ConfigError, match="Unknown key"):
        load_project_config(tmp_path)


def test_invalid_profile_raises(tmp_path: Path) -> None:
    (tmp_path / ".okf.yaml").write_text("profile: blog\n")
    with pytest.raises(ConfigError, match="profile must be one of"):
        load_project_config(tmp_path)


def test_invalid_workers_raises(tmp_path: Path) -> None:
    (tmp_path / ".okf.yaml").write_text("workers: 0\n")
    with pytest.raises(ConfigError, match="workers must be a positive integer"):
        load_project_config(tmp_path)


def test_resolve_value_precedence() -> None:
    env = {"OKF_MODEL": "env/model"}
    result = resolve_value("cli/model", "OKF_MODEL", "file/model", "default", env=env)
    assert result == ("cli/model", "cli")
    assert resolve_value(None, "OKF_MODEL", "file/model", "default", env=env) == (
        "env/model",
        "env",
    )
    assert resolve_value(None, "OKF_MODEL", "file/model", "default", env={}) == (
        "file/model",
        "file",
    )
    assert resolve_value(None, "OKF_MODEL", None, "default", env={}) == (
        "default",
        "default",
    )
