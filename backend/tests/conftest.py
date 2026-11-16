"""pytest 公共夹具。

注意：环境变量必须在导入 app 之前设置——Settings 在模块导入时就已实例化。

数据库有两种跑法：
- 默认：每次会话建一个临时 SQLite 库（零依赖，CI / 本机都能跑）；
- 指定 TEST_DB_URL 时改为连真实 MySQL（用来验证与线上同款数据库的兼容性），
  例如 PowerShell：
      $env:TEST_DB_URL="mysql+pymysql://admin:123456@127.0.0.1:3306/admin_panel_test?charset=utf8mb4"
      pytest -q
  ⚠️ 该库会在会话开始时被 DROP 全部表重建，务必指向专用的测试库。
"""
import atexit
import os
import shutil
import tempfile
import uuid

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _make_test_root() -> str:
    """挑一个纯 ASCII 的临时目录，并且用默认权限创建。

    - SQLAlchemy 解析含中文的 sqlite URL 会失败，所以要避开中文 TEMP 路径；
    - tempfile.mkdtemp() 在 Windows 上会建 0700 目录，受限令牌下 SQLite 无法在其中建库，
      因此这里用 os.makedirs 的默认权限手工建目录。
    """
    candidates = [
        os.environ.get("PYTEST_TMP_DIR", ""),
        tempfile.gettempdir(),
        os.path.join(_PROJECT_ROOT, ".pytest-tmp"),
    ]
    for base in candidates:
        if not base or not os.path.isabs(base) or not base.isascii():
            continue
        try:
            os.makedirs(base, exist_ok=True)
            root = os.path.join(base, f"admin_panel_test_{uuid.uuid4().hex[:8]}")
            os.makedirs(root, exist_ok=True)
            return root
        except OSError:
            continue
    root = os.path.join(tempfile.gettempdir(), f"admin_panel_test_{uuid.uuid4().hex[:8]}")
    os.makedirs(root, exist_ok=True)
    return root



_TEST_DB_URL = os.environ.get("TEST_DB_URL", "").strip()
if _TEST_DB_URL:
    _TEST_ROOT = _make_test_root()
    atexit.register(shutil.rmtree, _TEST_ROOT, True)
    os.environ["DB_URL"] = _TEST_DB_URL
else:
    _TEST_ROOT = _make_test_root()
    atexit.register(shutil.rmtree, _TEST_ROOT, True)
    os.environ["DB_URL"] = "sqlite:///" + os.path.join(_TEST_ROOT, "test.db").replace("\\", "/")
os.environ["UPLOAD_DIR"] = os.path.join(_TEST_ROOT, "uploads")
os.environ["CAPTCHA_ENABLED"] = "false"
os.environ["RATE_LIMIT_ENABLED"] = "false"
# 指向一个不存在的端口，强制走进程内存缓存，避免测试污染真实 Redis
os.environ["REDIS_HOST"] = "127.0.0.1"
os.environ["REDIS_PORT"] = "6399"
os.environ["LOGIN_MAX_FAILS"] = "3"
os.environ["LOGIN_LOCK_MINUTES"] = "1"
os.environ["LOG_LEVEL"] = "WARNING"


import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import models  # noqa: E402,F401  注册全部表


@pytest.fixture(scope="session")
def _database() -> None:
    """MySQL 模式：清空上次残留的表，保证每次从空库开始（SQLite 每次都是新文件，无需处理）。"""
    if engine.dialect.name != "sqlite":
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)


@pytest.fixture(scope="session")
def client(_database):
    with TestClient(app) as c:
        yield c


def login(client: TestClient, username: str, password: str) -> dict:
    resp = client.post("/api/auth/login", json={"username": username, "password": password})
    body = resp.json()
    assert body["code"] == 200, body
    return {"Authorization": f"Bearer {body['data']['token']}"}


@pytest.fixture(scope="session")
def admin(client) -> dict:
    return login(client, "admin", "123456")


@pytest.fixture(scope="session")
def menus(client, admin) -> list:
    body = client.get("/api/menus", headers=admin).json()
    assert body["code"] == 200, body
    return body["data"]


def menu_id(menus: list, path: str) -> int:
    for item in menus:
        if item["path"] == path:
            return item["id"]
    raise AssertionError(f"菜单不存在：{path}")
