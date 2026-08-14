import time
import asyncio
from collections import OrderedDict
from fastapi import HTTPException, Request

class TokenBucket:
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = float(capacity)
        self.last_refill = time.monotonic()
        self.lock = asyncio.Lock()

    async def consume(self, tokens: int = 1) -> bool:
        async with self.lock:
            now = time.monotonic()
            elapsed = now - self.last_refill
            
            self.tokens = min(float(self.capacity), self.tokens + elapsed * self.refill_rate)
            self.last_refill = now
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

class InMemoryRateLimiter:
    def __init__(self, capacity: int, refill_rate: float, max_keys: int = 10000):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.max_keys = max_keys
        self.buckets = OrderedDict()
        self.global_lock = asyncio.Lock()

    async def check(self, key: str) -> None:
        async with self.global_lock:
            if key not in self.buckets:
                if len(self.buckets) >= self.max_keys:
                    self.buckets.popitem(last=False)
                self.buckets[key] = TokenBucket(self.capacity, self.refill_rate)
            else:
                self.buckets.move_to_end(key)
            bucket = self.buckets[key]

        if not await bucket.consume(1):
            raise HTTPException(
                status_code=429,
                detail="Too Many Requests",
                headers={"Retry-After": "1"}
            )

# Data plane: 100 requests per 10 seconds (10 req/s, burst 100)
data_plane_limiter = InMemoryRateLimiter(capacity=100, refill_rate=10.0)

# Control plane: 100 requests per 10 seconds (10 req/s, burst 100)
control_plane_limiter = InMemoryRateLimiter(capacity=100, refill_rate=10.0)

async def rate_limit_api_key(request: Request):
    api_key = request.headers.get("X-Project-API-Key")
    if api_key:
        await data_plane_limiter.check(f"apikey:{api_key}")

async def rate_limit_ip(request: Request):
    ip = request.headers.get("CF-Connecting-IP") or request.headers.get("X-Forwarded-For")
    if not ip and request.client:
        ip = request.client.host
    if not ip:
        ip = "unknown"
    await control_plane_limiter.check(f"ip:{ip}")

