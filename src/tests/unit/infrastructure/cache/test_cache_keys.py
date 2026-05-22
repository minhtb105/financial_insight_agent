"""Unit tests for cache key generation."""

from infrastructure.cache.cache_keys import make_cache_key, make_overview_cache_key


def test_make_cache_key_basic():
    key = make_cache_key("price", "VCB")
    assert key == "price:VCB"


def test_make_cache_key_with_dates():
    key = make_cache_key("price", "VCB", start="2026-03-01", end="2026-03-10")
    assert key == "price:VCB:2026-03-01:2026-03-10"


def test_make_cache_key_with_extra():
    key = make_cache_key("price", "VCB", interval="1d", requested_field="close")
    assert key.startswith("price:VCB:")
    assert len(key) > len("price:VCB:")
    assert key != "price:VCB"


def test_make_overview_cache_key():
    key = make_overview_cache_key("company", "VCB")
    assert key == "company:VCB"
