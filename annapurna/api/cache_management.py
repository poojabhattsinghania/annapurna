"""API endpoints for cache management"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from annapurna.utils.cache import cache, warm_cache, invalidate_recipe_cache

router = APIRouter()


class CacheStats(BaseModel):
    hits: int
    misses: int
    hit_rate: float
    total_keys: int


@router.get("/stats", response_model=CacheStats)
def get_cache_stats():
    """Get cache statistics"""
    stats = cache.get_stats()

    return CacheStats(
        hits=stats.get('hits', 0),
        misses=stats.get('misses', 0),
        hit_rate=round(stats.get('hit_rate', 0.0), 2),
        total_keys=stats.get('keys', 0)
    )


@router.post("/warm")
def warm_cache_endpoint():
    """Warm cache with common queries"""
    try:
        warm_cache()
        return {
            'status': 'success',
            'message': 'Cache warming completed'
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/invalidate/recipe/{recipe_id}")
def invalidate_recipe_cache_endpoint(recipe_id: str):
    """Invalidate all caches related to a specific recipe"""
    try:
        invalidate_recipe_cache(recipe_id)
        return {
            'status': 'success',
            'message': f'Cache invalidated for recipe {recipe_id}'
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/invalidate/pattern")
def invalidate_pattern(pattern: str):
    """Invalidate all cache keys matching a pattern"""
    try:
        deleted = cache.invalidate_pattern(f"annapurna:{pattern}")
        return {
            'status': 'success',
            'keys_deleted': deleted,
            'pattern': pattern
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/flush")
def flush_cache():
    """Flush entire cache (use with caution!)"""
    try:
        cache.flush_all()
        return {
            'status': 'success',
            'message': 'Cache flushed successfully'
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/keys")
def list_cache_keys(pattern: str = "*", limit: int = 100):
    """List cache keys matching a pattern"""
    try:
        keys = cache.redis_client.keys(f"annapurna:{pattern}")[:limit]
        return {
            'total': len(keys),
            'keys': keys
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
