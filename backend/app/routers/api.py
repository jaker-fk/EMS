import io
import json
import os
import platform
import re
import time
import uuid
from datetime import date, datetime, timedelta
from datetime import time as dtime

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core import captcha, redis_client
from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user, is_super_admin, require_perms
from app.core.oplog import fmt_dt as _fmt
from app.core.oplog import write_log as log
from app.core.response import Resp
from app.core.security import (
    ADMIN_SCOPE,
    blacklist_token,
    create_token,
    hash_password,
    password_policy_error,
    verify_password,
)
from app.models.models import (
    BusinessData,
    DictItem,
    DictType,
    FileRecord,
    Menu,
    OperationLog,
    Role,
    RoleMenu,
    User,
    UserRole,
)
from app.schemas.schemas import (
    BatchStatusIn,
    BizCreate,
    ChangePwdIn,
    DictItemCreate,
    DictTypeCreate,
    LoginIn,
    MenuCreate,
    ProfileUpdate,
    ResetPwdIn,
    RoleCreate,
    UserCreate,
    UserUpdate,
)

router = APIRouter()

_START_TIME = time.time()
_UNSAFE_FILENAME = re.compile(r"[^\w\-. \u4e00-\u9fa5]")


# ---------------------------------------------------------------- helpers
def _paging(page: int, size: int) -> tuple[int, int]:
    """分页参数兜底：page>=1，1<=size<=100，避免超大 limit 拖垮数据库。"""
    try:
        page = int(page)
    except (TypeError, ValueError):
        page = 1
    try:
        size = int(size)
    except (TypeError, ValueError):
        size = 10
    return max(page, 1), min(max(size, 1), 100)


def _super(db: Session, user: User) -> bool:
    return is_super_admin(user, db)


def _role_ids(db: Session, uid: int) -> list[int]:
    return [x.role_id for x in db.query(UserRole).filter(UserRole.user_id == uid).all()]


def _role_names(db: Session, uid: int) -> list[str]:
    ids = _role_ids(db, uid)
    if not ids:
        return []
    return [r.name for r in db.query(Role).filter(Role.id.in_(ids)).all()]


def _has_role(db: Session, uid: int, name: str) -> bool:
    return db.query(Role).join(UserRole, UserRole.role_id == Role.id).filter(
        UserRole.user_id == uid, Role.name == name
    ).first() is not None


def _valid_role_ids(db: Session, role_ids: list[int]) -> list[int]:
    """过滤掉不存在 / 已删除的角色，避免脏关联。"""
    if not role_ids:
        return []
    rows = db.query(Role.id).filter(Role.id.in_(role_ids), Role.is_deleted == 0).all()
    return [r[0] for r in rows]


def _valid_menu_ids(db: Session, menu_ids: list[int]) -> list[int]:
    if not menu_ids:
        return []
    rows = db.query(Menu.id).filter(Menu.id.in_(menu_ids), Menu.is_deleted == 0).all()
    return [r[0] for r in rows]


def _guard_super_target(db: Session, operator: User, uid: int) -> str | None:
    """非超级管理员不得修改 / 删除超级管理员账号。"""
    if uid == operator.id:
        return None
    if _has_role(db, uid, "super_admin") and not _super(db, operator):
        return "无权操作超级管理员账号"
    return None


def _bump_menus():
    redis_client.redis_set("cache:menus:ver", uuid.uuid4().hex, ex=86400 * 30)


def _bump_dicts():
    redis_client.redis_set("cache:dict:ver", uuid.uuid4().hex, ex=86400 * 30)


def _menu_version() -> str:
    return redis_client.redis_get("cache:menus:ver") or "0"


def _dict_version() -> str:
    return redis_client.redis_get("cache:dict:ver") or "0"


def _to_tree(rows: list[Menu], skip_types=("F",)) -> list[dict]:
    items = {}
    for m in rows:
        if m.menu_type in skip_types:
            continue
        items[m.id] = {
            "id": m.id, "parent_id": m.parent_id, "name": m.name,
            "menu_type": m.menu_type, "path": m.path, "component": m.component,
            "perms": m.perms, "icon": m.icon, "sort": m.sort,
            "visible": m.visible, "children": [],
        }
    roots = []
    for node in items.values():
        pid = node["parent_id"]
        if pid and pid in items:
            items[pid]["children"].append(node)
        else:
            roots.append(node)
    return roots


def _menu_descendant_ids(db: Session, mid: int) -> set[int]:
    """返回某菜单的全部后代 id，用于阻止把父级指向自己的子级（形成环）。"""
    rows = db.query(Menu.id, Menu.parent_id).filter(Menu.is_deleted == 0).all()
    children: dict[int, list[int]] = {}
    for cid, pid in rows:
        children.setdefault(pid, []).append(cid)
    result, stack = set(), [mid]
    while stack:
        for child in children.get(stack.pop(), []):
            if child not in result:
                result.add(child)
                stack.append(child)
    return result


def _accessible_menus(db: Session, user: User) -> list[Menu]:
    rows = db.query(Menu).filter(Menu.is_deleted == 0).order_by(Menu.sort, Menu.id).all()
    if _super(db, user):
        return rows
    by_id = {m.id: m for m in rows}
    mids = set(
        rm.menu_id
        for role_id in _role_ids(db, user.id)
        for rm in db.query(RoleMenu).filter(RoleMenu.role_id == role_id).all()
    )
    # 把已选菜单的祖先目录一并纳入，保证树完整
    for mid in list(mids):
        cur = by_id.get(mid)
        while cur and cur.parent_id and cur.parent_id in by_id:
            mids.add(cur.parent_id)
            cur = by_id.get(cur.parent_id)
    return [m for m in rows if m.id in mids]


