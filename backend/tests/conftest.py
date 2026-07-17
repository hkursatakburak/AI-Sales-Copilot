"""Pytest ortak fixture'ları.

`client` fixture'ı, her test için temiz bir FastAPI uygulaması üzerinden
çalışan bir `TestClient` döndürür. TestClient gerçek bir ağ portu açmaz;
istekleri uygulama içine doğrudan iletir (hızlı ve izole).

Kimlik doğrulama (`get_current_user`) testlerde devre dışı bırakılır:
gerçek bir kullanıcı oluşturmak yerine sahte bir kullanıcı nesnesi döndürülür.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.auth import get_current_user
from app.core.config import Settings
from app.main import create_app


def _fake_user():
    user = MagicMock()
    user.email = "test@copilot.test"
    user.is_active = True
    return user


def make_test_app(settings: Settings):
    """Testlerde kullanılacak, kimlik doğrulaması devre dışı bırakılmış uygulama."""
    app = create_app(settings=settings)
    app.dependency_overrides[get_current_user] = _fake_user
    return app


@pytest.fixture
def settings() -> Settings:
    # Testlerde ortamdan/`.env`'den bağımsız, sabit ayar kullanırız.
    return Settings(environment="test", log_level="WARNING", cors_allow_origins=["*"])


@pytest.fixture
def client(settings: Settings) -> TestClient:
    return TestClient(make_test_app(settings))
