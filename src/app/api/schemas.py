# Pydantic 请求/响应模型（会话/状态/错误）

# schemas.py
from pydantic import BaseModel
from typing import Optional, Literal, Dict, Any

class CreateSessionReq(BaseModel):
    user: str
    shop: Optional[str] = None            # 前端可不传，由登录后识别
    filename_mode: Literal["latest_only"] = "latest_only"
    headless: Optional[bool] = None
    timeout_ms: Optional[int] = None
    viewport: Optional[Dict[str, int]] = None
    device_scale_factor: Optional[float] = None

class CreateSessionResp(BaseModel):
    session_id: str
    qrcode_b64: str
    base_dir: str
    expires_at: int                       # epoch seconds

class SessionStateResp(BaseModel):
    state: Literal["waiting", "otp_required", "logged_in", "error"]
    shop_name: Optional[str] = None
    cookies_path: Optional[str] = None
    cookies: Optional[Any] = None         # 可配置是否回传
    qrcode_b64: Optional[str] = None      # 若刷新过期二维码，附上新图
    error_code: Optional[str] = None
    error_msg: Optional[str] = None
    qr_expires_at: Optional[int] = None

class SubmitOtpReq(BaseModel):
    kind: Literal["email", "sms"] = "sms"
    code: str

class OkResp(BaseModel):
    ok: bool = True
