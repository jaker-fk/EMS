import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.core.database import Base, engine, SessionLocal
from app.core.ratelimit import allow
from app.core.security import decode_token, hash_password
from app.models import models
from app.routers.api import router

app = FastAPI(title=settings.APP_NAME, docs_url="/api/docs", openapi_url="/api/openapi.json")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def rate_limit_mw(request: Request, call_next):
    path = request.url.path
    if request.method in ("POST", "PUT", "DELETE") and path.startswith("/api"):
        ip = request.client.host if request.client else "unknown"
        if path == "/api/auth/login":
            allowed = allow(f"login:{ip}", 10, 60)
        else:
            allowed = allow(f"{ip}:{request.method}:{path}", 60, 60)
        if not allowed:
            return JSONResponse({"code": 429, "msg": "请求过于频繁，请稍后再试", "data": None}, status_code=200)
    return await call_next(request)


# ---------------------------------------------------------------- 操作日志安全网
_MODULE_MAP = [
    ("/api/users", "用户管理"),
    ("/api/roles", "角色管理"),
    ("/api/menus", "菜单管理"),
    ("/api/dict", "数据字典"),
    ("/api/logs", "操作日志"),
    ("/api/biz", "业务数据"),
    ("/api/upload", "文件管理"),
    ("/api/files", "文件管理"),
    ("/api/profile", "个人中心"),
    ("/api/auth", "认证"),
]


def _module_of(path: str) -> str:
    for prefix, name in _MODULE_MAP:
        if path.startswith(prefix):
            return name
    return "系统"


def _action_of(method: str, path: str) -> str:
    if path.endswith("/logout"):
        return "登出"
    return {"POST": "新增", "PUT": "修改", "DELETE": "删除"}.get(method, method)


def _persist_log(user_id, username, module, action, method, path, ip, result) -> None:
    try:
        db = SessionLocal()
        try:
            db.add(models.OperationLog(
                user_id=user_id, username=username, module=module, action=action,
                method=method, path=path, ip=ip, result=result,
            ))
            db.commit()
        finally:
            db.close()
    except Exception:
        pass


@app.middleware("http")
async def oper_log_mw(request: Request, call_next):
    """兜底：未被端点显式记录日志的写操作自动落库（已显式记录的会打标记跳过）。"""
    response = await call_next(request)
    try:
        path = request.url.path
        method = request.method
        if (method in ("POST", "PUT", "DELETE") and path.startswith("/api")
                and path != "/api/health" and not path.startswith("/api/docs")
                and not path.endswith("/login")
                and not getattr(request.state, "logged", False)):
            uid, username = None, ""
            auth = request.headers.get("authorization", "")
            if auth.lower().startswith("bearer "):
                uid_s = decode_token(auth[7:])
                if uid_s:
                    try:
                        uid = int(uid_s)
                        db = SessionLocal()
                        try:
                            u = db.query(models.User).filter(models.User.id == uid).first()
                            username = u.username if u else ""
                        finally:
                            db.close()
                    except Exception:
                        uid, username = None, ""
            ip = request.client.host if request.client else ""
            result = "成功" if response.status_code < 400 else "失败"
            await run_in_threadpool(
                _persist_log, uid, username, _module_of(path), _action_of(method, path),
                method, path, ip, result,
            )
    except Exception:
        pass
    return response


@app.exception_handler(StarletteHTTPException)
async def http_exc(req: Request, exc: StarletteHTTPException):
    return JSONResponse({"code": exc.status_code, "msg": exc.detail, "data": None}, status_code=200)


@app.exception_handler(Exception)
async def global_exc(req: Request, exc: Exception):
    print(f"[UNHANDLED] {req.method} {req.url.path}: {exc}")
    return JSONResponse({"code": 500, "msg": "系统异常，请稍后重试", "data": None}, status_code=200)


@app.on_event("startup")
def startup():
    try:
        Base.metadata.create_all(bind=engine)
        _seed()
    except Exception as e:
        print("DB init failed:", e)
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    try:
        app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")
    except Exception:
        pass


