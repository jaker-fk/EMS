"""接口限流：优先 Redis 固定窗口（多实例共享），Redis 不可用时退化为进程内存滑动窗口。

- 登录：按 IP 10 次 / 60 秒
- 其他写操作：按 IP + 方法 + 路径 60 次 / 60 秒
"""
import threading
import time
from collections import defaultdict, deque

from app.core import redis_client

_mem_lock = threading.Lock()
_buckets: dict[str, deque] = defaultdict(deque)


def _redis_allow(key: str, limit: int, window: int) -> bool | None:
    client = redis_client.get_client()
    if client is None:
        return None
    try:
        count = redis_client.incr_with_ttl(f"rl:{key}", window)
        return count <= limit
    except Exception:  # pragma: no cover - 极端情况下回退内存
        return None


def _memory_allow(key: str, limit: int, window: int) -> bool:
    now = time.time()
    with _mem_lock:
        dq = _buckets[key]
        while dq and now - dq[0] > window:
            dq.popleft()
        if len(dq) >= limit:
            return False
        dq.append(now)
        # 防止内存持续增长
        if len(_buckets) > 10000:
            for k, v in list(_buckets.items()):
                if not v or now - v[-1] > window * 5:
                    _buckets.pop(k, None)
        return True


def allow(key: str, limit: int, window: int = 60) -> bool:
    result = _redis_allow(key, limit, window)
    if result is not None:
        return result
    return _memory_allow(key, limit, window)