def _user_context(db: Session, user: User) -> dict:
    is_super = _super(db, user)
    menus = _accessible_menus(db, user)
    # 超级管理员前端同样用通配符表示全部按钮权限，与后端 require_perms 保持一致
    perms = ["*"] if is_super else sorted({m.perms for m in menus if m.perms})
    tree = _to_tree(menus, skip_types=("F",))

    # 只保留可见菜单
    def prune(nodes):
        out = []
        for n in nodes:
            n["children"] = prune(n["children"])
            if n["visible"]:
                out.append(n)
        return out

    return {
        "menus": prune(tree),
        "perms": perms,
        "user": {"id": user.id, "username": user.username, "nickname": user.nickname},
        "roles": _role_names(db, user.id),
    }


def _user_row(db: Session, u: User) -> dict:
    rids = _role_ids(db, u.id)
    names = [r.name for r in db.query(Role).filter(Role.id.in_(rids)).all()] if rids else []
    return {
        "id": u.id, "username": u.username, "nickname": u.nickname,
        "phone": u.phone, "status": u.status,
        "role_ids": rids, "role_names": names,
        "created_at": _fmt(u.created_at),
    }


def _log_row(r: OperationLog) -> dict:
    return {
        "id": r.id, "username": r.username, "module": r.module, "action": r.action,
        "method": r.method, "path": r.path, "ip": r.ip, "params": r.params,
        "result": r.result, "created_at": _fmt(r.created_at),
    }


def _parse_ids(ids: str) -> list[int]:
    seen, out = set(), []
    for part in (ids or "").split(","):
        part = part.strip()
        if part.isdigit():
            v = int(part)
            if v not in seen:
                seen.add(v)
                out.append(v)
    return out


def _date_bound(value: str, is_end: bool) -> str:
    """只传日期（YYYY-MM-DD）时补齐时分秒，保证结束日整日包含。"""
    v = (value or "").strip()
    if len(v) == 10:
        return f"{v} 23:59:59" if is_end else f"{v} 00:00:00"
    return v


def _display_filename(name: str) -> str:
    """清洗用户上传的原始文件名：去掉目录部分，过滤特殊字符，限制长度。"""
    base = os.path.basename((name or "").replace("\\", "/")).strip()
    base = _UNSAFE_FILENAME.sub("_", base).strip(" .")
    return (base or "file")[:120]


def _xlsx_response(wb: Workbook, filename: str) -> StreamingResponse:
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _log_query(db: Session, username: str, module: str, action: str, result: str,
               keyword: str, start: str, end: str):
    q = db.query(OperationLog)
    if username:
        q = q.filter(OperationLog.username.like(f"%{username}%"))
    if module:
        q = q.filter(OperationLog.module == module)
    if action:
        q = q.filter(OperationLog.action == action)
    if result:
        q = q.filter(OperationLog.result == result)
    if keyword:
        like = f"%{keyword}%"
        q = q.filter(
            (OperationLog.path.like(like))
            | (OperationLog.params.like(like))
            | (OperationLog.username.like(like))
        )
    if start:
        q = q.filter(OperationLog.created_at >= _date_bound(start, False))
    if end:
        q = q.filter(OperationLog.created_at <= _date_bound(end, True))
    return q


# ---------------------------------------------------------------- auth
@router.get("/auth/captcha")
def auth_captcha():
    """返回验证码开关状态；关闭时前端直接隐藏验证码输入框。"""
    if not settings.CAPTCHA_ENABLED:
        return Resp.ok({"enabled": False})
    return Resp.ok({"enabled": True, **captcha.generate()})


@router.post("/auth/login")
def login(body: LoginIn, req: Request, db: Session = Depends(get_db)):
    if settings.CAPTCHA_ENABLED and not captcha.verify(body.captcha_key, body.captcha_code):
        return Resp.fail("验证码错误或已过期", code=400)

    username = body.username.strip()
    fail_key = f"login:fail:{username.lower()}"
    fails = int(redis_client.redis_get(fail_key) or 0)
    if fails >= settings.LOGIN_MAX_FAILS:
        return Resp.fail(
            f"密码错误次数过多，请 {settings.LOGIN_LOCK_MINUTES} 分钟后再试", code=429
        )

    u = db.query(User).filter(User.username == username, User.is_deleted == 0).first()
    if not u or not verify_password(body.password, u.password_hash):
        # 用原子自增计数，避免多实例并发下 GET+SET 竞态导致锁定失效
        fails_now = redis_client.incr_with_ttl(fail_key, settings.LOGIN_LOCK_MINUTES * 60)
        log(db, None, "登录", "登录", req, params=username, result="失败",
            method="POST", username=username)
        left = settings.LOGIN_MAX_FAILS - fails_now
        if left <= 0:
            return Resp.fail(
                f"账号或密码错误，账号已锁定 {settings.LOGIN_LOCK_MINUTES} 分钟", code=400
            )
        return Resp.fail(f"账号或密码错误，还可尝试 {left} 次", code=400)

    if u.status == 0:
        log(db, u, "登录", "登录", req, params=username, result="失败", method="POST")
        return Resp.fail("账号已禁用，请联系管理员", code=403)

    redis_client.redis_delete(fail_key)
    token = create_token(str(u.id))
    log(db, u, "登录", "登录", req, params=username, result="成功", method="POST")
    return Resp.ok({
        "token": token,
        "user": {"id": u.id, "username": u.username, "nickname": u.nickname},
        "role_ids": _role_ids(db, u.id),
    })


