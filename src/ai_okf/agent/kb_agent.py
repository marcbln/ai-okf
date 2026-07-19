import os
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from ai_okf.agent.capabilities.code_analysis import CodebaseAnalysisCapability
from ai_okf.agent.capabilities.okf_generation import OKFGenerationCapability
from ai_okf.config import DEFAULT_API_BASE, DEFAULT_MODEL


def build_agent(model_name: str | None = None, api_base: str | None = None) -> Agent[dict[str, Any], str]:
    model_name = model_name or os.environ.get("OKF_MODEL", DEFAULT_MODEL)
    api_base = api_base or os.environ.get("OKF_API_BASE", DEFAULT_API_BASE)
    api_key = os.environ.get("OKF_API_KEY", "no-key-required")

    model = OpenAIChatModel(
        model_name,
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
