import threading
from unittest.mock import patch, MagicMock


from infrastructure.dependencies import Dependencies, get_deps, init_deps, shutdown_deps


class TestDependencies:
    def test_init_defaults_are_none(self):
        deps = Dependencies()
        assert deps.memory_cache is None
        assert deps.redis_cache is None
        assert deps.cache_config is None
        assert deps.cache_manager is None
        assert deps.serialization_manager is None
        assert deps.session_manager is None
        assert deps.short_term_memory is None
        assert deps.memory_manager is None
        assert deps.llm_provider is None
        assert deps.metrics_collector is None
        assert deps.alert_manager is None

    @patch("infrastructure.dependencies.Dependencies._init_serialization")
    @patch("infrastructure.dependencies.Dependencies._init_memory_cache")
    @patch("infrastructure.dependencies.Dependencies._init_cache_config")
    @patch("infrastructure.dependencies.Dependencies._init_redis_cache")
    @patch("infrastructure.dependencies.Dependencies._init_cache_manager")
    @patch("infrastructure.dependencies.Dependencies._init_session_manager")
    @patch("infrastructure.dependencies.Dependencies._init_short_term_memory")
    @patch("infrastructure.dependencies.Dependencies._init_memory_manager")
    @patch("infrastructure.dependencies.Dependencies._init_llm_provider")
    @patch("infrastructure.dependencies.Dependencies._init_observability")
    def test_init_calls_all_tiers(self, *mocks):
        deps = Dependencies()
        deps.init()
        for m in mocks:
            m.assert_called_once()

    def test_shutdown_no_crash_when_none(self):
        deps = Dependencies()
        deps.shutdown()

    def test_shutdown_calls_stop_on_manager(self):
        deps = Dependencies()
        deps.memory_manager = MagicMock()
        deps.alert_manager = MagicMock()
        deps.metrics_collector = MagicMock()
        deps.shutdown()
        deps.memory_manager.stop_background_tasks.assert_called_once()
        deps.alert_manager.stop.assert_called_once()
        deps.metrics_collector.stop.assert_called_once()

    def test_shutdown_calls_close_on_services(self):
        deps = Dependencies()
        for attr in (
            "short_term_memory",
            "session_manager",
            "cache_manager",
            "redis_cache",
            "memory_cache",
            "llm_provider",
        ):
            mock = MagicMock()
            setattr(deps, attr, mock)
        deps.shutdown()
        for attr in (
            "short_term_memory",
            "session_manager",
            "cache_manager",
            "redis_cache",
            "memory_cache",
            "llm_provider",
        ):
            getattr(deps, attr).close.assert_called_once()

    def test_shutdown_handles_close_exception(self):
        deps = Dependencies()
        mock = MagicMock()
        mock.close.side_effect = RuntimeError("boom")
        deps.short_term_memory = mock
        deps.shutdown()

    @patch("infrastructure.cache.serialization.SerializationManager")
    def test_init_serialization_success(self, mock_mgr):
        deps = Dependencies()
        deps._init_serialization()
        assert deps.serialization_manager is not None

    @patch("infrastructure.cache.serialization.SerializationManager", side_effect=Exception("fail"))
    def test_init_serialization_failure(self, mock_mgr):
        deps = Dependencies()
        deps._init_serialization()
        assert deps.serialization_manager is None

    @patch("infrastructure.cache.memory_cache.MemoryCache")
    def test_init_memory_cache_success(self, mock_cache):
        deps = Dependencies()
        deps._init_memory_cache()
        assert deps.memory_cache is not None

    @patch("infrastructure.cache.config.CacheConfig")
    def test_init_cache_config_success(self, mock_cfg):
        deps = Dependencies()
        deps._init_cache_config()
        assert deps.cache_config is not None

    @patch("infrastructure.cache.config.CacheConfig", side_effect=Exception("cfg fail"))
    def test_init_cache_config_graceful(self, mock_cfg):
        deps = Dependencies()
        deps._init_cache_config()
        assert deps.cache_config is None

    @patch("infrastructure.cache.redis_cache.RedisCache")
    def test_init_redis_cache_no_client(self, mock_redis):
        mock_redis.return_value.get_raw_client.return_value = None
        deps = Dependencies()
        deps._init_redis_cache()
        assert deps.redis_cache is None

    @patch("infrastructure.cache.redis_cache.RedisCache")
    def test_init_redis_cache_with_client(self, mock_redis):
        mock_redis.return_value.get_raw_client.return_value = MagicMock()
        deps = Dependencies()
        deps._init_redis_cache()
        assert deps.redis_cache is not None

    @patch("infrastructure.cache.redis_cache.RedisCache", side_effect=Exception("conn refused"))
    def test_init_redis_cache_graceful(self, mock_redis):
        deps = Dependencies()
        deps._init_redis_cache()
        assert deps.redis_cache is None

    def test_init_cache_manager_skipped_when_no_redis(self):
        deps = Dependencies()
        deps.redis_cache = None
        deps._init_cache_manager()
        assert deps.cache_manager is None

    @patch("infrastructure.cache.cache_manager.CacheManager")
    def test_init_cache_manager_success(self, mock_mgr):
        deps = Dependencies()
        deps.redis_cache = MagicMock()
        deps._init_cache_manager()
        assert deps.cache_manager is not None

    def test_init_session_skipped_when_no_redis(self):
        deps = Dependencies()
        deps.redis_cache = None
        deps._init_session_manager()
        assert deps.session_manager is None

    def test_init_short_term_skipped_when_no_redis(self):
        deps = Dependencies()
        deps.redis_cache = None
        deps._init_short_term_memory()
        assert deps.short_term_memory is None

    @patch("infrastructure.memory.memory_manager.MemoryManager")
    def test_init_memory_manager_starts_background(self, mock_mm):
        deps = Dependencies()
        deps._init_memory_manager()
        assert deps.memory_manager is not None
        deps.memory_manager.start_background_tasks.assert_called_once()

    @patch("infrastructure.memory.memory_manager.MemoryManager", side_effect=Exception("oom"))
    def test_init_memory_manager_graceful(self, mock_mm):
        deps = Dependencies()
        deps._init_memory_manager()
        assert deps.memory_manager is None

    @patch("infrastructure.memory.memory_manager.MemoryManager")
    def test_init_memory_manager_no_start_background(self, mock_mm):
        mock_mm.return_value = MagicMock(spec=[])
        deps = Dependencies()
        deps._init_memory_manager()

    @patch("infrastructure.llm.llm_provider.LLMProvider")
    def test_init_llm_provider_success(self, mock_llm):
        deps = Dependencies()
        deps._init_llm_provider()
        assert deps.llm_provider is not None

    @patch("infrastructure.llm.llm_provider.LLMProvider", side_effect=Exception("no key"))
    def test_init_llm_provider_graceful(self, mock_llm):
        deps = Dependencies()
        deps._init_llm_provider()
        assert deps.llm_provider is None

    @patch("infrastructure.observability.metrics.collector.get_metrics_collector")
    @patch("infrastructure.observability.init_observability")
    def test_init_observability_success(self, mock_init, mock_metrics):
        deps = Dependencies()
        deps._init_observability()
        assert deps.metrics_collector is not None
        assert deps.alert_manager is not None

    @patch("infrastructure.observability.init_observability", side_effect=Exception("obs down"))
    def test_init_observability_graceful(self, mock_init):
        deps = Dependencies()
        deps._init_observability()
        assert deps.alert_manager is None


