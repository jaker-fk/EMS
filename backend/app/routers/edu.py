"""教培业务后台接口：课程上架、分类、师资、资讯、报名线索。

挂在 /api 下，全部走 RBAC 接口级权限；超级管理员直通。
"""
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request
from openpyxl import Workbook
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_perms
from app.core.excel import xlsx_response
from app.core.oplog import fmt_dt, write_log
from app.core.response import Resp
from app.models.models import Article, Course, CourseCategory, Enrollment, Teacher, User
from app.schemas.schemas import (
    ArticleIn,
    CategoryIn,
    CourseIn,
    CourseStatusIn,
    EnrollmentUpdate,
    TeacherIn,
)

router = APIRouter(tags=["教培管理"])

ENROLL_STATUS = {0: "待跟进", 1: "已联系", 2: "已成交", 3: "已失效"}


def _paging(page: int, size: int) -> tuple[int, int]:
    try:
        page = max(int(page), 1)
    except (TypeError, ValueError):
        page = 1
    try:
        size = int(size)
    except (TypeError, ValueError):
        size = 10
    return page, min(max(size, 1), 100)


def _ids(value: str) -> list[int]:
    out = []
    for part in (value or "").split(","):
        part = part.strip()
        if part.isdigit() and int(part) not in out:
            out.append(int(part))
    return out


def _tags(value: str) -> list[str]:
    return [item.strip() for item in (value or "").split(",") if item.strip()]


def _course_row(course: Course, cat=None, tea=None) -> dict:
    return {
        "id": course.id,
        "title": course.title,
        "subtitle": course.subtitle,
        "cover": course.cover,
        "summary": course.summary,
        "description": course.description,
        "category_id": course.category_id,
        "category_name": cat.name if cat else "",
        "teacher_id": course.teacher_id,
        "teacher_name": tea.name if tea else "",
        "price": course.price,
        "original_price": course.original_price,
        "lessons": course.lessons,
        "duration": course.duration,
        "level": course.level,
        "suitable": course.suitable,
        "tags": course.tags,
        "status": course.status,
        "is_recommend": course.is_recommend,
        "sort": course.sort,
        "view_count": course.view_count or 0,
        "created_at": fmt_dt(course.created_at),
        "updated_at": fmt_dt(course.update_time),
    }