@router.post("/auth/logout")
def logout(req: Request):
    auth = req.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        # 只注销后台管理员 Token，避免误伤同一浏览器里的前台学员登录
        blacklist_token(auth[7:], scope=ADMIN_SCOPE)
    return Resp.ok(msg="已退出登录")


@router.get("/auth/menus")
def my_menus(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """当前用户可访问的菜单树 + 按钮权限标识（Redis 缓存）。"""
    key = f"ctx:{_menu_version()}:{user.id}"
    cached = redis_client.redis_get(key)
    if cached:
        return Resp.ok(json.loads(cached))
    ctx = _user_context(db, user)
    redis_client.redis_set(key, json.dumps(ctx, ensure_ascii=False), ex=settings.CACHE_TTL)
    return Resp.ok(ctx)


# ---------------------------------------------------------------- dashboard
@router.get("/dashboard/overview")
def dashboard_overview(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """首页数据看板：核心计数 + 近 7 天操作趋势 + 模块分布 + 最近操作 + 运行信息。"""
    today = date.today()
    week_start = datetime.combine(today - timedelta(days=6), dtime.min)
    today_start = datetime.combine(today, dtime.min)

    cards = {
        "users": db.query(User).filter(User.is_deleted == 0).count(),
        "roles": db.query(Role).filter(Role.is_deleted == 0).count(),
        "menus": db.query(Menu).filter(Menu.is_deleted == 0).count(),
        "files": db.query(FileRecord).count(),
        "biz": db.query(BusinessData).count(),
        "logs": db.query(OperationLog).count(),
    }
    today_logs = db.query(OperationLog).filter(OperationLog.created_at >= today_start).count()
    fail_logs = db.query(OperationLog).filter(OperationLog.result == "失败").count()
    new_users = db.query(User).filter(
        User.is_deleted == 0, User.created_at >= week_start
    ).count()

    # 近 7 天趋势（按天分组，MySQL 与 SQLite 均可用 func.date）
    day_col = func.date(OperationLog.created_at)
    rows = (
        db.query(day_col, func.count(OperationLog.id))
        .filter(OperationLog.created_at >= week_start)
        .group_by(day_col)
        .all()
    )
    counted = {str(r[0]): int(r[1]) for r in rows if r[0] is not None}
    trend = []
    for offset in range(6, -1, -1):
        d = today - timedelta(days=offset)
        trend.append({"date": d.strftime("%m-%d"), "count": counted.get(d.isoformat(), 0)})

    count_col = func.count(OperationLog.id)
    modules = [
        {"name": (name or "未分类"), "value": int(value)}
        for name, value in (
            db.query(OperationLog.module, count_col)
            .group_by(OperationLog.module)
            .order_by(count_col.desc())
            .limit(6)
            .all()
        )
    ]

    recent = [
        _log_row(r)
        for r in db.query(OperationLog).order_by(OperationLog.id.desc()).limit(8).all()
    ]

    try:
        db_name = db.get_bind().dialect.name
    except Exception:
        db_name = "unknown"

    return Resp.ok({
        "cards": cards,
        "todayLogs": today_logs,
        "failLogs": fail_logs,
        "newUsers": new_users,
        "trend": trend,
        "modules": modules,
        "recent": recent,
        "system": {
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "python": platform.python_version(),
            "database": db_name,
            "cache": "redis" if redis_client.available() else "memory",
            "captcha": settings.CAPTCHA_ENABLED,
            "uptime": int(time.time() - _START_TIME),
        },
    })


# ---------------------------------------------------------------- users
@router.get("/users", dependencies=[Depends(require_perms("system:user:list"))])
def list_users(keyword: str = "", status: int | None = None, page: int = 1, size: int = 10,
               db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    page, size = _paging(page, size)
    q = db.query(User).filter(User.is_deleted == 0)
    if keyword:
        q = q.filter((User.username.like(f"%{keyword}%")) | (User.nickname.like(f"%{keyword}%")))
    if status is not None:
        q = q.filter(User.status == status)
    total = q.count()
    rows = q.order_by(User.id.desc()).offset((page - 1) * size).limit(size).all()
    return Resp.page(total, [_user_row(db, r) for r in rows])


@router.get("/users/export", dependencies=[Depends(require_perms("system:user:list"))])
def export_users(keyword: str = "", status: int | None = None, req: Request = None,
                 db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = db.query(User).filter(User.is_deleted == 0)
    if keyword:
        q = q.filter((User.username.like(f"%{keyword}%")) | (User.nickname.like(f"%{keyword}%")))
    if status is not None:
        q = q.filter(User.status == status)
    rows = q.order_by(User.id.desc()).limit(10000).all()

    wb = Workbook()
    ws = wb.active
    ws.title = "用户列表"
    ws.append(["ID", "账号", "昵称", "手机号", "角色", "状态", "创建时间"])
    for r in rows:
        ws.append([
            r.id, r.username, r.nickname, r.phone, "、".join(_role_names(db, r.id)),
            "启用" if r.status else "禁用", _fmt(r.created_at),
        ])
    for column, width in zip("ABCDEFG", (8, 18, 18, 16, 24, 10, 20), strict=False):
        ws.column_dimensions[column].width = width

    log(db, user, "用户管理", "导出", req, params=keyword, method="GET")
    return _xlsx_response(wb, f"users_{datetime.now():%Y%m%d%H%M%S}.xlsx")


@router.post("/users", dependencies=[Depends(require_perms("system:user:add"))])
def create_user(body: UserCreate, req: Request, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    if db.query(User).filter(User.username == body.username, User.is_deleted == 0).first():
        return Resp.fail("用户名已存在")
    err = password_policy_error(body.password)
    if err:
        return Resp.fail(err)
    u = User(username=body.username, password_hash=hash_password(body.password),
             nickname=body.nickname, phone=body.phone, status=body.status)
    db.add(u)
    db.commit()
    db.refresh(u)
    for rid in _valid_role_ids(db, body.role_ids):
        db.add(UserRole(user_id=u.id, role_id=rid))
    db.commit()
    _bump_menus()
    log(db, user, "用户管理", "新增", req, params=body.username, method="POST")
    return Resp.ok({"id": u.id})


@router.put("/users/batch/status", dependencies=[Depends(require_perms("system:user:edit"))])
def batch_user_status(body: BatchStatusIn, req: Request, db: Session = Depends(get_db),
                      user: User = Depends(get_current_user)):
    ids = [i for i in body.ids if i]
    if not ids:
        return Resp.fail("参数错误")
    if body.status == 0 and user.id in ids:
        return Resp.fail("不能禁用当前登录账号")
    targets = db.query(User).filter(User.id.in_(ids), User.is_deleted == 0).all()
    for t in targets:
        if body.status == 0 and _has_role(db, t.id, "super_admin") and not _super(db, user):
            return Resp.fail("无权禁用超级管理员账号")
        t.status = body.status
    db.commit()
    log(db, user, "用户管理", "批量启用" if body.status else "批量禁用", req,
        params=",".join(str(i) for i in ids), method="PUT")
    return Resp.ok({"changed": len(targets)})


@router.put("/users/{uid}", dependencies=[Depends(require_perms("system:user:edit"))])
def update_user(uid: int, body: UserUpdate, req: Request, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    u = db.query(User).filter(User.id == uid, User.is_deleted == 0).first()
    if not u:
        return Resp.fail("用户不存在")
    denied = _guard_super_target(db, user, uid)
    if denied:
        return Resp.fail(denied, code=403)
    if body.nickname is not None:
        u.nickname = body.nickname
    if body.phone is not None:
        u.phone = body.phone
    if body.status is not None:
        if uid == user.id and body.status == 0:
            return Resp.fail("不能禁用当前登录账号")
        u.status = body.status
    if body.role_ids is not None:
        if uid == user.id and _has_role(db, uid, "super_admin"):
            super_role = db.query(Role).filter(Role.name == "super_admin").first()
            keep = _valid_role_ids(db, body.role_ids)
            if super_role and super_role.id not in keep:
                return Resp.fail("不能移除自己的超级管理员角色", code=403)
        db.query(UserRole).filter(UserRole.user_id == uid).delete()
        for rid in _valid_role_ids(db, body.role_ids):
            db.add(UserRole(user_id=uid, role_id=rid))
    db.commit()
    _bump_menus()
    log(db, user, "用户管理", "修改", req, params=u.username, method="PUT")
    return Resp.ok()


@router.put("/users/{uid}/password", dependencies=[Depends(require_perms("system:user:reset"))])
def reset_password(uid: int, body: ResetPwdIn, req: Request, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    u = db.query(User).filter(User.id == uid, User.is_deleted == 0).first()
    if not u:
        return Resp.fail("用户不存在")
    denied = _guard_super_target(db, user, uid)
    if denied:
        return Resp.fail(denied, code=403)
    err = password_policy_error(body.password)
    if err:
        return Resp.fail(err)
    u.password_hash = hash_password(body.password)
    db.commit()
    log(db, user, "用户管理", "重置密码", req, params=u.username, method="PUT")
    return Resp.ok()


@router.delete("/users", dependencies=[Depends(require_perms("system:user:remove"))])
def delete_users(ids: str = Query(""), req: Request = None, db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    id_list = _parse_ids(ids)
    if not id_list:
        return Resp.fail("参数错误")
    if user.id in id_list:
        return Resp.fail("不能删除当前登录账号")
    for target_id in id_list:
        denied = _guard_super_target(db, user, target_id)
        if denied:
            return Resp.fail(denied, code=403)
    db.query(User).filter(User.id.in_(id_list)).update({User.is_deleted: 1}, synchronize_session=False)
    db.query(UserRole).filter(UserRole.user_id.in_(id_list)).delete(synchronize_session=False)
    db.commit()
    _bump_menus()
    log(db, user, "用户管理", "删除", req, params=ids, method="DELETE")
    return Resp.ok()


# ---------------------------------------------------------------- roles
@router.get("/roles", dependencies=[Depends(require_perms("system:role:list"))])
def list_roles(keyword: str = "", page: int = 1, size: int = 10, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    page, size = _paging(page, size)
    q = db.query(Role).filter(Role.is_deleted == 0)
    if keyword:
        q = q.filter(Role.name.like(f"%{keyword}%"))
    total = q.count()
    rows = q.order_by(Role.id.desc()).offset((page - 1) * size).limit(size).all()
    data = []
    for r in rows:
        data.append({
            "id": r.id, "name": r.name, "code": r.code, "desc": r.desc,
            "status": r.status,
            "user_count": db.query(UserRole).filter(UserRole.role_id == r.id).count(),
            "created_at": _fmt(r.created_at),
        })
    return Resp.page(total, data)


@router.get("/roles/all")
def all_roles(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.query(Role).filter(Role.is_deleted == 0, Role.status == 1).order_by(Role.id).all()
    return Resp.ok([{"id": r.id, "name": r.name, "code": r.code} for r in rows])


@router.post("/roles", dependencies=[Depends(require_perms("system:role:add"))])
def create_role(body: RoleCreate, req: Request, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    if db.query(Role).filter(Role.name == body.name, Role.is_deleted == 0).first():
        return Resp.fail("角色名称已存在")
    r = Role(name=body.name, code=body.code, desc=body.desc, status=body.status)
    db.add(r)
    db.commit()
    db.refresh(r)
    for mid in _valid_menu_ids(db, body.menu_ids):
        db.add(RoleMenu(role_id=r.id, menu_id=mid))
    db.commit()
    _bump_menus()
    log(db, user, "角色管理", "新增", req, params=body.name, method="POST")
    return Resp.ok({"id": r.id})


@router.put("/roles/{rid}", dependencies=[Depends(require_perms("system:role:edit"))])
def update_role(rid: int, body: RoleCreate, req: Request, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    r = db.query(Role).filter(Role.id == rid, Role.is_deleted == 0).first()
    if not r:
        return Resp.fail("角色不存在")
    if r.name == "super_admin" and body.name != "super_admin":
        return Resp.fail("超级管理员角色不可重命名", code=403)
    if r.name == "super_admin" and body.status == 0:
        return Resp.fail("超级管理员角色不可禁用", code=403)
    r.name, r.code, r.desc, r.status = body.name, body.code, body.desc, body.status
    db.query(RoleMenu).filter(RoleMenu.role_id == rid).delete()
    for mid in _valid_menu_ids(db, body.menu_ids):
        db.add(RoleMenu(role_id=rid, menu_id=mid))
    db.commit()
    _bump_menus()
    log(db, user, "角色管理", "修改", req, params=r.name, method="PUT")
    return Resp.ok()


@router.delete("/roles/{rid}", dependencies=[Depends(require_perms("system:role:remove"))])
def delete_role(rid: int, req: Request, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    r = db.query(Role).filter(Role.id == rid, Role.is_deleted == 0).first()
    if not r:
        return Resp.fail("角色不存在")
    if r.name == "super_admin":
        return Resp.fail("超级管理员角色不可删除", code=403)
    if db.query(UserRole).filter(UserRole.role_id == rid).count() > 0:
        return Resp.fail("该角色已绑定用户，不可删除", code=403)
    r.is_deleted = 1
    db.query(RoleMenu).filter(RoleMenu.role_id == rid).delete()
    db.commit()
    _bump_menus()
    log(db, user, "角色管理", "删除", req, params=r.name, method="DELETE")
    return Resp.ok()


@router.get("/roles/{rid}/menus", dependencies=[Depends(require_perms("system:role:assign", "system:role:list"))])
def role_menus(rid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return Resp.ok([x.menu_id for x in db.query(RoleMenu).filter(RoleMenu.role_id == rid).all()])


# ---------------------------------------------------------------- menus
@router.get("/menus", dependencies=[Depends(require_perms("system:menu:list"))])
def list_menus(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.query(Menu).filter(Menu.is_deleted == 0).order_by(Menu.sort, Menu.id).all()
    data = [{
        "id": m.id, "parent_id": m.parent_id, "name": m.name, "menu_type": m.menu_type,
        "path": m.path, "component": m.component, "perms": m.perms, "icon": m.icon,
        "sort": m.sort, "visible": m.visible,
    } for m in rows]
    return Resp.ok(data)


@router.get("/menus/tree", dependencies=[Depends(require_perms("system:menu:list"))])
def menu_tree(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.query(Menu).filter(Menu.is_deleted == 0).order_by(Menu.sort, Menu.id).all()
    return Resp.ok(_to_tree(rows, skip_types=()))


@router.post("/menus", dependencies=[Depends(require_perms("system:menu:add"))])
def create_menu(body: MenuCreate, req: Request, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    if body.parent_id:
        parent = db.query(Menu).filter(Menu.id == body.parent_id, Menu.is_deleted == 0).first()
        if not parent:
            return Resp.fail("上级菜单不存在")
        if parent.menu_type == "F":
            return Resp.fail("按钮类型菜单不能作为上级")
    m = Menu(**body.model_dump())
    db.add(m)
    db.commit()
    _bump_menus()
    log(db, user, "菜单管理", "新增", req, params=body.name, method="POST")
    return Resp.ok({"id": m.id})


@router.put("/menus/{mid}", dependencies=[Depends(require_perms("system:menu:edit"))])
def update_menu(mid: int, body: MenuCreate, req: Request, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    m = db.query(Menu).filter(Menu.id == mid, Menu.is_deleted == 0).first()
    if not m:
        return Resp.fail("菜单不存在")
    if body.parent_id == mid:
        return Resp.fail("父级菜单不能是自身")
    if body.parent_id:
        parent = db.query(Menu).filter(Menu.id == body.parent_id, Menu.is_deleted == 0).first()
        if not parent:
            return Resp.fail("上级菜单不存在")
        if parent.menu_type == "F":
            return Resp.fail("按钮类型菜单不能作为上级")
        if body.parent_id in _menu_descendant_ids(db, mid):
            return Resp.fail("父级菜单不能是自己的子级，否则会形成循环")
    for k, v in body.model_dump().items():
        setattr(m, k, v)
    db.commit()
    _bump_menus()
    log(db, user, "菜单管理", "修改", req, params=body.name, method="PUT")
    return Resp.ok()


@router.delete("/menus/{mid}", dependencies=[Depends(require_perms("system:menu:remove"))])
def delete_menu(mid: int, req: Request, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    m = db.query(Menu).filter(Menu.id == mid, Menu.is_deleted == 0).first()
    if not m:
        return Resp.fail("菜单不存在")
    if db.query(Menu).filter(Menu.parent_id == mid, Menu.is_deleted == 0).count() > 0:
        return Resp.fail("存在子菜单，不允许删除", code=403)
    m.is_deleted = 1
    db.query(RoleMenu).filter(RoleMenu.menu_id == mid).delete()
    db.commit()
    _bump_menus()
    log(db, user, "菜单管理", "删除", req, params=m.name, method="DELETE")
    return Resp.ok()


# ---------------------------------------------------------------- dictionaries
@router.get("/dict/types", dependencies=[Depends(require_perms("system:dict:list"))])
def list_dict_types(keyword: str = "", page: int = 1, size: int = 10,
                    db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    page, size = _paging(page, size)
    q = db.query(DictType)
    if keyword:
        q = q.filter((DictType.name.like(f"%{keyword}%")) | (DictType.dict_type.like(f"%{keyword}%")))
    total = q.count()
    rows = q.order_by(DictType.id.desc()).offset((page - 1) * size).limit(size).all()
    data = [{
        "id": r.id, "dict_type": r.dict_type, "name": r.name,
        "status": r.status, "remark": r.remark,
        "item_count": db.query(DictItem).filter(DictItem.dict_type == r.dict_type).count(),
    } for r in rows]
    return Resp.page(total, data)


@router.post("/dict/types", dependencies=[Depends(require_perms("system:dict:add"))])
def create_dict_type(body: DictTypeCreate, req: Request, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    if db.query(DictType).filter(DictType.dict_type == body.dict_type).first():
        return Resp.fail("字典类型编码已存在")
    db.add(DictType(**body.model_dump()))
    db.commit()
    _bump_dicts()
    log(db, user, "数据字典", "新增", req, params=body.dict_type, method="POST")
    return Resp.ok()


@router.put("/dict/types/{tid}", dependencies=[Depends(require_perms("system:dict:edit"))])
def update_dict_type(tid: int, body: DictTypeCreate, req: Request, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    t = db.query(DictType).filter(DictType.id == tid).first()
    if not t:
        return Resp.fail("字典类型不存在")
    old = t.dict_type
    if old != body.dict_type and db.query(DictType).filter(DictType.dict_type == body.dict_type).first():
        return Resp.fail("字典类型编码已存在")
    for k, v in body.model_dump().items():
        setattr(t, k, v)
    if old != body.dict_type:
        db.query(DictItem).filter(DictItem.dict_type == old).update({"dict_type": body.dict_type})
    db.commit()
    _bump_dicts()
    log(db, user, "数据字典", "修改", req, params=body.dict_type, method="PUT")
    return Resp.ok()


@router.delete("/dict/types/{tid}", dependencies=[Depends(require_perms("system:dict:remove"))])
def delete_dict_type(tid: int, req: Request, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    t = db.query(DictType).filter(DictType.id == tid).first()
    if not t:
        return Resp.fail("字典类型不存在")
    db.query(DictItem).filter(DictItem.dict_type == t.dict_type).delete()
    db.delete(t)
    db.commit()
    _bump_dicts()
    log(db, user, "数据字典", "删除", req, params=t.dict_type, method="DELETE")
    return Resp.ok()


@router.get("/dict/items", dependencies=[Depends(require_perms("system:dict:list"))])
def list_dict_items(dict_type: str = "", page: int = 1, size: int = 10,
                    db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    page, size = _paging(page, size)
    q = db.query(DictItem)
    if dict_type:
        q = q.filter(DictItem.dict_type == dict_type)
    total = q.count()
    rows = q.order_by(DictItem.sort, DictItem.id).offset((page - 1) * size).limit(size).all()
    data = [{
        "id": r.id, "dict_type": r.dict_type, "label": r.label, "value": r.value,
        "sort": r.sort, "status": r.status, "remark": r.remark,
    } for r in rows]
    return Resp.page(total, data)


@router.post("/dict/items", dependencies=[Depends(require_perms("system:dict:add"))])
def create_dict_item(body: DictItemCreate, req: Request, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    db.add(DictItem(**body.model_dump()))
    db.commit()
    _bump_dicts()
    log(db, user, "数据字典", "新增字典项", req, params=body.label, method="POST")
    return Resp.ok()


@router.put("/dict/items/{iid}", dependencies=[Depends(require_perms("system:dict:edit"))])
def update_dict_item(iid: int, body: DictItemCreate, req: Request, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    it = db.query(DictItem).filter(DictItem.id == iid).first()
    if not it:
        return Resp.fail("字典项不存在")
    for k, v in body.model_dump().items():
        setattr(it, k, v)
    db.commit()
    _bump_dicts()
    log(db, user, "数据字典", "修改字典项", req, params=body.label, method="PUT")
    return Resp.ok()


@router.delete("/dict/items/{iid}", dependencies=[Depends(require_perms("system:dict:remove"))])
def delete_dict_item(iid: int, req: Request, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    it = db.query(DictItem).filter(DictItem.id == iid).first()
    if not it:
        return Resp.fail("字典项不存在")
    db.delete(it)
    db.commit()
    _bump_dicts()
    log(db, user, "数据字典", "删除字典项", req, params=it.label, method="DELETE")
    return Resp.ok()


@router.get("/dict/data/{dict_type}")
def dict_data(dict_type: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """下拉数据源（已启用项，Redis 缓存）。"""
    key = f"dict:{_dict_version()}:{dict_type}"
    cached = redis_client.redis_get(key)
    if cached:
        return Resp.ok(json.loads(cached))
    rows = (db.query(DictItem)
            .filter(DictItem.dict_type == dict_type, DictItem.status == 1)
            .order_by(DictItem.sort, DictItem.id).all())
    data = [{"label": r.label, "value": r.value} for r in rows]
    redis_client.redis_set(key, json.dumps(data, ensure_ascii=False), ex=settings.CACHE_TTL)
    return Resp.ok(data)


# ---------------------------------------------------------------- operation logs
@router.get("/logs", dependencies=[Depends(require_perms("system:log:list"))])
def list_logs(username: str = "", module: str = "", action: str = "", result: str = "",
              keyword: str = "", start: str = "", end: str = "", page: int = 1, size: int = 10,
              db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    page, size = _paging(page, size)
    q = _log_query(db, username, module, action, result, keyword, start, end)
    total = q.count()
    rows = q.order_by(OperationLog.id.desc()).offset((page - 1) * size).limit(size).all()
    return Resp.page(total, [_log_row(r) for r in rows])


@router.get("/logs/options", dependencies=[Depends(require_perms("system:log:list"))])
def log_options(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """日志筛选项：数据库里出现过的模块与操作类型，避免前端写死。"""
    modules = [r[0] for r in db.query(OperationLog.module).distinct().all() if r[0]]
    actions = [r[0] for r in db.query(OperationLog.action).distinct().all() if r[0]]
    return Resp.ok({"modules": sorted(modules), "actions": sorted(actions)})


@router.get("/logs/export", dependencies=[Depends(require_perms("system:log:list"))])
def export_logs(username: str = "", module: str = "", action: str = "", result: str = "",
                keyword: str = "", start: str = "", end: str = "", req: Request = None,
                db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = _log_query(db, username, module, action, result, keyword, start, end)
    rows = q.order_by(OperationLog.id.desc()).limit(20000).all()

    wb = Workbook()
    ws = wb.active
    ws.title = "操作日志"
    ws.append(["ID", "操作人", "模块", "类型", "方法", "请求地址", "请求参数", "IP", "结果", "时间"])
    for r in rows:
        ws.append([
            r.id, r.username, r.module, r.action, r.method, r.path,
            (r.params or "")[:500], r.ip, r.result, _fmt(r.created_at),
        ])
    for column, width in zip("ABCDEFGHIJ", (8, 14, 14, 12, 8, 32, 40, 16, 8, 20), strict=False):
        ws.column_dimensions[column].width = width

    log(db, user, "操作日志", "导出", req, params=f"共 {len(rows)} 条", method="GET")
    return _xlsx_response(wb, f"logs_{datetime.now():%Y%m%d%H%M%S}.xlsx")


# ---------------------------------------------------------------- profile
@router.get("/profile")
def profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ctx = _user_context(db, user)
    return Resp.ok({
        "user": {"id": user.id, "username": user.username, "nickname": user.nickname,
                 "phone": user.phone, "status": user.status,
                 "created_at": _fmt(user.created_at)},
        "roles": ctx["roles"],
        "perms": ctx["perms"],
    })


@router.put("/profile")
def update_profile(body: ProfileUpdate, req: Request, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    u = db.query(User).filter(User.id == user.id, User.is_deleted == 0).first()
    if not u:
        return Resp.fail("用户不存在", code=401)
    if body.nickname is not None:
        u.nickname = body.nickname
    if body.phone is not None:
        u.phone = body.phone
    db.commit()
    log(db, user, "个人中心", "修改资料", req, params=u.username, method="PUT")
    return Resp.ok({"nickname": u.nickname, "phone": u.phone})


@router.put("/profile/password")
def change_password(body: ChangePwdIn, req: Request, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    u = db.query(User).filter(User.id == user.id, User.is_deleted == 0).first()
    if not u:
        return Resp.fail("用户不存在", code=401)
    if not verify_password(body.old_password, u.password_hash):
        return Resp.fail("原密码错误")
    if body.old_password == body.new_password:
        return Resp.fail("新密码不能与原密码相同")
    err = password_policy_error(body.new_password)
    if err:
        return Resp.fail(err)
    u.password_hash = hash_password(body.new_password)
    db.commit()
    log(db, user, "个人中心", "修改密码", req, params=u.username, method="PUT")
    return Resp.ok(msg="密码修改成功")


@router.get("/profile/logs")
def my_logs(page: int = 1, size: int = 10, db: Session = Depends(get_db),
            user: User = Depends(get_current_user)):
    page, size = _paging(page, size)
    q = db.query(OperationLog).filter(OperationLog.user_id == user.id)
    total = q.count()
    rows = q.order_by(OperationLog.id.desc()).offset((page - 1) * size).limit(size).all()
    data = [{
        "id": r.id, "module": r.module, "action": r.action, "path": r.path,
        "ip": r.ip, "result": r.result, "created_at": _fmt(r.created_at),
    } for r in rows]
    return Resp.page(total, data)


# ---------------------------------------------------------------- business (扩展演示)
@router.get("/biz", dependencies=[Depends(require_perms("biz:list"))])
def list_biz(keyword: str = "", page: int = 1, size: int = 10, db: Session = Depends(get_db),
             user: User = Depends(get_current_user)):
    page, size = _paging(page, size)
    q = db.query(BusinessData)
    if keyword:
        q = q.filter(BusinessData.name.like(f"%{keyword}%"))
    total = q.count()
    rows = q.order_by(BusinessData.id.desc()).offset((page - 1) * size).limit(size).all()
    return Resp.page(total, [{"id": r.id, "name": r.name, "category": r.category,
                              "price": r.price, "remark": r.remark,
                              "created_at": _fmt(r.created_at)} for r in rows])


@router.post("/biz", dependencies=[Depends(require_perms("biz:list"))])
def create_biz(body: BizCreate, req: Request, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    db.add(BusinessData(**body.model_dump()))
    db.commit()
    log(db, user, "业务数据", "新增", req, params=body.name, method="POST")
    return Resp.ok()


@router.put("/biz/{bid}", dependencies=[Depends(require_perms("biz:list"))])
def update_biz(bid: int, body: BizCreate, req: Request, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    r = db.query(BusinessData).filter(BusinessData.id == bid).first()
    if not r:
        return Resp.fail("记录不存在")
    for k, v in body.model_dump().items():
        setattr(r, k, v)
    db.commit()
    log(db, user, "业务数据", "修改", req, params=body.name, method="PUT")
    return Resp.ok()


@router.delete("/biz", dependencies=[Depends(require_perms("biz:list"))])
def delete_biz(ids: str = "", req: Request = None, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    id_list = _parse_ids(ids)
    if not id_list:
        return Resp.fail("参数错误")
    db.query(BusinessData).filter(BusinessData.id.in_(id_list)).delete(synchronize_session=False)
    db.commit()
    log(db, user, "业务数据", "删除", req, params=ids, method="DELETE")
    return Resp.ok()


@router.get("/biz/export", dependencies=[Depends(require_perms("biz:list"))])
def export_biz(keyword: str = "", req: Request = None, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    q = db.query(BusinessData)
    if keyword:
        q = q.filter(BusinessData.name.like(f"%{keyword}%"))
    wb = Workbook()
    ws = wb.active
    ws.append(["ID", "名称", "分类", "价格", "备注", "创建时间"])
    for r in q.order_by(BusinessData.id.desc()).limit(10000).all():
        ws.append([r.id, r.name, r.category, r.price, r.remark, _fmt(r.created_at)])
    for column, width in zip("ABCDEF", (8, 24, 16, 12, 30, 20), strict=False):
        ws.column_dimensions[column].width = width

    log(db, user, "业务数据", "导出", req, params=keyword, method="GET")
    return _xlsx_response(wb, f"biz_{datetime.now():%Y%m%d%H%M%S}.xlsx")


# ---------------------------------------------------------------- files
@router.post("/upload", dependencies=[Depends(require_perms("file:list"))])
def upload(req: Request, f: UploadFile = File(...), db: Session = Depends(get_db),
           user: User = Depends(get_current_user)):
    original = f.filename or ""
    ext = os.path.splitext(original)[1].lower()
    if ext not in settings.ALLOWED_EXT_SET:
        return Resp.fail(f"不支持的文件类型 {ext or '(无扩展名)'}", code=403)

    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    declared = getattr(f, "size", None)
    if declared is not None and declared > max_bytes:
        return Resp.fail(f"文件大小不能超过 {settings.MAX_UPLOAD_MB}MB")

    data = f.file.read(max_bytes + 1)
    if len(data) > max_bytes:
        return Resp.fail(f"文件大小不能超过 {settings.MAX_UPLOAD_MB}MB")
    if not data:
        return Resp.fail("文件内容为空")

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    # 落盘名完全由服务端生成（uuid + 白名单扩展名），杜绝 ../ 路径穿越与同名覆盖
    stored = f"{uuid.uuid4().hex}{ext}"
    root = os.path.realpath(settings.UPLOAD_DIR)
    target = os.path.realpath(os.path.join(root, stored))
    if os.path.dirname(target) != root:
        return Resp.fail("非法的文件名", code=400)

    with open(target, "wb") as out:
        out.write(data)

    safe_name = _display_filename(original)
    db.add(FileRecord(filename=safe_name, filepath=f"/uploads/{stored}",
                      size=len(data), uploader=user.username))
    db.commit()
    log(db, user, "文件管理", "上传", req, params=safe_name, method="POST")
    return Resp.ok({"url": f"/uploads/{stored}", "filename": safe_name})


@router.get("/files", dependencies=[Depends(require_perms("file:list"))])
def list_files(keyword: str = "", page: int = 1, size: int = 10,
               db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    page, size = _paging(page, size)
    q = db.query(FileRecord)
    if keyword:
        q = q.filter(FileRecord.filename.like(f"%{keyword}%"))
    total = q.count()
    rows = q.order_by(FileRecord.id.desc()).offset((page - 1) * size).limit(size).all()
    return Resp.page(total, [{
        "id": r.id, "filename": r.filename, "url": r.filepath,
        "size": r.size, "uploader": r.uploader, "created_at": _fmt(r.created_at),
    } for r in rows])


@router.delete("/files/{fid}", dependencies=[Depends(require_perms("file:list"))])
def delete_file(fid: int, req: Request, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    rec = db.query(FileRecord).filter(FileRecord.id == fid).first()
    if not rec:
        return Resp.fail("文件不存在")
    name = os.path.basename(rec.filepath or "")
    root = os.path.realpath(settings.UPLOAD_DIR)
    path = os.path.realpath(os.path.join(root, name))
    if name and os.path.dirname(path) == root:
        try:
            if os.path.isfile(path):
                os.remove(path)
        except OSError:
            pass
    db.delete(rec)
    db.commit()
    log(db, user, "文件管理", "删除", req, params=rec.filename, method="DELETE")
    return Resp.ok()
