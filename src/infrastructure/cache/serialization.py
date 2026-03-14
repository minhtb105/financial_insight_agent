"""
Serialization utilities for Redis caching with multiple format support.

Provides JSON, MessagePack, and Redis Hash serialization strategies.
"""

import json
import logging
import msgpack
from typing import Any, Dict, Optional, Union
from enum import Enum

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
        """Check if MessagePack is available."""
        try:
            import msgpack
            return True
        except ImportError:
            logger.warning("MessagePack not available, using JSON fallback")
            return False
    
    def serialize(
        self, 
        data: Any, 
        format: Optional[SerializationFormat] = None
    ) -> Union[str, Dict[str, str]]:
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
            # Fallback to JSON
            return self._serialize_json(data)
    
    def deserialize(
        self, 
        data: Union[str, Dict[str, str]], 
        format: Optional[SerializationFormat] = None
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
            # Fallback to JSON
            return self._deserialize_json(data)
    
    def _serialize_json(self, data: Any) -> str:
        """Serialize data to JSON string."""
        try:
            return json.dumps(data, ensure_ascii=False, default=str)
        except (TypeError, ValueError) as e:
            logger.error(f"JSON serialization failed: {e}")
            return json.dumps({"error": "Serialization failed", "data": str(data)})
    
    def _deserialize_json(self, data: str) -> Any:
        """Deserialize JSON string to Python object."""
        try:
            return json.loads(data)
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"JSON deserialization failed: {e}")
            return None
    
    def _serialize_msgpack(self, data: Any) -> str:
        """Serialize data to MessagePack binary (encoded as string)."""
        try:
            # MessagePack returns bytes, encode as base64 string for Redis storage
            import base64
            packed = msgpack.packb(data, default=str)
            return base64.b64encode(packed).decode('ascii')
        except Exception as e:
            logger.error(f"MessagePack serialization failed: {e}")
            # Fallback to JSON
            return self._serialize_json(data)
    
    def _deserialize_msgpack(self, data: str) -> Any:
        """Deserialize MessagePack binary from string."""
        try:
            import base64
            packed = base64.b64decode(data.encode('ascii'))
            return msgpack.unpackb(packed, raw=False, strict_map_key=False)
        except Exception as e:
            logger.error(f"MessagePack deserialization failed: {e}")
            # Fallback to JSON
            return self._deserialize_json(data)
    
    def _serialize_redis_hash(self, data: Any) -> Dict[str, str]:
        """Serialize data to Redis Hash format (dict of string fields)."""
        if not isinstance(data, dict):
            # Convert to dict format
            if hasattr(data, '__dict__'):
                data = data.__dict__
            else:
                data = {"value": str(data)}
        
        # Convert all values to strings for Redis Hash
        hash_data = {}
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                # Nested structures need to be serialized
                hash_data[str(key)] = self._serialize_json(value)
            else:
                hash_data[str(key)] = str(value)
        
        return hash_data
    
    def _deserialize_redis_hash(self, data: Dict[str, str]) -> Any:
        """Deserialize Redis Hash to Python object."""
        if not isinstance(data, dict):
            return data
        
        result = {}
        for key, value in data.items():
            # Try to deserialize nested JSON strings
            try:
                # Check if value looks like JSON
                if value.startswith(('{', '[')) and value.endswith(('}', ']')):
                    result[key] = self._deserialize_json(value)
                else:
                    result[key] = value
            except (json.JSONDecodeError, TypeError):
                result[key] = value
        
        return result
    
    def _detect_format(self, data: Union[str, Dict[str, str]]) -> SerializationFormat:
        """Auto-detect serialization format."""
        if isinstance(data, dict):
            return SerializationFormat.REDIS_HASH
        elif isinstance(data, str):
            # Check for MessagePack (base64 encoded binary)
            try:
                import base64
                import msgpack
                packed = base64.b64decode(data.encode('ascii'))
                msgpack.unpackb(packed)
                return SerializationFormat.MSGPACK
            except:
                pass
            
            # Check for JSON
            try:
                json.loads(data)
                return SerializationFormat.JSON
            except (json.JSONDecodeError, TypeError):
                pass
        
        # Default to JSON
        return SerializationFormat.JSON
    
    def get_compression_ratio(self, data: Any, format: SerializationFormat) -> float:
        """Calculate compression ratio compared to JSON."""
        json_size = len(self._serialize_json(data))
        target_size = len(self.serialize(data, format))
        return json_size / target_size if target_size > 0 else 1.0
    
    def get_format_stats(self, data: Any) -> Dict[str, Dict[str, Union[int, float]]]:
        """Get size comparison for all available formats."""
        stats = {}
        
        # JSON baseline
        json_data = self._serialize_json(data)
        json_size = len(json_data)
        stats["json"] = {"size": json_size, "compression": 1.0}
        
        # MessagePack
        if self._msgpack_available:
            try:
                msgpack_data = self._serialize_msgpack(data)
                msgpack_size = len(msgpack_data)
                stats["msgpack"] = {
                    "size": msgpack_size,
                    "compression": json_size / msgpack_size if msgpack_size > 0 else 1.0
                }
            except Exception as e:
                stats["msgpack"] = {"error": str(e)}
        
        # Redis Hash (approximate)
        try:
            hash_data = self._serialize_redis_hash(data)
            # Estimate Redis Hash size (sum of key+value lengths)
            hash_size = sum(len(k) + len(v) for k, v in hash_data.items())
            stats["redis_hash"] = {
                "size": hash_size,
                "compression": json_size / hash_size if hash_size > 0 else 1.0
            }
        except Exception as e:
            stats["redis_hash"] = {"error": str(e)}
        
        return stats


# Global serialization manager instance
_serialization_manager: Optional[SerializationManager] = None


def get_serialization_manager() -> SerializationManager:
    """Get global serialization manager instance."""
    global _serialization_manager
    if _serialization_manager is None:
        _serialization_manager = SerializationManager()
    return _serialization_manager


def set_serialization_manager_instance(manager: SerializationManager) -> None:
    """Set global serialization manager instance (for testing)."""
    global _serialization_manager
    _serialization_manager = manager