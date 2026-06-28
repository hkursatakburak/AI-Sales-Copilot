"""Yapılandırma (Settings) testleri."""

from __future__ import annotations

import pytest

from app.core.config import Settings


def test_defaults() -> None:
    settings = Settings()
    assert settings.app_name == "AI Sales Copilot"
    assert settings.environment == "development"
    assert settings.is_production is False


def test_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COPILOT_ENVIRONMENT", "production")
    monkeypatch.setenv("COPILOT_LOG_LEVEL", "DEBUG")
    settings = Settings()
    assert settings.environment == "production"
    assert settings.is_production is True
    assert settings.log_level == "DEBUG"
