from pathlib import Path

import typer
from dotenv import load_dotenv

from ai_okf.commands.init_cmd import init_command
from ai_okf.commands.update_cmd import update_command
from ai_okf.config import CLI_CONTEXT_SETTINGS

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env.local")

app = typer.Typer(
    context_settings=CLI_CONTEXT_SETTINGS,
    no_args_is_help=True,
    name="okf",
    help=(
        "OKF Knowledge Base Agent — explore codebases and generate "
        "structured knowledge bundles."
    ),
)

app.command(name="init")(init_command)
app.command(name="update")(update_command)
