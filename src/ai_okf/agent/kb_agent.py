import os
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.settings import ModelSettings
from rich.console import Console

from ai_okf.agent.capabilities.code_analysis import (
    CodebaseAnalysisCapability,
    NotesAnalysisCapability,
)
from ai_okf.agent.capabilities.okf_generation import (
    NotesOKFGenerationCapability,
    OKFGenerationCapability,
)
from ai_okf.config import (
    DEFAULT_MODEL,
    PROVIDER_API_KEY_ENV,
    PrivacyError,
    is_loopback_url,
    resolve_api_base,
)

_console = Console()


def _resolve_api_key(provider: str) -> str:
    env_var = PROVIDER_API_KEY_ENV.get(provider)
    if env_var is None:
        env_var = "OPENCODE_API_KEY"
    key = os.environ.get(env_var) or ""
    if not key:
        raise RuntimeError(
            f"Missing API key: set {env_var} in .env.local "
            f"(needed for provider '{provider}')"
        )
    return key


def _make_verbose_agent(
    agent: Agent[dict[str, Any], str],
) -> Agent[dict[str, Any], str]:
    original_run_sync = agent.run_sync

    def verbose_run_sync(prompt: str, **kwargs: Any) -> Any:
        _console.print("[bold]───── LLM Request ─────[/bold]")
        _console.print(prompt)
        _console.print("[bold]───────────────────────[/bold]")
        result = original_run_sync(prompt, **kwargs)
        _console.print("[bold]───── LLM Response ────[/bold]")
        _console.print(str(result.output))
        _console.print("[bold]───────────────────────[/bold]")
        return result

    agent.run_sync = verbose_run_sync  # type: ignore[assignment, method-assign]
    return agent


def build_agent(
    model_name: str | None = None,
    api_base: str | None = None,
    verbose: bool = False,
    allow_cloud: bool = False,
    profile: str = "code",
    max_tokens: int = 2048,
    timeout: float = 240.0,
) -> Agent[dict[str, Any], str]:
    model_name = model_name or DEFAULT_MODEL

    provider = "opencode-zen"
    stripped_model = model_name
    if "/" in model_name:
        provider, stripped_model = model_name.split("/", 1)

    api_base = resolve_api_base(model_name, api_base)
    local = is_loopback_url(api_base)
    if not local and not allow_cloud:
        raise PrivacyError(
            f"Refusing non-local LLM endpoint '{api_base}'. "
            "Point --api-base at a loopback server (e.g. "
            "http://127.0.0.1:1234/v1), or pass --cloud to allow "
            "sending data off this machine."
        )

    if local:
        env_var = PROVIDER_API_KEY_ENV.get(provider, "OPENCODE_API_KEY")
        api_key = os.environ.get(env_var) or "local"
    else:
        api_key = _resolve_api_key(provider)

    if verbose:
        _console.print(f"[dim]Model:[/dim] [cyan]{model_name}[/cyan]")
        _console.print(f"[dim]Provider:[/dim] [cyan]{provider}[/cyan]")
        _console.print(f"[dim]API Base:[/dim] [cyan]{api_base}[/cyan]")

    model = OpenAIChatModel(
        stripped_model,
        provider=OpenAIProvider(
            base_url=f"{api_base.rstrip('/')}/",
            api_key=api_key,
        ),
    )

    if profile == "notes":
        capabilities = [NotesAnalysisCapability(), NotesOKFGenerationCapability()]
    else:
        capabilities = [CodebaseAnalysisCapability(), OKFGenerationCapability()]

    agent = Agent(
        model,
        deps_type=dict[str, Any],
        capabilities=capabilities,
        model_settings=ModelSettings(
            max_tokens=max_tokens,
            timeout=timeout,
            extra_body={"reasoning_effort": "none"} if local else None,
        ),
    )

    if verbose:
        agent = _make_verbose_agent(agent)

    return agent
