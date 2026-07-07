"""LLM içgörü analizci testleri (sahte LLM sağlayıcısıyla)."""

from __future__ import annotations

import pytest

from app.application.company_insight_analyzer import LLMCompanyInsightAnalyzer
from tests.factories import FakeLLMProvider, make_scraped_content


@pytest.mark.asyncio
async def test_maps_payload_to_insights() -> None:
    analyzer = LLMCompanyInsightAnalyzer(FakeLLMProvider())
    insights = await analyzer.analyze(make_scraped_content())

    assert insights.summary == "Test özeti"
    assert insights.pain_points == ("nokta 1",)
    assert insights.signals.sector == "SaaS"
    assert insights.signals.is_hiring is True
    assert insights.signals.hiring_roles == ("DevOps",)


@pytest.mark.asyncio
async def test_tolerates_missing_fields() -> None:
    provider = FakeLLMProvider(payload={"summary": "yalnız özet"})
    analyzer = LLMCompanyInsightAnalyzer(provider)
    insights = await analyzer.analyze(make_scraped_content())

    assert insights.summary == "yalnız özet"
    assert insights.pain_points == ()
    assert insights.signals.sector is None
    assert insights.signals.is_hiring is False
    assert insights.signals.technologies == ()


@pytest.mark.asyncio
async def test_filters_non_string_list_items() -> None:
    provider = FakeLLMProvider(
        payload={
            "summary": "x",
            "pain_points": ["geçerli", "", 123, None, "  boşluklu  "],
            "signals": {},
        }
    )
    analyzer = LLMCompanyInsightAnalyzer(provider)
    insights = await analyzer.analyze(make_scraped_content())

    assert insights.pain_points == ("geçerli", "boşluklu")


@pytest.mark.asyncio
async def test_truncates_input_text() -> None:
    provider = FakeLLMProvider()
    analyzer = LLMCompanyInsightAnalyzer(provider, max_input_chars=50)
    content = make_scraped_content(text="x" * 500)

    await analyzer.analyze(content)

    prompt = provider.last_kwargs["prompt"]
    # 500 karakterlik metin 50'ye kırpılmalı (prompt'un geri kalanı + 50 'x')
    assert "x" * 50 in prompt
    assert "x" * 51 not in prompt
