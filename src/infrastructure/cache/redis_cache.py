"""
Redis-based caching implementation for the financial insight agent.

Provides distributed caching with persistence and TTL management.
"""

import logging
import threading
import time
from typing import Any
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
        password: str | None = None,
        ttl_hours: int = 2,
        max_connections: int = 50,
        serialization_format: SerializationFormat = SerializationFormat.JSON,
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
        self._last_reconnect_attempt: float = 0.0
        self._reconnect_interval: float = 30.0
        self._reconnect_lock = threading.Lock()
        self._connect()
        self._serialization_manager = SerializationManager(default_format=serialization_format)

    def _connect(self) -> None:
        """Establish connection to Redis with retry."""
        max_retries = 2
        for attempt in range(max_retries):
            try:
                self._client = redis.Redis(
                    host=self.host,
                    port=self.port,
                    db=self.db,
                    password=self.password,
                    decode_responses=True,
                    socket_connect_timeout=3,
                    socket_timeout=3,
                    retry_on_timeout=True,
                    health_check_interval=30,
                )

                self._client.ping()
                logger.info(f"Connected to Redis at {self.host}:{self.port}")
                return

            except (ConnectionError, TimeoutError, RedisError) as e:
                logger.error(f"Failed to connect to Redis (attempt {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2**attempt)
        self._client = None

    def get_raw_client(self) -> redis.Redis | None:
        """Get the underlying Redis client for low-level operations."""
        now = time.time()
        with self._reconnect_lock:
            if self._client is None:
                if now - self._last_reconnect_attempt >= self._reconnect_interval:
                    self._last_reconnect_attempt = now
                    self._connect()
            elif self._client is not None:
                try:
                    self._client.ping()
                except (ConnectionError, TimeoutError, RedisError):
                    self._client = None
                    self._last_reconnect_attempt = now
                    self._connect()
        return self._client

    def _serialize(
        self, data: Any, format: SerializationFormat | None = None
    ) -> str | dict[str, str]:
        """Serialize data using configured format."""
        return self._serialization_manager.serialize(data, format)

    def _deserialize(
        self, data: str | dict[str, str], format: SerializationFormat | None = None
    ) -> Any:
        """Deserialize data using configured format."""
        return self._serialization_manager.deserialize(data, format)

    def _get_key(self, key: str, namespace: str = "cache") -> str:
        """Generate full cache key with namespace."""
        return f"{namespace}:{key}"

    def get(
        self, key: str, namespace: str = "cache", format: SerializationFormat | None = None
    ) -> Any | None:
        """
        Get value from cache.

        Args:
            key: Cache key
            namespace: Cache namespace
            format: Serialization format (auto-detects if None)

        Returns:
            Cached value or None if not found/expired
        """
        client = self.get_raw_client()
        if client is None:
            logger.warning("Redis client not available, skipping cache get")
            return None

        try:
            full_key = self._get_key(key, namespace)

            # Determine if we should use Redis Hash
            if format == SerializationFormat.REDIS_HASH or (
                format is None and self.serialization_format == SerializationFormat.REDIS_HASH
            ):
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
        ttl_hours: int | None = None,
        namespace: str = "cache",
        format: SerializationFormat | None = None,
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
        client = self.get_raw_client()
        if client is None:
            logger.warning("Redis client not available, skipping cache set")
            return False

        try:
            full_key = self._get_key(key, namespace)
            target_format = format or self.serialization_format
            serialized_value = self._serialize(value, target_format)
            ttl_seconds = (ttl_hours or self.ttl_hours) * 3600

            if target_format == SerializationFormat.REDIS_HASH:
                client.hset(full_key, mapping=serialized_value)
                client.expire(full_key, ttl_seconds)
                logger.debug(
                    f"Cached key {key} with TTL {ttl_hours or self.ttl_hours}h using format REDIS_HASH"
                )
                return True
            else:
                client.setex(full_key, ttl_seconds, serialized_value)
                logger.debug(
                    f"Cached key {key} with TTL {ttl_hours or self.ttl_hours}h using format {target_format.value}"
                )
                return True

        except RedisError as e:
            logger.error(f"Redis SET error for key {key}: {e}")
            return False

    def list_push(self, key: str, value: str, namespace: str = "cache") -> bool:
        client = self.get_raw_client()
        if client is None:
            return False
        try:
            return bool(client.lpush(self._get_key(key, namespace), value))
        except RedisError as e:
            logger.error(f"Redis LPUSH error for key {key}: {e}")
            return False

    def list_trim(self, key: str, start: int, stop: int, namespace: str = "cache") -> bool:
        client = self.get_raw_client()
        if client is None:
            return False
        try:
            client.ltrim(self._get_key(key, namespace), start, stop)
            return True
        except RedisError as e:
            logger.error(f"Redis LTRIM error for key {key}: {e}")
            return False

    def list_range(self, key: str, start: int, stop: int, namespace: str = "cache") -> list:
        client = self.get_raw_client()
        if client is None:
            return []
        try:
            return client.lrange(self._get_key(key, namespace), start, stop)
        except RedisError as e:
            logger.error(f"Redis LRANGE error for key {key}: {e}")
            return []

    def list_length(self, key: str, namespace: str = "cache") -> int:
        client = self.get_raw_client()
        if client is None:
            return 0
        try:
            return client.llen(self._get_key(key, namespace))
        except RedisError as e:
            logger.error(f"Redis LLEN error for key {key}: {e}")
            return 0

    def hash_set(self, key: str, field: str, value: str, namespace: str = "cache") -> bool:
        client = self.get_raw_client()
        if client is None:
            return False
        try:
            return bool(client.hset(self._get_key(key, namespace), field, value))
        except RedisError as e:
            logger.error(f"Redis HSET error for key {key}: {e}")
            return False

    def hash_get_all(self, key: str, namespace: str = "cache") -> dict:
        client = self.get_raw_client()
        if client is None:
            return {}
        try:
            return client.hgetall(self._get_key(key, namespace))
        except RedisError as e:
            logger.error(f"Redis HGETALL error for key {key}: {e}")
            return {}

    def hash_multi_get(self, key: str, fields: list, namespace: str = "cache") -> list:
        client = self.get_raw_client()
        if client is None:
            return []
        try:
            return client.hmget(self._get_key(key, namespace), *fields)
        except RedisError as e:
            logger.error(f"Redis HMGET error for key {key}: {e}")
            return []

    def hash_length(self, key: str, namespace: str = "cache") -> int:
        client = self.get_raw_client()
        if client is None:
            return 0
        try:
            return client.hlen(self._get_key(key, namespace))
        except RedisError as e:
            logger.error(f"Redis HLEN error for key {key}: {e}")
            return 0

    def set_add(self, key: str, value: str, namespace: str = "cache") -> bool:
        client = self.get_raw_client()
        if client is None:
            return False
        try:
            return bool(client.sadd(self._get_key(key, namespace), value))
        except RedisError as e:
            logger.error(f"Redis SADD error for key {key}: {e}")
            return False

    def set_members(self, key: str, namespace: str = "cache") -> set:
        client = self.get_raw_client()
        if client is None:
            return set()
        try:
            return client.smembers(self._get_key(key, namespace))
        except RedisError as e:
            logger.error(f"Redis SMEMBERS error for key {key}: {e}")
            return set()

    def delete_multi(self, keys: list, namespace: str = "cache") -> bool:
        client = self.get_raw_client()
        if client is None:
            return False
        try:
            full_keys = [self._get_key(k, namespace) for k in keys]
            return bool(client.delete(*full_keys))
        except RedisError as e:
            logger.error(f"Redis DELETE MULTI error: {e}")
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
        client = self.get_raw_client()
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
        client = self.get_raw_client()
        if client is None:
            return False

        try:
            full_key = self._get_key(key, namespace)
            return bool(client.exists(full_key))

        except RedisError as e:
            logger.error(f"Redis EXISTS error for key {key}: {e}")
            return False

    def keys(self, pattern: str = "*", namespace: str = "cache") -> list[str]:
        """
        Get all keys matching pattern.

        Args:
            pattern: Key pattern (supports Redis glob patterns)
            namespace: Cache namespace

        Returns:
            List of matching keys
        """
        client = self.get_raw_client()
        if client is None:
            return []

        try:
            full_pattern = self._get_key(pattern, namespace)
            keys = list(client.scan_iter(match=full_pattern))
            return [key.replace(f"{namespace}:", "") for key in keys]

        except RedisError as e:
            logger.error(f"Redis SCAN error for pattern {pattern}: {e}")
            return []

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
        client = self.get_raw_client()
        if client is None:
            return False

        try:
            full_key = self._get_key(key, namespace)
            ttl_seconds = ttl_hours * 3600
            return bool(client.expire(full_key, ttl_seconds))

        except RedisError as e:
            logger.error(f"Redis EXPIRE error for key {key}: {e}")
            return False

    def flush(self, namespace: str | None = None) -> bool:
        client = self.get_raw_client()
        if client is None:
            return False

        try:
            if namespace:
                keys = self.keys("*", namespace)
                if keys:
                    full_keys = [self._get_key(key, namespace) for key in keys]
                    client.delete(*full_keys)
            else:
                logger.warning("Flush without namespace is not allowed for safety")
                return False

            logger.info(f"Flushed cache namespace: {namespace or 'all'}")
            return True

        except RedisError as e:
            logger.error(f"Redis FLUSH error: {e}")
            return False

    def info(self) -> dict[str, Any]:
        """
        Get Redis info and cache statistics.

        Returns:
            Dictionary with Redis info and cache stats
        """
        client = self.get_raw_client()
        if client is None:
            return {"error": "Redis client not available"}

        try:
            return {
                "connection_status": "connected",
                "host": self.host,
                "port": self.port,
                "db": self.db,
                "serialization_format": self.serialization_format.value,
                "msgpack_available": self._serialization_manager._msgpack_available,
                "keys_count": client.dbsize(),
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


def get_cache() -> RedisCache | None:
    """Get Redis cache instance from Dependencies container."""
    from infrastructure.dependencies import get_deps

    deps = get_deps()
    return deps.redis_cache if deps is not None else None


def get_cache_with_format(format: SerializationFormat) -> RedisCache | None:
    """Get Redis cache instance (format param maintained for API compat)."""
    return get_cache()
