"""REST endpoints for browsing stored traces."""

from __future__ import annotations

from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from infrastructure.auth.dependencies import get_current_admin_user
from infrastructure.db.models.user import User
from infrastructure.observability.tracing import get_tracer

router = APIRouter(prefix="/traces", tags=["observability"])

_MAX_LIMIT = 200


class TraceSummary(BaseModel):
    trace_id: str = Field(..., description="Unique trace identifier")
    request_id: Optional[str] = None
    root_name: Optional[str] = None
    status: str = "running"
    started_at: Optional[float] = None
    ended_at: Optional[float] = None
    duration_ms: Optional[float] = None
    num_spans: int = 0
    total_tokens: int = 0
    llm_call_count: int = 0
    tool_call_count: int = 0


class TraceListResponse(BaseModel):
    enabled: bool = True
    count: int = 0
    traces: list[TraceSummary] = Field(default_factory=list)


class TraceDetailResponse(BaseModel):
    enabled: bool = True
    trace: dict[str, Any]


def _get_store():
    tracer = get_tracer()
    if not tracer.enabled or tracer.store is None:
        return None, tracer
    return tracer.store, tracer


@router.get(
    "",
    response_model=TraceListResponse,
    summary="Danh sách trace",
    description="Liệt kê các trace gần nhất với bộ lọc tùy chọn.",
)
async def list_traces(
    limit: int = Query(50, ge=1, le=_MAX_LIMIT),
    offset: int = Query(0, ge=0),
    status: Optional[Literal["ok", "error", "running"]] = None,
    min_duration_ms: Optional[float] = Query(None, ge=0),
    name_filter: Optional[str] = Query(None, max_length=100),
    _admin: User = Depends(get_current_admin_user),
):
    store, _tracer = _get_store()
    if store is None:
        return TraceListResponse(enabled=False, count=0, traces=[])
    try:
        rows = store.list_traces(
            limit=limit,
            offset=offset,
            status=status,
            min_duration_ms=min_duration_ms,
            name_filter=name_filter,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Trace store read failed: {exc}") from exc
    return TraceListResponse(
        enabled=True,
        count=len(rows),
        traces=[TraceSummary(**row) for row in rows],
    )


@router.get(
    "/{trace_id}",
    response_model=TraceDetailResponse,
    summary="Chi tiết một trace",
    description="Trả về toàn bộ span tree của một trace theo trace_id.",
)
async def get_trace(trace_id: str, _admin: User = Depends(get_current_admin_user)):
    store, _tracer = _get_store()
    if store is None:
        raise HTTPException(status_code=503, detail="Tracing is disabled")
    trace = store.get_trace(trace_id)
    if trace is None:
        raise HTTPException(status_code=404, detail=f"Trace '{trace_id}' not found")
    return TraceDetailResponse(enabled=True, trace=trace)
