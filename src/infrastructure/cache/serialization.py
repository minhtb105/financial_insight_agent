"""
Serialization utilities for Redis caching with multiple format support.

Provides JSON, MessagePack, and Redis Hash serialization strategies.
"""

import json
import logging
from typing import Any
from enum import Enum

try:
    import msgpack

    _MSGPACK_AVAILABLE = True
except ImportError:
    msgpack = None
    _MSGPACK_AVAILABLE = False

logger = logging.getLogger(__name__)


class SerializationFormat(Enum):
    """Supported serialization formats."""

    JSON = "json"
    MSGPACK = "msgpack"
    REDIS_HASH = "redis_hash"


class SerializationManager:
    """Manages different serialization formats with fallback support."""

    def __init__(self, default_format: SerializationFormat = SerializationFormat.JSON):
        """
        Initialize serialization manager.

        Args:
            default_format: Default serialization format
        """
        self.default_format = default_format
        self._msgpack_available = self._check_msgpack_availability()

        if not self._msgpack_available and default_format == SerializationFormat.MSGPACK:
            logger.warning("MessagePack not available, falling back to JSON")
            self.default_format = SerializationFormat.JSON

    def _check_msgpack_availability(self) -> bool:
        return _MSGPACK_AVAILABLE

    def serialize(
        self, data: Any, format: SerializationFormat | None = None
    ) -> str | dict[str, str]:
        """
        Serialize data using specified format.

        Args:
            data: Data to serialize
            format: Serialization format (uses default if None)

        Returns:
            Serialized data (string for JSON/MSGPACK, dict for Redis Hash)
        """
        target_format = format or self.default_format

        try:
            if target_format == SerializationFormat.JSON:
                return self._serialize_json(data)
            elif target_format == SerializationFormat.MSGPACK and self._msgpack_available:
                return self._serialize_msgpack(data)
            elif target_format == SerializationFormat.REDIS_HASH:
                return self._serialize_redis_hash(data)
            else:
                # Fallback to JSON
                logger.warning(f"Format {target_format} not available, falling back to JSON")
                return self._serialize_json(data)

        except Exception as e:
            logger.error(f"Serialization failed for format {target_format}: {e}")
            if target_format != SerializationFormat.JSON:
                return self._serialize_json(data)
            raise

    def deserialize(
        self, data: str | dict[str, str], format: SerializationFormat | None = None
    ) -> Any:
        """
        Deserialize data using specified format.

        Args:
            data: Serialized data
            format: Serialization format (auto-detects if None)

        Returns:
            Deserialized data
        """
        if format is None:
            format = self._detect_format(data)

        try:
            if format == SerializationFormat.JSON:
                return self._deserialize_json(data)
            elif format == SerializationFormat.MSGPACK and self._msgpack_available:
                return self._deserialize_msgpack(data)
            elif format == SerializationFormat.REDIS_HASH:
                return self._deserialize_redis_hash(data)
            else:
                # Fallback to JSON
                return self._deserialize_json(data)

        except Exception as e:
            logger.error(f"Deserialization failed for format {format}: {e}")
            if format != SerializationFormat.JSON:
                return self._deserialize_json(data)
            raise

    def _serialize_json(self, data: Any) -> str:
        """Serialize data to JSON string."""
        try:
            return json.dumps(data, ensure_ascii=False, default=str)
        except (TypeError, ValueError) as e:
            logger.error(f"JSON serialization failed: {e}")
            raise

    def _deserialize_json(self, data: str) -> Any:
        """Deserialize JSON string to Python object."""
        try:
            return json.loads(data)
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"JSON deserialization failed: {e}")
            raise

    def _serialize_msgpack(self, data: Any) -> str:
        if not _MSGPACK_AVAILABLE:
            return self._serialize_json(data)
        try:
            import base64

            packed = msgpack.packb(data, default=str)
            return base64.b64encode(packed).decode("ascii")
        except Exception as e:
            logger.error(f"MessagePack serialization failed: {e}")
            # Fallback to JSON
            return self._serialize_json(data)

    def _deserialize_msgpack(self, data: str) -> Any:
        if not _MSGPACK_AVAILABLE:
            return self._deserialize_json(data)
        try:
            import base64

            packed = base64.b64decode(data.encode("ascii"))
            return msgpack.unpackb(packed, raw=False, strict_map_key=False)
        except Exception as e:
            logger.error(f"MessagePack deserialization failed: {e}")
            # Fallback to JSON
            return self._deserialize_json(data)

    def _serialize_redis_hash(self, data: Any) -> dict[str, str]:
        """Serialize data to Redis Hash format (dict of string fields)."""
        if not isinstance(data, dict):
            # Convert to dict format
            data = data.__dict__ if hasattr(data, "__dict__") else {"value": str(data)}

        # Convert all values to strings for Redis Hash
        hash_data = {}
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                # Nested structures need to be serialized
                hash_data[str(key)] = self._serialize_json(value)
            else:
                hash_data[str(key)] = str(value)

        return hash_data

    def _deserialize_redis_hash(self, data: dict[str, str]) -> Any:
        """Deserialize Redis Hash to Python object."""
        if not isinstance(data, dict):
            return data

        result = {}
        for key, value in data.items():
            # Try to deserialize nested JSON strings
            try:
                # Check if value looks like JSON
                if value.startswith(("{", "[")) and value.endswith(("}", "]")):
                    result[key] = self._deserialize_json(value)
                else:
                    result[key] = value
            except (json.JSONDecodeError, TypeError):
                result[key] = value

        return result

    def _detect_format(self, data: str | dict[str, str]) -> SerializationFormat:
        if isinstance(data, dict):
            return SerializationFormat.REDIS_HASH
        elif isinstance(data, str) and _MSGPACK_AVAILABLE:
            try:
                import base64

                packed = base64.b64decode(data.encode("ascii"))
                msgpack.unpackb(packed)
                return SerializationFormat.MSGPACK
            except Exception:
                pass

            # Check for JSON
            try:
                json.loads(data)
                return SerializationFormat.JSON
            except (json.JSONDecodeError, TypeError):
                pass

        # Default to JSON
        return SerializationFormat.JSON


# Global serialization manager instance
_serialization_manager: SerializationManager | None = None


def get_serialization_manager() -> SerializationManager:
    """Get global serialization manager instance — prefer Dependencies container."""
    from infrastructure.dependencies import get_deps

    deps = get_deps()
    if deps is not None and deps.serialization_manager is not None:
        return deps.serialization_manager

    global _serialization_manager
    if _serialization_manager is None:
        _serialization_manager = SerializationManager()
    return _serialization_manager


def set_serialization_manager_instance(manager: SerializationManager) -> None:
    """Set global serialization manager instance (for testing)."""
    global _serialization_manager
    _serialization_manager = manager
