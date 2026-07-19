from pathlib import Path

CLI_CONTEXT_SETTINGS: dict[str, object] = {
    "help_option_names": ["-h", "--help"],
}

DEFAULT_MODEL = "opencode-zen/deepseek-v4-flash-free"
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
