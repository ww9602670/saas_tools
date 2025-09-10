# 会话存储：内存版 + Redis 元数据（owner_instance、TTL）

# session_store.py
import threading
from typing import Optional, Dict, Any
from dataclasses import dataclass

@dataclass
class SessionRec:
    session_id: str
    owner_instance: str               # 哪个实例持有 Page/Context
    user: str
    shop_slug: Optional[str]
    base_dir: str
    state: str                        # waiting / otp_required / logged_in / error
    page: Any = None                  # 仅在本实例内存持有
    context: Any = None
    qrcode_path: Optional[str] = None
    cookies_path: Optional[str] = None
    created_at: int = 0
    expires_at: int = 0
    qr_expires_at: Optional[int] = None
    error_code: Optional[str] = None
    error_msg: Optional[str] = None

class SessionStore:
    def __init__(self, settings, redis=None):
        self._mem: Dict[str, SessionRec] = {}
        self._lock = threading.RLock()
        self._settings = settings
        self._redis = redis    # 仅存元数据：{session_id: owner_instance}

    def register_owner(self, session_id:str, owner:str):
        if self._redis:
            self._redis.hset("session_owners", session_id, owner)

    def get_owner(self, session_id:str) -> Optional[str]:
        if self._redis:
            v = self._redis.hget("session_owners", session_id)
            return v.decode() if v else None
        rec = self._mem.get(session_id)
        return rec.owner_instance if rec else None

    def put_local(self, rec: SessionRec):
        with self._lock:
            self._mem[rec.session_id] = rec

    def get_local(self, session_id:str) -> Optional[SessionRec]:
        with self._lock:
            return self._mem.get(session_id)

    def remove_local(self, session_id:str):
        with self._lock:
            self._mem.pop(session_id, None)