def _seed():
    """首次启动自动灌入角色、菜单（含按钮权限）、字典、超级管理员。"""
    db = SessionLocal()
    try:
        if db.query(models.Role).count() == 0:
            db.add_all([
                models.Role(name="super_admin", code="SUPER_ADMIN", desc="超级管理员"),
                models.Role(name="admin", code="ADMIN", desc="普通管理员"),
                models.Role(name="operator", code="OPERATOR", desc="普通操作员"),
            ])
            db.commit()

        if db.query(models.Menu).count() == 0:
            pages = [
                ("用户管理", "/users", "User", 1, "system:user:list"),
                ("角色管理", "/roles", "Avatar", 2, "system:role:list"),
                ("菜单管理", "/menus", "Menu", 3, "system:menu:list"),
                ("数据字典", "/dicts", "Collection", 4, "system:dict:list"),
                ("操作日志", "/logs", "Document", 5, "system:log:list"),
                ("个人中心", "/profile", "UserFilled", 6, "profile:view"),
                ("业务数据", "/biz", "Goods", 7, "biz:list"),
                ("文件管理", "/files", "Folder", 8, "file:list"),
            ]
            path_to_id = {}
            for name, path, icon, sort, perms in pages:
                m = models.Menu(parent_id=0, name=name, menu_type="C", path=path, icon=icon,
                                sort=sort, perms=perms, component=f"views/{path.strip('/').capitalize()}.vue")
                db.add(m)
                db.flush()
                path_to_id[path] = m.id
            buttons = {
                "/users": [("新增用户", "system:user:add"), ("编辑用户", "system:user:edit"),
                           ("删除用户", "system:user:remove"), ("重置密码", "system:user:reset")],
                "/roles": [("新增角色", "system:role:add"), ("编辑角色", "system:role:edit"),
                           ("删除角色", "system:role:remove"), ("分配权限", "system:role:assign")],
                "/menus": [("新增菜单", "system:menu:add"), ("编辑菜单", "system:menu:edit"),
                           ("删除菜单", "system:menu:remove")],
                "/dicts": [("新增字典", "system:dict:add"), ("编辑字典", "system:dict:edit"),
                           ("删除字典", "system:dict:remove")],
            }
            for path, btns in buttons.items():
                for i, (name, perms) in enumerate(btns):
                    db.add(models.Menu(parent_id=path_to_id[path], name=name, menu_type="F",
                                       perms=perms, sort=i))
            db.commit()

            admin_role = db.query(models.Role).filter(models.Role.name == "admin").first()
            for m in db.query(models.Menu).all():
                db.add(models.RoleMenu(role_id=admin_role.id, menu_id=m.id))
            db.commit()

        if not db.query(models.User).filter(models.User.username == "admin").first():
            admin = models.User(username="admin", password_hash=hash_password("123456"),
                                nickname="超级管理员", phone="13800000000", status=1)
            db.add(admin)
            db.commit()
            super_role = db.query(models.Role).filter(models.Role.name == "super_admin").first()
            db.add(models.UserRole(user_id=admin.id, role_id=super_role.id))
            db.commit()

        if db.query(models.DictType).count() == 0:
            dicts = [
                ("user_status", "用户状态", [("启用", "1", 1), ("禁用", "0", 2)]),
                ("menu_type", "菜单类型", [("目录", "M", 1), ("页面", "C", 2), ("按钮", "F", 3)]),
                ("yes_no", "是否", [("是", "1", 1), ("否", "0", 2)]),
            ]
            for dtype, name, items in dicts:
                db.add(models.DictType(dict_type=dtype, name=name, remark="系统内置"))
                for label, value, sort in items:
                    db.add(models.DictItem(dict_type=dtype, label=label, value=value, sort=sort))
            db.commit()
    finally:
        db.close()


app.include_router(router, prefix="/api")


@app.get("/api/health")
def health():
    return {"code": 200, "msg": "ok", "data": {"app": settings.APP_NAME}}
