"""Kural tabanlı, açıklanabilir lead scoring motoru.

Tasarım ilkeleri (kullanıcının şartları):
- KESİNLİKLE kural tabanlı; makine öğrenmesi YOK.
- Açıklanabilir (Explainable AI): her puanın gerekçesi `ScoreReason` olarak döner.
- İleride XGBoost/LightGBM eklenebilir: bu sınıf `ScoringEngine` arayüzünü
  uygular; aynı arayüzü uygulayan bir ML motoru, DI'da bununla yer değiştirebilir.

Kurallar `ScoringConfig` ile yapılandırılabilir (hedef profil, ağırlıklar,
eşikler) — böylece kuralları koda gömmek yerine ayarlanabilir kılarız.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.interfaces import ScoringEngine
from app.domain.models import CompanySignals, LeadScore, LeadTier, ScoreReason

# Çalışan sayısı bandına verilen puanlar (B2B "sweet spot" orta ölçek).
_DEFAULT_BAND_POINTS: dict[str, int] = {
    "1-10": 5,
    "11-50": 15,
    "51-200": 30,
    "201-500": 30,
    "501-1000": 20,
    "1000+": 10,
}


@dataclass(frozen=True)
class ScoringConfig:
    target_sectors: frozenset[str] = frozenset(
        {"saas", "software", "yazılım", "teknoloji", "technology", "fintech",
         "e-ticaret", "e-commerce", "ecommerce", "ai", "yapay zeka"}
    )
    sector_points: int = 25
    band_points: dict[str, int] = field(default_factory=lambda: dict(_DEFAULT_BAND_POINTS))
    hiring_points: int = 15
    growth_points_per_signal: int = 10
    growth_points_cap: int = 20
    technology_points: int = 10
    hot_threshold: int = 70
    warm_threshold: int = 40


class RuleBasedScoringEngine(ScoringEngine):
    def __init__(self, config: ScoringConfig | None = None):
        self._config = config or ScoringConfig()

    def score(self, signals: CompanySignals) -> LeadScore:
        cfg = self._config
        reasons: list[ScoreReason] = []

        # Kural 1: Hedef sektör eşleşmesi
        if signals.sector:
            sector_lc = signals.sector.lower()
            if any(target in sector_lc for target in cfg.target_sectors):
                reasons.append(
                    ScoreReason(
                        rule="target_sector",
                        points=cfg.sector_points,
                        explanation=f"Hedef sektörde ('{signals.sector}').",
                    )
                )

        # Kural 2: Çalışan sayısı bandı
        if signals.employee_band and signals.employee_band in cfg.band_points:
            pts = cfg.band_points[signals.employee_band]
            if pts:
                reasons.append(
                    ScoreReason(
                        rule="company_size",
                        points=pts,
                        explanation=f"Çalışan bandı {signals.employee_band} (uygun ölçek).",
                    )
                )

        # Kural 3: Aktif işe alım sinyali
        if signals.is_hiring:
            detail = (
                f" ({', '.join(signals.hiring_roles[:3])})" if signals.hiring_roles else ""
            )
            reasons.append(
                ScoreReason(
                    rule="active_hiring",
                    points=cfg.hiring_points,
                    explanation=f"Aktif işe alım sinyali{detail}.",
                )
            )

        # Kural 4: Büyüme sinyalleri (üst sınırlı)
        if signals.growth_signals:
            pts = min(
                len(signals.growth_signals) * cfg.growth_points_per_signal,
                cfg.growth_points_cap,
            )
            reasons.append(
                ScoreReason(
                    rule="growth_signals",
                    points=pts,
                    explanation=(
                        f"{len(signals.growth_signals)} büyüme sinyali: "
                        f"{', '.join(signals.growth_signals[:3])}."
                    ),
                )
            )

        # Kural 5: Teknoloji ipuçları
        if signals.technologies:
            reasons.append(
                ScoreReason(
                    rule="tech_stack",
                    points=cfg.technology_points,
                    explanation=(
                        f"Teknoloji sinyali: {', '.join(signals.technologies[:3])}."
                    ),
                )
            )

        total = sum(r.points for r in reasons)
        value = max(0, min(100, total))

        if not reasons:
            reasons.append(
                ScoreReason(
                    rule="insufficient_signals",
                    points=0,
                    explanation="Puanlamaya yetecek belirgin sinyal bulunamadı.",
                )
            )

        return LeadScore(value=value, tier=self._tier(value), reasons=tuple(reasons))

    def _tier(self, value: int) -> LeadTier:
        if value >= self._config.hot_threshold:
            return LeadTier.HOT
        if value >= self._config.warm_threshold:
            return LeadTier.WARM
        return LeadTier.COLD
