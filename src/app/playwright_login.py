# src/app/playwright_login.py
# -*- coding: utf-8 -*-
"""
通用的扫码登录/元素截图库函数（同步版，兼容现有调用）：
- 不读取环境变量，不包含业务常量（URL/选择器）
- 支持 headless / timeout / viewport / device_scale_factor / proxy
- 支持导出 cookies，并按域名过滤（字符串或列表）
- Phase 0：新增可选 browser 参数；传入则仅关闭 context，不关闭 browser
"""
from __future__ import annotations

import os
import json
import time
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from playwright.sync_api import (
    sync_playwright,
    TimeoutError as PWTimeoutError,
    Browser as SyncBrowser,
    Page as SyncPage,
)

def _normalize_domains(domains: Union[str, List[str], None]) -> List[str]:
    if domains is None:
        return []
    if isinstance(domains, str):
        return [domains]
    return [d for d in domains if d]

def _atomic_write_bytes(path: Path, data: bytes) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name, dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp, str(path))
        try:
            os.chmod(path, 0o600)
        except Exception:
            pass
    finally:
        # os.replace 已删除临时文件
        pass

def _atomic_write_json(path: Path, obj) -> None:
    data = json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8")
    _atomic_write_bytes(path, data)

def _click_with_fallback(page: SyncPage, selector: str, js_click_fallback: bool = False, timeout_ms: int = 10000) -> None:
    el = page.wait_for_selector(selector, timeout=timeout_ms)
    try:
        el.click(timeout=timeout_ms)
    except Exception:
        if js_click_fallback:
            page.evaluate("""(sel) => {
                const el = document.querySelector(sel);
                if (el) el.click();
            }""", selector)
        else:
            raise

def qr_login_capture(
    *,
    login_url: str,
    actions: Optional[List[Dict]] = None,
    target_selector: str,
    ready_mode: str = "element",          # 兼容历史参数；"bg" 也按元素截图
    outfile: str = "qrcode.png",
    headless: bool = True,
    timeout_ms: int = 60_000,
    viewport: Optional[Tuple[int, int]] = None,
    device_scale_factor: Optional[float] = None,
    export_cookies: bool = False,
    cookie_domains: Union[str, List[str], None] = None,
    cookies_outfile: str = "cookies.json",
    proxy: Optional[str] = None,          # 例如 "http://user:pass@host:port"
    browser: Optional[SyncBrowser] = None,# 新增：复用 Browser；传入则仅关闭 context
    debug_prefix: str = "debug",
) -> Dict:
    """
    返回:
        {
          "screenshot": "qrcode.png",
          "cookies": [...],            # 若 export_cookies=True
          "timing_ms": {"ready": <int>}
        }
    """
    t0 = time.time()
    cookie_domains_list = _normalize_domains(cookie_domains)

    play = None
    launched_here = False
    ctx = None
    page = None
    try:
        if browser is None:
            play = sync_playwright().start()
            browser = play.chromium.launch(
                headless=headless,
                args=["--disable-dev-shm-usage", "--no-sandbox"],
            )
            launched_here = True

        context_kwargs = {}
        if viewport:
            context_kwargs["viewport"] = {"width": int(viewport[0]), "height": int(viewport[1])}
        if device_scale_factor:
            context_kwargs["device_scale_factor"] = device_scale_factor
        if proxy:
            context_kwargs["proxy"] = {"server": proxy}

        ctx = browser.new_context(**context_kwargs)
        page = ctx.new_page()
        page.goto(login_url, timeout=timeout_ms, wait_until="domcontentloaded")

        # 执行动作序列（点击/等待等）
        for act in (actions or []):
            sel = act.get("selector")
            if not sel:
                continue
            if act.get("click"):
                _click_with_fallback(page, sel, js_click_fallback=act.get("js_click_fallback", False), timeout_ms=min(timeout_ms, 15_000))
            else:
                page.wait_for_selector(sel, timeout=min(timeout_ms, 15_000))
            wait_ms = act.get("wait_ms")
            if wait_ms:
                page.wait_for_timeout(int(wait_ms))

        # 等待二维码元素就绪并截图
        el = page.wait_for_selector(target_selector, timeout=timeout_ms)
        # 某些站点二维码是 <canvas> 或 background-image，元素截图更稳
        png = el.screenshot(type="png")
        _atomic_write_bytes(Path(outfile), png)

        # 导出 cookies（可选）
        cookies: List[Dict] = []
        if export_cookies:
            cookies = ctx.cookies()
            if cookie_domains_list:
                filtered = []
                for c in cookies:
                    dom = c.get("domain") or ""
                    if any(d in dom for d in cookie_domains_list):
                        filtered.append(c)
                cookies = filtered
            _atomic_write_json(Path(cookies_outfile), cookies)

        return {
            "screenshot": outfile,
            "cookies": cookies,
            "timing_ms": {"ready": int((time.time() - t0) * 1000)},
        }

    except PWTimeoutError as e:
        # 超时也一样做调试留证
        try:
            if page:
                page.screenshot(path=f"{debug_prefix}_page.png", full_page=True)
                html = page.content()
                with open(f"{debug_prefix}_page.html", "w", encoding="utf-8") as f:
                    f.write(html)
        except Exception:
            pass
        raise
    except Exception:
        # 失败时尽可能留下一些调试信息
        try:
            if page:
                page.screenshot(path=f"{debug_prefix}_page.png", full_page=True)
                html = page.content()
                with open(f"{debug_prefix}_page.html", "w", encoding="utf-8") as f:
                    f.write(html)
        except Exception:
            pass
        raise
    finally:
        # 只关 context；如本函数自建了 browser，再关 browser / 停止 playwright
        try:
            if ctx:
                ctx.close()
        finally:
            if launched_here and browser:
                browser.close()
            if launched_here and play:
                play.stop()
