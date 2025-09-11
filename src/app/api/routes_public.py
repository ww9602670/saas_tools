# src/app/api/routes_public.py
from __future__ import annotations

from fastapi import APIRouter
from .schemas import CreateSessionReq, CreateSessionResp, SessionStateResp, SubmitOtpReq, OkResp
from ..settings import settings
from ..services.browser_pool import get_pool
from ..services.session_store import get_store
from ..connectors.doudian_qr import DoudianQRConnector

router = APIRouter(prefix="/api/doudian", tags=["doudian"])

def _connector() -> DoudianQRConnector:
    pool = get_pool(settings.max_active_contexts)
    store = get_store()
    return DoudianQRConnector(settings=settings, pool=pool, store=store)

@router.post("/sessions", response_model=CreateSessionResp)
async def create_session(body: CreateSessionReq):
    c = _connector()
    res = await c.create_session(user=body.user)
    return CreateSessionResp(
        session_id=res["session_id"],
        qrcode_b64=res["qrcode_b64"],
        base_dir=res["base_dir"],
        expires_at=res.get("qr_expires_at"),
    )

@router.get("/sessions/{sid}/status", response_model=SessionStateResp)
async def get_status(sid: str):
    c = _connector()
    res = await c.poll_status(sid)
    return SessionStateResp(**res)

@router.post("/sessions/{sid}/otp", response_model=SessionStateResp)
async def submit_otp(sid: str, body: SubmitOtpReq):
    c = _connector()
    res = await c.submit_otp(sid, kind=body.kind, code=body.code)
    return SessionStateResp(**res)

@router.delete("/sessions/{sid}", response_model=OkResp)
async def close_session(sid: str):
    c = _connector()
    res = await c.close(sid)
    return OkResp(ok=res.get("ok", True))
