"""LLM sağlayıcı fabrikası ve Gemini JSON ayrıştırma testleri."""

from __future__ import annotations

from types import SimpleNamespace

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


def test_gemini_parses_json_with_trailing_and_leading_text() -> None:
    text = 'İşte istediğiniz JSON:\n{"summary": "x", "n": 2}\nUmarım yardımcı olur.'
    assert GeminiLLMProvider._parse_json(text) == {"summary": "x", "n": 2}


def test_gemini_parses_fenced_json_with_language_tag() -> None:
    assert GeminiLLMProvider._parse_json('```json\n{"a": 1}\n```') == {"a": 1}


def test_gemini_max_tokens_error_message_mentions_limit() -> None:
    with pytest.raises(LLMError) as exc:
        GeminiLLMProvider._parse_json('{"summary": "yarım kal', finish_reason="MAX_TOKENS")
    assert "limit" in str(exc.value).lower()


# --- Gemini yanıt metni çıkarımı (candidates/parts) ---


def _fake_response(parts_texts: list[str], *, finish_reason=None, dot_text: str | None = None):
    parts = [SimpleNamespace(text=t) for t in parts_texts]
    content = SimpleNamespace(parts=parts)
    candidate = SimpleNamespace(content=content, finish_reason=finish_reason)
    return SimpleNamespace(candidates=[candidate], text=dot_text)


def test_gemini_extracts_text_from_parts() -> None:
    resp = _fake_response(['{"a":', ' 1}'])
    text, finish = GeminiLLMProvider._extract_text(resp)
    assert text == '{"a": 1}'
    assert finish is None


def test_gemini_extract_falls_back_to_response_text() -> None:
    # Parça yok ama response.text dolu -> ona düşülür.
    resp = SimpleNamespace(candidates=[], text="düz metin")
    text, _ = GeminiLLMProvider._extract_text(resp)
    assert text == "düz metin"


def test_gemini_extract_reports_finish_reason() -> None:
    resp = _fake_response(['{"a":1}'], finish_reason="MAX_TOKENS")
    _, finish = GeminiLLMProvider._extract_text(resp)
    assert str(finish).endswith("MAX_TOKENS")
