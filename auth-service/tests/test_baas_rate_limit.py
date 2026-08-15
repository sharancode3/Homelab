import unittest
import asyncio
from app.api.rate_limiter import InMemoryRateLimiter
from fastapi import HTTPException

class TestRateLimiter(unittest.IsolatedAsyncioTestCase):
    async def test_rate_limit_exceeded(self):
        limiter = InMemoryRateLimiter(capacity=2, refill_rate=0.0) # No refill
        
        # First 2 should pass
        await limiter.check("test_key")
        await limiter.check("test_key")
        
        # 3rd should fail
        with self.assertRaises(HTTPException) as context:
            await limiter.check("test_key")
            
        self.assertEqual(context.exception.status_code, 429)
        self.assertEqual(context.exception.headers.get("Retry-After"), "60")
        
    async def test_rate_limit_refill(self):
        limiter = InMemoryRateLimiter(capacity=2, refill_rate=10.0) # 10 tokens per second
        
        # Drain bucket
        await limiter.check("test_key")
        await limiter.check("test_key")
        
        with self.assertRaises(HTTPException):
            await limiter.check("test_key")
            
        # Wait for refill
        await asyncio.sleep(0.2) # Should refill 2 tokens
        
        # Should succeed again
        await limiter.check("test_key")
