"""
Short-term memory implementation using Redis.

Stores recent interactions and context for immediate access.
Features:
- 2-hour TTL with LTRIM policy
- RDB + AOF persistence
- Automatic cleanup and migration to episodic memory
- Per-user isolation via user_id suffix on Redis keys
"""

import logging
import time
from typing import Any
from datetime import datetime, timezone
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
        password: str | None = None,
        ttl_hours: int = 2,
        max_messages: int = 100,
        migration_threshold: int = 50,
    ):
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.ttl_hours = ttl_hours
        self.max_messages = max_messages
        self.migration_threshold = migration_threshold

        self._redis = get_cache_with_format(SerializationFormat.MSGPACK)
        if not self._redis:
            self._redis = RedisCache(
                host=host,
                port=port,
                db=db,
                password=password,
                serialization_format=SerializationFormat.MSGPACK,
                ttl_hours=ttl_hours,
            )

        self._user_id: str | None = None
        self._message_list_key = "memory:short_term:messages"
        self._facts_key = "memory:short_term:facts"
        self._summary_key = "memory:short_term:summary"

    # ------------------------------------------------------------------
    # Key resolution (per-user isolation)
    # ------------------------------------------------------------------
    def _resolve_key(self, base: str, user_id: str | None) -> str:
        # Use explicit None check: "" is a valid (but empty) id and should not fallback to global.
        uid = user_id if user_id is not None else self._user_id
        if uid is not None and uid != "":
            return f"{base}:{uid}"
        # No user -> isolate as "anonymous" instead of global leak.
        # Callers that want global must explicitly pass "" with knowledge.
        return f"{base}:anonymous" if base.startswith("memory:") else base

    def _msg_key(self, user_id: str | None = None) -> str:
        return self._resolve_key("memory:short_term:messages", user_id)

    def _facts_key_for(self, user_id: str | None = None) -> str:
        return self._resolve_key("memory:short_term:facts", user_id)

    def _summary_key_for(self, user_id: str | None = None) -> str:
        return self._resolve_key("memory:short_term:summary", user_id)

    def set_user_context(self, user_id: str) -> None:
        """Legacy mutable mode — prefer passing user_id explicitly to each method."""
        self._user_id = user_id
        self._message_list_key = f"memory:short_term:messages:{user_id}"
        self._facts_key = f"memory:short_term:facts:{user_id}"
        self._summary_key = f"memory:short_term:summary:{user_id}"
        logger.info("Set user context %s — TTL=%sh, max_messages=%d", user_id, self.ttl_hours, self.max_messages)

    def _serialize_memory_item(self, item: dict[str, Any]) -> str:
        memory_item = {
            "timestamp": time.time(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "content": item,
            "type": item.get("type", "interaction"),
            "confidence": item.get("confidence", 0.5),
            "access_count": 0,
            "last_accessed": time.time(),
        }
        return self._redis._serialize(memory_item)

    def _deserialize_memory_item(self, data: str) -> dict[str, Any] | None:
        try:
            return self._redis._deserialize(data)
        except Exception as e:
            logger.error(f"Failed to deserialize memory item: {e}")
            return None

    def add_interaction(
        self,
        user_query: str,
        agent_response: str,
        context: dict[str, Any] | None = None,
        confidence: float = 0.5,
        user_id: str | None = None,
    ) -> bool:
        interaction = {
            "type": "interaction",
            "user_query": user_query,
            "agent_response": agent_response,
            "context": context or {},
            "confidence": confidence,
            "timestamp": time.time(),
        }
        try:
            msg_key = self._msg_key(user_id)
            serialized = self._serialize_memory_item(interaction)
            result = self._redis.list_push(msg_key, serialized)
            if result:
                self._redis.list_trim(msg_key, 0, self.max_messages - 1)
                self._redis.expire(msg_key, self.ttl_hours)
                self._check_migration_trigger(user_id=user_id)
                logger.debug(f"Added interaction to short-term memory (user={user_id or self._user_id}, confidence: {confidence:.2f})")
                return True
            return False
        except RedisError as e:
            logger.error(f"Failed to add interaction to short-term memory: {e}")
            return False

    def get_recent_interactions(self, limit: int = 10, user_id: str | None = None) -> list[dict[str, Any]]:
        try:
            msg_key = self._msg_key(user_id)
            messages_data = self._redis.list_range(msg_key, 0, limit - 1)
            interactions = []
            for msg_data in messages_data:
                item = self._deserialize_memory_item(msg_data)
                if item and item.get("content", {}).get("type") == "interaction":
                    interactions.append(item["content"])
            if interactions:
                self._update_access_counts(interactions, user_id=user_id)
            return interactions
        except RedisError as e:
            logger.error(f"Failed to get recent interactions: {e}")
            return []

    def get_facts(self, fact_types: list[str] | None = None, user_id: str | None = None) -> dict[str, Any]:
        try:
            facts_key = self._facts_key_for(user_id)
            if fact_types:
                facts_data = self._redis.hash_multi_get(facts_key, fact_types)
                facts = {}
                for i, fact_type in enumerate(fact_types):
                    if facts_data[i]:
                        item = self._deserialize_memory_item(facts_data[i])
                        if item:
                            facts[fact_type] = item["content"]
            else:
                facts_data = self._redis.hash_get_all(facts_key)
                facts = {}
                for fact_type, fact_data in facts_data.items():
                    item = self._deserialize_memory_item(fact_data)
                    if item:
                        facts[fact_type] = item["content"]
            if facts:
                fact_keys = list(facts.keys())
                self._update_access_counts(list(facts.values()), fact_keys, user_id=user_id)
            return facts
        except RedisError as e:
            logger.error(f"Failed to get facts: {e}")
            return {}

    def _update_access_counts(
        self, items: list[dict[str, Any]], keys: list[str] | None = None, user_id: str | None = None
    ) -> None:
        try:
            if keys and len(keys) == len(items):
                facts_key = self._facts_key_for(user_id)
                for i in range(len(items)):
                    raw = self._redis.hash_multi_get(facts_key, [keys[i]])
                    if raw and raw[0]:
                        full = self._deserialize_memory_item(raw[0])
                        if full:
                            full["access_count"] = full.get("access_count", 0) + 1
                            full["last_accessed"] = time.time()
                            updated = self._redis._serialize(full)
                            self._redis.hash_set(facts_key, keys[i], updated)
        except RedisError as e:
            logger.error(f"Failed to update access counts: {e}")

    def _check_migration_trigger(self, user_id: str | None = None) -> None:
        try:
            msg_key = self._msg_key(user_id)
            message_count = self._redis.list_length(msg_key)
            if message_count >= self.migration_threshold:
                logger.info(f"Migration threshold reached ({message_count} messages, user={user_id or self._user_id}), triggering migration")
        except RedisError as e:
            logger.error(f"Failed to check migration trigger: {e}")

    def cleanup_expired(self, user_id: str | None = None) -> int:
        try:
            cleaned = 0
            msg_key = self._msg_key(user_id)
            current_count = self._redis.list_length(msg_key)
            if current_count > self.max_messages:
                self._redis.list_trim(msg_key, 0, self.max_messages - 1)
                cleaned += current_count - self.max_messages
            return cleaned
        except RedisError as e:
            logger.error(f"Failed to cleanup expired items: {e}")
            return 0

    def get_stats(self, user_id: str | None = None) -> dict[str, Any]:
        try:
            msg_key = self._msg_key(user_id)
            facts_key = self._facts_key_for(user_id)
            message_count = self._redis.list_length(msg_key)
            fact_count = self._redis.hash_length(facts_key)
            return {
                "memory_type": "short_term",
                "user_id": user_id or self._user_id,
                "message_count": message_count,
                "fact_count": fact_count,
                "max_messages": self.max_messages,
                "ttl_hours": self.ttl_hours,
                "migration_threshold": self.migration_threshold,
                "redis_info": self._redis.info(),
            }
        except RedisError as e:
            logger.error(f"Failed to get stats: {e}")
            return {"error": str(e)}

    def clear(self, user_id: str | None = None) -> bool:
        try:
            msg_key = self._msg_key(user_id)
            facts_key = self._facts_key_for(user_id)
            summary_key = self._summary_key_for(user_id)
            # Also clean legacy global keys when clearing anonymous to avoid orphaned data.
            keys_to_delete = [msg_key, facts_key, summary_key]
            if (user_id is None and self._user_id is None) or (user_id == "anonymous"):
                # Legacy global keys without suffix (pre-fix) -> delete once.
                keys_to_delete.extend(["memory:short_term:messages", "memory:short_term:facts", "memory:short_term:summary"])
            result = self._redis.delete_multi(keys_to_delete)
            logger.info("Cleared short-term memory (user=%s)", user_id if user_id is not None else (self._user_id or "anonymous"))
            return result
        except RedisError as e:
            logger.error(f"Failed to clear short-term memory: {e}")
            return False

    def close(self) -> None:
        if self._redis:
            self._redis.close()
        logger.info("Short-term memory closed")


# Global short-term memory instance
_short_term_memory_instance: ShortTermMemory | None = None


def get_short_term_memory() -> ShortTermMemory | None:
    """Get global short-term memory instance — prefer Dependencies container."""
    from infrastructure.dependencies import get_deps

    deps = get_deps()
    if deps is not None and deps.short_term_memory is not None:
        return deps.short_term_memory

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
