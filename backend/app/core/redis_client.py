"""Redis 热点缓存（可选）。本地无 Redis 时自动降级为进程内存缓存，避免连接阻塞。

设计：首次调用快速探测（1 次、1s 超时），失败后标记 _available=False，
后续请求直接走内存缓存，不再触碰网络。
"""
import time
import threading

try:
    import redis
    from app.core.config import settings
    _client = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        decode_responses=True,
        socket_connect_timeout=1,
        socket_timeout=1,
    )
except Exception:
    _client = None

_available: bool | None = None
_mem: dict = {}
_lock = threading.Lock()


def _probe() -> bool:
    global _available
    if _available is not None:
        return _available
    # 原生 socket 发 PING（1s 硬超时），绕开 redis-py 的重试/退避，保证最多慢 1 次、1 秒
    import socket as _socket
    try:
        s = _socket.create_connection((settings.REDIS_HOST, settings.REDIS_PORT), timeout=1)
        s.settimeout(1)
        try:
            s.sendall(b"*1\r\n$4\r\nPING\r\n")
            ok = s.recv(16).startswith(b"+PONG")
        finally:
            s.close()
        _available = bool(ok)
    except Exception:
        _available = False
    return _available


def redis_get(key: str):
    if _probe():
        try:
            v = _client.get(key)
            if v is not None:
                return v
        except Exception:
            pass
    with _lock:
        item = _mem.get(key)
        if item and item[1] > time.time():
            return item[0]
        _mem.pop(key, None)
    return None


def redis_set(key: str, value: str, ex: int = 300):
    with _lock:
        _mem[key] = (value, time.time() + ex)
    if _probe():
        try:
            _client.set(key, value, ex=ex)
        except Exception:
            pass


def redis_delete(*keys: str):
    with _lock:
        for k in keys:
            _mem.pop(k, None)
    if _probe():
        try:
            if keys:
                _client.delete(*keys)
        except Exception:
            pass
