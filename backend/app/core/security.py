import re
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt

from app.core import redis_client
from app.core.config import settings


def hash_password(p: str) -> str:
    return bcrypt.hashpw(p.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(p: str, h: str) -> bool:
    try:
        return bcrypt.checkpw(p.encode("utf-8"), h.encode("utf-8"))
    except Exception:
        return False


def password_policy_error(p: str) -> str | None:
    """密码强度校验：返回给用户的中文提示，None 表示通过。"""
    p = p or ""
    if len(p) < settings.PASSWORD_MIN_LEN:
        return f"密码长度至少 {settings.PASSWORD_MIN_LEN} 位"
    classes = sum(
        bool(re.search(pattern, p))
        for pattern in (r"[a-z]", r"[A-Z]", r"\d", r"[^A-Za-z0-9]")
    )
    if classes < settings.PASSWORD_MIN_CLASSES:
        return "密码需包含小写字母、大写字母、数字、符号中的至少两类"
    if len(set(p)) <= 2:
        return "密码过于简单，请勿使用重复字符"
    return None


def _now() -> datetime:
    """统一使用带时区的 UTC 时间，避免 utcnow() 被当作本地时间参与计算。"""
    return datetime.now(timezone.utc)


# Token 作用域：后台管理员与前台学员账号各用一套，互相不能串用。
ADMIN_SCOPE = "admin"
SITE_SCOPE = "site"


def create_token(sub: str, scope: str = ADMIN_SCOPE) -> str:
    exp = _now() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(sub), "jti": uuid.uuid4().hex, "scope": scope, "exp": exp}
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


def decode_token(token: str, scope: str | None = None) -> str | None:
    """解析 Token 并校验作用域；不带 scope 的历史 Token 只当作后台管理员 Token。"""
    payload = decode_payload(token)
    if not payload:
        return None
    if scope is not None and str(payload.get("scope") or ADMIN_SCOPE) != scope:
        return None
    sub = payload.get("sub")
    return str(sub) if sub is not None else None


def blacklist_token(token: str, scope: str | None = None) -> None:
    """登出时把 Token 的 jti 写入黑名单，剩余有效期过后自动过期。

    ``scope`` 用于防止用前台接口注销后台 Token（或反之）。
    """
    payload = decode_payload(token)
    if not payload:
        return
    if scope is not None and str(payload.get("scope") or ADMIN_SCOPE) != scope:
        return
    jti = payload.get("jti")
    exp = payload.get("exp")
    if not jti:
        return
    ttl = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    if exp:
        # exp 是 epoch 秒：必须用「带时区的当前时间」相减，
        # 否则 utcnow().timestamp() 会按本地时区解释，导致黑名单过期时间偏移 8 小时。
        ttl = max(int(exp - _now().timestamp()), 1)
    redis_client.redis_set(f"jwt:black:{jti}", "1", ex=ttl)
