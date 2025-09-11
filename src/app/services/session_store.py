# src/app/services/session_store.py
from __future__ import annotations
import threading, time
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Callable

@dataclass
class SessionRec:
    session_id: str
    user: str
    base_dir: str
    state: str = "waiting"  # waiting | otp_required | logged_in | closed | error
    shop_slug: Optional[str] = None
    page: Any = None
    context: Any = None
    release_ctx: Optional[Callable] = None
    created_at: float = field(default_factory=time.time)
    expires_at: float = field(default_factory=lambda: time.time() + 10 * 60)
    qr_expires_at: Optional[int] = None
    qrcode_b64: Optional[str] = None
    cookies_path: Optional[str] = None
    error_code: Optional[str] = None
    error_msg: Optional[str] = None

class SessionStore:
    def __init__(self, ttl_seconds: int = 10 * 60):
        self._mem: Dict[str, SessionRec] = {}
        self._lock = threading.RLock()
        self._ttl = ttl_seconds
        threading.Thread(target=self._gc_loop, daemon=True).start()

    def _gc_loop(self):
        while True:
            now = time.time()
            with self._lock:
                to_del = [
                    sid
                    for sid, rec in self._mem.items()
                    if rec.expires_at < now or rec.state in ("closed", "error")
                ]
                for sid in to_del:
                    self._mem.pop(sid, None)
            time.sleep(5)

    def put(self, rec: SessionRec):
        with self._lock:
            self._mem[rec.session_id] = rec

    def get(self, session_id: str) -> Optional[SessionRec]:
        with self._lock:
            return self._mem.get(session_id)

    def remove(self, session_id: str):
        with self._lock:
            self._mem.pop(session_id, None)

_store: Optional[SessionStore] = None
def get_store() -> SessionStore:
    global _store
    if _store is None:
        _store = SessionStore(ttl_seconds=10 * 60)
    return _store
