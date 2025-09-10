# 抖店实现（二维码、店铺名判定、OTP 识别/提交、二维码刷新）

# doudian_qr.py
from pathlib import Path
import time
from ..constants import DOUDIAN, ERRORS
from ..utils.slug import slugify
from ..utils.files import atomic_write_json

class DoudianQRConnector:
    def __init__(self, settings, pool, qrcode_refresher, otp_flow):
        self.settings = settings
        self.pool = pool
        self.qr = qrcode_refresher
        self.otp = otp_flow

    async def create_session(self, user:str) -> dict:
        # 1) 借 Context
        async with self.pool.lease_context(viewport={"width":1280,"height":800}, scale=1.0) as ctx:
            page = await ctx.new_page()
            await page.goto(DOUDIAN["login_url"], wait_until="domcontentloaded")
            # 2) 等待二维码出现并截图
            qr_b64, qrcode_path = await self.qr.capture_qr(page, DOUDIAN["qr_selector"])
            rec = {
                "page": page, "context": ctx,
                "state": "waiting",
                "qrcode_path": qrcode_path,
                "qr_expires_at": int(time.time()) + DOUDIAN["qr_ttl_seconds"],
            }
            return rec | {"qrcode_b64": qr_b64}

    async def poll_status(self, rec) -> dict:
        page = rec["page"]
        # 1) 先判 OTP
        if await self.otp.is_otp_page(page):
            rec["state"] = "otp_required"
            return {"state":"otp_required"}

        # 2) 判已登录（抓店铺名）
        try:
            el = await page.query_selector(DOUDIAN["shop_name_selector"])
            if el:
                shop_name = (await el.text_content() or "").strip()
                if shop_name:
                    shop_slug = slugify(shop_name)
                    # 导出 cookies（按域过滤可以在 playwright_login 里重用）
                    cookies = await page.context.cookies()
                    base_dir = Path(self.settings.output_dir) / rec["user"] / "doudian" / shop_slug
                    cookies_path = base_dir / f"{shop_slug}_cookies.json"
                    base_dir.mkdir(parents=True, exist_ok=True)
                    await atomic_write_json(cookies_path, cookies)
                    rec.update({"state":"logged_in","shop_slug":shop_slug,"cookies_path":str(cookies_path)})
                    return {
                        "state":"logged_in","shop_name":shop_name,
                        "cookies_path": str(cookies_path), "cookies": cookies
                    }
        except Exception:
            pass

        # 3) 判二维码过期并刷新（一次）
        if int(time.time()) >= (rec.get("qr_expires_at") or 0):
            if await self.qr.refresh_and_recapture(page):
                rec["qr_expires_at"] = int(time.time()) + DOUDIAN["qr_ttl_seconds"]
                new_b64 = await self.qr.last_qr_b64(page)
                return {"state":"waiting","qrcode_b64": new_b64,"qr_expires_at":rec["qr_expires_at"]}
            return {"state":"error","error_code":ERRORS["QR_EXPIRED"],"error_msg":"QR expired"}

        return {"state":"waiting","qr_expires_at": rec.get("qr_expires_at")}

    async def submit_otp(self, rec, kind:str, code:str) -> dict:
        ok = await self.otp.submit(page=rec["page"], kind=kind, code=code)
        if not ok:
            return {"state":"otp_required","error_code":"otp_invalid"}
        # 提交后让前端再次轮询
        return {"state":"waiting"}
