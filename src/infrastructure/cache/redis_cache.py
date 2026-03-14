"""
Redis-based caching implementation for the financial insight agent.

Provides distributed caching with persistence and TTL management.
"""

import logging
from typing import Any, Optional, Dict, List, Union
import redis
from redis.exceptions import RedisError, ConnectionError, TimeoutError

from infrastructure.cache.serialization import SerializationManager, SerializationFormat

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis-based cache implementation with advanced features."""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        ttl_hours: int = 2,
        max_connections: int = 50,
        serialization_format: SerializationFormat = SerializationFormat.JSON
    ):
        """
        Initialize Redis cache.
        
        Args:
            host: Redis server host
            port: Redis server port
            db: Redis database number
            password: Redis password (optional)
            ttl_hours: Default TTL in hours
            max_connections: Maximum connection pool size
            serialization_format: Serialization format (JSON, MSGPACK, REDIS_HASH)
        """
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.ttl_hours = ttl_hours
        self.max_connections = max_connections
        self.serialization_format = serialization_format
        
        self._client = None
        self._connect()
        self._serialization_manager = SerializationManager(default_format=serialization_format)
    
    def _connect(self) -> None:
        """Establish connection to Redis."""
        try:
            self._client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30,
                max_connections=self.max_connections
            )
            
            # Test connection
            self._client.ping()
            logger.info(f"Connected to Redis at {self.host}:{self.port}")
            
        except (ConnectionError, TimeoutError, RedisError) as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._client = None
    
    def _get_client(self) -> Optional[redis.Redis]:
        """Get Redis client, reconnect if needed."""
        if self._client is None:
            self._connect()
        return self._client
    
    def _serialize(self, data: Any, format: Optional[SerializationFormat] = None) -> Union[str, Dict[str, str]]:
        """Serialize data using configured format."""
        return self._serialization_manager.serialize(data, format)
    
    def _deserialize(self, data: Union[str, Dict[str, str]], format: Optional[SerializationFormat] = None) -> Any:
        """Deserialize data using configured format."""
        return self._serialization_manager.deserialize(data, format)
    
    def _get_key(self, key: str, namespace: str = "cache") -> str:
        """Generate full cache key with namespace."""
        return f"{namespace}:{key}"
    
    def get(self, key: str, namespace: str = "cache", format: Optional[SerializationFormat] = None) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            namespace: Cache namespace
            format: Serialization format (auto-detects if None)
            
        Returns:
            Cached value or None if not found/expired
        """
        client = self._get_client()
        if client is None:
            logger.warning("Redis client not available, skipping cache get")
            return None
        
        try:
            full_key = self._get_key(key, namespace)
            
            # Determine if we should use Redis Hash
            if format == SerializationFormat.REDIS_HASH or (format is None and self.serialization_format == SerializationFormat.REDIS_HASH):
                data = client.hgetall(full_key)
                if not data:
                    return None
                return self._deserialize(data, SerializationFormat.REDIS_HASH)
            else:
                data = client.get(full_key)
                if data is None:
                    return None
                return self._deserialize(data, format)
            
        except RedisError as e:
            logger.error(f"Redis GET error for key {key}: {e}")
            return None
    
    def set(
        self, 
        key: str, 
        value: Any, 
        ttl_hours: Optional[int] = None,
        namespace: str = "cache",
        format: Optional[SerializationFormat] = None
    ) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl_hours: TTL in hours (uses default if None)
            namespace: Cache namespace
            format: Serialization format (uses default if None)
            
        Returns:
            True if successful, False otherwise
        """
        client = self._get_client()
        if client is None:
            logger.warning("Redis client not available, skipping cache set")
            return False
        
        try:
            full_key = self._get_key(key, namespace)
            target_format = format or self.serialization_format
            serialized_value = self._serialize(value, target_format)
            ttl_seconds = (ttl_hours or self.ttl_hours) * 3600
            
            if target_format == SerializationFormat.REDIS_HASH:
                # Use Redis Hash
                result = client.hset(full_key, mapping=serialized_value)
                if result:
                    client.expire(full_key, ttl_seconds)
            else:
                # Use regular SET
                result = client.setex(full_key, ttl_seconds, serialized_value)
            
            if result:
                logger.debug(f"Cached key {key} with TTL {ttl_hours or self.ttl_hours}h using format {target_format.value}")
            
            return bool(result)
            
        except RedisError as e:
            logger.error(f"Redis SET error for key {key}: {e}")
            return False
    
    def delete(self, key: str, namespace: str = "cache") -> bool:
        """
        Delete key from cache.
        
        Args:
            key: Cache key
            namespace: Cache namespace
            
        Returns:
            True if successful, False otherwise
        """
        client = self._get_client()
        if client is None:
            logger.warning("Redis client not available, skipping cache delete")
            return False
        
        try:
            full_key = self._get_key(key, namespace)
            result = client.delete(full_key)
            return bool(result)
            
        except RedisError as e:
            logger.error(f"Redis DELETE error for key {key}: {e}")
            return False
    
    def exists(self, key: str, namespace: str = "cache") -> bool:
        """
        Check if key exists in cache.
        
        Args:
            key: Cache key
            namespace: Cache namespace
            
        Returns:
            True if key exists, False otherwise
        """
        client = self._get_client()
        if client is None:
            return False
        
        try:
            full_key = self._get_key(key, namespace)
            return bool(client.exists(full_key))
            
        except RedisError as e:
            logger.error(f"Redis EXISTS error for key {key}: {e}")
            return False
    
    def keys(self, pattern: str = "*", namespace: str = "cache") -> List[str]:
        """
        Get all keys matching pattern.
        
        Args:
            pattern: Key pattern (supports Redis glob patterns)
            namespace: Cache namespace
            
        Returns:
            List of matching keys
        """
        client = self._get_client()
        if client is None:
            return []
        
        try:
            full_pattern = self._get_key(pattern, namespace)
            keys = client.keys(full_pattern)
            return [key.replace(f"{namespace}:", "") for key in keys]
            
        except RedisError as e:
            logger.error(f"Redis KEYS error for pattern {pattern}: {e}")
            return []
    
    def ttl(self, key: str, namespace: str = "cache") -> Optional[int]:
        """
        Get TTL for key in seconds.
        
        Args:
            key: Cache key
            namespace: Cache namespace
            
        Returns:
            TTL in seconds, or None if key doesn't exist or has no TTL
        """
        client = self._get_client()
        if client is None:
            return None
        
        try:
            full_key = self._get_key(key, namespace)
            return client.ttl(full_key)
            
        except RedisError as e:
            logger.error(f"Redis TTL error for key {key}: {e}")
            return None
    
    def expire(self, key: str, ttl_hours: int, namespace: str = "cache") -> bool:
        """
        Set TTL for existing key.
        
        Args:
            key: Cache key
            ttl_hours: TTL in hours
            namespace: Cache namespace
            
        Returns:
            True if successful, False otherwise
        """
        client = self._get_client()
        if client is None:
            return False
        
        try:
            full_key = self._get_key(key, namespace)
            ttl_seconds = ttl_hours * 3600
            return bool(client.expire(full_key, ttl_seconds))
            
        except RedisError as e:
            logger.error(f"Redis EXPIRE error for key {key}: {e}")
            return False
    
    def flush(self, namespace: Optional[str] = None) -> bool:
        """
        Flush cache.
        
        Args:
            namespace: If provided, only flush keys in this namespace
            
        Returns:
            True if successful, False otherwise
        """
        client = self._get_client()
        if client is None:
            return False
        
        try:
            if namespace:
                keys = self.keys("*", namespace)
                if keys:
                    full_keys = [self._get_key(key, namespace) for key in keys]
                    client.delete(*full_keys)
            else:
                client.flushdb()
            
            logger.info(f"Flushed cache namespace: {namespace or 'all'}")
            return True
            
        except RedisError as e:
            logger.error(f"Redis FLUSH error: {e}")
            return False
    
    def info(self) -> Dict[str, Any]:
        """
        Get Redis info and cache statistics.
        
        Returns:
            Dictionary with Redis info and cache stats
        """
        client = self._get_client()
        if client is None:
            return {"error": "Redis client not available"}
        
        try:
            info = client.info()
            return {
                "redis_info": info,
                "connection_status": "connected",
                "host": self.host,
                "port": self.port,
                "db": self.db,
                "serialization_format": self.serialization_format.value,
                "msgpack_available": self._serialization_manager._msgpack_available
            }
            
        except RedisError as e:
            logger.error(f"Redis INFO error: {e}")
            return {"error": str(e)}
    
    def close(self) -> None:
        """Close Redis connection."""
        if self._client:
            try:
                self._client.close()
                logger.info("Redis connection closed")
            except RedisError as e:
                logger.error(f"Error closing Redis connection: {e}")
            finally:
                self._client = None


# Global cache instance
_cache_instance: Optional[RedisCache] = None


def get_cache() -> Optional[RedisCache]:
    """Get global cache instance."""
    global _cache_instance
    if _cache_instance is None:
        try:
            _cache_instance = RedisCache()
        except Exception as e:
            logger.error(f"Failed to create Redis cache instance: {e}")
            _cache_instance = None
    return _cache_instance


def get_cache_with_format(format: SerializationFormat) -> Optional[RedisCache]:
    """Get cache instance with specific serialization format."""
    try:
        return RedisCache(serialization_format=format)
    except Exception as e:
        logger.error(f"Failed to create Redis cache instance with format {format}: {e}")
        return None


def set_cache_instance(cache: RedisCache) -> None:
    """Set global cache instance (for testing)."""
    global _cache_instance
    _cache_instance = cache
