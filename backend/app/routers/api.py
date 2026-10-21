import io
import json
import os
import time
import uuid

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from sqlalchemy.orm import Session

from app.core import captcha, redis_client
from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user, is_super_admin, require_perms
from app.core.response import Resp
from app.core.security import (
    blacklist_token,
    create_token,
    hash_password,
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
    BizCreate,
    ChangePwdIn,
    DictItemCreate,
    DictTypeCreate,
    LoginIn,
    MenuCreate,
    ResetPwdIn,
    RoleCreate,
    UserCreate,
    UserUpdate,
)

router = APIRouter()


# ---------------------------------------------------------------- helpers
def _ip(req: Request) -> str:
    if not req or not req.client:
        return ""
    return req.client.host


def log(db: Session, user, module: str, action: str, req: Request, params: str = "",
        result: str = "成功", method: str = ""):
    if req:
        try:
            req.state.logged = True  # 标记已记录，避免中间件安全网重复写一条
        except Exception:
            pass
    try:
        db.add(OperationLog(
            user_id=user.id if user else None,
            username=user.username if user else "",
            module=module, action=action, method=method or (req.method if req else ""),
            path=req.url.path if req else "", ip=_ip(req),
            params=(params or "")[:2000], result=result,
        ))
        db.commit()
    except Exception:
        db.rollback()


def _super(db: Session, user: User) -> bool:
    return is_super_admin(user, db)


def _role_ids(db: Session, uid: int) -> list[int]:
    return [x.role_id for x in db.query(UserRole).filter(UserRole.user_id == uid).all()]


def _role_names(db: Session, uid: int) -> list[str]:
    ids = _role_ids(db, uid)
    if not ids:
        return []
    return [r.name for r in db.query(Role).filter(Role.id.in_(ids)).all()]


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
    menus = _accessible_menus(db, user)
    perms = sorted({m.perms for m in menus if m.perms})
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
        "created_at": u.created_at.strftime("%Y-%m-%d %H:%M:%S") if u.created_at else "",
    }


def _parse_ids(ids: str) -> list[int]:
    return [int(x) for x in (ids or "").split(",") if x.strip().isdigit()]


# ---------------------------------------------------------------- auth
@router.get("/auth/captcha")
def auth_captcha():
    return Resp.ok(captcha.generate())


@router.post("/auth/login")
def login(body: LoginIn, req: Request, db: Session = Depends(get_db)):
    if settings.CAPTCHA_ENABLED and not captcha.verify(body.captcha_key, body.captcha_code):
        return Resp.fail("验证码错误或已过期", code=400)
    u = db.query(User).filter(User.username == body.username, User.is_deleted == 0).first()
    if not u or not verify_password(body.password, u.password_hash):
        log(db, u, "登录", "登录", req, params=body.username, result="失败", method="POST")
        return Resp.fail("账号或密码错误", code=400)
    if u.status == 0:
        return Resp.fail("账号已禁用", code=403)
    token = create_token(str(u.id))
    log(db, u, "登录", "登录", req, params=body.username, result="成功", method="POST")
    return Resp.ok({
        "token": token,
        "user": {"id": u.id, "username": u.username, "nickname": u.nickname},
        "role_ids": _role_ids(db, u.id),
    })


@router.post("/auth/logout")
def logout(req: Request):
    auth = req.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        blacklist_token(auth[7:])
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


