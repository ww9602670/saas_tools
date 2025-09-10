# 现有：补充 MAX_ACTIVE_CONTEXTS、ROLE、REDIS_URL 等
# src/app/settings.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import os
from pathlib import Path
from typing import Literal
from uuid import uuid4 

from pydantic import Field, ValidationError, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# 工程目录
BASE_DIR = Path(__file__).resolve().parents[2]   # /app
ENVS_DIR = BASE_DIR / ".envs"


class Settings(BaseSettings):
    """
    仅承载“运行时”配置（跨业务通用）：
    - 环境 dev/test/prod
    - 无头/超时/分辨率/缩放
    - 代理
    - 产物输出目录
    - 可选：是否保存调试产物
    """
    model_config = SettingsConfigDict(extra="ignore")

    # 运行环境
    app_env: Literal["dev", "test", "prod"] = "dev"

    # Playwright 运行时参数
    headless: bool | None = None              # 未显式设置时：dev=False，test/prod=True
    timeout_ms: int = 20_000
    viewport_width: int = 1440
    viewport_height: int = 900
    device_scale_factor: int = 2
    proxy: str | None = None                  # 例如 "http://user:pass@host:port"

    # 输出目录（二维码、cookies 等）
    output_dir: Path = Field(default=BASE_DIR)

    # 调试
    debug_save_artifacts: bool = False

    role: Literal["monolith", "gateway", "worker"] = "monolith"
    max_active_contexts: int = 3
    redis_url: str = "redis://redis:6379/0"   # 1+N时使用；单实例可不连也能跑
    instance_id: str = Field(default_factory=lambda: f"inst-{uuid4().hex[:8]}")
    output_dir: Path = Path("/app/users")     # 目录按 user/shop_slug/session_id 分层

    # ---------- 校验 & 智能默认 ----------
    @field_validator("timeout_ms", "viewport_width", "viewport_height", "device_scale_factor")
    @classmethod
    def _positive(cls, v, info):
        if v <= 0:
            raise ValueError(f"{info.field_name} must be > 0")
        return v

    @model_validator(mode="after")
    def _defaults_and_dirs(self):
        # headless 未设：dev=False；test/prod=True
        if self.headless is None:
            object.__setattr__(self, "headless", self.app_env != "dev")

        # 确保输出目录存在
        out = self.output_dir
        if not out.exists():
            out.mkdir(parents=True, exist_ok=True)
        return self

    # 便捷：以 tuple 形式拿 viewport
    @property
    def viewport(self) -> tuple[int, int]:
        return (self.viewport_width, self.viewport_height)

    # 便于调试打印
    def dump(self) -> str:
        return (
            f"Settings(app_env={self.app_env!r}, headless={self.headless}, "
            f"timeout_ms={self.timeout_ms}, viewport=({self.viewport_width}x{self.viewport_height}), "
            f"scale={self.device_scale_factor}, proxy={self.proxy!r}, "
            f"output_dir='{self.output_dir}', debug_save_artifacts={self.debug_save_artifacts})"
        )


def load_settings() -> Settings:
    """按 APP_ENV 选择 .env 文件并加载；没有 .env 也能用默认值"""
    app_env = os.getenv("APP_ENV", "dev").lower()
    if app_env not in {"dev", "test", "prod"}:
        app_env = "dev"
    env_file = ENVS_DIR / f"{app_env}.env"
    if env_file.exists():
        return Settings(_env_file=env_file, _env_file_encoding="utf-8")
    return Settings()


# 全局单例（启动即校验）
try:
    settings = load_settings()
except ValidationError as e:
    raise SystemExit(f"[Settings Error] {e}") from e
