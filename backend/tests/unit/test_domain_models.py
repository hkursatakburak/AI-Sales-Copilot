"""Alan modellerinin değişmezliği (immutability) ve doğrulama kuralları."""

from __future__ import annotations

import dataclasses

import pytest

from app.domain.models import LeadScore, LeadTier, ScoreReason


def test_lead_score_accepts_valid_range() -> None:
    score = LeadScore(value=0, tier=LeadTier.COLD)
    assert score.value == 0

    score = LeadScore(value=100, tier=LeadTier.HOT)
    assert score.value == 100


@pytest.mark.parametrize("invalid_value", [-1, 101, 200])
def test_lead_score_rejects_out_of_range(invalid_value: int) -> None:
    with pytest.raises(ValueError):
        LeadScore(value=invalid_value, tier=LeadTier.WARM)


def test_lead_score_is_immutable() -> None:
    score = LeadScore(value=50, tier=LeadTier.WARM)
    with pytest.raises(dataclasses.FrozenInstanceError):
        score.value = 99  # type: ignore[misc]


def test_score_reason_holds_explanation() -> None:
    reason = ScoreReason(rule="company_size", points=30, explanation="50-500 çalışan")
    assert reason.points == 30
    assert "çalışan" in reason.explanation
