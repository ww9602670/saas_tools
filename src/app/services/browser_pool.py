# 单例 BrowserPool：ensure_started, lease_context, dispose

# browser_pool.py
from contextlib import asynccontextmanager
from asyncio import Semaphore
from playwright.async_api import async_playwright

class BrowserPool:
    _instance = None

    def __init__(self, max_contexts:int):
        self._sem = Semaphore(max_contexts)
        self._browser = None
        self._play = None

    async def ensure_started(self):
        if self._browser is not None:
            return
        self._play = await async_playwright().start()
        self._browser = await self._play.chromium.launch(
            headless=True, args=["--disable-dev-shm-usage","--no-sandbox"]
        )

    @asynccontextmanager
    async def lease_context(self, viewport=None, scale=None, user_agent=None, proxy=None):
        await self.ensure_started()
        async with self._sem:
            ctx = await self._browser.new_context(
                viewport=viewport, device_scale_factor=scale, user_agent=user_agent, proxy=proxy
            )
            try:
                yield ctx
            finally:
                await ctx.close()

    async def dispose(self):
        try:
            if self._browser: await self._browser.close()
        finally:
            if self._play: await self._play.stop()

# 单例获取
pool: BrowserPool | None = None
def get_pool(settings) -> BrowserPool:
    global pool
    if pool is None:
        pool = BrowserPool(settings.max_active_contexts)
    return pool
