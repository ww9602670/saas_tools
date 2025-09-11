# src/app/services/qrcode_refresh.py
from __future__ import annotations
import base64, time
from pathlib import Path
from typing import Optional
from ..utils.files import atomic_write_bytes

class QRCodeRefresher:
    def __init__(self, *, qr_selector: str, refresh_button_selector: str):
        self.qr_selector = qr_selector
        self.refresh_button_selector = refresh_button_selector
        self._last_b64: Optional[str] = None

    async def capture_qr(self, page, *, out_path: Optional[Path] = None) -> str:
        el = await page.wait_for_selector(self.qr_selector, timeout=30_000)
        png = await el.screenshot(type="png")
        if out_path:
            atomic_write_bytes(out_path, png)
        b64 = base64.b64encode(png).decode("ascii")
        self._last_b64 = b64
        return b64

    async def refresh_and_recapture(self, page) -> Optional[str]:
        btn = await page.query_selector(self.refresh_button_selector)
        if not btn:
            return None
        await btn.click()
        await page.wait_for_timeout(800)
        try:
            return await self.capture_qr(page)
        except Exception:
            return None

    async def last_qr_b64(self) -> Optional[str]:
        return self._last_b64
