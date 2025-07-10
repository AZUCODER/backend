"""
Cache management endpoints for frontend Redis integration.

This module provides endpoints for frontend applications to interact with
Redis cache for enhanced state management and performance optimization.
"""

from typing import Any, Optional
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.services.redis_service import redis_service
from app.dependencies import require_role
from app.models.user import UserRole

router = APIRouter()


class CacheSetRequest(BaseModel):
    key: str
    value: Any
    ttl: Optional[int] = 300  # Default 5 minutes


class CacheClearRequest(BaseModel):
    pattern: str = "frontend:*"


@router.post("/cache/set")
async def set_cache(
    request: CacheSetRequest,
    _: Any = Depends(require_role(UserRole.USER))
):
    """
    Set a cache entry in Redis.
    
    Args:
        request: Cache set request with key, value, and optional TTL
        
    Returns:
        Success response
    """
    try:
        success = redis_service.set(request.key, request.value, request.ttl)
        if success:
            return {"success": True, "message": "Cache entry set successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to set cache entry"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cache operation failed: {str(e)}"
        )


@router.get("/cache/get/{key:path}")
async def get_cache(
    key: str,
    _: Any = Depends(require_role(UserRole.USER))
):
    """
    Get a cache entry from Redis.
    
    Args:
        key: Cache key to retrieve
        
    Returns:
        Cache data if found
    """
    try:
        data = redis_service.get(key)
        if data is not None:
            return {"success": True, "data": data}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cache entry not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cache operation failed: {str(e)}"
        )


@router.delete("/cache/delete/{key:path}")
async def delete_cache(
    key: str,
    _: Any = Depends(require_role(UserRole.USER))
):
    """
    Delete a cache entry from Redis.
    
    Args:
        key: Cache key to delete
        
    Returns:
        Success response
    """
    try:
        success = redis_service.delete(key)
        if success:
            return {"success": True, "message": "Cache entry deleted successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete cache entry"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cache operation failed: {str(e)}"
        )


@router.post("/cache/clear")
async def clear_cache(
    request: CacheClearRequest,
    _: Any = Depends(require_role(UserRole.USER))
):
    """
    Clear cache entries matching a pattern.
    
    Args:
        request: Cache clear request with pattern
        
    Returns:
        Success response with number of cleared entries
    """
    try:
        success = redis_service.clear_cache(request.pattern)
        if success:
            return {"success": True, "message": "Cache cleared successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to clear cache"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cache operation failed: {str(e)}"
        )


@router.get("/cache/stats")
async def get_cache_stats(
    _: Any = Depends(require_role(UserRole.ADMIN))
):
    """
    Get cache statistics (Admin only).
    
    Returns:
        Cache statistics including memory usage, keys, etc.
    """
    try:
        if not redis_service.is_connected():
            return {
                "success": False,
                "message": "Redis not connected",
                "stats": {
                    "connected": False,
                    "memory_usage": 0,
                    "total_keys": 0,
                    "frontend_keys": 0
                }
            }

        # Get Redis info
        client = redis_service.client
        info = client.info()
        
        # Count frontend keys
        frontend_keys = len(client.keys("frontend:*"))
        
        stats = {
            "connected": True,
            "memory_usage": info.get("used_memory_human", "0B"),
            "total_keys": info.get("db0", {}).get("keys", 0),
            "frontend_keys": frontend_keys,
            "redis_version": info.get("redis_version", "unknown"),
            "uptime": info.get("uptime_in_seconds", 0)
        }
        
        return {"success": True, "stats": stats}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cache stats: {str(e)}"
        )


@router.get("/cache/keys/{pattern:path}")
async def list_cache_keys(
    pattern: str = "frontend:*",
    _: Any = Depends(require_role(UserRole.ADMIN))
):
    """
    List cache keys matching a pattern (Admin only).
    
    Args:
        pattern: Pattern to match keys
        
    Returns:
        List of matching keys
    """
    try:
        if not redis_service.is_connected():
            return {"success": False, "message": "Redis not connected", "keys": []}

        client = redis_service.client
        keys = client.keys(pattern)
        
        # Get TTL for each key
        key_info = []
        for key in keys[:100]:  # Limit to 100 keys for performance
            ttl = client.ttl(key)
            key_info.append({
                "key": key,
                "ttl": ttl,
                "expires_in": f"{ttl}s" if ttl > 0 else "no expiration"
            })
        
        return {"success": True, "keys": key_info}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list cache keys: {str(e)}"
        ) 