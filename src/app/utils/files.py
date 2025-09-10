import json, os, tempfile
from pathlib import Path

# Linux 容器里可用 fcntl；如需跨平台，后续换 filelock
import fcntl

class FileLock:
    def __init__(self, path: Path):
        self.lock_path = Path(str(path) + ".lock")
        self.f = None

    def __enter__(self):
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self.f = open(self.lock_path, "w")
        fcntl.flock(self.f, fcntl.LOCK_EX)
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            fcntl.flock(self.f, fcntl.LOCK_UN)
        finally:
            self.f.close()

def _atomic_write_bytes(path: Path, data: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=path.name, dir=path.parent)
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    os.replace(tmp_path, path)
    try:
        os.chmod(path, 0o600)
    except Exception:
        pass

def atomic_write_json(path: Path, obj):
    data = json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8")
    with FileLock(path):
        _atomic_write_bytes(path, data)

def atomic_write_bytes(path: Path, data: bytes):
    with FileLock(path):
        _atomic_write_bytes(path, data)
