# 二维码过期检测 & 自动点击“刷新”封装

# qrcode_refresh.py
import base64, time
from pathlib import Path
from ..utils.files import atomic_write_bytes

class QRCodeRefresher:
    async def capture_qr(self, page, selector:str):
        el = await page.wait_for_selector(selector, timeout=30_000)
        png = await el.screenshot(type="png")
        # 落盘（会话目录由上层传入，这里简化）
        path = Path("/tmp") / f"qrcode_{int(time.time()*1000)}.png"
        await atomic_write_bytes(path, png)
        b64 = base64.b64encode(png).decode()
        self._last_b64 = b64 
        return b64, str(path)

    async def refresh_and_recapture(self, page):
        btn = await page.query_selector("button.account-center-code-expired-refresh")
        if not btn:
            return False
        await btn.click()
        await page.wait_for_timeout(600)  # 等新二维码渲染
        # 再抓一次
        el = await page.query_selector("img.qrcode, canvas.qrcode, div.qrcode img")
        if not el:
            return False
        png = await el.screenshot(type="png")
        self._last_b64 = base64.b64encode(png).decode()
        return True

    async def last_qr_b64(self, page):
        return getattr(self, "_last_b64", None)

