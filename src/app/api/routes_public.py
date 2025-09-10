# src/app/api/routes_public.py
from fastapi import APIRouter, Depends
from typing import Optional

# 这些模型你后面会放到 api/schemas.py；即使现在没有，也不影响语法编译
try:
    from .schemas import (
        CreateSessionReq, CreateSessionResp,
        SessionStateResp, SubmitOtpReq, OkResp
    )
except Exception:
    # 临时兜底的轻量模型（仅为编译通过；运行期建议使用正式 schemas）
    from pydantic import BaseModel
    class CreateSessionReq(BaseModel):
        user: str
    class CreateSessionResp(BaseModel):
        session_id: str
        qrcode_b64: str
        base_dir: str
        expires_at: int
    class SessionStateResp(BaseModel):
        state: str
        shop_name: Optional[str] = None
        cookies_path: Optional[str] = None
        qrcode_b64: Optional[str] = None
        error_code: Optional[str] = None
        error_msg: Optional[str] = None
        qr_expires_at: Optional[int] = None
    class SubmitOtpReq(BaseModel):
        kind: str = "sms"
        code: str
    class OkResp(BaseModel):
        ok: bool = True

router = APIRouter(prefix="/api/doudian", tags=["doudian"])

# 简单依赖骨架（避免编译期 NameError）
class Deps:
    def __init__(self):
        self.settings = None
        self.store = None
        self.owner = None

def get_deps():
    return Deps()

@router.post("/sessions", response_model=CreateSessionResp)
async def create_session(_: CreateSessionReq, deps: Deps = Depends(get_deps)):
    # 占位返回，后续填充真实逻辑
    return CreateSessionResp(
        session_id="sess_demo",
        qrcode_b64="",
        base_dir="/app/users/demo/doudian",
        expires_at=0,
    )

@router.get("/sessions/{sid}/status", response_model=SessionStateResp)
async def session_status(sid: str, deps: Deps = Depends(get_deps)):
    # 占位：总是 waiting
    return SessionStateResp(state="waiting", qr_expires_at=0)

@router.post("/sessions/{sid}/otp", response_model=SessionStateResp)
async def submit_otp(sid: str, body: SubmitOtpReq, deps: Deps = Depends(get_deps)):
    # 占位：提交后继续 waiting
    return SessionStateResp(state="waiting")

@router.delete("/sessions/{sid}", response_model=OkResp)
async def close_session(sid: str, deps: Deps = Depends(get_deps)):
    return OkResp()

# 兼容老接口（一次性二维码）——先返回占位数据
@router.post("/qr")
async def one_shot_qr():
    return {"ok": True, "note": "placeholder; implement later"}
