import os
import logging
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

logger = logging.getLogger(__name__)

_SKIP_REASON = "OPENAI_API_KEY not set — integration tests against real LLM skipped"
_API_KEY_MISSING = not os.getenv("OPENAI_API_KEY")


def pytest_configure(config):
    if _API_KEY_MISSING:
        logger.warning(_SKIP_REASON)


@pytest.fixture(scope="session", autouse=True)
def _mock_infrastructure():
    """Mock all infrastructure so integration tests work without API keys or external services."""
    with (
        patch("interfaces.api.app.StockAgent") as mock_agent_cls,
        patch("interfaces.api.app.GuardrailPipeline") as mock_gr_cls,
        patch("interfaces.api.app.init_deps") as mock_init,
        patch("interfaces.api.app.shutdown_deps") as mock_shutdown,
    ):
        mock_agent = MagicMock()
        mock_agent.run.return_value = "Giá đóng cửa của VCB hôm qua là 105,000 VND."
        mock_agent.run_stream.return_value = iter(["Giá đóng ", "cửa của ", "VCB hôm qua là 105,000 VND."])
        mock_agent_cls.return_value = mock_agent

        mock_gr = MagicMock()
        mock_gr.check.return_value = MagicMock(passed=True)
        mock_gr_cls.return_value = mock_gr

        yield mock_agent_cls, mock_gr_cls


@pytest.fixture
def client(_mock_infrastructure):
    from interfaces.api.app import app

    with TestClient(app) as c:
        yield c
