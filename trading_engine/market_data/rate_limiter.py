"""Async rate limiter implementing the Token Bucket algorithm for market data providers."""

import asyncio
import time
from typing import Optional


class AsyncTokenBucketRateLimiter:
    """Thread-safe and async-safe token bucket rate limiter.

    Enforces that calls do not exceed `rate_limit_per_second`.
    """

    def __init__(self, rate_limit_per_second: float = 3.0, capacity: Optional[float] = None) -> None:
        if rate_limit_per_second <= 0:
            raise ValueError("Rate limit must be greater than 0")
        self.rate = rate_limit_per_second
        self.capacity = capacity if capacity is not None else rate_limit_per_second
        self.tokens = self.capacity
        self.last_updated = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: float = 1.0) -> None:
        """Acquire `tokens`, asynchronously sleeping if bucket is depleted."""
        async with self._lock:
            while True:
                now = time.monotonic()
                elapsed = now - self.last_updated
                self.last_updated = now

                # Replenish tokens
                self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)

                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return

                # Calculate required sleep duration
                missing_tokens = tokens - self.tokens
                sleep_seconds = missing_tokens / self.rate
                await asyncio.sleep(sleep_seconds)
