from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, get_db
from app.core.security import decode_token
from app.models.models import Menu, OperationLog, Role, RoleMenu, User, UserRole

sec = HTTPBearer(auto_error=False)


def get_current_user(req: Request, cred: HTTPAuthorizationCredentials = Depends(sec), db: Session = Depends(get_db)) -> User:
    token = cred.credentials if cred else ""
    if not token:
        raise HTTPException(status_code=401, detail="未登录")
    uid = decode_token(token)
    if not uid:
        raise HTTPException(status_code=401, detail="Token过期")
    u = db.query(User).filter(User.id == int(uid)).first()
    if not u or u.status == 0:
        raise HTTPException(status_code=401, detail="账号不可用")
    return u


def is_super_admin(user: User, db: Session) -> bool:
    roles = db.query(Role.name).join(UserRole, UserRole.role_id == Role.id).filter(UserRole.user_id == user.id).all()
    return any(r[0] == "super_admin" for r in roles)


def user_perms(db: Session, user: User) -> set[str]:
    """当前用户拥有的权限标识集合（角色 -> 菜单/按钮 perms）；超级管理员返回 {"*"}。"""
    if is_super_admin(user, db):
        return {"*"}
    rows = (
        db.query(Menu.perms)
        .join(RoleMenu, RoleMenu.menu_id == Menu.id)
        .join(UserRole, UserRole.role_id == RoleMenu.role_id)
        .filter(UserRole.user_id == user.id, Menu.is_deleted == 0, Menu.perms != "")
        .all()
    )
    return {r[0] for r in rows if r[0]}


def _log_denied(req: Request, user: User, required: tuple[str, ...]) -> None:
    """记录越权访问，并标记本次请求已写日志，避免中间件重复记录。"""
    try:
        try:
            req.state.logged = True
        except Exception:
            pass
        db = SessionLocal()
        try:
            db.add(OperationLog(
                user_id=user.id if user else None,
                username=user.username if user else "",
                module="权限校验", action="越权访问",
                method=req.method, path=req.url.path,
                ip=(req.client.host if req.client else ""),
                params=",".join(required), result="失败",
            ))
            db.commit()
        finally:
            db.close()
    except Exception:
        pass


def require_perms(*required: str):
    """接口级权限依赖：命中任一权限标识即放行，超级管理员直通，否则 403。"""

    def checker(req: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
        if not required:
            return user
        have = user_perms(db, user)
        if "*" in have or any(p in have for p in required):
            return user
        _log_denied(req, user, required)
        raise HTTPException(status_code=403, detail=f"无权限：{required[0]}")

    return checker
