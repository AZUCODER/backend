"""
Redis service for caching and session management.

This module provides a Redis service class for handling caching operations,
session storage, and other Redis-based functionality.
"""

import json
import logging
from typing import Any, Optional, Union
from redis import Redis
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class RedisService:
    """
    Redis service for caching and session management.
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize Redis connection.
        
        Args:
            redis_url: Redis connection URL. If None, uses settings.REDIS_URL
        """
        self.redis_url = redis_url or getattr(settings, 'REDIS_URL', 'redis://localhost:6379')
        self.client: Optional[Redis] = None
        self._connect()
    
    def _connect(self) -> None:
        """Establish Redis connection."""
        try:
            if self.redis_url:
                self.client = Redis.from_url(
                    self.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True
                )
                # Test connection
                self.client.ping()
                logger.info("Redis connection established successfully")
            else:
                logger.warning("REDIS_URL not configured, Redis functionality disabled")
                self.client = None
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.client = None
    
    def is_connected(self) -> bool:
        """Check if Redis is connected."""
        if not self.client:
            return False
        try:
            self.client.ping()
            return True
        except Exception:
            # Try to reconnect if connection is lost
            self._connect()
            if self.client:
                try:
                    self.client.ping()
                    return True
                except Exception:
                    pass
            return False
    
    def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """
        Set a key-value pair in Redis.
        
        Args:
            key: Redis key
            value: Value to store (will be JSON serialized)
            expire: Expiration time in seconds
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_connected():
            return False
        
        try:
            serialized_value = json.dumps(value) if not isinstance(value, (str, int, float, bool)) else value
            result = self.client.set(key, serialized_value, ex=expire)
            return bool(result)
        except Exception as e:
            logger.error(f"Error setting Redis key {key}: {e}")
            return False
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from Redis.
        
        Args:
            key: Redis key
            
        Returns:
            The value if found, None otherwise
        """
        if not self.is_connected():
            return None
        
        try:
            value = self.client.get(key)
            if value is None:
                return None
            
            # Try to deserialize JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        except Exception as e:
            logger.error(f"Error getting Redis key {key}: {e}")
            return None
    
    def delete(self, key: str) -> bool:
        """
        Delete a key from Redis.
        
        Args:
            key: Redis key to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_connected():
            return False
        
        try:
            result = self.client.delete(key)
            return bool(result)
        except Exception as e:
            logger.error(f"Error deleting Redis key {key}: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """
        Check if a key exists in Redis.
        
        Args:
            key: Redis key to check
            
        Returns:
            bool: True if key exists, False otherwise
        """
        if not self.is_connected():
            return False
        
        try:
            return bool(self.client.exists(key))
        except Exception as e:
            logger.error(f"Error checking Redis key {key}: {e}")
            return False
    
    def expire(self, key: str, seconds: int) -> bool:
        """
        Set expiration time for a key.
        
        Args:
            key: Redis key
            seconds: Expiration time in seconds
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_connected():
            return False
        
        try:
            return bool(self.client.expire(key, seconds))
        except Exception as e:
            logger.error(f"Error setting expiration for Redis key {key}: {e}")
            return False
    
    def ttl(self, key: str) -> int:
        """
        Get time to live for a key.
        
        Args:
            key: Redis key
            
        Returns:
            int: TTL in seconds, -1 if no expiration, -2 if key doesn't exist
        """
        if not self.is_connected():
            return -2
        
        try:
            return self.client.ttl(key)
        except Exception as e:
            logger.error(f"Error getting TTL for Redis key {key}: {e}")
            return -2
    
    def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """
        Increment a counter in Redis.
        
        Args:
            key: Redis key
            amount: Amount to increment (default: 1)
            
        Returns:
            int: New value if successful, None otherwise
        """
        if not self.is_connected():
            return None
        
        try:
            return self.client.incr(key, amount)
        except Exception as e:
            logger.error(f"Error incrementing Redis key {key}: {e}")
            return None
    
    def set_user_session(self, user_id: str, session_data: dict, expire: int = 3600) -> bool:
        """
        Store user session data.
        
        Args:
            user_id: User ID
            session_data: Session data to store
            expire: Expiration time in seconds (default: 1 hour)
            
        Returns:
            bool: True if successful, False otherwise
        """
        key = f"session:{user_id}"
        return self.set(key, session_data, expire)
    
    def get_user_session(self, user_id: str) -> Optional[dict]:
        """
        Retrieve user session data.
        
        Args:
            user_id: User ID
            
        Returns:
            dict: Session data if found, None otherwise
        """
        key = f"session:{user_id}"
        return self.get(key)
    
    def delete_user_session(self, user_id: str) -> bool:
        """
        Delete user session data.
        
        Args:
            user_id: User ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        key = f"session:{user_id}"
        return self.delete(key)
    
    def set_cache(self, key: str, data: Any, expire: int = 300) -> bool:
        """
        Cache data with expiration.
        
        Args:
            key: Cache key
            data: Data to cache
            expire: Expiration time in seconds (default: 5 minutes)
            
        Returns:
            bool: True if successful, False otherwise
        """
        cache_key = f"cache:{key}"
        return self.set(cache_key, data, expire)
    
    def get_cache(self, key: str) -> Optional[Any]:
        """
        Retrieve cached data.
        
        Args:
            key: Cache key
            
        Returns:
            Cached data if found, None otherwise
        """
        cache_key = f"cache:{key}"
        return self.get(cache_key)
    
    def clear_cache(self, pattern: str = "cache:*") -> bool:
        """
        Clear cache entries matching pattern.
        
        Args:
            pattern: Pattern to match keys (default: "cache:*")
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_connected():
            return False
        
        try:
            keys = self.client.keys(pattern)
            if keys:
                self.client.delete(*keys)
                logger.info(f"Cleared {len(keys)} cache entries")
            return True
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return False


# Global Redis service instance
redis_service = RedisService() 