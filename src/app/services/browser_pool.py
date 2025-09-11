# src/app/services/browser_pool.py
from __future__ import annotations
from asyncio import Semaphore, Lock
from contextlib import asynccontextmanager
from typing import Optional, AsyncIterator, Tuple

from playwright.async_api import async_playwright, Browser, BrowserContext

class BrowserPool:
    """
    单进程常驻 Browser；用 Semaphore 限制同时活跃的 Context 数量。
    """
    def __init__(self, max_contexts: int = 3):
        self._max = max_contexts
        self._sem = Semaphore(max_contexts)
        self._play = None
        self._browser: Optional[Browser] = None
        self._lock = Lock()

    async def ensure_started(self, headless: bool = True) -> Browser:
        if self._browser:
            return self._browser
        async with self._lock:
            if self._browser:
                return self._browser
            self._play = await async_playwright().start()
            self._browser = await self._play.chromium.launch(
                headless=headless,
                args=["--disable-dev-shm-usage", "--no-sandbox"],
            )
            return self._browser

    @asynccontextmanager
    async def lease_context(
        self,
        *,
        viewport: Optional[Tuple[int, int]] = None,
        device_scale_factor: Optional[float] = None,
        proxy: Optional[str] = None,
    ) -> AsyncIterator[BrowserContext]:
        """
        临时租用一个 Context；with 结束后自动关闭。
        """
        await self._sem.acquire()
        ctx: Optional[BrowserContext] = None
        try:
            kwargs = {}
            if viewport:
                kwargs["viewport"] = {"width": int(viewport[0]), "height": int(viewport[1])}
            if device_scale_factor:
                kwargs["device_scale_factor"] = device_scale_factor
            if proxy:
                kwargs["proxy"] = {"server": proxy}
            ctx = await self._browser.new_context(**kwargs)  # type: ignore
            yield ctx
        finally:
            if ctx:
                await ctx.close()
            self._sem.release()

    async def new_context_acquired(
        self, *, viewport=None, device_scale_factor=None, proxy=None
    ):
        """
        持久会话用：获取一个 Context，并返回 (ctx, release)。
        需要在登录完成或销毁会话时显式调用 release() 归还配额。
        """
        await self._sem.acquire()
        kwargs = {}
        if viewport:
            kwargs["viewport"] = {"width": int(viewport[0]), "height": int(viewport[1])}
        if device_scale_factor:
            kwargs["device_scale_factor"] = device_scale_factor
        if proxy:
            kwargs["proxy"] = {"server": proxy}
        ctx = await self._browser.new_context(**kwargs)  # type: ignore

        async def release():
            try:
                await ctx.close()
            finally:
                self._sem.release()

        return ctx, release

    async def dispose(self):
        try:
            if self._browser:
                await self._browser.close()
        finally:
            if self._play:
                await self._play.stop()
                self._play = None
                self._browser = None


# 单例
_pool: Optional[BrowserPool] = None

def get_pool(max_contexts: int = 3) -> BrowserPool:
    global _pool
    if _pool is None:
        _pool = BrowserPool(max_contexts)
    return _pool
