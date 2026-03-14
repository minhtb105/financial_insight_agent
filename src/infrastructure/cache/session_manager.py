"""
Session management using Redis Hash for efficient storage.

Provides session-based caching with automatic cleanup and cross-request context preservation.
"""

import json
import logging
from typing import Any, Optional, Dict, List
from datetime import datetime, timedelta
from redis.exceptions import RedisError

from infrastructure.cache.redis_cache import RedisCache, get_cache_with_format
from infrastructure.cache.serialization import SerializationFormat

logger = logging.getLogger(__name__)


class SessionManager:
    """Redis Hash-based session manager for efficient storage."""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 2,  # Use different DB for sessions
        password: Optional[str] = None,
        session_ttl_hours: int = 24,  # Longer TTL for sessions
        cleanup_interval_hours: int = 6
    ):
        """
        Initialize session manager.
        
        Args:
            host: Redis server host
            port: Redis server port
            db: Redis database number (different from cache)
            password: Redis password
            session_ttl_hours: Session TTL in hours
            cleanup_interval_hours: Cleanup interval in hours
        """
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.session_ttl_hours = session_ttl_hours
        self.cleanup_interval_hours = cleanup_interval_hours
        
        # Use Redis Hash format for sessions
        self._redis = get_cache_with_format(SerializationFormat.REDIS_HASH)
        if not self._redis:
            # Fallback to direct Redis connection with Hash format
            self._redis = RedisCache(
                host=host,
                port=port,
                db=db,
                password=password,
                serialization_format=SerializationFormat.REDIS_HASH,
                ttl_hours=session_ttl_hours
            )
        
        # Session-specific namespace
        self._session_namespace = "session"
        self._user_sessions_key = "session:active_users"
        self._session_stats_key = "session:stats"
        
        logger.info(f"Initialized SessionManager with TTL={session_ttl_hours}h")
    
    def _get_session_key(self, session_id: str) -> str:
        """Generate session key."""
        return f"session:{session_id}"
    
    def create_session(
        self, 
        session_id: str, 
        user_id: Optional[str] = None,
        initial_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Create a new session using Redis Hash.
        
        Args:
            session_id: Unique session identifier
            user_id: Optional user identifier
            initial_data: Initial session data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            session_data = {
                "session_id": session_id,
                "user_id": user_id or "anonymous",
                "created_at": datetime.now().isoformat(),
                "last_accessed": datetime.now().isoformat(),
                "access_count": "1",
                "query_count": "0",
                "preferences": json.dumps({}),
                "context": json.dumps({}),
                "metadata": json.dumps({
                    "ip_address": "unknown",
                    "user_agent": "unknown",
                    "session_type": "interactive"
                })
            }
            
            # Add initial data if provided
            if initial_data:
                for key, value in initial_data.items():
                    if key not in session_data:
                        session_data[key] = str(value)
            
            session_key = self._get_session_key(session_id)
            success = self._redis.set(
                key=session_key,
                value=session_data,
                namespace=self._session_namespace,
                ttl_hours=self.session_ttl_hours
            )
            
            if success:
                # Track active users
                self._track_user_session(user_id or "anonymous", session_id)
                logger.info(f"Created session {session_id} for user {user_id or 'anonymous'}")
            
            return success
            
        except RedisError as e:
            logger.error(f"Failed to create session {session_id}: {e}")
            return False
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session data.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session data or None if not found/expired
        """
        try:
            session_key = self._get_session_key(session_id)
            session_data = self._redis.get(
                key=session_key,
                namespace=self._session_namespace
            )
            
            if session_data:
                # Update last accessed time and access count
                self._update_session_access(session_id)
                return session_data
            
            return None
            
        except RedisError as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            return None
    
    def update_session(
        self, 
        session_id: str, 
        updates: Dict[str, Any],
        extend_ttl: bool = True
    ) -> bool:
        """
        Update session data.
        
        Args:
            session_id: Session identifier
            updates: Data to update
            extend_ttl: Whether to extend session TTL
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get current session data
            current_data = self.get_session(session_id)
            if not current_data:
                return False
            
            # Apply updates
            updated_data = current_data.copy()
            for key, value in updates.items():
                updated_data[key] = str(value)
            
            # Update last accessed time
            updated_data["last_accessed"] = datetime.now().isoformat()
            
            session_key = self._get_session_key(session_id)
            success = self._redis.set(
                key=session_key,
                value=updated_data,
                namespace=self._session_namespace,
                ttl_hours=self.session_ttl_hours if extend_ttl else None
            )
            
            if success:
                logger.debug(f"Updated session {session_id}")
            
            return success
            
        except RedisError as e:
            logger.error(f"Failed to update session {session_id}: {e}")
            return False
    
    def increment_query_count(self, session_id: str) -> bool:
        """Increment query count for session."""
        try:
            current_data = self.get_session(session_id)
            if not current_data:
                return False
            
            query_count = int(current_data.get("query_count", "0")) + 1
            return self.update_session(session_id, {"query_count": str(query_count)})
            
        except Exception as e:
            logger.error(f"Failed to increment query count for session {session_id}: {e}")
            return False
    
    def set_user_preferences(self, session_id: str, preferences: Dict[str, Any]) -> bool:
        """Set user preferences for session."""
        try:
            return self.update_session(session_id, {"preferences": json.dumps(preferences)})
        except Exception as e:
            logger.error(f"Failed to set user preferences for session {session_id}: {e}")
            return False
    
    def get_user_preferences(self, session_id: str) -> Dict[str, Any]:
        """Get user preferences for session."""
        try:
            session_data = self.get_session(session_id)
            if not session_data or "preferences" not in session_data:
                return {}
            
            return json.loads(session_data["preferences"])
        except Exception as e:
            logger.error(f"Failed to get user preferences for session {session_id}: {e}")
            return {}
    
    def set_context(self, session_id: str, context: Dict[str, Any]) -> bool:
        """Set cross-request context for session."""
        try:
            return self.update_session(session_id, {"context": json.dumps(context)})
        except Exception as e:
            logger.error(f"Failed to set context for session {session_id}: {e}")
            return False
    
    def get_context(self, session_id: str) -> Dict[str, Any]:
        """Get cross-request context for session."""
        try:
            session_data = self.get_session(session_id)
            if not session_data or "context" not in session_data:
                return {}
            
            return json.loads(session_data["context"])
        except Exception as e:
            logger.error(f"Failed to get context for session {session_id}: {e}")
            return {}
    
    def delete_session(self, session_id: str) -> bool:
        """Delete session."""
        try:
            session_key = self._get_session_key(session_id)
            success = self._redis.delete(session_key, namespace=self._session_namespace)
            
            if success:
                logger.info(f"Deleted session {session_id}")
            
            return success
            
        except RedisError as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False
    
    def extend_session(self, session_id: str, hours: int = None) -> bool:
        """Extend session TTL."""
        try:
            session_key = self._get_session_key(session_id)
            ttl_hours = hours or self.session_ttl_hours
            
            # Get current data and re-set with new TTL
            session_data = self.get_session(session_id)
            if not session_data:
                return False
            
            success = self._redis.set(
                key=session_key,
                value=session_data,
                namespace=self._session_namespace,
                ttl_hours=ttl_hours
            )
            
            if success:
                logger.debug(f"Extended session {session_id} TTL to {ttl_hours} hours")
            
            return success
            
        except RedisError as e:
            logger.error(f"Failed to extend session {session_id}: {e}")
            return False
    
    def _update_session_access(self, session_id: str) -> None:
        """Update session access time and count."""
        try:
            current_data = self.get_session(session_id)
            if current_data:
                access_count = int(current_data.get("access_count", "0")) + 1
                updates = {
                    "last_accessed": datetime.now().isoformat(),
                    "access_count": str(access_count)
                }
                self.update_session(session_id, updates, extend_ttl=False)
        except Exception as e:
            logger.error(f"Failed to update session access for {session_id}: {e}")
    
    def _track_user_session(self, user_id: str, session_id: str) -> None:
        """Track user's active sessions."""
        try:
            # Add to user's session list
            user_sessions_key = f"user_sessions:{user_id}"
            self._redis._get_client().sadd(user_sessions_key, session_id)
            self._redis._get_client().expire(user_sessions_key, self.session_ttl_hours * 3600)
        except Exception as e:
            logger.error(f"Failed to track user session for {user_id}: {e}")
    
    def get_user_sessions(self, user_id: str) -> List[str]:
        """Get all active sessions for a user."""
        try:
            user_sessions_key = f"user_sessions:{user_id}"
            sessions = self._redis._get_client().smembers(user_sessions_key)
            return list(sessions)
        except Exception as e:
            logger.error(f"Failed to get user sessions for {user_id}: {e}")
            return []
    
    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions and return count cleaned."""
        try:
            # Redis handles TTL automatically, but we can do additional cleanup
            # This is mainly for tracking and stats purposes
            return 0
        except RedisError as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")
            return 0
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics."""
        try:
            # Get all session keys
            session_keys = self._redis.keys("*", namespace=self._session_namespace)
            active_sessions = len(session_keys)
            
            # Get some basic stats
            total_queries = 0
            total_accesses = 0
            recent_sessions = 0
            
            cutoff_time = datetime.now() - timedelta(hours=1)
            
            for session_key in session_keys[:100]:  # Sample first 100 for performance
                session_data = self.get_session(session_key.replace(f"{self._session_namespace}:", ""))
                if session_data:
                    total_queries += int(session_data.get("query_count", "0"))
                    total_accesses += int(session_data.get("access_count", "0"))
                    
                    last_access = datetime.fromisoformat(session_data.get("last_accessed", "1970-01-01T00:00:00"))
                    if last_access > cutoff_time:
                        recent_sessions += 1
            
            return {
                "active_sessions": active_sessions,
                "total_queries": total_queries,
                "total_accesses": total_accesses,
                "recent_sessions_1h": recent_sessions,
                "session_ttl_hours": self.session_ttl_hours,
                "cleanup_interval_hours": self.cleanup_interval_hours
            }
            
        except RedisError as e:
            logger.error(f"Failed to get session stats: {e}")
            return {"error": str(e)}
    
    def clear_all_sessions(self) -> bool:
        """Clear all sessions."""
        try:
            session_keys = self._redis.keys("*", namespace=self._session_namespace)
            if session_keys:
                full_keys = [self._get_session_key(key) for key in session_keys]
                result = self._redis._get_client().delete(*full_keys)
                logger.info(f"Cleared {len(session_keys)} sessions")
                return bool(result)
            return True
            
        except RedisError as e:
            logger.error(f"Failed to clear all sessions: {e}")
            return False
    
    def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            self._redis.close()
        logger.info("SessionManager closed")


# Global session manager instance
_session_manager_instance: Optional[SessionManager] = None


def get_session_manager() -> Optional[SessionManager]:
    """Get global session manager instance."""
    global _session_manager_instance
    if _session_manager_instance is None:
        try:
            _session_manager_instance = SessionManager()
        except Exception as e:
            logger.error(f"Failed to create session manager instance: {e}")
            _session_manager_instance = None
    return _session_manager_instance


def set_session_manager_instance(manager: SessionManager) -> None:
    """Set global session manager instance (for testing)."""
    global _session_manager_instance
    _session_manager_instance = manager