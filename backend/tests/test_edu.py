"""教培业务回归测试：前台官网 + 后台课程/分类/师资/报名。"""
import uuid

from conftest import login, menu_id


def _name(prefix: str = "t") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:6]}"


def _phone() -> str:
    return "139" + str(uuid.uuid4().int % 10 ** 8).zfill(8)


# ---------------------------------------------------------------- 前台官网
def test_site_home(client):
    body = client.get("/api/site/home").json()
    assert body["code"] == 200
    data = body["data"]
    assert data["stats"]["courses"] >= 1
    assert data["stats"]["teachers"] >= 1
    assert data["categories"]
    assert data["recommend"]
    # 卡片必须带分类与讲师名称，前台才能正常展示
    assert all(item["category_name"] for item in data["recommend"])


def test_site_course_publish_visibility(client, admin):
    cat = client.post("/api/course-categories", json={"name": _name("分类")}, headers=admin).json()
    assert cat["code"] == 200
    category_id = cat["data"]["id"]

    created = client.post(
        "/api/courses",
        json={"title": _name("未上架课程"), "category_id": category_id, "price": 100, "status": 0},
        headers=admin,
    ).json()
    assert created["code"] == 200
    course_id = created["data"]["id"]

    def site_ids() -> list[int]:
        rows = client.get("/api/site/courses", params={"size": 100}).json()["data"]["list"]
        return [row["id"] for row in rows]

    # 未上架：前台看不到
    assert course_id not in site_ids()

    # 上架后：前台可见，详情可访问
    assert client.put(
        f"/api/courses/{course_id}/status", json={"status": 1}, headers=admin
    ).json()["code"] == 200
    assert course_id in site_ids()
    detail = client.get(f"/api/site/courses/{course_id}").json()
    assert detail["code"] == 200
    assert detail["data"]["title"]

    # 下架后：前台详情直接 404
    client.put(f"/api/courses/{course_id}/status", json={"status": 0}, headers=admin)
    assert client.get(f"/api/site/courses/{course_id}").json()["code"] == 404

    client.delete("/api/courses", params={"ids": str(course_id)}, headers=admin)
    client.delete(f"/api/course-categories/{category_id}", headers=admin)


def test_site_enroll_and_follow_up(client, admin):
    course = client.get("/api/site/courses", params={"size": 1}).json()["data"]["list"][0]
    phone = _phone()
    payload = {
        "course_id": course["id"],
        "name": "测试家长",
        "phone": phone,
        "age": "8 岁",
        "source": "试听",
        "remark": "想先听一节",
    }

    first = client.post("/api/site/enroll", json=payload).json()
    assert first["code"] == 200, first
    assert first["data"]["duplicated"] is False

    # 10 分钟内同手机号同课程重复提交：判定为重复，不新增记录
    second = client.post("/api/site/enroll", json=payload).json()
    assert second["code"] == 200
    assert second["data"]["duplicated"] is True

    listed = client.get("/api/enrollments", params={"keyword": phone}, headers=admin).json()
    assert listed["code"] == 200
    assert listed["data"]["total"] == 1
    row = listed["data"]["list"][0]
    assert row["status"] == 0 and row["status_text"] == "待跟进"
    assert row["course_title"] == course["title"]

    updated = client.put(
        f"/api/enrollments/{row['id']}", json={"status": 2, "remark": "已成交"}, headers=admin
    ).json()
    assert updated["code"] == 200
    after = client.get("/api/enrollments", params={"keyword": phone}, headers=admin).json()
    assert after["data"]["list"][0]["status_text"] == "已成交"

    exported = client.get("/api/enrollments/export", headers=admin)
    assert exported.status_code == 200
    assert exported.content[:2] == b"PK"


# ---------------------------------------------------------------- 后台约束
def test_category_and_teacher_delete_guards(client, admin):
    category_id = client.post(
        "/api/course-categories", json={"name": _name("分类")}, headers=admin
    ).json()["data"]["id"]
    teacher_id = client.post(
        "/api/teachers", json={"name": _name("老师")}, headers=admin
    ).json()["data"]["id"]
    course_id = client.post(
        "/api/courses",
        json={"title": _name("课程"), "category_id": category_id, "teacher_id": teacher_id},
        headers=admin,
    ).json()["data"]["id"]

    # 分类 / 教师被课程引用时不允许删除
    assert client.delete(f"/api/course-categories/{category_id}", headers=admin).json()["code"] == 403
    assert client.delete(f"/api/teachers/{teacher_id}", headers=admin).json()["code"] == 403

    # 软删除课程后即可删除
    assert client.delete("/api/courses", params={"ids": str(course_id)}, headers=admin).json()["code"] == 200
    assert client.delete(f"/api/course-categories/{category_id}", headers=admin).json()["code"] == 200
    assert client.delete(f"/api/teachers/{teacher_id}", headers=admin).json()["code"] == 200


def test_edu_rbac_permissions(client, admin, menus):
    """只有课程查看权限的角色，能读列表但不能上架课程。"""
    courses_menu_id = menu_id(menus, "/admin/courses")
    role = client.post(
        "/api/roles",
        json={"name": _name("教务角色"), "menu_ids": [courses_menu_id]},
        headers=admin,
    ).json()
    assert role["code"] == 200
    role_id = role["data"]["id"]

    username = _name("edu")
    created = client.post(
        "/api/users",
        json={"username": username, "password": "Abcd1234", "role_ids": [role_id]},
        headers=admin,
    ).json()
    assert created["code"] == 200
    user_id = created["data"]["id"]

    headers = login(client, username, "Abcd1234")
    assert client.get("/api/courses", headers=headers).json()["code"] == 200

    denied = client.put("/api/courses/1/status", json={"status": 0}, headers=headers).json()
    assert denied["code"] == 403
    assert "无权限" in denied["msg"]

    client.delete("/api/users", params={"ids": str(user_id)}, headers=admin)
    assert client.delete(f"/api/roles/{role_id}", headers=admin).json()["code"] == 200
