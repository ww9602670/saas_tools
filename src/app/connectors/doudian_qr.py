# src/app/connectors/doudian_qr.py
from __future__ import annotations
from pathlib import Path
import time
from typing import Dict, Any

from ..constants import DOUDIAN
from ..utils.slug import slugify
from ..utils.files import atomic_write_json
from ..services.browser_pool import BrowserPool
from ..services.session_store import SessionRec, SessionStore
from ..services.qrcode_refresh import QRCodeRefresher
from ..services.otp_flow import OTPFlow

class DoudianQRConnector:
    def __init__(self, settings, pool: BrowserPool, store: SessionStore):
        self.settings = settings
        self.pool = pool
        self.store = store
        self.qr = QRCodeRefresher(
            qr_selector=DOUDIAN["qr_container"],
            refresh_button_selector=DOUDIAN["qr_refresh_button"],
        )
        self.otp = OTPFlow()

    async def create_session(self, *, user: str) -> Dict[str, Any]:
        await self.pool.ensure_started(headless=self.settings.headless)
        ctx, release = await self.pool.new_context_acquired(
            viewport=self.settings.viewport,
            device_scale_factor=self.settings.device_scale_factor,
            proxy=self.settings.proxy,
        )
        page = await ctx.new_page()
        await page.goto(DOUDIAN["login_url"], timeout=self.settings.timeout_ms)

        # 打开“扫码登录”区域（按你脚本的固定点击）
        try:
            el = await page.query_selector("div.login-switcher--cell")
            if el:
                await el.click()
                await page.wait_for_timeout(300)
        except Exception:
            pass

        b64 = await self.qr.capture_qr(page)
        sid = f"ses-{int(time.time() * 1000)}-{id(page) % 10000}"
        base_dir = Path(self.settings.output_dir) / user / "doudian"
        base_dir.mkdir(parents=True, exist_ok=True)

        rec = SessionRec(
            session_id=sid,
            user=user,
            base_dir=str(base_dir),
            state="waiting",
            page=page,
            context=ctx,
            release_ctx=release,
            qr_expires_at=int(time.time()) + DOUDIAN["qr_ttl_seconds"],
            qrcode_b64=b64,
        )
        self.store.put(rec)
        return {
            "session_id": sid,
            "qrcode_b64": b64,
            "qr_expires_at": rec.qr_expires_at,
            "base_dir": str(base_dir),
        }

    async def poll_status(self, session_id: str) -> Dict[str, Any]:
        rec = self.store.get(session_id)
        if not rec or not rec.page:
            return {"state": "error", "error_code": "not_found", "error_msg": "session not found"}
        page = rec.page

        # 1) 是否在验证码输入页
        try:
            if await self.otp.is_otp_page(page):
                rec.state = "otp_required"
                return {"state": "otp_required"}
        except Exception:
            pass

        # 2) 是否已登录：读取店铺名
        try:
            el = await page.query_selector(DOUDIAN["shop_name_selector"])
            if el:
                shop_name = (await el.text_content() or "").strip()
                if shop_name:
                    shop_slug = slugify(shop_name)
                    cookies = await page.context.cookies()
                    shop_dir = Path(rec.base_dir) / shop_slug
                    shop_dir.mkdir(parents=True, exist_ok=True)
                    cookies_path = shop_dir / f"{shop_slug}_cookies.json"
                    atomic_write_json(cookies_path, cookies)
                    rec.state = "logged_in"
                    rec.shop_slug = shop_slug
                    rec.cookies_path = str(cookies_path)

                    # 登录成功后关闭 Context/释放配额
                    await self._close_rec(rec)
                    return {
                        "state": "logged_in",
                        "shop_name": shop_name,
                        "cookies_path": str(cookies_path),
                        "cookies": cookies,
                    }
        except Exception:
            pass

        # 3) 二维码是否过期 → 刷新并返回新二维码
        now = int(time.time())
        if rec.qr_expires_at and now >= rec.qr_expires_at:
            new_b64 = await self.qr.refresh_and_recapture(page)
            if new_b64:
                rec.qrcode_b64 = new_b64
                rec.qr_expires_at = now + DOUDIAN["qr_ttl_seconds"]
                return {
                    "state": "waiting",
                    "qrcode_b64": new_b64,
                    "qr_expires_at": rec.qr_expires_at,
                }
            return {"state": "error", "error_code": "qr_expired", "error_msg": "QR expired, recreate session"}

        return {"state": "waiting", "qr_expires_at": rec.qr_expires_at}

    async def submit_otp(self, session_id: str, *, kind: str, code: str) -> Dict[str, Any]:
        rec = self.store.get(session_id)
        if not rec or not rec.page:
            return {"state": "error", "error_code": "not_found"}
        ok = await self.otp.submit(rec.page, kind=kind, code=code)
        if not ok:
            return {"state": "otp_required", "error_code": "otp_invalid"}
        return {"state": "waiting"}

    async def close(self, session_id: str) -> Dict[str, Any]:
        rec = self.store.get(session_id)
        if not rec:
            return {"ok": True}
        await self._close_rec(rec)
        rec.state = "closed"
        self.store.remove(session_id)
        return {"ok": True}

    async def _close_rec(self, rec: SessionRec):
        try:
            if rec.page:
                await rec.page.close()
        except Exception:
            pass
        try:
            if rec.release_ctx:
                await rec.release_ctx()
        except Exception:
            pass
        rec.page = None
        rec.context = None
