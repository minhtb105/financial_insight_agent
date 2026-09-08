"""Helpers for MCP tool wrappers — mirrors tool_registry error handling."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)
TOOL_ERR_PREFIX = "TOOL_ERR#"


def _categorize_error(e: Exception) -> str:
    if isinstance(e, TimeoutError):
        return f"{TOOL_ERR_PREFIX}TIMEOUT {e}"
    if isinstance(e, ValueError):
        return f"{TOOL_ERR_PREFIX}VALIDATION {e}"
    if isinstance(e, KeyError):
        return f"{TOOL_ERR_PREFIX}NOT_FOUND {e}"
    if isinstance(e, PermissionError):
        return f"{TOOL_ERR_PREFIX}AUTH {e}"
    return f"{TOOL_ERR_PREFIX}UNKNOWN {e}"


def _safe_json(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, indent=2)
    except (TypeError, ValueError):
        return str(obj)


def _wrap(fn_name: str, result: Any) -> str:
    if result is None:
        return _safe_json({"data": None, "note": f"No data returned for {fn_name}"})
    if isinstance(result, dict) and "error" in result:
        result = dict(result)
        error_keys = {k for k in result if k != "error"}
        if not error_keys:
            return _safe_json({"data": None, "note": f"Service error for {fn_name}: {result['error']}"})
        result["_partial_error"] = True
        result["_error"] = result.pop("error")
    return _safe_json(result)


def call_service(name: str, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> str:
    try:
        result = fn(*args, **kwargs)
    except Exception as e:
        logger.exception("%s failed", name)
        return _categorize_error(e)
    return _wrap(name, result)
