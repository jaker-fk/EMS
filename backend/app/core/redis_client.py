"""Redis 热点缓存（可选）：不可用时自动降级为进程内存，避免请求被网络阻塞。

生产多实例部署请开启 Redis；`REDIS_REQUIRED=true` 时 /api/ready 会因 Redis 不可用而失败。
"""
import threading
import time

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
except Exception:  # pragma: no cover - 依赖缺失时直接降级
    _client = None

_available: bool | None = None
_mem: dict = {}
_lock = threading.Lock()

# 原子自增 + 首次设置过期时间：限流、登录失败计数都用它，避免 GET+SET 的竞态
_INCR_LUA = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then
  redis.call('PEXPIRE', KEYS[1], ARGV[1])
end
return current
"""


def _probe() -> bool:
    global _available
    if _available is not None:
        return _available
    _available = ping()
    return _available


def ping() -> bool:
    """每次真实探测一次，供 /api/ready 使用；同时刷新缓存状态。"""
    global _available
    if _client is None:
        _available = False
        return False
    try:
        _available = bool(_client.ping())
    except Exception:
        _available = False
    return _available


def get_client():
    """返回可用的 redis 客户端；未连接时返回 None（调用方需自行降级）。"""
    return _client if _probe() else None


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


def incr_with_ttl(key: str, ttl: int) -> int:
    """原子自增并在首次写入时设置过期时间；Redis 不可用时退化为进程内计数。"""
    client = get_client()
    if client is not None:
        try:
            return int(client.eval(_INCR_LUA, 1, key, max(int(ttl * 1000), 1000)))
        except Exception:
            pass
    with _lock:
        value, expires = _mem.get(key, (0, 0))
        now = time.time()
        if expires <= now:
            value = 0
        value = int(value) + 1
        _mem[key] = (value, now + ttl)
        return value


def available() -> bool:
    """当前是否真的连上了 Redis（供看板 / 健康检查展示缓存模式）。"""
    return bool(_probe())