class TestDepsFunctions:
    def teardown_method(self):
        import infrastructure.dependencies as mod

        mod._deps = None
        mod._deps_initialized = False

    def test_get_deps_returns_same_instance(self):
        d1 = get_deps()
        d2 = get_deps()
        assert d1 is d2

    def test_get_deps_thread_safety(self):
        results = []

        def get():
            results.append(get_deps())

        threads = [threading.Thread(target=get) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert all(r is results[0] for r in results)

    @patch("infrastructure.dependencies.Dependencies.init")
    def test_init_deps_calls_init(self, mock_init):
        result = init_deps()
        mock_init.assert_called_once()
        assert result is not None

    @patch("infrastructure.dependencies.Dependencies.init")
    def test_init_deps_is_idempotent(self, mock_init):
        init_deps()
        init_deps()
        mock_init.assert_called_once()

    @patch("infrastructure.dependencies.Dependencies.init")
    def test_init_deps_thread_safety(self, mock_init):
        results = []

        def init():
            results.append(init_deps())

        threads = [threading.Thread(target=init) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        mock_init.assert_called_once()
        assert all(r is results[0] for r in results)

    @patch("infrastructure.dependencies.Dependencies.shutdown")
    def test_shutdown_deps(self, mock_shutdown):
        import infrastructure.dependencies as mod

        mod._deps = Dependencies()
        mod._deps_initialized = True
        shutdown_deps()
        mock_shutdown.assert_called_once()

    def test_shutdown_deps_idempotent_no_crash(self):
        shutdown_deps()
        shutdown_deps()
