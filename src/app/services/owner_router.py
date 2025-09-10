# 1+N 路由：基于 Redis 的 session→worker 归属 & 反向代理

# owner_router.py
import httpx
from fastapi import HTTPException
from .session_store import SessionStore

class OwnerRouter:
    def __init__(self, settings, store: SessionStore):
        self.settings = settings
        self.store = store

    async def forward_if_not_owner(self, session_id: str, path: str, method:str="GET", json=None):
        owner = self.store.get_owner(session_id)
        if self.settings.role in ("monolith", "worker"):
            # 本实例可能就是owner
            if owner and owner != self.settings.instance_id:
                # 1+N：转发到 owner 的 /internal/*
                url = f"http://{owner}/internal{path}"   # owner 需在注册时带主机:端口
                async with httpx.AsyncClient(timeout=10) as cli:
                    r = await getattr(cli, method.lower())(url, json=json)
                    r.raise_for_status()
                    return r.json()
            return None
        elif self.settings.role == "gateway":
            if not owner:
                raise HTTPException(status_code=404, detail="session not found")
            url = f"http://{owner}/internal{path}"
            async with httpx.AsyncClient(timeout=10) as cli:
                r = await getattr(cli, method.lower())(url, json=json)
                r.raise_for_status()
                return r.json()
