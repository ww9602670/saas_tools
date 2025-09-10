# 现有：改造支持可选 browser（仅关闭context）
# src/app/playwright_login.py
# -*- coding: utf-8 -*-
"""
通用的扫码登录/元素截图库函数：
- 不读取环境变量，不包含业务常量（URL/选择器）
- 支持 headless/timeout/viewport/device_scale_factor/proxy
- 支持导出 cookies，并按域名过滤（字符串或列表）
"""
from __future__ import annotations

import json
import time
from typing import Dict, List, Optional, Tuple, Union

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError


def _normalize_domains(domains: Optional[Union[List[str], str]]) -> Optional[List[str]]:
    if not domains:
        return None
    if isinstance(domains, str):
        return [s.strip() for s in domains.split(",") if s.strip()]
    return [str(x).strip() for x in domains if str(x).strip()]


def _js_click(page, selector: str) -> None:
    page.evaluate(
        """sel => {
            const el = document.querySelector(sel);
            if (el) el.click();
        }""",
        selector,
    )


def qr_login_capture(
    *,
    login_url: str,
    target_selector: str,
    actions: Optional[List[Dict]] = None,   # [{'selector': '...', 'click': True, 'type_text': 'xxx', 'wait_ms': 300, 'js_click_fallback': True}]
    outfile: str = "qrcode.png",
    headless: bool = True,
    timeout_ms: int = 20_000,
    viewport: Tuple[int, int] = (1440, 900),
    device_scale_factor: int = 2,
    ready_mode: str = "bg",                 # 'bg' | 'img' | 'custom'
    ready_js: Optional[str] = None,         # ready_mode='custom' 时用于判定就绪
    min_box: Tuple[int, int] = (120, 120),
    debug_prefix: str = "debug",
    export_cookies: bool = False,
    cookie_domains: Optional[Union[List[str], str]] = None,
    cookies_outfile: str = "cookies.json",
    proxy: Optional[str] = None,            # 例如 "http://user:pass@host:port"
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

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=["--disable-dev-shm-usage", "--no-sandbox"],
        )
        ctx = p.chromium.launch_persistent_context  # 保留示例写法，不使用持久化
        # 这里我们使用普通 context
        ctx = browser.new_context(
            viewport={"width": viewport[0], "height": viewport[1]},
            device_scale_factor=device_scale_factor,
            proxy={"server": proxy} if proxy else None,
        )
        page = ctx.new_page()

        try:
            page.goto(login_url, timeout=timeout_ms, wait_until="load")

            # 执行业务动作（点击/输入/等待）
            for act in (actions or []):
                sel = act.get("selector")
                if sel:
                    page.wait_for_selector(sel, timeout=timeout_ms, state="visible")
                if act.get("click"):
                    try:
                        page.click(sel, timeout=timeout_ms)
                    except Exception:
                        if act.get("js_click_fallback"):
                            _js_click(page, sel)
                        else:
                            raise
                if "type_text" in act:
                    page.fill(sel, str(act["type_text"]))
                if "wait_ms" in act:
                    page.wait_for_timeout(int(act["wait_ms"]))

            # 等待二维码元素出现并“就绪”
            locator = page.locator(target_selector)
            locator.wait_for(state="visible", timeout=timeout_ms)

            # 轮询直到满足就绪条件
            deadline = time.time() + (timeout_ms / 1000)
            while True:
                box = locator.bounding_box()
                ok_size = bool(box) and box["width"] >= min_box[0] and box["height"] >= min_box[1]
                ok_ready = ok_size

                if ready_mode == "bg":
                    # 背景图存在（通常二维码是 background-image）
                    has_bg = page.evaluate(
                        """sel => {
                            const el = document.querySelector(sel);
                            if (!el) return false;
                            const bg = getComputedStyle(el).backgroundImage || '';
                            return bg.includes('url(');
                        }""",
                        target_selector,
                    )
                    ok_ready = ok_size and bool(has_bg)
                elif ready_mode == "img":
                    # <img> 标签加载完成
                    loaded = page.evaluate(
                        """sel => {
                            const el = document.querySelector(sel);
                            if (!el) return false;
                            const img = el.tagName === 'IMG' ? el : el.querySelector('img');
                            return !!(img && img.complete && img.naturalWidth > 0 && img.naturalHeight > 0);
                        }""",
                        target_selector,
                    )
                    ok_ready = ok_size and bool(loaded)
                elif ready_mode == "custom" and ready_js:
                    ok_ready = bool(page.evaluate(ready_js))

                if ok_ready:
                    break
                if time.time() > deadline:
                    raise PWTimeoutError(f"Target not ready: selector={target_selector}")
                page.wait_for_timeout(150)

            # 截图（针对元素）
            locator.screenshot(path=outfile)

            result: Dict = {
                "screenshot": outfile,
                "cookies": [],
                "timing_ms": {"ready": int((time.time() - t0) * 1000)},
            }

            # 导出 cookies（可按域过滤）
            if export_cookies:
                cookies = ctx.cookies()
                if cookie_domains_list:
                    keep = []
                    for c in cookies:
                        d = (c.get("domain") or "").lstrip(".").lower()
                        if any(d.endswith(dom.lstrip(".").lower()) for dom in cookie_domains_list):
                            keep.append(c)
                    cookies = keep
                with open(cookies_outfile, "w", encoding="utf-8") as f:
                    json.dump(cookies, f, ensure_ascii=False, indent=2)
                result["cookies"] = cookies

            return result

        except Exception as e:
            # 失败时尽可能留下一些调试信息
            try:
                page.screenshot(path=f"{debug_prefix}_page.png", full_page=True)
                html = page.content()
                with open(f"{debug_prefix}_page.html", "w", encoding="utf-8") as f:
                    f.write(html)
            except Exception:
                pass
            raise e
        finally:
            ctx.close()
            browser.close()
