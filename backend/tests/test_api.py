"""接口级回归测试：覆盖认证、权限、CRUD、上传安全、看板与导出。"""
import os
import uuid

from conftest import login, menu_id


def _name(prefix: str = "u") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


# ---------------------------------------------------------------- 健康检查 / 认证
def test_health(client):
    body = client.get("/api/health").json()
    assert body["code"] == 200
    assert body["data"]["version"]


def test_login_wrong_password(client):
    body = client.post("/api/auth/login", json={"username": "admin", "password": "wrong-pass"}).json()
    assert body["code"] == 400
    assert "账号或密码错误" in body["msg"]


def test_login_lockout_after_failures(client):
    username = _name("lock")
    for _ in range(3):
        body = client.post("/api/auth/login", json={"username": username, "password": "x"}).json()
        assert body["code"] == 400
    body = client.post("/api/auth/login", json={"username": username, "password": "x"}).json()
    assert body["code"] == 429


def test_invalid_token_rejected(client):
    body = client.get("/api/profile", headers={"Authorization": "Bearer not-a-real-token"}).json()
    assert body["code"] == 401


def test_captcha_disabled_flag(client):
    body = client.get("/api/auth/captcha").json()
    assert body["code"] == 200
    assert body["data"]["enabled"] is False


def test_menus_include_dashboard(client, admin):
    body = client.get("/api/auth/menus", headers=admin).json()
    assert body["code"] == 200
    paths = [m["path"] for m in body["data"]["menus"]]
    assert "/admin/dashboard" in paths
    assert "/admin/edu" in paths
    assert "*" in body["data"]["perms"]


# ---------------------------------------------------------------- 权限
def test_rbac_denies_write_without_permission(client, admin, menus):
    users_menu_id = menu_id(menus, "/admin/users")
    role_name = _name("role")
    created_role = client.post(
        "/api/roles",
        json={"name": role_name, "code": "ROLE_X", "desc": "", "status": 1, "menu_ids": [users_menu_id]},
        headers=admin,
    ).json()
    assert created_role["code"] == 200, created_role
    role_id = created_role["data"]["id"]

    username = _name("limited")
    created_user = client.post(
        "/api/users",
        json={"username": username, "password": "Abcd1234", "nickname": "受限用户", "status": 1,
              "role_ids": [role_id]},
        headers=admin,
    ).json()
    assert created_user["code"] == 200, created_user
    user_id = created_user["data"]["id"]

    user_headers = login(client, username, "Abcd1234")

    # 有 list 权限：可以读
    listed = client.get("/api/users", headers=user_headers).json()
    assert listed["code"] == 200

    # 没有 add 权限：写操作被拦截并落一条越权日志
    denied = client.post(
        "/api/users",
        json={"username": _name("shadow"), "password": "Abcd1234"},
        headers=user_headers,
    ).json()
    assert denied["code"] == 403
    assert "无权限" in denied["msg"]

    logs = client.get("/api/logs", params={"action": "越权访问"}, headers=admin).json()
    assert any(item["username"] == username for item in logs["data"]["list"])

    client.delete("/api/users", params={"ids": str(user_id)}, headers=admin)
    assert client.delete(f"/api/roles/{role_id}", headers=admin).json()["code"] == 200


def test_soft_deleted_user_token_invalidated(client, admin):
    username = _name("gone")
    user_id = client.post(
        "/api/users", json={"username": username, "password": "Abcd1234"}, headers=admin
    ).json()["data"]["id"]
    user_headers = login(client, username, "Abcd1234")
    assert client.get("/api/profile", headers=user_headers).json()["code"] == 200

    assert client.delete("/api/users", params={"ids": str(user_id)}, headers=admin).json()["code"] == 200
    body = client.get("/api/profile", headers=user_headers).json()
    assert body["code"] == 401


# ---------------------------------------------------------------- 用户
def test_batch_status_and_export(client, admin):
    ids = []
    for _ in range(2):
        created = client.post(
            "/api/users", json={"username": _name("batch"), "password": "Abcd1234"}, headers=admin
        ).json()
        assert created["code"] == 200
        ids.append(created["data"]["id"])

    body = client.put(
        "/api/users/batch/status", json={"ids": ids, "status": 0}, headers=admin
    ).json()
    assert body["code"] == 200
    assert body["data"]["changed"] == 2

    listed = client.get("/api/users", params={"status": 0, "size": 100}, headers=admin).json()
    assert {u["id"] for u in listed["data"]["list"]} >= set(ids)

    exported = client.get("/api/users/export", headers=admin)
    assert exported.status_code == 200
    assert exported.content[:2] == b"PK"  # xlsx 本质是 zip
    assert "attachment" in exported.headers["content-disposition"].lower()

    client.delete("/api/users", params={"ids": ",".join(str(i) for i in ids)}, headers=admin)


