"""Host bazlı rate limiter testleri."""

from __future__ import annotations

import time

import pytest

from app.infrastructure.scraping.rate_limiter import HostRateLimiter


@pytest.mark.asyncio
async def test_no_wait_on_first_request() -> None:
    limiter = HostRateLimiter(0.1)
    start = time.monotonic()
    await limiter.acquire("https://a.com/x")
    assert time.monotonic() - start < 0.05


@pytest.mark.asyncio
async def test_second_request_same_host_waits() -> None:
    limiter = HostRateLimiter(0.05)
    await limiter.acquire("https://a.com/x")
    start = time.monotonic()
    await limiter.acquire("https://a.com/y")  # aynı host -> beklemeli
    assert time.monotonic() - start >= 0.05


@pytest.mark.asyncio
async def test_different_hosts_do_not_block_each_other() -> None:
    limiter = HostRateLimiter(0.2)
    await limiter.acquire("https://a.com/x")
    start = time.monotonic()
    await limiter.acquire("https://b.com/x")  # farklı host -> beklemez
    assert time.monotonic() - start < 0.1


@pytest.mark.asyncio
async def test_zero_interval_disables_limiting() -> None:
    limiter = HostRateLimiter(0.0)
    await limiter.acquire("https://a.com/x")
    start = time.monotonic()
    await limiter.acquire("https://a.com/y")
    assert time.monotonic() - start < 0.05
