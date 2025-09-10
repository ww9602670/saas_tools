# 原子写 & 文件锁（临时文件 + os.replace）

# files.py
import json, os, tempfile, fcntl
from pathlib import Path

class FileLock:
    def __init__(self, path:Path): self.path = Path(str(path)+".lock")
    def __enter__(self):
        self.f = open(self.path, "w"); fcntl.flock(self.f, fcntl.LOCK_EX); return self
    def __exit__(self, exc_type, exc, tb): fcntl.flock(self.f, fcntl.LOCK_UN); self.f.close()

async def atomic_write_json(path:Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with FileLock(path):
        tmp = Path(tempfile.mkstemp(prefix=path.name, dir=path.parent)[1])
        with open(tmp, "w") as f: json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)

async def atomic_write_bytes(path:Path, data:bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    with FileLock(path):
        tmp = Path(tempfile.mkstemp(prefix=path.name, dir=path.parent)[1])
        with open(tmp, "wb") as f: f.write(data)
        os.replace(tmp, path)