"""
Memory manager for the financial insight agent.

Orchestrates the 3-tier memory system with automatic migration,
deduplication, and temporal weighting.
"""

import logging
import time
from typing import Any, Optional, Dict, List
from datetime import datetime
import threading
from dataclasses import dataclass

from infrastructure.memory.short_term.memory import get_short_term_memory
from infrastructure.memory.episodic.memory import get_episodic_memory
from infrastructure.memory.long_term.memory import get_long_term_memory

logger = logging.getLogger(__name__)


@dataclass
class MemoryConfig:
    """Configuration for memory management."""
    short_term_ttl_hours: int = 2
    short_term_max_messages: int = 100
    short_term_migration_threshold: int = 50
    
    episodic_similarity_threshold: float = 0.7
    episodic_max_episodes: int = 10000
    episodic_cleanup_days: int = 30
    
    long_term_temporal_decay_rate: float = 0.1
    long_term_max_company_profiles: int = 1000
    long_term_max_market_patterns: int = 500
    long_term_cleanup_months: int = 12
    
    # Migration policies
    auto_migration_enabled: bool = True
    migration_batch_size: int = 10
    migration_interval_minutes: int = 30
    
    # Cleanup policies
    auto_cleanup_enabled: bool = True
    cleanup_interval_hours: int = 24


