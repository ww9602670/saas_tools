# tools/preflight.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import sys
import textwrap
from pathlib import Path
from typing import Tuple

# --- 让脚本可直接运行：把 <repo>/src 加到 sys.path ---
REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# --- 尽早导入 settings（只包含运行时字段的版本） ---
try:
    from app.settings import settings
except Exception as e:  # noqa: BLE001
    print("❌ 无法导入 app.settings：", e)
    print("   请确认 src 布局与 PYTHONPATH。已尝试自动加入：", SRC_DIR)
    sys.exit(1)

def hr():
    print("-" * 72)

def ok(msg: str):
    print(f"✅ {msg}")

def warn(msg: str):
    print(f"⚠️  {msg}")

def bad(msg: str):
    print(f"❌ {msg}")

def check_output_dir() -> bool:
    out = settings.output_dir
    try:
        out.mkdir(parents=True, exist_ok=True)
        test_file = out / ".preflight_write_test"
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink(missing_ok=True)
        ok(f"输出目录可写：{out}")
        return True
    except Exception as e:  # noqa: BLE001
        bad(f"输出目录不可写：{out} → {e}")
        return False

def check_playwright() -> Tuple[bool, str]:
    try:
        import importlib.metadata as m  # py3.10+
        try:
            pw_ver = m.version("playwright")
        except Exception:
            pw_ver = "unknown"
    except Exception:
        pw_ver = "unknown"

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,  # 预检强制无头
                args=["--disable-dev-shm-usage", "--no-sandbox"],
            )
            ctx = browser.new_context(
                viewport={"width": settings.viewport_width, "height": settings.viewport_height},
                device_scale_factor=settings.device_scale_factor,
                proxy={"server": settings.proxy} if settings.proxy else None,
            )
            page = ctx.new_page()
            page.goto("about:blank")
            version = browser.version
            ctx.close()
            browser.close()

        ok(f"Chromium 可用（playwright={pw_ver}, browser={version}）")
        return True, version
    except Exception as e:  # noqa: BLE001
        bad("Chromium 启动失败。")
        print(textwrap.indent(str(e), prefix="   "))
        print("   常见原因：")
        print("   - 缺少系统依赖（若未用官方 Playwright 镜像）")
        print("   - 容器权限或 /dev/shm 太小（考虑 --shm-size=1g）")
        print("   - 使用有头模式但没有 X Server（请改 headless=True 或使用 xvfb-run）")
        return False, ""

def main() -> int:
    print("🔎 Preflight / 运行环境自检")
    hr()
    print("Settings:")
    print(" ", settings.dump())
    hr()

    ok("Python 工作目录：" + str(REPO_ROOT))
    ok("已加入 PYTHONPATH：" + str(SRC_DIR))

    hr()
    passed = True

    # 1) 输出目录
    passed &= check_output_dir()

    # 2) Playwright / Chromium
    ok(f"准备以无头模式检查浏览器（viewport={settings.viewport_width}x{settings.viewport_height}, scale={settings.device_scale_factor}）")
    ok(f"代理：{settings.proxy!r}")
    pw_ok, _ = check_playwright()
    passed &= pw_ok

    hr()
    if passed:
        ok("预检通过 ✅ 一切就绪！")
        return 0
    else:
        bad("预检未通过，请根据上面的错误信息修复后重试。")
        return 1

if __name__ == "__main__":
    sys.exit(main())
