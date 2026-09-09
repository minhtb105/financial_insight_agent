"""Memory routes — per-user memory inspection and cleanup."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from infrastructure.auth.dependencies import get_current_user
from infrastructure.db.models.user import User
from infrastructure.memory.memory_manager import get_memory_manager

router = APIRouter(prefix="/memory", tags=["memory"])


class MemoryResponse(BaseModel):
    user_id: str
    memory: dict[str, Any]


@router.get(
    "",
    response_model=MemoryResponse,
    summary="Lấy memory của user hiện tại",
)
async def get_my_memory(
    top_k: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
):
    mgr = get_memory_manager()
    if mgr is None:
        return MemoryResponse(user_id=current_user.id, memory={})
    data = mgr.search_memory(query="", top_k=top_k, user_id=current_user.id)
    return MemoryResponse(user_id=current_user.id, memory=data)


@router.delete(
    "",
    summary="Xóa memory của user hiện tại",
)
async def clear_my_memory(
    current_user: User = Depends(get_current_user),
):
    mgr = get_memory_manager()
    if mgr is None:
        return {"cleared": False, "detail": "Memory not available"}
    ok = mgr.clear_all(user_id=current_user.id)
    return {"cleared": ok, "user_id": current_user.id}


@router.get(
    "/stats",
    summary="Thống kê memory của user hiện tại",
)
async def memory_stats(
    current_user: User = Depends(get_current_user),
):
    mgr = get_memory_manager()
    if mgr is None:
        return {"error": "Memory not available"}
    return mgr.get_stats(user_id=current_user.id)
