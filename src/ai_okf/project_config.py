import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml  # type: ignore[import-untyped]

CONFIG_FILENAME = ".okf.yaml"
VALID_PROFILES = ("code", "notes")
VALID_KEYS = {"profile", "model", "api_base", "output", "workers"}


class ConfigError(ValueError):
    """Raised when .okf.yaml is invalid or contains unknown keys."""


@dataclass(frozen=True)
class ProjectConfig:
    profile: str | None = None
    model: str | None = None
    api_base: str | None = None
    output: str | None = None
    workers: int | None = None


def load_project_config(root: Path) -> tuple[ProjectConfig, Path | None]:
    """Load `<root>/.okf.yaml`, returning the config and the path if present."""
    path = root / CONFIG_FILENAME
    if not path.exists():
        return ProjectConfig(), None
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML in {path}: {exc}") from exc
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise ConfigError(f"{path} must contain a YAML mapping")

    unknown = set(raw) - VALID_KEYS
    if unknown:
        names = ", ".join(sorted(str(key) for key in unknown))
        raise ConfigError(f"Unknown key(s) in {path}: {names}")

    profile = raw.get("profile")
    if profile is not None and profile not in VALID_PROFILES:
        raise ConfigError(f"profile must be one of {VALID_PROFILES} in {path}")

    workers = raw.get("workers")
    if workers is not None and (
        not isinstance(workers, int) or isinstance(workers, bool) or workers < 1
    ):
        raise ConfigError(f"workers must be a positive integer in {path}")

    for key in ("model", "api_base", "output"):
        value = raw.get(key)
        if value is not None and not isinstance(value, str):
            raise ConfigError(f"{key} must be a string in {path}")

    return (
        ProjectConfig(
            profile=profile,
            model=raw.get("model"),
            api_base=raw.get("api_base"),
            output=raw.get("output"),
            workers=workers,
        ),
        path,
    )


def resolve_value(
    cli_value: Any,
    env_name: str,
    file_value: Any,
    default: Any,
    *,
    env: Mapping[str, str] | None = None,
) -> tuple[Any, str]:
    """Resolve a setting by precedence: CLI > env > file > default."""
    if cli_value is not None:
        return cli_value, "cli"
    source = os.environ if env is None else env
    env_value = source.get(env_name)
    if env_value is not None and env_value != "":
        return env_value, "env"
    if file_value is not None:
        return file_value, "file"
    return default, "default"
