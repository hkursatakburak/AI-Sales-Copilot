"""Kural tabanlı lead scoring motoru testleri (saf, deterministik kurallar)."""

from __future__ import annotations

from app.application.rule_based_scoring_engine import RuleBasedScoringEngine
from app.domain.models import CompanySignals, LeadTier


def _signals(**overrides) -> CompanySignals:
    base = dict(
        sector=None,
        employee_band=None,
        is_hiring=False,
        hiring_roles=(),
        growth_signals=(),
        technologies=(),
    )
    base.update(overrides)
    return CompanySignals(**base)


def test_empty_signals_score_zero_cold() -> None:
    engine = RuleBasedScoringEngine()
    score = engine.score(_signals())
    assert score.value == 0
    assert score.tier == LeadTier.COLD
    assert score.reasons  # açıklanabilirlik: "yeterli sinyal yok" gerekçesi
    assert score.reasons[0].rule == "insufficient_signals"


def test_target_sector_adds_points() -> None:
    engine = RuleBasedScoringEngine()
    score = engine.score(_signals(sector="SaaS"))
    assert score.value == 25
    assert any(r.rule == "target_sector" for r in score.reasons)


def test_non_target_sector_no_points() -> None:
    engine = RuleBasedScoringEngine()
    score = engine.score(_signals(sector="tarım"))
    assert score.value == 0


def test_employee_band_sweet_spot() -> None:
    engine = RuleBasedScoringEngine()
    assert engine.score(_signals(employee_band="51-200")).value == 30
    assert engine.score(_signals(employee_band="11-50")).value == 15
    assert engine.score(_signals(employee_band="1000+")).value == 10


def test_hiring_signal_adds_points_and_mentions_roles() -> None:
    engine = RuleBasedScoringEngine()
    score = engine.score(_signals(is_hiring=True, hiring_roles=("DevOps", "Satış")))
    reason = next(r for r in score.reasons if r.rule == "active_hiring")
    assert reason.points == 15
    assert "DevOps" in reason.explanation


def test_growth_signals_are_capped() -> None:
    engine = RuleBasedScoringEngine()
    many = ("a", "b", "c", "d", "e")  # 5 * 10 = 50, ama cap 20
    score = engine.score(_signals(growth_signals=many))
    reason = next(r for r in score.reasons if r.rule == "growth_signals")
    assert reason.points == 20


def test_score_is_clamped_to_100() -> None:
    engine = RuleBasedScoringEngine()
    score = engine.score(
        _signals(
            sector="fintech",  # 25
            employee_band="51-200",  # 30
            is_hiring=True,  # 15
            growth_signals=("x", "y", "z"),  # 20 (cap)
            technologies=("AWS", "React"),  # 10
        )
    )
    assert score.value == 100
    assert score.tier == LeadTier.HOT


def test_tiers_by_threshold() -> None:
    engine = RuleBasedScoringEngine()
    assert engine.score(_signals(sector="SaaS")).tier == LeadTier.COLD  # 25
    assert engine.score(_signals(sector="SaaS", employee_band="11-50")).tier == LeadTier.WARM  # 40
    assert engine.score(
        _signals(sector="SaaS", employee_band="51-200", is_hiring=True)
    ).tier == LeadTier.HOT  # 70


def test_every_reason_is_explainable() -> None:
    engine = RuleBasedScoringEngine()
    score = engine.score(_signals(sector="SaaS", is_hiring=True))
    for reason in score.reasons:
        assert reason.explanation  # her gerekçe boş olmamalı
        assert reason.rule