# ---------------------------------------------------------------- users
@router.get("/users", dependencies=[Depends(require_perms("system:user:list"))])
def list_users(keyword: str = "", status: int | None = None, page: int = 1, size: int = 10,
               db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = db.query(User).filter(User.is_deleted == 0)
    if keyword:
        q = q.filter((User.username.like(f"%{keyword}%")) | (User.nickname.like(f"%{keyword}%")))
    if status is not None:
        q = q.filter(User.status == status)
    total = q.count()
    rows = q.order_by(User.id.desc()).offset((page - 1) * size).limit(min(size, 100)).all()
    return Resp.page(total, [_user_row(db, r) for r in rows])


@router.post("/users", dependencies=[Depends(require_perms("system:user:add"))])
def create_user(body: UserCreate, req: Request, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    if db.query(User).filter(User.username == body.username, User.is_deleted == 0).first():
        return Resp.fail("用户名已存在")
    u = User(username=body.username, password_hash=hash_password(body.password),
             nickname=body.nickname, phone=body.phone, status=body.status)
    db.add(u)
    db.commit()
    db.refresh(u)
    for rid in body.role_ids:
        db.add(UserRole(user_id=u.id, role_id=rid))
    db.commit()
    _bump_menus()
    log(db, user, "用户管理", "新增", req, params=body.username, method="POST")
    return Resp.ok({"id": u.id})


@router.put("/users/{uid}", dependencies=[Depends(require_perms("system:user:edit"))])
def update_user(uid: int, body: UserUpdate, req: Request, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    u = db.query(User).filter(User.id == uid, User.is_deleted == 0).first()
    if not u:
        return Resp.fail("用户不存在")
    if body.nickname is not None:
        u.nickname = body.nickname
    if body.phone is not None:
        u.phone = body.phone
    if body.status is not None:
        if uid == user.id and body.status == 0:
            return Resp.fail("不能禁用当前登录账号")
        u.status = body.status
    if body.role_ids is not None:
        db.query(UserRole).filter(UserRole.user_id == uid).delete()
        for rid in body.role_ids:
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
    q = db.query(Role).filter(Role.is_deleted == 0)
    if keyword:
        q = q.filter(Role.name.like(f"%{keyword}%"))
    total = q.count()
    rows = q.order_by(Role.id.desc()).offset((page - 1) * size).limit(min(size, 100)).all()
    data = []
    for r in rows:
        data.append({
            "id": r.id, "name": r.name, "code": r.code, "desc": r.desc,
            "status": r.status,
            "user_count": db.query(UserRole).filter(UserRole.role_id == r.id).count(),
        })
    return Resp.page(total, data)


@router.get("/roles/all")
def all_roles(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.query(Role).filter(Role.is_deleted == 0, Role.status == 1).order_by(Role.id).all()
    return Resp.ok([{"id": r.id, "name": r.name} for r in rows])


@router.post("/roles", dependencies=[Depends(require_perms("system:role:add"))])
def create_role(body: RoleCreate, req: Request, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    if db.query(Role).filter(Role.name == body.name, Role.is_deleted == 0).first():
        return Resp.fail("角色名称已存在")
    r = Role(name=body.name, code=body.code, desc=body.desc, status=body.status)
    db.add(r)
    db.commit()
    db.refresh(r)
    for mid in body.menu_ids:
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
    r.name, r.code, r.desc, r.status = body.name, body.code, body.desc, body.status
    db.query(RoleMenu).filter(RoleMenu.role_id == rid).delete()
    for mid in body.menu_ids:
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
    m = Menu(**body.model_dump())
    db.add(m)
    db.commit()
    _bump_menus()
    log(db, user, "菜单管理", "新增", req, params=body.name, method="POST")
    return Resp.ok()


@router.put("/menus/{mid}", dependencies=[Depends(require_perms("system:menu:edit"))])
def update_menu(mid: int, body: MenuCreate, req: Request, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    m = db.query(Menu).filter(Menu.id == mid, Menu.is_deleted == 0).first()
    if not m:
        return Resp.fail("菜单不存在")
    if body.parent_id == mid:
        return Resp.fail("父级菜单不能是自身")
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
    q = db.query(DictType)
    if keyword:
        q = q.filter((DictType.name.like(f"%{keyword}%")) | (DictType.dict_type.like(f"%{keyword}%")))
    total = q.count()
    rows = q.order_by(DictType.id.desc()).offset((page - 1) * size).limit(min(size, 100)).all()
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
    q = db.query(DictItem)
    if dict_type:
        q = q.filter(DictItem.dict_type == dict_type)
    total = q.count()
    rows = q.order_by(DictItem.sort, DictItem.id).offset((page - 1) * size).limit(min(size, 100)).all()
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
def list_logs(username: str = "", module: str = "", action: str = "",
              start: str = "", end: str = "", page: int = 1, size: int = 10,
              db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = db.query(OperationLog)
    if username:
        q = q.filter(OperationLog.username.like(f"%{username}%"))
    if module:
        q = q.filter(OperationLog.module == module)
    if action:
        q = q.filter(OperationLog.action == action)
    if start:
        q = q.filter(OperationLog.created_at >= start)
    if end:
        q = q.filter(OperationLog.created_at <= end)
    total = q.count()
    rows = q.order_by(OperationLog.id.desc()).offset((page - 1) * size).limit(min(size, 100)).all()
    data = [{
        "id": r.id, "username": r.username, "module": r.module, "action": r.action,
        "method": r.method, "path": r.path, "ip": r.ip, "params": r.params,
        "result": r.result,
        "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else "",
    } for r in rows]
    return Resp.page(total, data)


# ---------------------------------------------------------------- profile
@router.get("/profile")
def profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ctx = _user_context(db, user)
    return Resp.ok({
        "user": {"id": user.id, "username": user.username, "nickname": user.nickname,
                 "phone": user.phone, "status": user.status,
                 "created_at": user.created_at.strftime("%Y-%m-%d %H:%M:%S") if user.created_at else ""},
        "roles": ctx["roles"],
        "perms": ctx["perms"],
    })


@router.put("/profile/password")
def change_password(body: ChangePwdIn, req: Request, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    u = db.query(User).filter(User.id == user.id).first()
    if not verify_password(body.old_password, u.password_hash):
        return Resp.fail("原密码错误")
    if body.old_password == body.new_password:
        return Resp.fail("新密码不能与原密码相同")
    u.password_hash = hash_password(body.new_password)
    db.commit()
    log(db, user, "个人中心", "修改密码", req, params=u.username, method="PUT")
    return Resp.ok(msg="密码修改成功")


@router.get("/profile/logs")
def my_logs(page: int = 1, size: int = 10, db: Session = Depends(get_db),
            user: User = Depends(get_current_user)):
    q = db.query(OperationLog).filter(OperationLog.user_id == user.id)
    total = q.count()
    rows = q.order_by(OperationLog.id.desc()).offset((page - 1) * size).limit(min(size, 100)).all()
    data = [{
        "id": r.id, "module": r.module, "action": r.action, "path": r.path,
        "ip": r.ip, "result": r.result,
        "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else "",
    } for r in rows]
    return Resp.page(total, data)


# ---------------------------------------------------------------- business (扩展演示)
@router.get("/biz", dependencies=[Depends(require_perms("biz:list"))])
def list_biz(keyword: str = "", page: int = 1, size: int = 10, db: Session = Depends(get_db),
             user: User = Depends(get_current_user)):
    q = db.query(BusinessData)
    if keyword:
        q = q.filter(BusinessData.name.like(f"%{keyword}%"))
    total = q.count()
    rows = q.order_by(BusinessData.id.desc()).offset((page - 1) * size).limit(min(size, 100)).all()
    return Resp.page(total, [{"id": r.id, "name": r.name, "category": r.category,
                              "price": r.price, "remark": r.remark} for r in rows])


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
    ws.append(["ID", "名称", "分类", "价格", "备注"])
    for r in q.all():
        ws.append([r.id, r.name, r.category, r.price, r.remark])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    log(db, user, "业务数据", "导出", req, params=keyword, method="GET")
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=biz.xlsx"},
    )


# ---------------------------------------------------------------- files
@router.post("/upload", dependencies=[Depends(require_perms("file:list"))])
def upload(req: Request, f: UploadFile = File(...), db: Session = Depends(get_db),
           user: User = Depends(get_current_user)):
    ext = os.path.splitext(f.filename or "")[1].lower()
    allowed = [x.strip() for x in settings.ALLOWED_EXTS.split(",")]
    if ext not in allowed:
        return Resp.fail(f"不支持的文件类型 {ext}", code=403)
    data = f.file.read()
    if len(data) > settings.MAX_UPLOAD_MB * 1024 * 1024:
        return Resp.fail("文件过大")
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    name = f"{int(time.time())}_{f.filename}"
    path = os.path.join(settings.UPLOAD_DIR, name)
    with open(path, "wb") as out:
        out.write(data)
    db.add(FileRecord(filename=f.filename, filepath=f"/uploads/{name}",
                      size=len(data), uploader=user.username))
    db.commit()
    log(db, user, "文件管理", "上传", req, params=f.filename, method="POST")
    return Resp.ok({"url": f"/uploads/{name}", "filename": f.filename})


@router.get("/files", dependencies=[Depends(require_perms("file:list"))])
def list_files(page: int = 1, size: int = 10, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    q = db.query(FileRecord)
    total = q.count()
    rows = q.order_by(FileRecord.id.desc()).offset((page - 1) * size).limit(min(size, 100)).all()
    return Resp.page(total, [{"id": r.id, "filename": r.filename, "url": r.filepath,
                              "size": r.size, "uploader": r.uploader} for r in rows])
