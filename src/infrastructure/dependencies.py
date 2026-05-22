import logging
import threading
from typing import TYPE_CHECKING, Protocol, runtime_checkable


@runtime_checkable
class Closable(Protocol):
    def close(self) -> None: ...


@runtime_checkable
class Stoppable(Protocol):
    def stop(self) -> None: ...

if TYPE_CHECKING:
    from infrastructure.cache.memory_cache import MemoryCache
    from infrastructure.cache.redis_cache import RedisCache
    from infrastructure.cache.config import CacheConfig
    from infrastructure.cache.cache_manager import CacheManager
    from infrastructure.cache.serialization import SerializationManager
    from infrastructure.cache.session_manager import SessionManager
    from infrastructure.memory.short_term.memory import ShortTermMemory
    from infrastructure.memory.memory_manager import MemoryManager
    from infrastructure.llm.llm_provider import LLMProvider
    from infrastructure.observability.metrics.collector import MetricsCollector
    from infrastructure.observability.alerting.manager import AlertManager
    from infrastructure.guardrails.output_guardrails import OutputGuardrails

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
        self.memory_cache: MemoryCache | None = None
        self.redis_cache: RedisCache | None = None
        self.cache_config: CacheConfig | None = None
        self.cache_manager: CacheManager | None = None
        self.serialization_manager: SerializationManager | None = None

        # Session
        self.session_manager: SessionManager | None = None

        # Memory
        self.short_term_memory: ShortTermMemory | None = None
        self.memory_manager: MemoryManager | None = None

        # LLM / Agent
        self.llm_provider: LLMProvider | None = None

        # Guardrails
        self.output_guardrails: OutputGuardrails | None = None

        # Observability
        self.metrics_collector: MetricsCollector | None = None
        self.alert_manager: AlertManager | None = None

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

        # ------ Tier 3 – Memory manager -------------------------------
        self._init_memory_manager()

        # ------ Tier 5 – Guardrails -----------------------------------
        self._init_output_guardrails()

        # ------ Tier 6 – LLM Provider --------------------------------
        self._init_llm_provider()

        # ------ Tier 7 – Observability --------------------------------
        self._init_observability()

        logger.info("All dependencies initialised")

    # ------------------------------------------------------------------
    # Shutdown – reverse order
    # ------------------------------------------------------------------
    def shutdown(self) -> None:
        logger.info("Shutting down application dependencies …")

        _stop_components: list[tuple[object | None, str]] = [
            (self.memory_manager, "MemoryManager"),
            (self.alert_manager, "AlertManager"),
            (self.metrics_collector, "MetricsCollector"),
        ]
        _close_components: list[tuple[object | None, str]] = [
            (self.short_term_memory, "ShortTermMemory"),
            (self.session_manager, "SessionManager"),
            (self.cache_manager, "CacheManager"),
            (self.redis_cache, "RedisCache"),
            (self.memory_cache, "MemoryCache"),
            (self.llm_provider, "LLMProvider"),
        ]

        for comp, name in _stop_components:
            if comp is None:
                continue
            try:
                if isinstance(comp, Stoppable):
                    comp.stop()
                elif hasattr(comp, "stop_background_tasks"):
                    comp.stop_background_tasks()
            except Exception:
                logger.exception("Error stopping %s", name)

        for comp, name in _close_components:
            if comp is None:
                continue
            try:
                if isinstance(comp, Closable):
                    comp.close()
            except Exception:
                logger.exception("Error closing %s", name)

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
            if redis.get_raw_client() is not None:
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

    def _init_memory_manager(self) -> None:
        try:
            from infrastructure.memory.memory_manager import MemoryManager

            self.memory_manager = MemoryManager()
            if hasattr(self.memory_manager, "start_background_tasks"):
                self.memory_manager.start_background_tasks()
            logger.debug("MemoryManager initialised")
        except Exception as e:
            logger.warning("Failed to init MemoryManager: %s", e)

    def _init_llm_provider(self) -> None:
        from infrastructure.llm.llm_provider import LLMProvider

        try:
            self.llm_provider = LLMProvider()
            logger.debug("LLMProvider initialised")
        except Exception as e:
            logger.warning("Failed to init LLMProvider: %s", e)

    def _init_output_guardrails(self) -> None:
        from infrastructure.guardrails.output_guardrails import OutputGuardrails

        try:
            self.output_guardrails = OutputGuardrails()
            logger.debug("OutputGuardrails initialised")
        except Exception as e:
            logger.warning("Failed to init OutputGuardrails: %s", e)

    def _init_observability(self) -> None:
        try:
            from infrastructure.observability import init_observability
            from infrastructure.observability.metrics.collector import (
                MetricsCollector,
                set_metrics_collector_instance,
            )

            self.metrics_collector = MetricsCollector()
            set_metrics_collector_instance(self.metrics_collector)
            self.alert_manager = init_observability()
            logger.debug("Observability initialised")
        except Exception as e:
            logger.warning("Failed to init observability: %s", e)


# ------------------------------------------------------------------
# Thread-safe singleton access
# ------------------------------------------------------------------
_deps: Dependencies | None = None
_deps_initialized: bool = False
_deps_lock = threading.Lock()


def get_deps() -> Dependencies | None:
    """Return the global Dependencies container, or ``None`` if not yet initialised."""
    global _deps
    if _deps is None:
        with _deps_lock:
            if _deps is None:
                _deps = Dependencies()
    return _deps


def init_deps() -> Dependencies:
    """Create (if needed) and initialise the global Dependencies container.

    Thread-safe: creation and initialisation are performed atomically under lock.
    Subsequent calls are idempotent.
    """
    global _deps, _deps_initialized
    with _deps_lock:
        if _deps is None:
            _deps = Dependencies()
        if not _deps_initialized:
            _deps.init()
            _deps_initialized = True
    return _deps


def shutdown_deps() -> None:
    """Shut down the global Dependencies container (idempotent)."""
    global _deps, _deps_initialized
    with _deps_lock:
        deps = _deps
        if deps is not None:
            deps.shutdown()
            _deps_initialized = False
            _deps = None
