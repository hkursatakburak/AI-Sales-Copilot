"""LLM sağlayıcı fabrikası ve Gemini JSON ayrıştırma testleri."""

from __future__ import annotations

import pytest

from app.core.config import Settings
from app.core.exceptions import LLMError
from app.infrastructure.llm.claude_provider import ClaudeLLMProvider
from app.infrastructure.llm.factory import create_llm_provider
from app.infrastructure.llm.gemini_provider import GeminiLLMProvider


def _settings(**overrides) -> Settings:
    base = dict(environment="test", anthropic_api_key=None, gemini_api_key=None)
    base.update(overrides)
    return Settings(**base)


def test_factory_returns_claude_when_selected_with_key() -> None:
    provider = create_llm_provider(_settings(llm_provider="claude", anthropic_api_key="sk-x"))
    assert isinstance(provider, ClaudeLLMProvider)


def test_factory_returns_gemini_when_selected_with_key() -> None:
    provider = create_llm_provider(_settings(llm_provider="gemini", gemini_api_key="g-x"))
    assert isinstance(provider, GeminiLLMProvider)


def test_factory_returns_none_when_key_missing() -> None:
    assert create_llm_provider(_settings(llm_provider="claude")) is None
    assert create_llm_provider(_settings(llm_provider="gemini")) is None


def test_factory_returns_none_for_unknown_provider() -> None:
    assert create_llm_provider(_settings(llm_provider="mistral", anthropic_api_key="x")) is None


def test_factory_provider_is_case_insensitive() -> None:
    provider = create_llm_provider(_settings(llm_provider="GEMINI", gemini_api_key="g-x"))
    assert isinstance(provider, GeminiLLMProvider)


# --- Gemini JSON ayrıştırma (saf) ---


def test_gemini_parses_plain_json() -> None:
    assert GeminiLLMProvider._parse_json('{"a": 1}') == {"a": 1}


def test_gemini_strips_markdown_fences() -> None:
    assert GeminiLLMProvider._parse_json('```json\n{"a": 2}\n```') == {"a": 2}


def test_gemini_raises_on_invalid_json() -> None:
    with pytest.raises(LLMError):
        GeminiLLMProvider._parse_json("bu JSON değil")


def test_gemini_raises_when_not_object() -> None:
    with pytest.raises(LLMError):
        GeminiLLMProvider._parse_json("[1, 2, 3]")
