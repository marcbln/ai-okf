import pytest

from ai_okf.agent.kb_agent import build_agent
from ai_okf.config import PrivacyError, is_loopback_url


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:1234/v1",
        "http://localhost:8080/v1",
        "http://[::1]:9000/v1",
    ],
)
def test_is_loopback_url_true(url: str) -> None:
    assert is_loopback_url(url) is True


@pytest.mark.parametrize(
    "url",
    [
        "https://opencode.ai/zen/v1",
        "https://openrouter.ai/api/v1",
        "http://10.0.0.5:1234/v1",
        "",
    ],
)
def test_is_loopback_url_false(url: str) -> None:
    assert is_loopback_url(url) is False


def test_build_agent_blocks_cloud_by_default() -> None:
    with pytest.raises(PrivacyError, match="Refusing non-local LLM endpoint"):
        build_agent(
            "opencode-zen/nemotron",
            api_base="https://opencode.ai/zen/v1",
        )


def test_build_agent_allows_cloud_when_opted_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENCODE_API_KEY", "test-key")
    agent = build_agent(
        "opencode-zen/nemotron",
        api_base="https://opencode.ai/zen/v1",
        allow_cloud=True,
    )
    assert agent is not None


def test_build_agent_allows_loopback_without_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENCODE_API_KEY", raising=False)
    agent = build_agent("local/qwen3", api_base="http://127.0.0.1:1234/v1")
    assert agent is not None
