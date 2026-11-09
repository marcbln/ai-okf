from fnmatch import fnmatch
from pathlib import Path
from urllib.parse import urlparse

CLI_CONTEXT_SETTINGS: dict[str, object] = {
    "help_option_names": ["-h", "--help"],
}

DEFAULT_MODEL = "opencode-zen/nemotron-3-ultra-free"
DEFAULT_OUTPUT = Path(".okf-bundle")

PROVIDER_BASE_URLS: dict[str, str] = {
    "opencode-zen": "https://opencode.ai/zen/v1",
    "opencode-go": "https://opencode.ai/zen/go/v1",
    "openrouter": "https://openrouter.ai/api/v1",
}

PROVIDER_API_KEY_ENV: dict[str, str] = {
    "opencode-zen": "OPENCODE_API_KEY",
    "opencode-go": "OPENCODE_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}

LOOPBACK_HOSTS: frozenset[str] = frozenset({"127.0.0.1", "::1", "localhost"})

CLOUD_DEFAULT_BASE = "https://opencode.ai/zen/v1"

DEFAULT_WORKERS = 4

MAX_FILE_BYTES = 512 * 1024

PROTECTED_NAME_GLOBS: tuple[str, ...] = (
    ".secrets.md",
    ".secrets",
    ".env",
    ".env.*",
    "*.env",
    "auth.json",
    ".netrc",
    ".npmrc",
    ".pypirc",
    "*credential*.json",
    "*credentials*.json",
    "*credential*.yaml",
    "*credentials*.yaml",
    "*credential*.yml",
    "*credentials*.yml",
    "*token*.json",
    "*token*.yaml",
    "*token*.yml",
    "*.pem",
    "*.key",
    "*.p12",
    "*.pfx",
    "*.keystore",
    "*.jks",
    "id_rsa*",
    "id_ed25519*",
    "id_ecdsa*",
    "id_dsa*",
)

EXTRA_TEXT_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".txt",
        ".rst",
        ".adoc",
        ".markdown",
        ".mdx",
        ".csv",
        ".tsv",
        ".xml",
        ".ini",
        ".cfg",
        ".conf",
        ".properties",
        ".gradle",
        ".tf",
        ".hcl",
        ".proto",
        ".graphql",
        ".gql",
        ".tex",
        ".org",
    }
)

KNOWN_TEXT_NAMES: frozenset[str] = frozenset(
    {
        "Makefile",
        "Dockerfile",
        "LICENSE",
        "README",
        "CHANGELOG",
        "TODO",
        ".gitignore",
        ".dockerignore",
        ".editorconfig",
        ".gitattributes",
    }
)


class PrivacyError(RuntimeError):
    """Raised when a run would contact a non-local endpoint without opt-in."""


def is_loopback_url(url: str) -> bool:
    """Return True when the URL points at the local machine."""
    if not url:
        return False
    host = (urlparse(url).hostname or "").lower()
    return host in LOOPBACK_HOSTS


def provider_of(model_name: str) -> str:
    """Return the provider prefix of a `provider/model` string."""
    return model_name.split("/", 1)[0] if "/" in model_name else "opencode-zen"


def resolve_api_base(model_name: str, api_base: str | None = None) -> str:
    """Return the explicit base URL, or the provider's default."""
    if api_base:
        return api_base
    return PROVIDER_BASE_URLS.get(provider_of(model_name), CLOUD_DEFAULT_BASE)


def is_protected_name(name: str) -> bool:
    """Return True when a filename matches a secret/credential pattern."""
    return any(fnmatch(name, pattern) for pattern in PROTECTED_NAME_GLOBS)


def is_protected_path(rel_path: str) -> bool:
    """Return True when the path's basename is protected."""
    return is_protected_name(Path(rel_path).name)
