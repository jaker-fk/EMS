"""前台学员账号回归测试：注册 / 登录 / 账号隔离 / 我的报名。

关键约束：
- 前台账号存在独立表 ``site_user``，与后台 ``sys_user`` 互不影响；
- 两类 Token 带不同 scope，前台 Token 进不了后台，后台 Token 也当不了学员。
"""
import uuid

PASSWORD = "Abcd1234"


def _username() -> str:
    return f"stu_{uuid.uuid4().hex[:8]}"


def _phone() -> str:
    return "137" + str(uuid.uuid4().int % 10 ** 8).zfill(8)


def _register(client, username: str, phone: str) -> dict:
    body = client.post(
        "/api/site/auth/register",
        json={"username": username, "password": PASSWORD, "nickname": "学员家长", "phone": phone},
    ).json()
    assert body["code"] == 200, body
    return body["data"]


def _site_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_site_register_login_and_scope_isolation(client, admin):
    username, phone = _username(), _phone()
    data = _register(client, username, phone)
    assert data["user"]["username"] == username
    assert data["user"]["phone"] == phone
    site_headers = _site_headers(data["token"])

    me = client.get("/api/site/me", headers=site_headers).json()
    assert me["code"] == 200
    assert me["data"]["user"]["nickname"] == "学员家长"

    # 前台 Token 不能用于任何后台接口
    assert client.get("/api/auth/menus", headers=site_headers).json()["code"] == 401
    assert client.get("/api/users", headers=site_headers).json()["code"] == 401
    assert client.get("/api/dashboard/overview", headers=site_headers).json()["code"] == 401
    # 后台 Token 也不能冒充学员
    assert client.get("/api/site/me", headers=admin).json()["code"] == 401

    # 重复注册：账号 / 手机号都要拦住
    dup_user = client.post(
        "/api/site/auth/register",
        json={"username": username, "password": PASSWORD, "phone": _phone()},
    ).json()
    assert dup_user["code"] == 400
    dup_phone = client.post(
        "/api/site/auth/register",
        json={"username": _username(), "password": PASSWORD, "phone": phone},
    ).json()
    assert dup_phone["code"] == 400

    # 支持手机号登录；输错一次后仍可正常登录
    assert client.post(
        "/api/site/auth/login", json={"account": phone, "password": "Wrong1234"}
    ).json()["code"] == 400
    logged = client.post(
        "/api/site/auth/login", json={"account": phone, "password": PASSWORD}
    ).json()
    assert logged["code"] == 200
    assert logged["data"]["user"]["username"] == username

    # 跨作用域登出不会误注销对方：学员调后台登出接口仍保持登录
    assert client.post("/api/auth/logout", headers=site_headers).json()["code"] == 200
    assert client.get("/api/site/me", headers=site_headers).json()["code"] == 200
    # 管理员调学员登出接口也不会掉后台登录态
    assert client.post("/api/site/auth/logout", headers=admin).json()["code"] == 200
    assert client.get("/api/auth/menus", headers=admin).json()["code"] == 200

    # 退出后 Token 进入黑名单，立即失效
    assert client.post("/api/site/auth/logout", headers=site_headers).json()["code"] == 200
    assert client.get("/api/site/me", headers=site_headers).json()["code"] == 401


def test_site_profile_and_password(client):
    username, phone = _username(), _phone()
    data = _register(client, username, phone)
    headers = _site_headers(data["token"])
    new_phone = _phone()

    updated = client.put(
        "/api/site/me", json={"nickname": "王妈妈", "phone": new_phone}, headers=headers
    ).json()
    assert updated["code"] == 200, updated
    assert updated["data"]["nickname"] == "王妈妈"
    assert updated["data"]["phone"] == new_phone

    # 手机号不能与已有账号冲突
    other = _register(client, _username(), _phone())
    conflict = client.put(
        "/api/site/me", json={"phone": other["user"]["phone"]}, headers=headers
    ).json()
    assert conflict["code"] == 400

    assert client.put(
        "/api/site/me/password",
        json={"old_password": "Wrong1234", "new_password": "Newpass123"},
        headers=headers,
    ).json()["code"] == 400
    assert client.put(
        "/api/site/me/password",
        json={"old_password": PASSWORD, "new_password": "Newpass123"},
        headers=headers,
    ).json()["code"] == 200

    assert client.post(
        "/api/site/auth/login", json={"account": new_phone, "password": PASSWORD}
    ).json()["code"] == 400
    assert client.post(
        "/api/site/auth/login", json={"account": new_phone, "password": "Newpass123"}
    ).json()["code"] == 200


def test_site_enrollment_attribution(client, admin):
    username, phone = _username(), _phone()
    data = _register(client, username, phone)
    headers = _site_headers(data["token"])
    course = client.get("/api/site/courses", params={"size": 1}).json()["data"]["list"][0]

    # 登录后提交：线索直接归属账号
    created = client.post(
        "/api/site/enroll",
        json={
            "course_id": course["id"],
            "name": "王妈妈",
            "phone": phone,
            "age": "9 岁",
            "source": "官网",
            "remark": "想了解上课时间",
        },
        headers=headers,
    ).json()
    assert created["code"] == 200, created
    assert created["data"]["duplicated"] is False

    mine = client.get("/api/site/me/enrollments", headers=headers).json()
    assert mine["code"] == 200
    assert mine["data"]["total"] >= 1
    assert mine["data"]["list"][0]["course_title"] == course["title"]
    assert mine["data"]["list"][0]["status_text"] == "待跟进"

    # 注册前用同一手机号留下的历史线索，也能在“我的报名”里看到
    guest_phone = _phone()
    guest_course = client.get("/api/site/courses", params={"size": 2}).json()["data"]["list"][1]
    guest = client.post(
        "/api/site/enroll",
        json={"course_id": guest_course["id"], "name": "游客", "phone": guest_phone},
    ).json()
    assert guest["code"] == 200
    account = _register(client, _username(), guest_phone)
    mine = client.get("/api/site/me/enrollments", headers=_site_headers(account["token"])).json()
    assert any(row["course_title"] == guest_course["title"] for row in mine["data"]["list"])

    # 后台线索池仍能看到这条报名，且后台账号不受影响
    leads = client.get("/api/enrollments", params={"keyword": phone}, headers=admin).json()
    assert leads["code"] == 200
    assert leads["data"]["total"] >= 1
