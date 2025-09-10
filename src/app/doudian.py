# 现有调试脚本：保留（加入原子写）
# src/app/doudian.py
# -*- coding: utf-8 -*-
from pathlib import Path
from app.settings import settings
from app.playwright_login import qr_login_capture

# 业务常量（抖店登录）
LOGIN_URL = "https://fxg.jinritemai.com/login/common?channel=zhaoshang"
ACTIONS = [
    # 例：点击“其他登录方式/扫码登录”
    {"selector": "div.login-switcher--cell", "click": True, "js_click_fallback": True, "wait_ms": 300},
    # 如需再点“扫码登录”tab，放开下一行
    # {"selector": "text=扫码登录", "click": True, "js_click_fallback": True, "wait_ms": 300},
]
TARGET_SELECTOR = "div.account-center-image-content"
COOKIE_DOMAINS = ["jinritemai.com", "zijieapi.com"]     # 业务域

# 产物（可用 settings.output_dir 统一到项目根或自定义目录）
QRCODE_FILE = Path(settings.output_dir) / "qrcode_doudian.png"
COOKIES_FILE = Path(settings.output_dir) / "cookies_doudian.json"

def main():
    print("[SETTINGS]", settings.dump())

    pack = qr_login_capture(
        login_url=LOGIN_URL,
        actions=ACTIONS,
        target_selector="div.account-center-image-content",
        ready_mode="bg",  # 二维码在 background-image
        outfile="/app/users/qrcode_doudian.png",
        headless=settings.headless,
        timeout_ms=settings.timeout_ms,
        viewport=(settings.viewport_width, settings.viewport_height),
        device_scale_factor=settings.device_scale_factor,
        export_cookies=False,
        cookie_domains=COOKIE_DOMAINS,
        cookies_outfile=str(COOKIES_FILE),
        # 选配：代理
        # proxy=settings.proxy,
    )
    print(pack)
    input("Press Enter to exit...")  # 开发期防退出；生产/CI 可移除

if __name__ == "__main__":
    main()
