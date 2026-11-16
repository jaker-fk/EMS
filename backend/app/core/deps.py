from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, get_db
from app.core.security import ADMIN_SCOPE, SITE_SCOPE, decode_token
from app.models.models import Menu, OperationLog, Role, RoleMenu, SiteUser, User, UserRole

sec = HTTPBearer(auto_error=False)


def get_current_user(
    req: Request,
    cred: HTTPAuthorizationCredentials = Depends(sec),
    db: Session = Depends(get_db),
) -> User:
    token = cred.credentials if cred else ""
    if not token:
        raise HTTPException(status_code=401, detail="未登录")
    uid = decode_token(token, scope=ADMIN_SCOPE)
    if not uid:
        raise HTTPException(status_code=401, detail="Token 已过期")
    try:
        uid_int = int(uid)
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Token 无效") from None
    u = db.query(User).filter(User.id == uid_int, User.is_deleted == 0).first()
    if not u:
        raise HTTPException(status_code=401, detail="账号不存在或已删除")
    if u.status == 0:
        raise HTTPException(status_code=401, detail="账号已禁用")
    req.state.current_user = u
    return u


def _site_user_from_token(db: Session, token: str) -> SiteUser | None:
    """解析前台学员 Token；作用域不符 / 账号不可用时返回 None。"""
    uid = decode_token(token, scope=SITE_SCOPE)
    if not uid:
        return None
    try:
        uid_int = int(uid)
    except (TypeError, ValueError):
        return None
    u = db.query(SiteUser).filter(SiteUser.id == uid_int, SiteUser.is_deleted == 0).first()
    if not u or u.status == 0:
        return None
    return u


def get_current_site_user(
    req: Request,
    cred: HTTPAuthorizationCredentials = Depends(sec),
    db: Session = Depends(get_db),
) -> SiteUser:
    """前台学员身份依赖：后台管理员 Token 在这里会被拒绝（scope 不同）。"""
    token = cred.credentials if cred else ""
    if not token:
        raise HTTPException(status_code=401, detail="请先登录学员账号")
    u = _site_user_from_token(db, token)
    if not u:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    req.state.current_site_user = u
    return u


def get_optional_site_user(
    req: Request,
    cred: HTTPAuthorizationCredentials = Depends(sec),
    db: Session = Depends(get_db),
) -> SiteUser | None:
    """免登录接口的可选学员身份：带合法学员 Token 时返回账号，否则按游客处理。"""
    token = cred.credentials if cred else ""
    if not token:
        return None
    u = _site_user_from_token(db, token)
    if u:
        req.state.current_site_user = u
    return u


def is_super_admin(user: User, db: Session) -> bool:
    roles = (
        db.query(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .filter(UserRole.user_id == user.id)
        .all()
    )
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


def request_perms(req: Request, db: Session, user: User) -> set[str]:
    """同一次请求内复用权限集合，避免一个接口多个依赖重复查库。"""
    cached = getattr(req.state, "perms", None)
    if cached is None:
        cached = user_perms(db, user)
        req.state.perms = cached
    return cached


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

    def checker(
        req: Request,
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        if not required:
            return user
        have = request_perms(req, db, user)
        if "*" in have or any(p in have for p in required):
            return user
        _log_denied(req, user, required)
        raise HTTPException(status_code=403, detail=f"无权限：{required[0]}")

    return checker
