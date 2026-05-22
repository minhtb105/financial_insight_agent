import pytest

# ---------------------------------------------------------------------------
# Marker-based path routing — auto-apply markers by test directory
# ---------------------------------------------------------------------------


def pytest_configure(config):
    config.addinivalue_line("markers", "unit: Unit tests (no external dependencies)")
    config.addinivalue_line("markers", "integration: Integration tests (require external services)")
    config.addinivalue_line("markers", "slow: Tests that take longer than normal")


def pytest_collection_modifyitems(config, items):
    marker_map = {
        "unit": pytest.mark.unit,
        "integration": pytest.mark.integration,
    }
    for item in items:
        path = item.nodeid
        for keyword, marker in marker_map.items():
            if f"/{keyword}/" in path or f"\\{keyword}\\" in path:
                if keyword not in item.keywords:
                    item.add_marker(marker)
                break
