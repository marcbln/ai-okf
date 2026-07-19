import os
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from rich.console import Console

from ai_okf.agent.capabilities.code_analysis import CodebaseAnalysisCapability
from ai_okf.agent.capabilities.okf_generation import OKFGenerationCapability
from ai_okf.config import DEFAULT_MODEL, PROVIDER_API_KEY_ENV, PROVIDER_BASE_URLS

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


def _make_verbose_agent(agent: Agent[dict[str, Any], str]) -> Agent[dict[str, Any], str]:
    original_run_sync = agent.run_sync

    def verbose_run_sync(prompt: str, **kwargs: Any) -> Any:
        _console.print("[bold]───────────────────── LLM Request ─────────────────────[/bold]")
        _console.print(prompt)
        _console.print("[bold]────────────────────────────────────────────────────────[/bold]")
        result = original_run_sync(prompt, **kwargs)
        _console.print("[bold]───────────────────── LLM Response ────────────────────[/bold]")
        _console.print(str(result.output))
        _console.print("[bold]────────────────────────────────────────────────────────[/bold]")
        return result

    agent.run_sync = verbose_run_sync  # type: ignore[method-assign]
    return agent


def build_agent(
    model_name: str | None = None,
    api_base: str | None = None,
    verbose: bool = False,
) -> Agent[dict[str, Any], str]:
    model_name = model_name or DEFAULT_MODEL

    provider = "opencode-zen"
    stripped_model = model_name
    if "/" in model_name:
        provider, stripped_model = model_name.split("/", 1)

    api_base = api_base or PROVIDER_BASE_URLS.get(provider, "https://opencode.ai/zen/v1")
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

    agent = Agent(
        model,
        deps_type=dict[str, Any],
        capabilities=[CodebaseAnalysisCapability(), OKFGenerationCapability()],
    )

    if verbose:
        agent = _make_verbose_agent(agent)

    return agent
