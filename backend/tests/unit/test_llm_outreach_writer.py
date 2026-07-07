"""Soğuk e-posta / pitch yazarı testleri (sahte LLM sağlayıcısıyla)."""

from __future__ import annotations

import pytest

from app.application.llm_outreach_writer import LLMOutreachWriter
from app.domain.models import CompanyInsights, SellerProfile
from tests.factories import FakeLLMProvider, make_signals

_SELLER = SellerProfile(name="TestCo", offering="harika bir ürün", rep_name="Ayşe")

_INSIGHTS = CompanyInsights(
    summary="Acme bulut yazılımı geliştirir.",
    pain_points=("Destek ekibi küçük görünüyor.",),
    signals=make_signals(sector="SaaS", hiring_roles=("DevOps",)),
)


def _writer(provider: FakeLLMProvider) -> LLMOutreachWriter:
    return LLMOutreachWriter(provider, _SELLER)


@pytest.mark.asyncio
async def test_write_cold_email_returns_text() -> None:
    provider = FakeLLMProvider()
    email = await _writer(provider).write_cold_email("Acme", _INSIGHTS)
    assert email == "Üretilen metin."


@pytest.mark.asyncio
async def test_email_system_prompt_bans_cliches_and_includes_seller() -> None:
    provider = FakeLLMProvider()
    await _writer(provider).write_cold_email("Acme", _INSIGHTS)

    system = provider.last_text_kwargs["system"]
    assert "TestCo" in system  # satıcı adı
    assert "harika bir ürün" in system  # değer önerisi
    assert "Ayşe" in system  # imza
    # Klişe yasakları sistem prompt'unda olmalı
    assert "I hope this email finds you well" in system
    assert "Devrim niteliğinde" in system


@pytest.mark.asyncio
async def test_email_prompt_contains_lead_context() -> None:
    provider = FakeLLMProvider()
    await _writer(provider).write_cold_email("Acme", _INSIGHTS)

    prompt = provider.last_text_kwargs["prompt"]
    assert "Acme" in prompt
    assert "Destek ekibi küçük görünüyor." in prompt  # acı noktası
    assert "SaaS" in prompt  # sektör sinyali
    assert "DevOps" in prompt  # işe alım rolü


@pytest.mark.asyncio
async def test_write_pitch_uses_pitch_token_budget() -> None:
    provider = FakeLLMProvider()
    writer = LLMOutreachWriter(provider, _SELLER, pitch_max_tokens=321)
    await writer.write_pitch("Acme", _INSIGHTS)
    assert provider.last_text_kwargs["max_tokens"] == 321
