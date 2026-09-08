"""Admin RAG endpoints — status & manual refresh."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from infrastructure.rag.pipeline import run_full_refresh
from infrastructure.rag.registry import get_last_runs
from infrastructure.rag.vector_store import ALIAS, alias_target, collection_info, list_collections

router = APIRouter(prefix="/admin/rag", tags=["rag"])


class RefreshRequest(BaseModel):
    force: bool = False
    week: str | None = None


def _check_admin(x_admin_token: str | None) -> None:
    expected = os.getenv("ADMIN_API_KEY")
    if not expected:
        return  # no protection if not set
    if x_admin_token != expected:
        raise HTTPException(status_code=403, detail="Forbidden: invalid admin token")


@router.get("/status")
def rag_status(x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")):
    _check_admin(x_admin_token)
    runs = get_last_runs(limit=10)
    alias = alias_target()
    collections = list_collections()
    info = collection_info(alias) if alias else None
    return {"alias": ALIAS, "alias_target": alias, "collections": collections, "alias_info": info, "last_runs": runs}


@router.post("/refresh")
def rag_refresh(body: RefreshRequest, x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")):
    _check_admin(x_admin_token)
    res = run_full_refresh(force=body.force, week=body.week)
    return res


@router.get("/manifest/{week}")
def rag_manifest(week: str, x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")):
    _check_admin(x_admin_token)
    p = Path(f"data/rag/manifests/{week}.json")
    if not p.exists():
        raise HTTPException(status_code=404, detail=f"Manifest {week} not found")
    return p.read_text(encoding="utf-8")
