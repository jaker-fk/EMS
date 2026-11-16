"""操作日志公共写入。

被 `routers/api.py`（系统功能）与 `routers/edu.py`（教培业务）共用：
统一写 sys_oper_log，并给 request 打标记，避免中间件安全网重复记录。
"""
from datetime import datetime

from fastapi import Request
from sqlalchemy.orm import Session

from app.models.models import OperationLog


def client_ip(req: Request | None) -> str:
    if not req or not req.client:
        return ""
    return req.client.host


def fmt_dt(value: datetime | None) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S") if value else ""


def write_log(db: Session, user, module: str, action: str, req: Request | None,
              params: str = "", result: str = "成功", method: str = "",
              username: str = "") -> None:
    if req is not None:
        try:
            req.state.logged = True  # 已显式记录，中间件不再重复写
        except Exception:
            pass
    try:
        db.add(OperationLog(
            user_id=user.id if user else None,
            username=(user.username if user else username),
            module=module,
            action=action,
            method=method or (req.method if req else ""),
            path=req.url.path if req else "",
            ip=client_ip(req),
            params=(params or "")[:2000],
            result=result,
        ))
        db.commit()
    except Exception:
        db.rollback()
