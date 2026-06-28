"""Pytest ortak fixture'ları.

`client` fixture'ı, her test için temiz bir FastAPI uygulaması üzerinden
çalışan bir `TestClient` döndürür. TestClient gerçek bir ağ portu açmaz;
istekleri uygulama içine doğrudan iletir (hızlı ve izole).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def settings() -> Settings:
    # Testlerde ortamdan/`.env`'den bağımsız, sabit ayar kullanırız.
    return Settings(environment="test", log_level="WARNING", cors_allow_origins=["*"])


@pytest.fixture
def client(settings: Settings) -> TestClient:
    app = create_app(settings=settings)
    return TestClient(app)
