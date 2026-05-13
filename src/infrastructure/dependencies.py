import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)


class Dependencies:
    """Single source of truth for all application singletons.

    Initialized once via :func:`init_deps()` in FastAPI lifespan.
    Every ``get_*()`` function across cache/memory modules delegates here first,
    falling back to legacy per-module singletons only when the container is not yet
    initialised (module-level code that runs before lifespan).
    """

    def __init__(self) -> None:
        # Cache layer
        self.memory_cache: Optional["MemoryCache"] = None
        self.redis_cache: Optional["RedisCache"] = None
        self.cache_config: Optional["CacheConfig"] = None
        self.cache_manager: Optional["CacheManager"] = None
        self.serialization_manager: Optional["SerializationManager"] = None

        # Session
        self.session_manager: Optional["SessionManager"] = None

        # Memory
        self.short_term_memory: Optional["ShortTermMemory"] = None
        self.episodic_memory: Optional["EpisodicMemory"] = None
        self.long_term_memory: Optional["LongTermMemory"] = None
        self.memory_manager: Optional["MemoryManager"] = None

        # LLM / Agent
        self.llm_provider: Optional["LLMProvider"] = None

        # Observability
        self.metrics_collector: Optional["MetricsCollector"] = None
        self.alert_manager: Optional["AlertManager"] = None

    # ------------------------------------------------------------------
    # Initialisation – ordered by dependency, each tier is optional
    # ------------------------------------------------------------------
    def init(self) -> None:
        logger.info("Initialising application dependencies …")

        # ------ Tier 1 – no external services -------------------------
        self._init_serialization()
        self._init_memory_cache()
        self._init_cache_config()

        # ------ Tier 2 – Redis (optional) -----------------------------
        self._init_redis_cache()
        self._init_cache_manager()
        self._init_session_manager()
        self._init_short_term_memory()

        # ------ Tier 3 – PostgreSQL (optional) ------------------------
        self._init_episodic_memory()
        self._init_long_term_memory()

        # ------ Tier 4 – Memory manager -------------------------------
        self._init_memory_manager()

        # ------ Tier 5 – Observability --------------------------------
        self._init_observability()

        logger.info("All dependencies initialised")

    # ------------------------------------------------------------------
    # Shutdown – reverse order
    # ------------------------------------------------------------------
    def shutdown(self) -> None:
        logger.info("Shutting down application dependencies …")

        if self.memory_manager is not None:
            try:
                self.memory_manager.stop()
            except Exception:
                logger.exception("Error stopping MemoryManager")
        if self.long_term_memory is not None:
            try:
                self.long_term_memory.close()
            except Exception:
                logger.exception("Error closing LongTermMemory")
        if self.episodic_memory is not None:
            try:
                self.episodic_memory.close()
            except Exception:
                logger.exception("Error closing EpisodicMemory")
        if self.short_term_memory is not None:
            try:
                self.short_term_memory.close()
            except Exception:
                logger.exception("Error closing ShortTermMemory")
        if self.session_manager is not None:
            try:
                self.session_manager.close()
            except Exception:
                logger.exception("Error closing SessionManager")
        if self.redis_cache is not None:
            try:
                self.redis_cache.close()
            except Exception:
                logger.exception("Error closing RedisCache")
        if self.memory_cache is not None:
            try:
                self.memory_cache.close()
            except Exception:
                logger.exception("Error closing MemoryCache")

        if self.alert_manager is not None:
            try:
                self.alert_manager.stop()
            except Exception:
                logger.exception("Error stopping AlertManager")

        logger.info("All dependencies shut down")

    # ------------------------------------------------------------------
    # Tier-initialisers
    # ------------------------------------------------------------------
    def _init_serialization(self) -> None:
        from infrastructure.cache.serialization import SerializationManager
        try:
            self.serialization_manager = SerializationManager()
            logger.debug("SerializationManager initialised")
        except Exception as e:
            logger.warning("Failed to init SerializationManager: %s", e)

    def _init_memory_cache(self) -> None:
        from infrastructure.cache.memory_cache import MemoryCache
        try:
            self.memory_cache = MemoryCache()
            logger.debug("MemoryCache initialised")
        except Exception as e:
            logger.warning("Failed to init MemoryCache: %s", e)

    def _init_cache_config(self) -> None:
        from infrastructure.cache.config import CacheConfig
        try:
            self.cache_config = CacheConfig()
            logger.debug("CacheConfig initialised")
        except Exception as e:
            logger.warning("Failed to init CacheConfig: %s", e)

    def _init_redis_cache(self) -> None:
        from infrastructure.cache.redis_cache import RedisCache
        try:
            redis = RedisCache()
            if redis._get_client() is not None:
                self.redis_cache = redis
                logger.debug("RedisCache initialised")
        except Exception as e:
            logger.warning("Redis unavailable — running in degraded mode: %s", e)

    def _init_cache_manager(self) -> None:
        if self.redis_cache is None:
            logger.debug("Skipping CacheManager (Redis unavailable)")
            return
        from infrastructure.cache.cache_manager import CacheManager
        try:
            self.cache_manager = CacheManager(
                enable_l1=True,
                enable_l2=True,
            )
            logger.debug("CacheManager initialised")
        except Exception as e:
            logger.warning("Failed to init CacheManager: %s", e)

    def _init_session_manager(self) -> None:
        if self.redis_cache is None:
            logger.debug("Skipping SessionManager (Redis unavailable)")
            return
        from infrastructure.cache.session_manager import SessionManager
        try:
            self.session_manager = SessionManager()
            logger.debug("SessionManager initialised")
        except Exception as e:
            logger.warning("Failed to init SessionManager: %s", e)

    def _init_short_term_memory(self) -> None:
        if self.redis_cache is None:
            logger.debug("Skipping ShortTermMemory (Redis unavailable)")
            return
        from infrastructure.memory.short_term.memory import ShortTermMemory
        try:
            self.short_term_memory = ShortTermMemory()
            logger.debug("ShortTermMemory initialised")
        except Exception as e:
            logger.warning("Failed to init ShortTermMemory: %s", e)

    def _init_episodic_memory(self) -> None:
        try:
            from infrastructure.memory.episodic.memory import EpisodicMemory
            self.episodic_memory = EpisodicMemory()
            logger.debug("EpisodicMemory initialised")
        except Exception as e:
            logger.warning("PostgreSQL (episodic) unavailable — %s", e)

    def _init_long_term_memory(self) -> None:
        try:
            from infrastructure.memory.long_term.memory import LongTermMemory
            self.long_term_memory = LongTermMemory()
            logger.debug("LongTermMemory initialised")
        except Exception as e:
            logger.warning("PostgreSQL (long-term) unavailable — %s", e)

    def _init_memory_manager(self) -> None:
        try:
            from infrastructure.memory.memory_manager import MemoryManager
            self.memory_manager = MemoryManager()
            if hasattr(self.memory_manager, "start_background_tasks"):
                self.memory_manager.start_background_tasks()
            logger.debug("MemoryManager initialised")
        except Exception as e:
            logger.warning("Failed to init MemoryManager: %s", e)

    def _init_observability(self) -> None:
        try:
            from infrastructure.observability import init_observability
            from infrastructure.observability.metrics.collector import get_metrics_collector
            self.metrics_collector = get_metrics_collector()
            self.alert_manager = init_observability()
            logger.debug("Observability initialised")
        except Exception as e:
            logger.warning("Failed to init observability: %s", e)


# ------------------------------------------------------------------
# Thread-safe singleton access
# ------------------------------------------------------------------
_deps: Optional[Dependencies] = None
_deps_lock = threading.Lock()


def get_deps() -> Optional[Dependencies]:
    """Return the global Dependencies container, or ``None`` if not yet initialised."""
    global _deps
    if _deps is None:
        with _deps_lock:
            if _deps is None:
                _deps = Dependencies()
    return _deps


def init_deps() -> Dependencies:
    """Create (if needed) and initialise the global Dependencies container."""
    deps = get_deps()
    if deps is not None:
        deps.init()
    return deps


def shutdown_deps() -> None:
    """Shut down the global Dependencies container (idempotent)."""
    deps = get_deps()
    if deps is not None:
        deps.shutdown()
