"""SSRF koruması (`UrlGuard`) testleri."""

from __future__ import annotations

import pytest

from app.core.exceptions import ScrapeError
from app.infrastructure.scraping.url_guard import UrlGuard


@pytest.mark.parametrize(
    "ip",
    [
        "127.0.0.1",  # loopback
        "10.0.0.5",  # özel
        "192.168.1.1",  # özel
        "169.254.169.254",  # link-local (bulut metadata!)
        "0.0.0.0",  # unspecified
        "::1",  # IPv6 loopback
    ],
)
def test_is_blocked_ip_blocks_internal(ip: str) -> None:
    assert UrlGuard.is_blocked_ip(ip) is True


@pytest.mark.parametrize("ip", ["8.8.8.8", "1.1.1.1", "93.184.216.34"])
def test_is_blocked_ip_allows_public(ip: str) -> None:
    assert UrlGuard.is_blocked_ip(ip) is False


def test_validate_rejects_non_http_scheme() -> None:
    guard = UrlGuard(allow_private=True)
    with pytest.raises(ScrapeError):
        guard.validate("ftp://example.com/file")


def test_validate_rejects_missing_host() -> None:
    guard = UrlGuard(allow_private=True)
    with pytest.raises(ScrapeError):
        guard.validate("http://")


def test_validate_blocks_localhost_when_private_disallowed() -> None:
    # localhost /etc/hosts üzerinden 127.0.0.1'e çözülür (ağ gerekmez).
    guard = UrlGuard(allow_private=False)
    with pytest.raises(ScrapeError):
        guard.validate("http://localhost:8000/path")


def test_validate_allows_localhost_when_private_allowed() -> None:
    guard = UrlGuard(allow_private=True)
    guard.validate("http://localhost:8000/path")  # hata fırlatmamalı
