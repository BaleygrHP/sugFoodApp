"""Caching utilities for LLM responses and expensive computations"""
import hashlib
import json
from typing import Any, Optional, Callable
from functools import wraps
import redis.asyncio as aioredis
from .logger import get_logger
from app.settings import settings

logger = get_logger(__name__)


class CacheManager:
    """Async Redis cache manager for LLM responses"""

    def __init__(self):
        self._redis: Optional[aioredis.Redis] = None
        self._enabled = True

    async def get_client(self) -> Optional[aioredis.Redis]:
        """Get or create Redis client"""
        if not self._enabled:
            return None

        if self._redis is None:
            try:
                redis_url = settings.infra.task_queue.message_broker
                # Use db=2 for caching (separate from Celery)
                redis_url = redis_url.replace("/0", "/2")
                self._redis = await aioredis.from_url(
                    redis_url,
                    encoding="utf-8",
                    decode_responses=True
                )
                # Test connection
                await self._redis.ping()
                logger.info("Redis cache initialized successfully")
            except Exception as e:
                logger.warning(f"Redis cache unavailable: {e}. Running without cache.")
                self._enabled = False
                self._redis = None

        return self._redis

    async def close(self):
        """Close Redis connection"""
        if self._redis:
            await self._redis.close()
            self._redis = None

    def _generate_key(self, prefix: str, data: dict) -> str:
        """Generate cache key from data"""
        # Sort keys for consistent hashing
        sorted_data = json.dumps(data, sort_keys=True, ensure_ascii=False)
        hash_value = hashlib.sha256(sorted_data.encode()).hexdigest()[:16]
        return f"{prefix}:{hash_value}"

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        client = await self.get_client()
        if not client:
            return None

        try:
            value = await client.get(key)
            if value:
                logger.debug(f"Cache hit: {key}")
                return json.loads(value)
            return None
        except Exception as e:
            logger.warning(f"Cache get error: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set value in cache with TTL (default 1 hour)"""
        client = await self.get_client()
        if not client:
            return False

        try:
            serialized = json.dumps(value, ensure_ascii=False)
            await client.setex(key, ttl, serialized)
            logger.debug(f"Cache set: {key} (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.warning(f"Cache set error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        client = await self.get_client()
        if not client:
            return False

        try:
            await client.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Cache delete error: {e}")
            return False

    async def get_or_compute(
        self,
        prefix: str,
        key_data: dict,
        compute_fn: Callable,
        ttl: int = 3600
    ) -> Any:
        """Get from cache or compute and store"""
        cache_key = self._generate_key(prefix, key_data)

        # Try to get from cache
        cached_value = await self.get(cache_key)
        if cached_value is not None:
            return cached_value

        # Compute value
        logger.debug(f"Cache miss: {cache_key}. Computing...")
        computed_value = await compute_fn() if callable(compute_fn) else compute_fn

        # Store in cache
        await self.set(cache_key, computed_value, ttl)

        return computed_value


# Global cache instance
_cache_manager = CacheManager()


def get_cache() -> CacheManager:
    """Get global cache manager instance"""
    return _cache_manager


def cached(prefix: str, ttl: int = 3600, key_builder: Optional[Callable] = None):
    """
    Decorator for caching async function results

    Args:
        prefix: Cache key prefix
        ttl: Time to live in seconds (default 1 hour)
        key_builder: Optional function to build cache key from args/kwargs

    Example:
        @cached(prefix="triage", ttl=1800)
        async def analyze_ticket(ticket_id: str, status: str):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache = get_cache()

            # Build cache key
            if key_builder:
                key_data = key_builder(*args, **kwargs)
            else:
                # Default: use all args and kwargs
                key_data = {
                    "args": str(args),
                    "kwargs": {k: str(v) for k, v in kwargs.items()}
                }

            # Get or compute
            async def compute():
                return await func(*args, **kwargs)

            return await cache.get_or_compute(prefix, key_data, compute, ttl)

        return wrapper
    return decorator


async def cache_similar_query(
    query: str,
    context_hash: str,
    response: str,
    ttl: int = 1800
) -> None:
    """Cache response for similar queries (30 min TTL)"""
    cache = get_cache()
    key = cache._generate_key("similar_query", {
        "query": query.lower().strip(),
        "context": context_hash
    })
    await cache.set(key, {"query": query, "response": response}, ttl)


async def get_similar_query_cache(
    query: str,
    context_hash: str
) -> Optional[str]:
    """Get cached response for similar query"""
    cache = get_cache()
    key = cache._generate_key("similar_query", {
        "query": query.lower().strip(),
        "context": context_hash
    })
    result = await cache.get(key)
    return result.get("response") if result else None
