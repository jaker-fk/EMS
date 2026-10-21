"""轻量级接口限流（滑动窗口，进程内存实现）。

生产环境可替换为 Redis + Lua 或 slowapi，这里用于演示“接口防刷 / 防重复提交”思路：
- 登录接口按 IP 限制（默认 10 次 / 60 秒）
- 其他写操作按 IP + 方法 + 路径限制（默认 60 次 / 60 秒）
"""
import threading
import time
from collections import defaultdict, deque

_lock = threading.Lock()
_buckets: dict[str, deque] = defaultdict(deque)


def allow(key: str, limit: int, window: int = 60) -> bool:
    now = time.time()
    with _lock:
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
