import os
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from ai_okf.agent.capabilities.code_analysis import CodebaseAnalysisCapability
from ai_okf.agent.capabilities.okf_generation import OKFGenerationCapability
from ai_okf.config import DEFAULT_MODEL, PROVIDER_API_KEY_ENV, PROVIDER_BASE_URLS


def _resolve_api_key(provider: str) -> str:
    env_var = PROVIDER_API_KEY_ENV.get(provider)
    if env_var:
        return os.environ.get(env_var, "")
    return os.environ.get("OPENCODE_API_KEY", "")


def build_agent(model_name: str | None = None, api_base: str | None = None) -> Agent[dict[str, Any], str]:
    model_name = model_name or DEFAULT_MODEL

    provider = "opencode-zen"
    stripped_model = model_name
    if "/" in model_name:
        provider, stripped_model = model_name.split("/", 1)

    api_base = api_base or PROVIDER_BASE_URLS.get(provider, "https://opencode.ai/zen/v1")
    api_key = _resolve_api_key(provider)

    model = OpenAIChatModel(
        stripped_model,
        provider=OpenAIProvider(
            base_url=f"{api_base.rstrip('/')}/",
            api_key=api_key,
        ),
    )

    return Agent(
        model,
        deps_type=dict[str, Any],
        capabilities=[CodebaseAnalysisCapability(), OKFGenerationCapability()],
    )
