"""
Memory manager for the financial insight agent.

Manages short-term Redis-backed memory with periodic cleanup.
Supports per-user isolation via user_id.
"""

import atexit
import logging
from typing import Any
from datetime import datetime, timezone
import threading
from dataclasses import dataclass

from infrastructure.memory.short_term.memory import get_short_term_memory

logger = logging.getLogger(__name__)


@dataclass
class MemoryConfig:
    """Configuration for memory management."""

    auto_cleanup_enabled: bool = True
    cleanup_interval_hours: int = 24
    # Sliding window: how many recent turns Reformulation receives.
    window_size: int = 5
    # Episodic (Qdrant) retrieval settings.
    episodic_enabled: bool = True
    episodic_top_k: int = 5
    episodic_min_score: float = 0.5


class MemoryManager:
    """
    Orchestrates short-term memory with periodic cleanup.
    All methods support optional user_id for per-user isolation.

    Tiers exposed via search_memory:
    - "working": last-turn (q_{t-1}, r_{t-1}, q_t) payload for Reformulation.
    - "sliding": k recent turns (chronological) + summary state.
    - "episodic": semantic hits from Qdrant past turns.
    - "short_term": legacy shape {interactions, facts, count}.
    """

    def __init__(self, config: MemoryConfig | None = None):
        self.config = config or MemoryConfig()
        self.short_term = get_short_term_memory()
        self.episodic = self._init_episodic()
        self._cleanup_lock = threading.Lock()
        self._last_cleanup = datetime.now(timezone.utc)
        self._stop_event = threading.Event()
        self._cleanup_task = None
        logger.info("Initialized MemoryManager with short-term memory")

    def _init_episodic(self):  # type: ignore[no-untyped-def]
        """Lazily build the episodic store; None when disabled/unavailable."""
        if not self.config.episodic_enabled:
            return None
        try:
            from infrastructure.memory.episodic.store import EpisodicStore

            return EpisodicStore(
                top_k=self.config.episodic_top_k,
                min_score=self.config.episodic_min_score,
            )
        except Exception as e:
            logger.warning("Episodic memory unavailable: %s", e)
            return None

    def _validated_user_id(self, user_id: str | None) -> str:
        # Strict per-user isolation: None/empty -> anonymous (not global). Caller should pass real user_id.
        if user_id is None or user_id == "":
            logger.debug("Memory call without user_id -> using anonymous isolation")
            return "anonymous"
        return user_id

    def add_interaction(
        self,
        user_query: str,
        agent_response: str,
        context: dict[str, Any] | None = None,
        confidence: float = 0.5,
        user_id: str | None = None,
    ) -> bool:
        if not self.short_term:
            logger.error("Short-term memory not available")
            return False
        try:
            return self.short_term.add_interaction(
                user_query=user_query,
                agent_response=agent_response,
                context=context,
                confidence=confidence,
                user_id=self._validated_user_id(user_id),
            )
        except Exception as e:
            logger.error(f"Failed to add interaction to memory: {e}")
            return False

    def search_memory(
        self,
        query: str,
        query_type: str | None = None,
        memory_tiers: list[str] | None = None,
        top_k: int = 10,
        user_id: str | None = None,
    ) -> dict[str, list[Any]]:
        tiers = memory_tiers or ["short_term"]
        results: dict[str, Any] = {}
        uid = self._validated_user_id(user_id)
        if "short_term" in tiers and self.short_term:
            try:
                interactions = self.short_term.get_recent_interactions(limit=top_k, user_id=uid)
                facts = self.short_term.get_facts(user_id=uid)
                results["short_term"] = {
                    "interactions": interactions,
                    "facts": facts,
                    "count": len(interactions) + len(facts),
                }
            except Exception as e:
                logger.error(f"Failed to search short-term memory: {e}")
                results["short_term"] = {"error": str(e)}
        if "working" in tiers and self.short_term:
            try:
                results["working"] = self.short_term.build_working_payload(
                    current_raw_query=query, user_id=uid
                )
            except Exception as e:
                logger.error(f"Failed to build working memory: {e}")
                results["working"] = {"error": str(e)}
        if "sliding" in tiers and self.short_term:
            try:
                turns = self.short_term.get_last_k_turns(k=self.config.window_size, user_id=uid)
                summary = self.short_term.get_summary(user_id=uid)
                results["sliding"] = {
                    "turns": turns,
                    "summary": summary,
                    "count": len(turns),
                }
            except Exception as e:
                logger.error(f"Failed to search sliding memory: {e}")
                results["sliding"] = {"error": str(e)}
        if "episodic" in tiers:
            if self.episodic is None:
                results["episodic"] = {"hits": [], "context": "", "count": 0, "error": "unavailable"}
            else:
                try:
                    results["episodic"] = self.episodic.search_episodes(
                        query=query, user_id=uid, top_k=self.config.episodic_top_k
                    )
                except Exception as e:
                    logger.error(f"Failed to search episodic memory: {e}")
                    results["episodic"] = {"hits": [], "context": "", "count": 0, "error": str(e)}
        return results

    def build_reformulation_inputs(
        self,
        raw_query: str,
        user_id: str | None = None,
        window_k: int | None = None,
        episodic_top_k: int | None = None,
    ) -> dict[str, Any]:
        """Collect all memory inputs for the Reformulation step.

        Returns {"working": {...}, "sliding": {turns, summary}, "episodic": {hits,...}}.
        The Reformulation step calls this BEFORE query splitting.
        """
        uid = self._validated_user_id(user_id)
        out: dict[str, Any] = {
            "working": {
                "turn_id": None,
                "previous_user_query": "",
                "previous_system_response": "",
                "current_raw_query": raw_query,
            },
            "sliding": {"turns": [], "summary": {"entities": [], "topics": [], "updated_at": None}, "count": 0},
            "episodic": {"hits": [], "context": "", "count": 0},
        }
        if self.short_term:
            try:
                out["working"] = self.short_term.build_working_payload(raw_query, user_id=uid)
                out["sliding"] = {
                    "turns": self.short_term.get_last_k_turns(
                        k=window_k or self.config.window_size, user_id=uid
                    ),
                    "summary": self.short_term.get_summary(user_id=uid),
                    "count": 0,
                }
                out["sliding"]["count"] = len(out["sliding"]["turns"])
            except Exception as e:
                logger.error(f"Failed to build reformulation inputs (short-term): {e}")
        if self.episodic is not None:
            try:
                out["episodic"] = self.episodic.search_episodes(
                    query=raw_query, user_id=uid, top_k=episodic_top_k or self.config.episodic_top_k
                )
            except Exception as e:
                logger.error(f"Failed to build reformulation inputs (episodic): {e}")
                out["episodic"] = {"hits": [], "context": "", "count": 0, "error": str(e)}
        else:
            out["episodic"] = {"hits": [], "context": "", "count": 0, "error": "unavailable"}
        return out

    def _check_cleanup_trigger(self) -> None:
        if not self.config.auto_cleanup_enabled:
            return
        with self._cleanup_lock:
            now = datetime.now(timezone.utc)
            if (now - self._last_cleanup).total_seconds() < self.config.cleanup_interval_hours * 3600:
                return
            self._perform_cleanup()
            self._last_cleanup = now

    def _perform_cleanup(self) -> None:
        if self.short_term:
            try:
                self.short_term.cleanup_expired()
            except Exception as e:
                logger.error(f"Failed to cleanup short-term memory: {e}")

    def get_stats(self, user_id: str | None = None) -> dict[str, Any]:
        stats = {
            "config": {
                "auto_cleanup_enabled": self.config.auto_cleanup_enabled,
                "cleanup_interval_hours": self.config.cleanup_interval_hours,
                "window_size": self.config.window_size,
                "episodic_enabled": self.config.episodic_enabled,
                "episodic_top_k": self.config.episodic_top_k,
                "episodic_min_score": self.config.episodic_min_score,
            },
            "last_cleanup": self._last_cleanup.isoformat(),
            "tiers": {},
        }
        if self.short_term:
            try:
                stats["tiers"]["short_term"] = self.short_term.get_stats(user_id=self._validated_user_id(user_id))
            except Exception as e:
                stats["tiers"]["short_term"] = {"error": str(e)}
        if self.episodic is not None:
            try:
                stats["tiers"]["episodic"] = {"count": self.episodic.count(self._validated_user_id(user_id))}
            except Exception as e:
                stats["tiers"]["episodic"] = {"error": str(e)}
        return stats

    def clear_all(self, user_id: str | None = None) -> bool:
        ok = True
        if self.short_term:
            try:
                self.short_term.clear(user_id=self._validated_user_id(user_id))
            except Exception as e:
                logger.error(f"Failed to clear short-term memory: {e}")
                ok = False
        if self.episodic is not None:
            try:
                self.episodic.clear_user_episodes(self._validated_user_id(user_id))
            except Exception as e:
                logger.error(f"Failed to clear episodic memory: {e}")
                ok = False
        return ok

    def start_background_tasks(self) -> None:
        if self._cleanup_task is None:
            self._cleanup_task = threading.Thread(target=self._background_cleanup_loop, daemon=True)
            self._cleanup_task.start()
        atexit.register(self.stop_background_tasks)
        logger.info("Started background memory management tasks")

    def stop_background_tasks(self) -> None:
        self._stop_event.set()
        logger.info("Stopped background memory management tasks")

    def _background_cleanup_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._check_cleanup_trigger()
                self._stop_event.wait(self.config.cleanup_interval_hours * 3600)
            except Exception as e:
                logger.error(f"Error in cleanup background loop: {e}")
                if self._stop_event.wait(3600):
                    break


def get_memory_manager() -> MemoryManager | None:
    """Get memory manager instance from Dependencies container."""
    from infrastructure.dependencies import get_deps

    deps = get_deps()
    return deps.memory_manager if deps is not None else None
