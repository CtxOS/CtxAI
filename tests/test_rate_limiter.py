import pytest
import time
from ctxai.helpers.rate_limiter import RateLimiter


class TestRateLimiter:
    @pytest.fixture
    def limiter(self):
        return RateLimiter(seconds=60, requests=10, tokens=100)

    def test_init_default(self):
        limiter = RateLimiter()
        assert limiter.timeframe == 60
        assert limiter.limits == {}

    def test_init_with_limits(self, limiter):
        assert limiter.timeframe == 60
        assert limiter.limits["requests"] == 10
        assert limiter.limits["tokens"] == 100

    def test_init_with_invalid_values(self):
        limiter = RateLimiter(seconds=30, requests="invalid", tokens=None)
        assert limiter.limits["requests"] == 0
        assert limiter.limits["tokens"] == 0

    @pytest.mark.asyncio
    async def test_add_single(self, limiter):
        limiter.add(requests=1)
        total = await limiter.get_total("requests")
        assert total == 1

    @pytest.mark.asyncio
    async def test_add_multiple(self, limiter):
        limiter.add(requests=1, tokens=50)
        req_total = await limiter.get_total("requests")
        tok_total = await limiter.get_total("tokens")
        assert req_total == 1
        assert tok_total == 50

    @pytest.mark.asyncio
    async def test_add_unknown_key(self, limiter):
        limiter.add(unknown_key=5)
        total = await limiter.get_total("unknown_key")
        assert total == 5

    @pytest.mark.asyncio
    async def test_get_total_unknown_key(self, limiter):
        total = await limiter.get_total("nonexistent")
        assert total == 0

    @pytest.mark.asyncio
    async def test_cleanup_removes_old(self, limiter):
        limiter.add(requests=5)
        limiter.values["requests"].append((time.time() - 120, 5))  # Add old entry
        await limiter.cleanup()
        total = await limiter.get_total("requests")
        assert total == 5

    @pytest.mark.asyncio
    async def test_cleanup_preserves_recent(self, limiter):
        limiter.add(requests=5)
        await limiter.cleanup()
        total = await limiter.get_total("requests")
        assert total == 5
