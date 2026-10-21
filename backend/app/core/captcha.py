"""图形验证码：生成随机字符 + 输出 SVG（无需 Pillow 依赖），答案存入 Redis/内存。"""
import base64
import random
import uuid

from app.core import redis_client

_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _svg(code: str) -> str:
    width, height = 120, 40
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f2f5fa"/>',
    ]
    # 干扰线
    for _ in range(5):
        x1, y1 = random.randint(0, width), random.randint(0, height)
        x2, y2 = random.randint(0, width), random.randint(0, height)
        color = f"#{random.randint(120, 200):02x}{random.randint(120, 200):02x}{random.randint(120, 200):02x}"
        parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="1"/>')
    # 字符
    for i, ch in enumerate(code):
        color = f"#{random.randint(20, 110):02x}{random.randint(20, 110):02x}{random.randint(20, 110):02x}"
        x = 14 + i * 26
        y = 28 + random.randint(-4, 4)
        rot = random.randint(-20, 20)
        parts.append(
            f'<text x="{x}" y="{y}" font-size="24" font-family="Arial" font-weight="bold" '
            f'fill="{color}" transform="rotate({rot} {x} {y})">{ch}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def generate() -> dict:
    code = "".join(random.choice(_CHARS) for _ in range(4))
    key = uuid.uuid4().hex
    redis_client.redis_set(f"captcha:{key}", code.lower(), ex=120)
    svg = _svg(code)
    b64 = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return {"key": key, "image": f"data:image/svg+xml;base64,{b64}"}


def verify(key: str, code: str) -> bool:
    if not key or not code:
        return False
    stored = redis_client.redis_get(f"captcha:{key}")
    redis_client.redis_delete(f"captcha:{key}")
    return bool(stored) and stored == code.strip().lower()