# ---------------------------------------------------------------- 课程分类
@router.get("/course-categories", dependencies=[Depends(require_perms("edu:category:list"))])
def list_categories(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = (
        db.query(CourseCategory)
        .filter(CourseCategory.is_deleted == 0)
        .order_by(CourseCategory.sort, CourseCategory.id)
        .all()
    )
    # 一次分组统计，避免每个分类各查一次课程数（N+1）
    course_counts = dict(
        db.query(Course.category_id, func.count(Course.id))
        .filter(Course.is_deleted == 0)
        .group_by(Course.category_id)
        .all()
    )
    data = []
    for c in rows:
        data.append({
            "id": c.id,
            "name": c.name,
            "desc": c.desc,
            "icon": c.icon,
            "sort": c.sort,
            "status": c.status,
            "course_count": course_counts.get(c.id, 0),
        })
    return Resp.ok(data)


@router.post("/course-categories", dependencies=[Depends(require_perms("edu:category:add"))])
def create_category(body: CategoryIn, req: Request, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    if db.query(CourseCategory).filter(
        CourseCategory.name == body.name, CourseCategory.is_deleted == 0
    ).first():
        return Resp.fail("分类名称已存在")
    row = CourseCategory(**body.model_dump())
    db.add(row)
    db.commit()
    write_log(db, user, "课程分类", "新增", req, params=body.name, method="POST")
    return Resp.ok({"id": row.id})


@router.put("/course-categories/{cid}", dependencies=[Depends(require_perms("edu:category:edit"))])
def update_category(cid: int, body: CategoryIn, req: Request, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    row = db.query(CourseCategory).filter(
        CourseCategory.id == cid, CourseCategory.is_deleted == 0
    ).first()
    if not row:
        return Resp.fail("分类不存在")
    for key, value in body.model_dump().items():
        setattr(row, key, value)
    db.commit()
    write_log(db, user, "课程分类", "修改", req, params=body.name, method="PUT")
    return Resp.ok()


@router.delete("/course-categories/{cid}", dependencies=[Depends(require_perms("edu:category:remove"))])
def delete_category(cid: int, req: Request, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    row = db.query(CourseCategory).filter(
        CourseCategory.id == cid, CourseCategory.is_deleted == 0
    ).first()
    if not row:
        return Resp.fail("分类不存在")
    used = db.query(Course).filter(Course.category_id == cid, Course.is_deleted == 0).count()
    if used:
        return Resp.fail(f"该分类下还有 {used} 门课程，请先调整分类", code=403)
    row.is_deleted = 1
    db.commit()
    write_log(db, user, "课程分类", "删除", req, params=row.name, method="DELETE")
    return Resp.ok()


# ---------------------------------------------------------------- 师资
@router.get("/teachers", dependencies=[Depends(require_perms("edu:teacher:list"))])
def list_teachers(keyword: str = "", page: int = 1, size: int = 10,
                  db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    page, size = _paging(page, size)
    q = db.query(Teacher).filter(Teacher.is_deleted == 0)
    if keyword:
        q = q.filter((Teacher.name.like(f"%{keyword}%")) | (Teacher.title.like(f"%{keyword}%")))
    total = q.count()
    rows = q.order_by(Teacher.sort, Teacher.id.desc()).offset((page - 1) * size).limit(size).all()
    # 一次分组统计每位教师的课程数，避免 N+1
    course_counts = dict(
        db.query(Course.teacher_id, func.count(Course.id))
        .filter(Course.is_deleted == 0)
        .group_by(Course.teacher_id)
        .all()
    )
    data = [{
        "id": t.id,
        "name": t.name,
        "title": t.title,
        "avatar": t.avatar,
        "intro": t.intro,
        "tags": t.tags,
        "years": t.years,
        "sort": t.sort,
        "status": t.status,
        "course_count": course_counts.get(t.id, 0),
        "created_at": fmt_dt(t.created_at),
    } for t in rows]
    return Resp.page(total, data)


@router.post("/teachers", dependencies=[Depends(require_perms("edu:teacher:add"))])
def create_teacher(body: TeacherIn, req: Request, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    row = Teacher(**body.model_dump())
    db.add(row)
    db.commit()
    write_log(db, user, "师资管理", "新增", req, params=body.name, method="POST")
    return Resp.ok({"id": row.id})


@router.put("/teachers/{tid}", dependencies=[Depends(require_perms("edu:teacher:edit"))])
def update_teacher(tid: int, body: TeacherIn, req: Request, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    row = db.query(Teacher).filter(Teacher.id == tid, Teacher.is_deleted == 0).first()
    if not row:
        return Resp.fail("教师不存在")
    for key, value in body.model_dump().items():
        setattr(row, key, value)
    db.commit()
    write_log(db, user, "师资管理", "修改", req, params=body.name, method="PUT")
    return Resp.ok()


@router.delete("/teachers/{tid}", dependencies=[Depends(require_perms("edu:teacher:remove"))])
def delete_teacher(tid: int, req: Request, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    row = db.query(Teacher).filter(Teacher.id == tid, Teacher.is_deleted == 0).first()
    if not row:
        return Resp.fail("教师不存在")
    used = db.query(Course).filter(Course.teacher_id == tid, Course.is_deleted == 0).count()
    if used:
        return Resp.fail(f"该教师还有 {used} 门课程，请先调整授课教师", code=403)
    row.is_deleted = 1
    db.commit()
    write_log(db, user, "师资管理", "删除", req, params=row.name, method="DELETE")
    return Resp.ok()


# ---------------------------------------------------------------- 课程
@router.get("/courses", dependencies=[Depends(require_perms("edu:course:list"))])
def list_courses(keyword: str = "", category_id: int = 0, status: int | None = None,
                 page: int = 1, size: int = 10, db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    page, size = _paging(page, size)
    q = db.query(Course).filter(Course.is_deleted == 0)
    if keyword:
        q = q.filter((Course.title.like(f"%{keyword}%")) | (Course.tags.like(f"%{keyword}%")))
    if category_id:
        q = q.filter(Course.category_id == category_id)
    if status is not None:
        q = q.filter(Course.status == status)
    total = q.count()
    rows = q.order_by(Course.sort, Course.id.desc()).offset((page - 1) * size).limit(size).all()

    cats = {c.id: c for c in db.query(CourseCategory).all()}
    teas = {t.id: t for t in db.query(Teacher).all()}
    return Resp.page(total, [_course_row(c, cats.get(c.category_id), teas.get(c.teacher_id)) for c in rows])


@router.get("/courses/{cid}", dependencies=[Depends(require_perms("edu:course:list"))])
def get_course(cid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    course = db.query(Course).filter(Course.id == cid, Course.is_deleted == 0).first()
    if not course:
        return Resp.fail("课程不存在")
    cat = db.query(CourseCategory).filter(CourseCategory.id == course.category_id).first()
    tea = db.query(Teacher).filter(Teacher.id == course.teacher_id).first()
    return Resp.ok(_course_row(course, cat, tea))


@router.post("/courses", dependencies=[Depends(require_perms("edu:course:add"))])
def create_course(body: CourseIn, req: Request, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    _check_course_refs(db, body)
    row = Course(**body.model_dump())
    db.add(row)
    db.commit()
    write_log(db, user, "课程管理", "新增", req, params=body.title, method="POST")
    return Resp.ok({"id": row.id})


@router.put("/courses/{cid}", dependencies=[Depends(require_perms("edu:course:edit"))])
def update_course(cid: int, body: CourseIn, req: Request, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    row = db.query(Course).filter(Course.id == cid, Course.is_deleted == 0).first()
    if not row:
        return Resp.fail("课程不存在")
    _check_course_refs(db, body)
    for key, value in body.model_dump().items():
        setattr(row, key, value)
    db.commit()
    write_log(db, user, "课程管理", "修改", req, params=body.title, method="PUT")
    return Resp.ok()


@router.put("/courses/{cid}/status", dependencies=[Depends(require_perms("edu:course:publish"))])
def toggle_course_status(cid: int, body: CourseStatusIn, req: Request, db: Session = Depends(get_db),
                         user: User = Depends(get_current_user)):
    row = db.query(Course).filter(Course.id == cid, Course.is_deleted == 0).first()
    if not row:
        return Resp.fail("课程不存在")
    row.status = body.status
    db.commit()
    action = "上架" if body.status == 1 else "下架"
    write_log(db, user, "课程管理", action, req, params=row.title, method="PUT")
    return Resp.ok({"status": row.status})


@router.delete("/courses", dependencies=[Depends(require_perms("edu:course:remove"))])
def delete_courses(ids: str = Query(""), req: Request = None, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    id_list = _ids(ids)
    if not id_list:
        return Resp.fail("参数错误")
    db.query(Course).filter(Course.id.in_(id_list)).update(
        {Course.is_deleted: 1}, synchronize_session=False
    )
    db.commit()
    write_log(db, user, "课程管理", "删除", req, params=ids, method="DELETE")
    return Resp.ok()


def _check_course_refs(db: Session, body: CourseIn) -> None:
    if body.category_id:
        exists = db.query(CourseCategory).filter(
            CourseCategory.id == body.category_id, CourseCategory.is_deleted == 0
        ).first()
        if not exists:
            body.category_id = 0
    if body.teacher_id:
        exists = db.query(Teacher).filter(
            Teacher.id == body.teacher_id, Teacher.is_deleted == 0
        ).first()
        if not exists:
            body.teacher_id = 0


# ---------------------------------------------------------------- 资讯
@router.get("/articles", dependencies=[Depends(require_perms("edu:article:list"))])
def list_articles(keyword: str = "", page: int = 1, size: int = 10,
                  db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    page, size = _paging(page, size)
    q = db.query(Article).filter(Article.is_deleted == 0)
    if keyword:
        q = q.filter(Article.title.like(f"%{keyword}%"))
    total = q.count()
    rows = q.order_by(Article.id.desc()).offset((page - 1) * size).limit(size).all()
    data = [{
        "id": a.id,
        "title": a.title,
        "category": a.category,
        "cover": a.cover,
        "summary": a.summary,
        "content": a.content,
        "status": a.status,
        "published_at": fmt_dt(a.published_at),
    } for a in rows]
    return Resp.page(total, data)


@router.post("/articles", dependencies=[Depends(require_perms("edu:article:add"))])
def create_article(body: ArticleIn, req: Request, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    row = Article(**body.model_dump())
    row.published_at = datetime.now()
    db.add(row)
    db.commit()
    write_log(db, user, "资讯管理", "新增", req, params=body.title, method="POST")
    return Resp.ok({"id": row.id})


@router.put("/articles/{aid}", dependencies=[Depends(require_perms("edu:article:edit"))])
def update_article(aid: int, body: ArticleIn, req: Request, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    row = db.query(Article).filter(Article.id == aid, Article.is_deleted == 0).first()
    if not row:
        return Resp.fail("文章不存在")
    for key, value in body.model_dump().items():
        setattr(row, key, value)
    db.commit()
    write_log(db, user, "资讯管理", "修改", req, params=body.title, method="PUT")
    return Resp.ok()


@router.delete("/articles/{aid}", dependencies=[Depends(require_perms("edu:article:remove"))])
def delete_article(aid: int, req: Request, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    row = db.query(Article).filter(Article.id == aid, Article.is_deleted == 0).first()
    if not row:
        return Resp.fail("文章不存在")
    row.is_deleted = 1
    db.commit()
    write_log(db, user, "资讯管理", "删除", req, params=row.title, method="DELETE")
    return Resp.ok()


# ---------------------------------------------------------------- 报名线索
@router.get("/enrollments", dependencies=[Depends(require_perms("edu:enrollment:list"))])
def list_enrollments(keyword: str = "", status: int | None = None, page: int = 1, size: int = 10,
                     db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    page, size = _paging(page, size)
    q = db.query(Enrollment)
    if keyword:
        like = f"%{keyword}%"
        q = q.filter(
            (Enrollment.name.like(like))
            | (Enrollment.phone.like(like))
            | (Enrollment.course_title.like(like))
        )
    if status is not None:
        q = q.filter(Enrollment.status == status)
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


@router.put("/enrollments/{eid}", dependencies=[Depends(require_perms("edu:enrollment:edit"))])
def update_enrollment(eid: int, body: EnrollmentUpdate, req: Request, db: Session = Depends(get_db),
                      user: User = Depends(get_current_user)):
    row = db.query(Enrollment).filter(Enrollment.id == eid).first()
    if not row:
        return Resp.fail("报名记录不存在")
    row.status = body.status
    if body.remark is not None:
        row.remark = body.remark
    db.commit()
    write_log(db, user, "报名线索", "跟进", req,
              params=f"{row.name}->{ENROLL_STATUS.get(row.status, '')}", method="PUT")
    return Resp.ok()


@router.delete("/enrollments", dependencies=[Depends(require_perms("edu:enrollment:remove"))])
def delete_enrollments(ids: str = Query(""), req: Request = None, db: Session = Depends(get_db),
                       user: User = Depends(get_current_user)):
    id_list = _ids(ids)
    if not id_list:
        return Resp.fail("参数错误")
    db.query(Enrollment).filter(Enrollment.id.in_(id_list)).delete(synchronize_session=False)
    db.commit()
    write_log(db, user, "报名线索", "删除", req, params=ids, method="DELETE")
    return Resp.ok()


@router.get("/enrollments/export", dependencies=[Depends(require_perms("edu:enrollment:export"))])
def export_enrollments(keyword: str = "", status: int | None = None, req: Request = None,
                       db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = db.query(Enrollment)
    if keyword:
        like = f"%{keyword}%"
        q = q.filter((Enrollment.name.like(like)) | (Enrollment.phone.like(like)))
    if status is not None:
        q = q.filter(Enrollment.status == status)
    rows = q.order_by(Enrollment.id.desc()).limit(20000).all()

    wb = Workbook()
    ws = wb.active
    ws.title = "报名线索"
    ws.append(["ID", "姓名", "手机号", "年龄", "意向课程", "来源", "状态", "备注", "提交时间"])
    for e in rows:
        ws.append([
            e.id, e.name, e.phone, e.age, e.course_title, e.source,
            ENROLL_STATUS.get(e.status, ""), e.remark, fmt_dt(e.created_at),
        ])
    for column, width in zip("ABCDEFGHI", (8, 14, 16, 10, 26, 12, 10, 30, 20), strict=False):
        ws.column_dimensions[column].width = width

    write_log(db, user, "报名线索", "导出", req, params=f"共 {len(rows)} 条", method="GET")
    return xlsx_response(wb, f"enrollments_{datetime.now():%Y%m%d%H%M%S}.xlsx")