def test_password_policy_enforced(client, admin):
    username = _name("pwd")
    created = client.post(
        "/api/users", json={"username": username, "password": "Abcd1234"}, headers=admin
    ).json()
    assert created["code"] == 200
    user_id = created["data"]["id"]

    weak = client.put(f"/api/users/{user_id}/password", json={"password": "aaaaaaaa"}, headers=admin).json()
    assert weak["code"] == 400
    assert "两类" in weak["msg"] or "过于简单" in weak["msg"]

    good = client.put(f"/api/users/{user_id}/password", json={"password": "Qwer1234"}, headers=admin).json()
    assert good["code"] == 200
    assert login(client, username, "Qwer1234")

    client.delete("/api/users", params={"ids": str(user_id)}, headers=admin)


# ---------------------------------------------------------------- 菜单树环形校验
def test_menu_cycle_rejected(client, admin):
    parent = client.post(
        "/api/menus", json={"name": _name("父"), "menu_type": "M", "path": _name("/p")}, headers=admin
    ).json()
    assert parent["code"] == 200
    parent_id = parent["data"]["id"]

    child = client.post(
        "/api/menus",
        json={"name": _name("子"), "menu_type": "C", "path": _name("/c"), "parent_id": parent_id},
        headers=admin,
    ).json()
    assert child["code"] == 200
    child_id = child["data"]["id"]

    cyclic = client.put(
        f"/api/menus/{parent_id}",
        json={"name": "父", "menu_type": "M", "path": "/p-cycle", "parent_id": child_id},
        headers=admin,
    ).json()
    assert cyclic["code"] == 400
    assert "子级" in cyclic["msg"]

    client.delete(f"/api/menus/{child_id}", headers=admin)
    client.delete(f"/api/menus/{parent_id}", headers=admin)


# ---------------------------------------------------------------- 上传安全
def test_upload_blocks_path_traversal(client, admin):
    body = client.post(
        "/api/upload",
        files={"f": ("../../evil.txt", b"hello", "text/plain")},
        headers=admin,
    ).json()
    assert body["code"] == 200, body
    url = body["data"]["url"]
    assert url.startswith("/uploads/")
    stored_name = url[len("/uploads/"):]
    assert ".." not in stored_name and "/" not in stored_name and "\\" not in stored_name

    root = os.path.realpath(os.environ["UPLOAD_DIR"])
    stored_path = os.path.realpath(os.path.join(root, stored_name))
    assert os.path.dirname(stored_path) == root
    assert os.path.isfile(stored_path)

    # 记录里保留的是清洗后的展示名，而不是原始路径
    assert body["data"]["filename"] == "evil.txt"


def test_upload_rejects_disallowed_extension(client, admin):
    body = client.post(
        "/api/upload", files={"f": ("evil.exe", b"MZ", "application/octet-stream")}, headers=admin
    ).json()
    assert body["code"] == 403


def test_upload_then_delete_file(client, admin):
    uploaded = client.post(
        "/api/upload", files={"f": ("note.txt", b"hello", "text/plain")}, headers=admin
    ).json()
    assert uploaded["code"] == 200

    listed = client.get("/api/files", params={"keyword": "note.txt"}, headers=admin).json()
    target = next((row for row in listed["data"]["list"] if row["filename"] == "note.txt"), None)
    assert target is not None

    assert client.delete(f"/api/files/{target['id']}", headers=admin).json()["code"] == 200
    remaining = client.get("/api/files", params={"keyword": "note.txt"}, headers=admin).json()
    assert all(row["id"] != target["id"] for row in remaining["data"]["list"])


# ---------------------------------------------------------------- 看板 / 日志 / 个人中心
def test_dashboard_overview(client, admin):
    body = client.get("/api/dashboard/overview", headers=admin).json()
    assert body["code"] == 200
    data = body["data"]
    assert {"users", "roles", "menus", "logs"} <= set(data["cards"])
    assert len(data["trend"]) == 7
    assert data["trend"][-1]["date"]
    assert data["system"]["version"]
    assert isinstance(data["modules"], list)


def test_logs_filter_and_export(client, admin):
    listed = client.get("/api/logs", params={"size": 5}, headers=admin).json()
    assert listed["code"] == 200
    assert "list" in listed["data"]

    options = client.get("/api/logs/options", headers=admin).json()
    assert options["code"] == 200
    assert "modules" in options["data"]

    start = "2000-01-01"
    filtered = client.get("/api/logs", params={"start": start, "end": "2099-12-31"}, headers=admin).json()
    assert filtered["code"] == 200 and filtered["data"]["total"] >= 1

    exported = client.get("/api/logs/export", headers=admin)
    assert exported.status_code == 200 and exported.content[:2] == b"PK"


def test_profile_update(client, admin):
    body = client.put(
        "/api/profile", json={"nickname": "超级管理员", "phone": "13800000000"}, headers=admin
    ).json()
    assert body["code"] == 200
    profile = client.get("/api/profile", headers=admin).json()
    assert profile["data"]["user"]["nickname"] == "超级管理员"
