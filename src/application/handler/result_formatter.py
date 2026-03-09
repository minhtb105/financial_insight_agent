from typing import Any, Dict


def ok(data: Any, meta: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Format chuẩn cho response thành công.
    """
    return {
        "status": "ok",
        "data": data,
        "meta": meta or {},
        "error": None
    }


def fail(message: str, meta: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Format chuẩn cho response thất bại.
    """
    return {
        "status": "error",
        "data": None,
        "meta": meta or {},
        "error": message
    }
