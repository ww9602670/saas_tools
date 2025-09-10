# src/app/api/routes.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import base64
import time
from pathlib import Path
from typing import List, Optional
import traceback

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.settings import settings
from app.playwright_login import qr_login_capture

# ---- 业务常量（与 doudian.py 保持一致，但不相互依赖，以免循环导入）----
LOGIN_URL = "https://fxg.jinritemai.com/login/common?channel=zhaoshang"
ACTIONS = [
    {"selector": "div.login-switcher--cell", "click": True, "js_click_fallback": True, "wait_ms": 300},
    # 如需再点“扫码登录”tab，放开下一行
    # {"selector": "text=扫码登录", "click": True, "js_click_fallback": True, "wait_ms": 300},
]
TARGET_SELECTOR = "div.account-center-image-content"
COOKIE_DOMAINS: List[str] = ["jinritemai.com", "zijieapi.com"]


# ---------- 请求&响应模型 ----------
class DoudianQRRequest(BaseModel):
    # 是否把二维码以 base64 内联返回（便于在 /docs 里直接预览）
    inline_base64: bool = True
    # 是否导出并返回 cookies
    export_cookies: bool = True

    # 运行时覆盖（可选）
    headless: bool | None = None
    timeout_ms: int | None = Field(default=None, gt=1000)
    viewport_width: int | None = Field(default=None, gt=320)
    viewport_height: int | None = Field(default=None, gt=320)
    device_scale_factor: int | None = Field(default=None, ge=1, le=3)

    # 将来可扩展：proxy、ready_mode、min_box 等


class DoudianQRResponse(BaseModel):
    qrcode_file: str
    qrcode_b64: str | None = None
    cookies_file: str | None = None
    cookies: list = Field(default_factory=list)
    timing_ms: dict


router = APIRouter(tags=["doudian"])


@router.post("/doudian/qr", response_model=DoudianQRResponse, summary="生成抖店登录二维码（可选返回 cookies）")
def doudian_qr(req: DoudianQRRequest) -> DoudianQRResponse:
    # 输出文件：带时间戳避免冲突
    ts = int(time.time() * 1000)
    out_dir: Path = settings.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    qrcode_path = out_dir / f"qrcode_doudian_{ts}.png"
    cookies_path = out_dir / f"cookies_doudian_{ts}.json"

    # 运行时参数 = 请求覆写优先，否则用 settings
    headless = req.headless if req.headless is not None else settings.headless
    timeout_ms = req.timeout_ms or settings.timeout_ms
    viewport = (
        req.viewport_width or settings.viewport_width,
        req.viewport_height or settings.viewport_height,
    )
    scale = req.device_scale_factor or settings.device_scale_factor

    try:
        pack = qr_login_capture(
            login_url=LOGIN_URL,
            actions=ACTIONS,
            target_selector=TARGET_SELECTOR,
            ready_mode="bg",
            outfile=str(qrcode_path),
            headless=headless,
            timeout_ms=timeout_ms,
            viewport=viewport,
            device_scale_factor=scale,
            export_cookies=req.export_cookies,
            cookie_domains=COOKIE_DOMAINS,
            cookies_outfile=str(cookies_path),
            proxy=settings.proxy,
        )
    except Exception as e:
        traceback.print_exc()
        # 常见错误：dev 环境 headless=False 但没有 X Server
        raise HTTPException(status_code=500, detail=f"Failed to create QR: {e}")

    # 组装响应
    qrcode_b64: Optional[str] = None
    if req.inline_base64:
        data = qrcode_path.read_bytes()
        qrcode_b64 = "data:image/png;base64," + base64.b64encode(data).decode("ascii")

    cookies_file = str(cookies_path) if req.export_cookies else None

    return DoudianQRResponse(
        qrcode_file=str(qrcode_path),
        qrcode_b64=qrcode_b64,
        cookies_file=cookies_file,
        cookies=pack.get("cookies", []) if req.export_cookies else [],
        timing_ms=pack.get("timing_ms", {}),
    )
