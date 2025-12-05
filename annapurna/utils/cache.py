"""Redis caching utilities"""

import json
import hashlib
from typing import Optional, Any, Callable
from functools import wraps
import redis
from annapurna.config import settings


class RedisCache:
    """Redis cache manager for frequent queries"""

    def __init__(self):
        """Initialize Redis connection"""
        self.redis_client = redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=5
        )
        self.default_ttl = 3600  # 1 hour default TTL

    def generate_key(self, prefix: str, *args, **kwargs) -> str:
        """
        Generate cache key from function arguments

        Args:
            prefix: Cache key prefix (e.g., 'search', 'recipe')
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Cache key string
        """
        # Create a string representation of all arguments
        key_data = {
            'args': args,
            'kwargs': kwargs
        }

        # Hash the data for a consistent key
        key_string = json.dumps(key_data, sort_keys=True)
        key_hash = hashlib.md5(key_string.encode()).hexdigest()

        return f"annapurna:{prefix}:{key_hash}"

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        try:
            value = self.redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except (redis.RedisError, json.JSONDecodeError) as e:
            print(f"Cache get error: {str(e)}")
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set value in cache

        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
            ttl: Time to live in seconds

        Returns:
            True if successful
        """
        try:
            ttl = ttl or self.default_ttl
            value_json = json.dumps(value)
            self.redis_client.setex(key, ttl, value_json)
            return True
        except (redis.RedisError, json.JSONEncodeError) as e:
            print(f"Cache set error: {str(e)}")
            return False

    def delete(self, key: str) -> bool:
        """
        Delete key from cache

        Args:
            key: Cache key

        Returns:
            True if successful
        """
        try:
            self.redis_client.delete(key)
            return True
        except redis.RedisError as e:
            print(f"Cache delete error: {str(e)}")
            return False

    def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all keys matching a pattern

        Args:
            pattern: Redis key pattern (e.g., 'annapurna:search:*')

        Returns:
            Number of keys deleted
        """
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except redis.RedisError as e:
            print(f"Cache invalidate error: {str(e)}")
            return 0

    def flush_all(self) -> bool:
        """
        Flush all cache (use with caution!)

        Returns:
            True if successful
        """
        try:
            self.redis_client.flushdb()
            return True
        except redis.RedisError as e:
            print(f"Cache flush error: {str(e)}")
            return False

    def get_stats(self) -> dict:
        """
        Get cache statistics

        Returns:
            Dict with cache stats
        """
        try:
            info = self.redis_client.info('stats')
            return {
                'hits': info.get('keyspace_hits', 0),
                'misses': info.get('keyspace_misses', 0),
                'hit_rate': self._calculate_hit_rate(info),
                'keys': self.redis_client.dbsize()
            }
        except redis.RedisError as e:
            print(f"Cache stats error: {str(e)}")
            return {}

    def _calculate_hit_rate(self, info: dict) -> float:
        """Calculate cache hit rate"""
        hits = info.get('keyspace_hits', 0)
        misses = info.get('keyspace_misses', 0)
        total = hits + misses
        return (hits / total * 100) if total > 0 else 0.0


# Global cache instance
cache = RedisCache()


def cached(prefix: str, ttl: Optional[int] = None):
    """
    Decorator for caching function results

    Args:
        prefix: Cache key prefix
        ttl: Time to live in seconds

    Example:
        @cached('search', ttl=1800)
        def search_recipes(query, filters):
            # ... expensive operation ...
            return results
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = cache.generate_key(prefix, *args, **kwargs)

            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                print(f"Cache HIT: {cache_key}")
                return cached_result

            # Cache miss - execute function
            print(f"Cache MISS: {cache_key}")
            result = func(*args, **kwargs)

            # Store in cache
            cache.set(cache_key, result, ttl)

            return result

        # Add cache invalidation method to function
        wrapper.invalidate_cache = lambda *args, **kwargs: cache.delete(
            cache.generate_key(prefix, *args, **kwargs)
        )

        return wrapper
    return decorator


def invalidate_recipe_cache(recipe_id: str):
    """
    Invalidate all caches related to a recipe

    This should be called when a recipe is updated

    Args:
        recipe_id: Recipe UUID
    """
    patterns = [
        f"annapurna:recipe:{recipe_id}*",
        f"annapurna:search:*",  # Invalidate all searches (conservative)
    ]

    total_deleted = 0
    for pattern in patterns:
        deleted = cache.invalidate_pattern(pattern)
        total_deleted += deleted

    print(f"Invalidated {total_deleted} cache keys for recipe {recipe_id}")


def warm_cache():
    """
    Pre-populate cache with common queries

    This can be run periodically to improve cache hit rate
    """
    from annapurna.models.base import SessionLocal
    from annapurna.api.search import HybridSearch
    from annapurna.api.schemas import SearchRequest, SearchFilters

    db = SessionLocal()

    try:
        search_engine = HybridSearch(db)

        # Common search queries to warm
        common_queries = [
            "breakfast recipes",
            "dinner recipes",
            "quick recipes",
            "north indian recipes",
            "south indian recipes",
            "jain recipes",
            "vrat recipes",
            "high protein recipes",
            "diabetic friendly recipes"
        ]

        for query in common_queries:
            # Execute search (will populate cache via decorator)
            print(f"Warming cache for: {query}")
            request = SearchRequest(query=query, limit=20)
            try:
                search_engine.hybrid_search(query, None, 20, 0)
            except Exception as e:
                print(f"Error warming cache for '{query}': {str(e)}")

        print("Cache warming completed")

    finally:
        db.close()
