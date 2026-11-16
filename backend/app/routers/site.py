"""前台官网接口。

- 官网内容（课程 / 师资 / 资讯）全部免登录，只暴露「已上架 / 已发布」数据；
- 前台学员账号与后台管理账号完全隔离：Token 带 scope，互不通用；
- 报名接口允许游客提交，登录后提交的线索会归属到该学员账号。
"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core import redis_client
from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_site_user, get_optional_site_user
from app.core.oplog import fmt_dt, write_log
from app.core.response import Resp
from app.core.security import (
    SITE_SCOPE,
    blacklist_token,
    create_token,
    hash_password,
    password_policy_error,
    verify_password,
)
from app.models.models import Article, Course, CourseCategory, Enrollment, SiteUser, Teacher
from app.schemas.schemas import (
    EnrollIn,
    SiteChangePwdIn,
    SiteLoginIn,
    SiteProfileUpdate,
    SiteRegisterIn,
)

router = APIRouter(prefix="/site", tags=["前台官网"])

ENROLL_STATUS = {0: "待跟进", 1: "已联系", 2: "已成交", 3: "已失效"}


def _paging(page: int, size: int, max_size: int = 24) -> tuple[int, int]:
    try:
        page = max(int(page), 1)
    except (TypeError, ValueError):
        page = 1
    try:
        size = int(size)
    except (TypeError, ValueError):
        size = 12
    return page, min(max(size, 1), max_size)


def _tags(value: str) -> list[str]:
    return [item.strip() for item in (value or "").split(",") if item.strip()]


def _category_map(db: Session) -> dict[int, CourseCategory]:
    rows = db.query(CourseCategory).filter(CourseCategory.is_deleted == 0).all()
    return {row.id: row for row in rows}


def _teacher_map(db: Session) -> dict[int, Teacher]:
    rows = db.query(Teacher).filter(Teacher.is_deleted == 0).all()
    return {row.id: row for row in rows}


def _teacher_card(teacher: Teacher) -> dict:
    return {
        "id": teacher.id,
        "name": teacher.name,
        "title": teacher.title,
        "avatar": teacher.avatar,
        "intro": teacher.intro,
        "tags": _tags(teacher.tags),
        "years": teacher.years,
    }


def _course_card(course: Course, category=None, teacher=None) -> dict:
    return {
        "id": course.id,
        "title": course.title,
        "subtitle": course.subtitle,
        "cover": course.cover,
        "summary": course.summary,
        "price": course.price,
        "original_price": course.original_price,
        "lessons": course.lessons,
        "duration": course.duration,
        "level": course.level,
        "tags": _tags(course.tags),
        "category_id": course.category_id,
        "category_name": category.name if category else "",
        "teacher_id": course.teacher_id,
        "teacher_name": teacher.name if teacher else "",
        "teacher_title": teacher.title if teacher else "",
        "is_recommend": course.is_recommend,
        "view_count": course.view_count,
    }


def _article_card(article: Article) -> dict:
    return {
        "id": article.id,
        "title": article.title,
        "category": article.category,
        "cover": article.cover,
        "summary": article.summary,
        "published_at": (article.published_at or article.created_at or datetime.now()).strftime("%Y-%m-%d"),
    }


def _published_courses(db: Session):
    return db.query(Course).filter(Course.status == 1, Course.is_deleted == 0)


@router.get("/home")
def site_home(db: Session = Depends(get_db)):
    """官网首页聚合数据：统计、分类、推荐课程、热门课程、师资、动态。"""
    cats = _category_map(db)
    teas = _teacher_map(db)

    recommend = (
        _published_courses(db)
        .filter(Course.is_recommend == 1)
        .order_by(Course.sort, Course.id.desc())
        .limit(6)
        .all()
    )
    if len(recommend) < 3:
        recommend = _published_courses(db).order_by(Course.sort, Course.id.desc()).limit(6).all()

    hot = (
        _published_courses(db)
        .order_by(func.coalesce(Course.view_count, 0).desc(), Course.id.desc())
        .limit(4)
        .all()
    )

    stats = {
        "courses": _published_courses(db).count(),
        "teachers": db.query(Teacher).filter(Teacher.is_deleted == 0, Teacher.status == 1).count(),
        "categories": db.query(CourseCategory).filter(
            CourseCategory.is_deleted == 0, CourseCategory.status == 1
        ).count(),
        "enrollments": db.query(Enrollment).count(),
    }

    return Resp.ok({
        "stats": stats,
        "categories": [
            {"id": c.id, "name": c.name, "desc": c.desc, "icon": c.icon}
            for c in db.query(CourseCategory)
            .filter(CourseCategory.is_deleted == 0, CourseCategory.status == 1)
            .order_by(CourseCategory.sort, CourseCategory.id)
            .all()
        ],
        "recommend": [_course_card(c, cats.get(c.category_id), teas.get(c.teacher_id)) for c in recommend],
        "hot": [_course_card(c, cats.get(c.category_id), teas.get(c.teacher_id)) for c in hot],
        "teachers": [
            _teacher_card(t)
            for t in db.query(Teacher)
            .filter(Teacher.is_deleted == 0, Teacher.status == 1)
            .order_by(Teacher.sort, Teacher.id)
            .limit(4)
            .all()
        ],
        "articles": [
            _article_card(a)
            for a in db.query(Article)
            .filter(Article.is_deleted == 0, Article.status == 1)
            .order_by(Article.published_at.desc(), Article.id.desc())
            .limit(3)
            .all()
        ],
    })


@router.get("/categories")
def site_categories(db: Session = Depends(get_db)):
    rows = (
        db.query(CourseCategory)
        .filter(CourseCategory.is_deleted == 0, CourseCategory.status == 1)
        .order_by(CourseCategory.sort, CourseCategory.id)
        .all()
    )
    return Resp.ok([{"id": c.id, "name": c.name, "desc": c.desc, "icon": c.icon} for c in rows])


@router.get("/courses")
def site_courses(keyword: str = "", category_id: int = 0, level: str = "",
                 page: int = 1, size: int = 12, db: Session = Depends(get_db)):
    page, size = _paging(page, size)
    cats, teas = _category_map(db), _teacher_map(db)
    q = _published_courses(db)
    if keyword:
        like = f"%{keyword}%"
        q = q.filter((Course.title.like(like)) | (Course.summary.like(like)) | (Course.tags.like(like)))
    if category_id:
        q = q.filter(Course.category_id == category_id)
    if level:
        q = q.filter(Course.level == level)
    total = q.count()
    rows = q.order_by(Course.sort, Course.id.desc()).offset((page - 1) * size).limit(size).all()
    return Resp.page(total, [_course_card(c, cats.get(c.category_id), teas.get(c.teacher_id)) for c in rows])


@router.get("/courses/{cid}")
def site_course_detail(cid: int, db: Session = Depends(get_db)):
    course = db.query(Course).filter(
        Course.id == cid, Course.status == 1, Course.is_deleted == 0
    ).first()
    if not course:
        return Resp.fail("课程不存在或已下架", code=404)

    course.view_count = (course.view_count or 0) + 1
    db.commit()

    cat = db.query(CourseCategory).filter(CourseCategory.id == course.category_id).first()
    teacher = db.query(Teacher).filter(Teacher.id == course.teacher_id).first()

    related = (
        _published_courses(db)
        .filter(Course.id != course.id, Course.category_id == course.category_id)
        .order_by(Course.sort, Course.id.desc())
        .limit(3)
        .all()
    )

    data = _course_card(course, cat, teacher)
    data.update({
        "description": course.description,
        "suitable": course.suitable,
        "related": [_course_card(c, cat, db.query(Teacher).filter(Teacher.id == c.teacher_id).first())
                    for c in related],
    })
    return Resp.ok(data)


@router.get("/teachers")
def site_teachers(db: Session = Depends(get_db)):
    rows = (
        db.query(Teacher)
        .filter(Teacher.is_deleted == 0, Teacher.status == 1)
        .order_by(Teacher.sort, Teacher.id)
        .all()
    )
    return Resp.ok([_teacher_card(t) for t in rows])


@router.get("/articles")
def site_articles(page: int = 1, size: int = 10, db: Session = Depends(get_db)):
    page, size = _paging(page, size)
    q = db.query(Article).filter(Article.is_deleted == 0, Article.status == 1)
    total = q.count()
    rows = q.order_by(Article.published_at.desc(), Article.id.desc()).offset((page - 1) * size).limit(size).all()
    return Resp.page(total, [_article_card(a) for a in rows])


@router.get("/articles/{aid}")
def site_article_detail(aid: int, db: Session = Depends(get_db)):
    article = db.query(Article).filter(
        Article.id == aid, Article.is_deleted == 0, Article.status == 1
    ).first()
    if not article:
        return Resp.fail("文章不存在", code=404)
    data = _article_card(article)
    data["content"] = article.content
    return Resp.ok(data)


@router.post("/enroll")
def site_enroll(body: EnrollIn, req: Request, db: Session = Depends(get_db),
                site_user: SiteUser | None = Depends(get_optional_site_user)):
    """前台提交报名 / 预约试听，进入后台线索池。

    未登录也可提交（游客线索）；带了学员 Token 时把线索归属到该账号，
    之后「个人中心 → 我的报名」就能直接看到进度。
    """
    course = None
    if body.course_id:
        course = db.query(Course).filter(
            Course.id == body.course_id, Course.is_deleted == 0
        ).first()
        if not course:
            return Resp.fail("课程不存在", code=404)

    # 同手机号 + 同课程 10 分钟内重复提交，视为重复点击，直接返回成功避免刷单
    since = datetime.now() - timedelta(minutes=10)
    duplicated = (
        db.query(Enrollment)
        .filter(
            Enrollment.phone == body.phone,
            Enrollment.course_id == body.course_id,
            Enrollment.created_at >= since,
        )
        .first()
    )
    if duplicated:
        # 游客先提交、登录后又提交同一门课：把已有线索补挂到账号上
        if site_user and not duplicated.site_user_id:
            duplicated.site_user_id = site_user.id
            db.commit()
        return Resp.ok({"id": duplicated.id, "duplicated": True}, msg="已收到你的报名，我们会尽快联系你")

    row = Enrollment(
        course_id=body.course_id,
        course_title=course.title if course else "",
        site_user_id=site_user.id if site_user else 0,
        name=body.name,
        phone=body.phone,
        age=body.age,
        source=body.source or "官网",
        remark=body.remark,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    write_log(db, None, "前台报名", "报名", req,
              params=f"{body.name}/{body.phone}/{row.course_title}", method="POST",
              username=body.name)
    return Resp.ok({"id": row.id, "duplicated": False}, msg="报名成功，课程顾问会尽快与你联系")


# ---------------------------------------------------------------- 前台学员账号
def _site_payload(user: SiteUser) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "nickname": user.nickname,
        "phone": user.phone,
    }


def _site_fail_key(account: str) -> str:
    return f"site_login:fail:{account.strip().lower()}"


@router.post("/auth/register")
def site_register(body: SiteRegisterIn, req: Request, db: Session = Depends(get_db)):
    """注册前台学员账号：成功后直接返回 Token，免去二次登录。"""
    # 账号 / 手机号共用一个登录入口，跨字段也要查重，避免「A 的账号 = B 的手机号」导致登录歧义
    if db.query(SiteUser).filter(
        SiteUser.is_deleted == 0,
        or_(SiteUser.username == body.username, SiteUser.phone == body.username),
    ).first():
        return Resp.fail("该账号已被注册，请直接登录")
    if db.query(SiteUser).filter(
        SiteUser.is_deleted == 0,
        or_(SiteUser.phone == body.phone, SiteUser.username == body.phone),
    ).first():
        return Resp.fail("该手机号已注册，请直接登录")

    err = password_policy_error(body.password)
    if err:
        return Resp.fail(err)

    user = SiteUser(
        username=body.username,
        password_hash=hash_password(body.password),
        nickname=body.nickname or body.username,
        phone=body.phone,
        status=1,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_token(str(user.id), scope=SITE_SCOPE)
    write_log(db, None, "前台账号", "注册", req,
              params=user.username, method="POST", username=user.username)
    return Resp.ok({"token": token, "user": _site_payload(user)}, msg="注册成功，已自动登录")


@router.post("/auth/login")
def site_login(body: SiteLoginIn, req: Request, db: Session = Depends(get_db)):
    """前台登录：账号或手机号 + 密码；失败次数与后台账号各自独立计数。"""
    account = body.account.strip()
    fail_key = _site_fail_key(account)
    fails = int(redis_client.redis_get(fail_key) or 0)
    if fails >= settings.LOGIN_MAX_FAILS:
        return Resp.fail(
            f"密码错误次数过多，请 {settings.LOGIN_LOCK_MINUTES} 分钟后再试", code=429
        )

    user = db.query(SiteUser).filter(
        SiteUser.username == account, SiteUser.is_deleted == 0
    ).first()
    if not user:
        # 账号没命中再按手机号找；账号优先，避免与手机号同值时产生歧义
        user = db.query(SiteUser).filter(
            SiteUser.phone == account, SiteUser.is_deleted == 0
        ).first()
    if not user or not verify_password(body.password, user.password_hash):
        fails_now = redis_client.incr_with_ttl(fail_key, settings.LOGIN_LOCK_MINUTES * 60)
        write_log(db, None, "前台账号", "登录", req,
                  params=account, result="失败", method="POST", username=account)
        left = settings.LOGIN_MAX_FAILS - fails_now
        if left <= 0:
            return Resp.fail(
                f"账号或密码错误，账号已锁定 {settings.LOGIN_LOCK_MINUTES} 分钟", code=400
            )
        return Resp.fail(f"账号或密码错误，还可尝试 {left} 次", code=400)

    if user.status == 0:
        write_log(db, None, "前台账号", "登录", req,
                  params=account, result="失败", method="POST", username=account)
        return Resp.fail("账号已禁用，请联系客服", code=403)

    redis_client.redis_delete(fail_key)
    token = create_token(str(user.id), scope=SITE_SCOPE)
    write_log(db, None, "前台账号", "登录", req,
              params=account, result="成功", method="POST", username=user.username)
    return Resp.ok({"token": token, "user": _site_payload(user)}, msg="登录成功")


@router.post("/auth/logout")
def site_logout(req: Request):
    """退出前台账号：Token 写入黑名单（仅学员 Token），后台登录态不受影响。"""
    auth = req.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        blacklist_token(auth[7:], scope=SITE_SCOPE)
    return Resp.ok(msg="已退出登录")


@router.get("/me")
def site_me(user: SiteUser = Depends(get_current_site_user)):
    """当前学员资料。后台管理员 Token 访问这里会返回 401。"""
    return Resp.ok({
        "user": {
            **_site_payload(user),
            "created_at": fmt_dt(user.created_at),
        },
    })


@router.put("/me")
def site_update_me(body: SiteProfileUpdate, req: Request,
                   user: SiteUser = Depends(get_current_site_user),
                   db: Session = Depends(get_db)):
    row = db.query(SiteUser).filter(SiteUser.id == user.id, SiteUser.is_deleted == 0).first()
    if not row:
        return Resp.fail("账号不存在或已删除", code=401)
    if body.nickname is not None:
        row.nickname = body.nickname
    if body.phone is not None and body.phone != row.phone:
        # 手机号与账号共用一个登录入口，改手机号时同样要避开他人的账号名
        if db.query(SiteUser).filter(
            SiteUser.id != row.id,
            SiteUser.is_deleted == 0,
            or_(SiteUser.phone == body.phone, SiteUser.username == body.phone),
        ).first():
            return Resp.fail("该手机号已被其他账号使用")
        row.phone = body.phone
    db.commit()
    write_log(db, None, "前台账号", "修改资料", req,
              params=row.username, method="PUT", username=row.username)
    return Resp.ok(_site_payload(row))


@router.put("/me/password")
def site_change_password(body: SiteChangePwdIn, req: Request,
                         user: SiteUser = Depends(get_current_site_user),
                         db: Session = Depends(get_db)):
    row = db.query(SiteUser).filter(SiteUser.id == user.id, SiteUser.is_deleted == 0).first()
    if not row:
        return Resp.fail("账号不存在或已删除", code=401)
    if not verify_password(body.old_password, row.password_hash):
        return Resp.fail("原密码错误")
    if body.old_password == body.new_password:
        return Resp.fail("新密码不能与原密码相同")
    err = password_policy_error(body.new_password)
    if err:
        return Resp.fail(err)
    row.password_hash = hash_password(body.new_password)
    db.commit()
    write_log(db, None, "前台账号", "修改密码", req,
              params=row.username, method="PUT", username=row.username)
    return Resp.ok(msg="密码修改成功")


@router.get("/me/enrollments")
def site_my_enrollments(page: int = 1, size: int = 10,
                        user: SiteUser = Depends(get_current_site_user),
                        db: Session = Depends(get_db)):
    """我的报名：按账号归属查询；注册前用同一手机号提交的历史线索也会带出来。"""
    page, size = _paging(page, size, max_size=50)
    cond = Enrollment.site_user_id == user.id
    if user.phone:
        cond = or_(cond, Enrollment.phone == user.phone)
    q = db.query(Enrollment).filter(cond)
    total = q.count()
    rows = q.order_by(Enrollment.id.desc()).offset((page - 1) * size).limit(size).all()
    data = [{
        "id": e.id,
        "course_id": e.course_id,
        "course_title": e.course_title,
        "name": e.name,
        "phone": e.phone,
        "age": e.age,
        "source": e.source,
        "status": e.status,
        "status_text": ENROLL_STATUS.get(e.status, "未知"),
        "remark": e.remark,
        "created_at": fmt_dt(e.created_at),
    } for e in rows]
    return Resp.page(total, data)

