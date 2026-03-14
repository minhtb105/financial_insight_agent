"""
Short-term memory implementation using Redis.

Stores recent interactions and context for immediate access.
Features:
- 2-hour TTL with LTRIM policy
- RDB + AOF persistence
- Automatic cleanup and migration to episodic memory
"""

import json
import logging
import time
from typing import Any, Optional, Dict, List
from datetime import datetime
from redis.exceptions import RedisError

from infrastructure.cache.redis_cache import RedisCache, get_cache_with_format
from infrastructure.cache.serialization import SerializationFormat

logger = logging.getLogger(__name__)


class ShortTermMemory:
    """Redis-based short-term memory with automatic migration."""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 1,  # Use different DB for memory
        password: Optional[str] = None,
        ttl_hours: int = 2,
        max_messages: int = 100,
        migration_threshold: int = 50
    ):
        """
        Initialize short-term memory.
        
        Args:
            host: Redis server host
            port: Redis server port
            db: Redis database number (different from cache)
            password: Redis password
            ttl_hours: TTL in hours for individual items
            max_messages: Maximum messages to keep in list
            migration_threshold: Number of messages before triggering migration
        """
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.ttl_hours = ttl_hours
        self.max_messages = max_messages
        self.migration_threshold = migration_threshold
        
        # Use Redis cache infrastructure with optimized serialization
        self._redis = get_cache_with_format(SerializationFormat.MSGPACK)
        if not self._redis:
            # Fallback to direct Redis connection with MessagePack
            self._redis = RedisCache(
                host=host,
                port=port,
                db=db,
                password=password,
                serialization_format=SerializationFormat.MSGPACK,
                ttl_hours=ttl_hours
            )
        
        # Memory-specific namespaces
        self._message_list_key = "memory:short_term:messages"
        self._facts_key = "memory:short_term:facts"
        self._summary_key = "memory:short_term:summary"
        
        logger.info(f"Initialized ShortTermMemory with TTL={ttl_hours}h, max_messages={max_messages}")
    
    def _serialize_memory_item(self, item: Dict[str, Any]) -> str:
        """Serialize memory item with metadata using MessagePack."""
        memory_item = {
            "timestamp": time.time(),
            "created_at": datetime.now().isoformat(),
            "content": item,
            "type": item.get("type", "interaction"),
            "confidence": item.get("confidence", 0.5),
            "access_count": 0,
            "last_accessed": time.time()
        }
        # Use the Redis cache's serialization manager
        return self._redis._serialize(memory_item)
    
    def _deserialize_memory_item(self, data: str) -> Optional[Dict[str, Any]]:
        """Deserialize memory item using MessagePack."""
        try:
            return self._redis._deserialize(data)
        except Exception as e:
            logger.error(f"Failed to deserialize memory item: {e}")
            return None
    
    def add_interaction(
        self, 
        user_query: str, 
        agent_response: str, 
        context: Optional[Dict[str, Any]] = None,
        confidence: float = 0.5
    ) -> bool:
        """
        Add user interaction to short-term memory.
        
        Args:
            user_query: User's question/query
            agent_response: Agent's response
            context: Additional context (parsed query, etc.)
            confidence: Confidence score for the interaction
            
        Returns:
            True if successful, False otherwise
        """
        interaction = {
            "type": "interaction",
            "user_query": user_query,
            "agent_response": agent_response,
            "context": context or {},
            "confidence": confidence,
            "timestamp": time.time()
        }
        
        try:
            # Add to message list (FIFO with LTRIM)
            serialized = self._serialize_memory_item(interaction)
            result = self._redis._get_client().lpush(self._message_list_key, serialized)
            
            if result:
                # Trim list to max_messages
                self._redis._get_client().ltrim(self._message_list_key, 0, self.max_messages - 1)
                
                # Set TTL for the list itself
                self._redis._get_client().expire(self._message_list_key, self.ttl_hours * 3600)
                
                # Check if migration is needed
                self._check_migration_trigger()
                
                logger.debug(f"Added interaction to short-term memory (confidence: {confidence:.2f})")
                return True
            
            return False
            
        except RedisError as e:
            logger.error(f"Failed to add interaction to short-term memory: {e}")
            return False
    
    def add_fact(
        self, 
        fact_type: str, 
        fact_value: Any, 
        source: str = "agent",
        confidence: float = 0.8
    ) -> bool:
        """
        Add fact to short-term memory.
        
        Args:
            fact_type: Type of fact (e.g., "company_profile", "market_pattern")
            fact_value: The fact value
            source: Source of the fact
            confidence: Confidence in the fact
            
        Returns:
            True if successful, False otherwise
        """
        fact = {
            "type": "fact",
            "fact_type": fact_type,
            "fact_value": fact_value,
            "source": source,
            "confidence": confidence,
            "timestamp": time.time()
        }
        
        try:
            # Store as hash for easy lookup by fact_type
            fact_key = f"{self._facts_key}:{fact_type}"
            serialized = self._serialize_memory_item(fact)
            
            result = self._redis._get_client().hset(self._facts_key, fact_type, serialized)
            
            if result:
                # Set TTL for facts
                self._redis._get_client().expire(self._facts_key, self.ttl_hours * 3600)
                
                logger.debug(f"Added fact to short-term memory: {fact_type}")
                return True
            
            return False
            
        except RedisError as e:
            logger.error(f"Failed to add fact to short-term memory: {e}")
            return False
    
    def get_recent_interactions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent interactions from short-term memory.
        
        Args:
            limit: Maximum number of interactions to return
            
        Returns:
            List of recent interactions
        """
        try:
            client = self._redis._get_client()
            if not client:
                return []
            
            # Get recent messages from list
            messages_data = client.lrange(self._message_list_key, 0, limit - 1)
            
            interactions = []
            for msg_data in messages_data:
                item = self._deserialize_memory_item(msg_data)
                if item and item.get("content", {}).get("type") == "interaction":
                    interactions.append(item["content"])
            
            # Update access counts
            if interactions:
                self._update_access_counts(interactions)
            
            return interactions
            
        except RedisError as e:
            logger.error(f"Failed to get recent interactions: {e}")
            return []
    
    def get_facts(self, fact_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Get facts from short-term memory.
        
        Args:
            fact_types: List of fact types to retrieve (None for all)
            
        Returns:
            Dictionary of facts
        """
        try:
            client = self._redis._get_client()
            if not client:
                return {}
            
            if fact_types:
                # Get specific fact types
                facts_data = client.hmget(self._facts_key, *fact_types)
                facts = {}
                for i, fact_type in enumerate(fact_types):
                    if facts_data[i]:
                        item = self._deserialize_memory_item(facts_data[i])
                        if item:
                            facts[fact_type] = item["content"]
            else:
                # Get all facts
                facts_data = client.hgetall(self._facts_key)
                facts = {}
                for fact_type, fact_data in facts_data.items():
                    item = self._deserialize_memory_item(fact_data)
                    if item:
                        facts[fact_type] = item["content"]
            
            # Update access counts
            if facts:
                self._update_access_counts(list(facts.values()))
            
            return facts
            
        except RedisError as e:
            logger.error(f"Failed to get facts: {e}")
            return {}
    
    def get_summary(self) -> Optional[Dict[str, Any]]:
        """Get current summary of short-term memory."""
        try:
            summary_data = self._redis.get("summary", namespace="memory:short_term")
            return summary_data
        except Exception as e:
            logger.error(f"Failed to get summary: {e}")
            return None
    
    def update_summary(self, summary: Dict[str, Any]) -> bool:
        """Update short-term memory summary."""
        try:
            return self._redis.set("summary", summary, namespace="memory:short_term")
        except Exception as e:
            logger.error(f"Failed to update summary: {e}")
            return False
    
    def _update_access_counts(self, items: List[Dict[str, Any]]) -> None:
        """Update access counts for items."""
        try:
            client = self._redis._get_client()
            if not client:
                return
            
            # Update access counts in Redis (this is a simplified approach)
            # In a real implementation, you might want to track this more systematically
            for item in items:
                if item.get("type") == "interaction":
                    # Could implement more sophisticated access tracking here
                    pass
                    
        except RedisError as e:
            logger.error(f"Failed to update access counts: {e}")
    
    def _check_migration_trigger(self) -> None:
        """Check if migration to episodic memory is needed."""
        try:
            client = self._redis._get_client()
            if not client:
                return
            
            # Count messages in list
            message_count = client.llen(self._message_list_key)
            
            if message_count >= self.migration_threshold:
                logger.info(f"Migration threshold reached ({message_count} messages), triggering migration")
                # Note: Actual migration would be handled by MemoryManager
                # This is just a trigger mechanism
                
        except RedisError as e:
            logger.error(f"Failed to check migration trigger: {e}")
    
    def cleanup_expired(self) -> int:
        """
        Clean up expired items and return count of cleaned items.
        
        Returns:
            Number of items cleaned up
        """
        try:
            client = self._redis._get_client()
            if not client:
                return 0
            
            # Redis handles TTL automatically, but we can do additional cleanup
            cleaned = 0
            
            # Clean up old messages beyond max_messages
            current_count = client.llen(self._message_list_key)
            if current_count > self.max_messages:
                # Remove excess messages from the end
                client.ltrim(self._message_list_key, 0, self.max_messages - 1)
                cleaned += current_count - self.max_messages
            
            return cleaned
            
        except RedisError as e:
            logger.error(f"Failed to cleanup expired items: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get short-term memory statistics."""
        try:
            client = self._redis._get_client()
            if not client:
                return {"error": "Redis client not available"}
            
            message_count = client.llen(self._message_list_key)
            fact_count = client.hlen(self._facts_key)
            
            return {
                "memory_type": "short_term",
                "message_count": message_count,
                "fact_count": fact_count,
                "max_messages": self.max_messages,
                "ttl_hours": self.ttl_hours,
                "migration_threshold": self.migration_threshold,
                "redis_info": self._redis.info()
            }
            
        except RedisError as e:
            logger.error(f"Failed to get stats: {e}")
            return {"error": str(e)}
    
    def clear(self) -> bool:
        """Clear all short-term memory."""
        try:
            client = self._redis._get_client()
            if not client:
                return False
            
            # Delete all memory keys
            keys_to_delete = [
                self._message_list_key,
                self._facts_key,
                f"{self._summary_key}:summary"
            ]
            
            result = client.delete(*keys_to_delete)
            logger.info(f"Cleared short-term memory ({result} keys deleted)")
            return bool(result)
            
        except RedisError as e:
            logger.error(f"Failed to clear short-term memory: {e}")
            return False
    
    def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            self._redis.close()
        logger.info("Short-term memory closed")


# Global short-term memory instance
_short_term_memory_instance: Optional[ShortTermMemory] = None


def get_short_term_memory() -> Optional[ShortTermMemory]:
    """Get global short-term memory instance."""
    global _short_term_memory_instance
    if _short_term_memory_instance is None:
        try:
            _short_term_memory_instance = ShortTermMemory()
        except Exception as e:
            logger.error(f"Failed to create short-term memory instance: {e}")
            _short_term_memory_instance = None
    return _short_term_memory_instance


def set_short_term_memory_instance(memory: ShortTermMemory) -> None:
    """Set global short-term memory instance (for testing)."""
    global _short_term_memory_instance
    _short_term_memory_instance = memory