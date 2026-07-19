from pathlib import Path

CLI_CONTEXT_SETTINGS: dict[str, object] = {
    "help_option_names": ["-h", "--help"],
}

DEFAULT_MODEL = "deepseek-v4-flash-free"
DEFAULT_API_BASE = "https://opencode.ai/zen/v1"
DEFAULT_OUTPUT = Path(".okf-bundle")
