from datetime import datetime, timedelta
import uuid

import bcrypt
from jose import jwt

from app.core.config import settings
from app.core import redis_client


def hash_password(p: str) -> str:
    return bcrypt.hashpw(p.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(p: str, h: str) -> bool:
    try:
        return bcrypt.checkpw(p.encode("utf-8"), h.encode("utf-8"))
    except Exception:
        return False


def create_token(sub: str) -> str:
    exp = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(sub), "jti": uuid.uuid4().hex, "exp": exp}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_payload(token: str) -> dict | None:
    """解析 Token，命中 Redis 黑名单（登出）则视为失效。"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except Exception:
        return None
    jti = payload.get("jti")
    if jti and redis_client.redis_get(f"jwt:black:{jti}"):
        return None
    return payload


def decode_token(token: str) -> str | None:
    payload = decode_payload(token)
    if not payload:
        return None
    sub = payload.get("sub")
    return str(sub) if sub is not None else None


def blacklist_token(token: str) -> None:
    """登出时把 Token 的 jti 写入黑名单，剩余有效期过后自动过期。"""
    payload = decode_payload(token)
    if not payload:
        return
    jti = payload.get("jti")
    exp = payload.get("exp")
    if not jti:
        return
    ttl = 3600
    if exp:
        ttl = max(int(exp - datetime.utcnow().timestamp()), 1)
    redis_client.redis_set(f"jwt:black:{jti}", "1", ex=ttl)