class MemoryManager:
    """
    Orchestrates the 3-tier memory system with intelligent migration
    and cleanup policies.
    """
    
    def __init__(self, config: Optional[MemoryConfig] = None):
        """
        Initialize memory manager.
        
        Args:
            config: Memory configuration
        """
        self.config = config or MemoryConfig()
        
        # Initialize memory tiers
        self.short_term = get_short_term_memory()
        self.episodic = get_episodic_memory()
        self.long_term = get_long_term_memory()
        
        # Migration state
        self._migration_lock = threading.Lock()
        self._cleanup_lock = threading.Lock()
        self._last_migration = datetime.now()
        self._last_cleanup = datetime.now()
        
        # Background tasks
        self._migration_task = None
        self._cleanup_task = None
        
        logger.info("Initialized MemoryManager with 3-tier memory system")
    
    def add_interaction(
        self, 
        user_query: str, 
        agent_response: str, 
        context: Optional[Dict[str, Any]] = None,
        confidence: float = 0.5
    ) -> bool:
        """
        Add interaction to short-term memory.
        
        Args:
            user_query: User's question/query
            agent_response: Agent's response
            context: Additional context (parsed query, etc.)
            confidence: Confidence score for the interaction
            
        Returns:
            True if successful, False otherwise
        """
        if not self.short_term:
            logger.error("Short-term memory not available")
            return False
        
        try:
            success = self.short_term.add_interaction(
                user_query=user_query,
                agent_response=agent_response,
                context=context,
                confidence=confidence
            )
            
            if success:
                # Trigger immediate migration check
                self._check_migration_trigger()
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to add interaction to memory: {e}")
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
            fact_type: Type of fact
            fact_value: The fact value
            source: Source of the fact
            confidence: Confidence in the fact
            
        Returns:
            True if successful, False otherwise
        """
        if not self.short_term:
            logger.error("Short-term memory not available")
            return False
        
        try:
            return self.short_term.add_fact(
                fact_type=fact_type,
                fact_value=fact_value,
                source=source,
                confidence=confidence
            )
            
        except Exception as e:
            logger.error(f"Failed to add fact to memory: {e}")
            return False
    
    def search_memory(
        self, 
        query: str, 
        query_type: Optional[str] = None,
        memory_tiers: Optional[List[str]] = None,
        top_k: int = 10
    ) -> Dict[str, List[Any]]:
        """
        Search across memory tiers.
        
        Args:
            query: Search query
            query_type: Filter by query type
            memory_tiers: List of memory tiers to search (short_term, episodic, long_term)
            top_k: Number of results per tier
            
        Returns:
            Dictionary with search results from each tier
        """
        if not memory_tiers:
            memory_tiers = ["short_term", "episodic", "long_term"]
        
        results = {}
        
        # Search short-term memory
        if "short_term" in memory_tiers and self.short_term:
            try:
                interactions = self.short_term.get_recent_interactions(limit=top_k)
                facts = self.short_term.get_facts()
                results["short_term"] = {
                    "interactions": interactions,
                    "facts": facts,
                    "count": len(interactions) + len(facts)
                }
            except Exception as e:
                logger.error(f"Failed to search short-term memory: {e}")
                results["short_term"] = {"error": str(e)}
        
        # Search episodic memory
        if "episodic" in memory_tiers and self.episodic:
            try:
                episodes = self.episodic.search_episodes(
                    query=query,
                    query_type=query_type,
                    top_k=top_k
                )
                facts = self.episodic.search_facts(
                    query=query,
                    fact_type=query_type,
                    top_k=top_k
                )
                results["episodic"] = {
                    "episodes": [ep.summary for ep in episodes],
                    "facts": [fact.fact_value for fact in facts],
                    "count": len(episodes) + len(facts)
                }
            except Exception as e:
                logger.error(f"Failed to search episodic memory: {e}")
                results["episodic"] = {"error": str(e)}
        
        # Search long-term memory
        if "long_term" in memory_tiers and self.long_term:
            try:
                company_profiles = self.long_term.search_company_profiles(
                    query=query,
                    top_k=top_k
                )
                query_pattern = self.long_term.get_query_pattern(query_type) if query_type else None
                
                results["long_term"] = {
                    "company_profiles": [p.ticker for p in company_profiles],
                    "query_pattern": query_pattern.pattern_data if query_pattern else None,
                    "count": len(company_profiles) + (1 if query_pattern else 0)
                }
            except Exception as e:
                logger.error(f"Failed to search long-term memory: {e}")
                results["long_term"] = {"error": str(e)}
        
        return results
    
    def get_query_pattern(self, query_type: str) -> Optional[Dict[str, Any]]:
        """Get query pattern from long-term memory."""
        if not self.long_term:
            return None
        
        try:
            pattern = self.long_term.get_query_pattern(query_type)
            return pattern.pattern_data if pattern else None
        except Exception as e:
            logger.error(f"Failed to get query pattern: {e}")
            return None
    
    def update_query_pattern(
        self, 
        query_type: str, 
        success: bool, 
        response_time: float,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update query pattern in long-term memory."""
        if not self.long_term:
            return False
        
        try:
            return self.long_term.update_query_pattern(
                query_type=query_type,
                success=success,
                response_time=response_time,
                additional_data=additional_data
            )
        except Exception as e:
            logger.error(f"Failed to update query pattern: {e}")
            return False
    
    def _check_migration_trigger(self) -> None:
        """Check if migration to higher tiers is needed."""
        if not self.config.auto_migration_enabled:
            return
        
        with self._migration_lock:
            now = datetime.now()
            
            # Check if enough time has passed since last migration
            if (now - self._last_migration).total_seconds() < self.config.migration_interval_minutes * 60:
                return
            
            # Check short-term memory for migration trigger
            if self.short_term:
                try:
                    # Get recent interactions for migration
                    interactions = self.short_term.get_recent_interactions(
                        limit=self.config.migration_batch_size
                    )
                    
                    if len(interactions) >= self.config.short_term_migration_threshold:
                        self._migrate_to_episodic(interactions)
                        self._last_migration = now
                        
                except Exception as e:
                    logger.error(f"Failed to check migration trigger: {e}")
    
    def _migrate_to_episodic(self, interactions: List[Dict[str, Any]]) -> bool:
        """Migrate interactions from short-term to episodic memory."""
        if not self.episodic:
            logger.error("Episodic memory not available for migration")
            return False
        
        try:
            # Generate summary for the episode
            summary = self._generate_episode_summary(interactions)
            
            # Migrate to episodic memory
            success = self.episodic.migrate_from_short_term(
                interactions=interactions,
                summary=summary
            )
            
            if success:
                # Clean up migrated interactions from short-term memory
                # Note: This is a simplified approach - in practice you might want
                # more sophisticated cleanup logic
                logger.info(f"Migrated {len(interactions)} interactions to episodic memory")
                
                # Trigger deduplication
                self.episodic.deduplicate_facts()
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to migrate to episodic memory: {e}")
            return False
    
    def _generate_episode_summary(self, interactions: List[Dict[str, Any]]) -> str:
        """Generate summary for an episode."""
        if not interactions:
            return "Empty episode"
        
        # Analyze interactions to create meaningful summary
        query_types = []
        tickers = set()
        time_range = None
        
        for interaction in interactions:
            context = interaction.get("context", {})
            if "query_type" in context:
                query_types.append(context["query_type"])
            if "tickers" in context:
                tickers.update(context["tickers"])
        
        # Create summary
        most_common_type = max(set(query_types), key=query_types.count) if query_types else "unknown"
        ticker_str = ", ".join(list(tickers)[:5])  # Limit to first 5 tickers
        if len(tickers) > 5:
            ticker_str += f" (+{len(tickers)-5} more)"
        
        return f"Episode with {len(interactions)} {most_common_type} queries for {ticker_str}"
    
    def _check_cleanup_trigger(self) -> None:
        """Check if cleanup is needed."""
        if not self.config.auto_cleanup_enabled:
            return
        
        with self._cleanup_lock:
            now = datetime.now()
            
            # Check if enough time has passed since last cleanup
            if (now - self._last_cleanup).total_seconds() < self.config.cleanup_interval_hours * 3600:
                return
            
            self._perform_cleanup()
            self._last_cleanup = now
    
    def _perform_cleanup(self) -> None:
        """Perform cleanup across all memory tiers."""
        cleanup_results = {}
        
        # Cleanup short-term memory
        if self.short_term:
            try:
                cleaned = self.short_term.cleanup_expired()
                cleanup_results["short_term"] = cleaned
            except Exception as e:
                logger.error(f"Failed to cleanup short-term memory: {e}")
                cleanup_results["short_term"] = f"Error: {e}"
        
        # Cleanup episodic memory
        if self.episodic:
            try:
                cleaned = self.episodic.cleanup_old_episodes()
                deduplicated = self.episodic.deduplicate_facts()
                cleanup_results["episodic"] = {
                    "episodes_cleaned": cleaned,
                    "facts_deduplicated": deduplicated
                }
            except Exception as e:
                logger.error(f"Failed to cleanup episodic memory: {e}")
                cleanup_results["episodic"] = f"Error: {e}"
        
        # Cleanup long-term memory
        if self.long_term:
            try:
                cleaned = self.long_term.cleanup_old_data()
                cleanup_results["long_term"] = cleaned
            except Exception as e:
                logger.error(f"Failed to cleanup long-term memory: {e}")
                cleanup_results["long_term"] = f"Error: {e}"
        
        logger.info(f"Memory cleanup completed: {cleanup_results}")
    
    def apply_temporal_decay(self) -> None:
        """Apply temporal decay to long-term memory."""
        if self.long_term:
            try:
                self.long_term._apply_temporal_decay()
                logger.debug("Applied temporal decay to long-term memory")
            except Exception as e:
                logger.error(f"Failed to apply temporal decay: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive memory statistics."""
        stats = {
            "config": {
                "auto_migration_enabled": self.config.auto_migration_enabled,
                "auto_cleanup_enabled": self.config.auto_cleanup_enabled,
                "migration_interval_minutes": self.config.migration_interval_minutes,
                "cleanup_interval_hours": self.config.cleanup_interval_hours
            },
            "last_migration": self._last_migration.isoformat(),
            "last_cleanup": self._last_cleanup.isoformat(),
            "tiers": {}
        }
        
        # Short-term memory stats
        if self.short_term:
            try:
                stats["tiers"]["short_term"] = self.short_term.get_stats()
            except Exception as e:
                stats["tiers"]["short_term"] = {"error": str(e)}
        
        # Episodic memory stats
        if self.episodic:
            try:
                stats["tiers"]["episodic"] = self.episodic.get_stats()
            except Exception as e:
                stats["tiers"]["episodic"] = {"error": str(e)}
        
        # Long-term memory stats
        if self.long_term:
            try:
                stats["tiers"]["long_term"] = self.long_term.get_stats()
            except Exception as e:
                stats["tiers"]["long_term"] = {"error": str(e)}
        
        return stats
    
    def clear_all(self) -> bool:
        """Clear all memory tiers."""
        success = True
        
        if self.short_term:
            try:
                self.short_term.clear()
            except Exception as e:
                logger.error(f"Failed to clear short-term memory: {e}")
                success = False
        
        if self.episodic:
            try:
                self.episodic.clear()
            except Exception as e:
                logger.error(f"Failed to clear episodic memory: {e}")
                success = False
        
        if self.long_term:
            try:
                self.long_term.clear()
            except Exception as e:
                logger.error(f"Failed to clear long-term memory: {e}")
                success = False
        
        return success
    
    def start_background_tasks(self) -> None:
        """Start background cleanup and migration tasks."""
        if self._migration_task is None:
            self._migration_task = threading.Thread(
                target=self._background_migration_loop,
                daemon=True
            )
            self._migration_task.start()
        
        if self._cleanup_task is None:
            self._cleanup_task = threading.Thread(
                target=self._background_cleanup_loop,
                daemon=True
            )
            self._cleanup_task.start()
        
        logger.info("Started background memory management tasks")
    
    def stop_background_tasks(self) -> None:
        """Stop background tasks."""
        # Background tasks are daemon threads, they will stop when main thread exits
        logger.info("Background memory management tasks will stop with main process")
    
    def _background_migration_loop(self) -> None:
        """Background loop for automatic migration."""
        while True:
            try:
                self._check_migration_trigger()
                time.sleep(self.config.migration_interval_minutes * 60)
            except Exception as e:
                logger.error(f"Error in migration background loop: {e}")
                time.sleep(60)  # Wait 1 minute before retrying
    
    def _background_cleanup_loop(self) -> None:
        """Background loop for automatic cleanup."""
        while True:
            try:
                self._check_cleanup_trigger()
                time.sleep(self.config.cleanup_interval_hours * 3600)
            except Exception as e:
                logger.error(f"Error in cleanup background loop: {e}")
                time.sleep(3600)  # Wait 1 hour before retrying


# Global memory manager instance
_memory_manager_instance: Optional[MemoryManager] = None


def get_memory_manager() -> Optional[MemoryManager]:
    """Get global memory manager instance."""
    global _memory_manager_instance
    if _memory_manager_instance is None:
        try:
            _memory_manager_instance = MemoryManager()
            _memory_manager_instance.start_background_tasks()
        except Exception as e:
            logger.error(f"Failed to create memory manager instance: {e}")
            _memory_manager_instance = None
    return _memory_manager_instance


def set_memory_manager_instance(manager: MemoryManager) -> None:
    """Set global memory manager instance (for testing)."""
    global _memory_manager_instance
    _memory_manager_instance = manager