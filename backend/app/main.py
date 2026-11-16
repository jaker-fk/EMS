import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import text
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.core import redis_client
from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.core.log_config import request_id_ctx, setup_logging
from app.core.metrics import DB_UP, REDIS_UP
from app.core.middleware import ObservabilityMiddleware
from app.core.ratelimit import allow
from app.core.security import ADMIN_SCOPE, SITE_SCOPE, decode_token, hash_password
from app.models import models
from app.routers.api import router as system_router
from app.routers.edu import router as edu_router
from app.routers.site import router as site_router

setup_logging()
logger = logging.getLogger("admin_panel")

# 管理端统一挂在 /admin 下，前台官网占据根路径
ADMIN_PREFIX = "/admin"


# ================================================================ 内置菜单
def _menu_spec() -> tuple[list[tuple], dict[str, list[tuple[str, str]]]]:
    """内置管理端菜单定义：(名称, 路径, 图标, 排序, 权限标识, 上级路径)。"""
    pages = [
        ("首页看板", "/admin/dashboard", "Odometer", 0, "", None),
        ("用户管理", "/admin/users", "User", 1, "system:user:list", None),
        ("角色管理", "/admin/roles", "Avatar", 2, "system:role:list", None),
        ("菜单管理", "/admin/menus", "Menu", 3, "system:menu:list", None),
        ("数据字典", "/admin/dicts", "Collection", 4, "system:dict:list", None),
        ("操作日志", "/admin/logs", "Document", 5, "system:log:list", None),
        ("文件管理", "/admin/files", "Folder", 6, "file:list", None),
        ("教务管理", "/admin/edu", "Reading", 7, "", None),
        ("课程管理", "/admin/courses", "Notebook", 8, "edu:course:list", "/admin/edu"),
        ("课程分类", "/admin/categories", "Files", 9, "edu:category:list", "/admin/edu"),
        ("师资团队", "/admin/teachers", "Avatar", 10, "edu:teacher:list", "/admin/edu"),
        ("报名线索", "/admin/enrollments", "Tickets", 11, "edu:enrollment:list", "/admin/edu"),
        ("资讯管理", "/admin/articles", "Notification", 12, "edu:article:list", None),
        ("个人中心", "/admin/profile", "UserFilled", 13, "profile:view", None),
        ("业务数据", "/admin/biz", "Goods", 14, "biz:list", None),
    ]
    buttons: dict[str, list[tuple[str, str]]] = {
        "/admin/users": [("新增用户", "system:user:add"), ("编辑用户", "system:user:edit"),
                         ("删除用户", "system:user:remove"), ("重置密码", "system:user:reset")],
        "/admin/roles": [("新增角色", "system:role:add"), ("编辑角色", "system:role:edit"),
                         ("删除角色", "system:role:remove"), ("分配权限", "system:role:assign")],
        "/admin/menus": [("新增菜单", "system:menu:add"), ("编辑菜单", "system:menu:edit"),
                         ("删除菜单", "system:menu:remove")],
        "/admin/dicts": [("新增字典", "system:dict:add"), ("编辑字典", "system:dict:edit"),
                         ("删除字典", "system:dict:remove")],
        "/admin/courses": [("新增课程", "edu:course:add"), ("编辑课程", "edu:course:edit"),
                           ("删除课程", "edu:course:remove"), ("上架下架", "edu:course:publish")],
        "/admin/categories": [("新增分类", "edu:category:add"), ("编辑分类", "edu:category:edit"),
                              ("删除分类", "edu:category:remove")],
        "/admin/teachers": [("新增教师", "edu:teacher:add"), ("编辑教师", "edu:teacher:edit"),
                            ("删除教师", "edu:teacher:remove")],
        "/admin/enrollments": [("跟进报名", "edu:enrollment:edit"),
                               ("删除报名", "edu:enrollment:remove"),
                               ("导出报名", "edu:enrollment:export")],
        "/admin/articles": [("新增资讯", "edu:article:add"), ("编辑资讯", "edu:article:edit"),
                            ("删除资讯", "edu:article:remove")],
    }
    return pages, buttons


def _migrate_admin_paths(db) -> None:
    """老库升级：把 /users 这类菜单路径统一挪到 /admin 下。"""
    changed = 0
    for menu in db.query(models.Menu).filter(models.Menu.menu_type.in_(("M", "C"))).all():
        path = (menu.path or "").strip()
        if path.startswith("/") and not path.startswith(ADMIN_PREFIX):
            menu.path = ADMIN_PREFIX + path
            changed += 1
    if changed:
        db.commit()
        logger.info("菜单路径迁移完成，共更新 %s 项", changed)


def _hide_legacy_demo(db) -> None:
    """旧版「业务数据」演示模块由教务模块取代：数据保留，但不再出现在导航里。"""
    rows = db.query(models.Menu).filter(
        models.Menu.path == "/admin/biz", models.Menu.visible != 0
    ).all()
    if rows:
        for menu in rows:
            menu.visible = 0
        db.commit()


def _ensure_builtin_menus(db) -> None:
    """幂等补齐内置菜单（含按钮），老库升级后新模块自动出现。"""
    pages, buttons = _menu_spec()
    dir_paths = {spec[5] for spec in pages if spec[5]}
    created: list[models.Menu] = []
    path_to_id: dict[str, int] = {}

    for name, path, icon, sort, perms, parent_path in pages:
        existing = db.query(models.Menu).filter(
            models.Menu.path == path, models.Menu.is_deleted == 0
        ).first()
        if existing:
            path_to_id[path] = existing.id
            continue
        menu_type = "M" if path in dir_paths else "C"
        parent_id = path_to_id.get(parent_path, 0) if parent_path else 0
        component = "" if menu_type == "M" else f"views/admin/{path.rsplit('/', 1)[-1].capitalize()}.vue"
        menu = models.Menu(
            parent_id=parent_id, name=name, menu_type=menu_type, path=path,
            component=component, icon=icon, sort=sort, perms=perms,
        )
        db.add(menu)
        db.flush()
        path_to_id[path] = menu.id
        created.append(menu)

    for parent_path, items in buttons.items():
        parent_id = path_to_id.get(parent_path, 0)
        if not parent_id:
            continue
        for index, (name, perms) in enumerate(items):
            exists = db.query(models.Menu).filter(
                models.Menu.parent_id == parent_id,
                models.Menu.perms == perms,
                models.Menu.is_deleted == 0,
            ).first()
            if exists:
                continue
            menu = models.Menu(parent_id=parent_id, name=name, menu_type="F",
                               perms=perms, sort=index)
            db.add(menu)
            db.flush()
            created.append(menu)

    if created:
        # 新模块默认授权给内置的「普通管理员」角色；其他自定义角色按需在角色管理里勾选
        admin_role = db.query(models.Role).filter(models.Role.name == "admin").first()
        if admin_role:
            for menu in created:
                db.add(models.RoleMenu(role_id=admin_role.id, menu_id=menu.id))
        db.commit()
        logger.info("已补充内置菜单 %s 项", len(created))
    else:
        db.commit()


# ================================================================ 种子数据
def _seed_roles(db) -> None:
    if db.query(models.Role).count() > 0:
        return
    db.add_all([
        models.Role(name="super_admin", code="SUPER_ADMIN", desc="超级管理员"),
        models.Role(name="admin", code="ADMIN", desc="普通管理员"),
        models.Role(name="operator", code="OPERATOR", desc="普通操作员"),
    ])
    db.commit()


def _seed_admin(db) -> None:
    if db.query(models.User).filter(models.User.username == "admin").first():
        return
    password = settings.ADMIN_INITIAL_PASSWORD
    if not password:
        if settings.is_prod:
            logger.warning(
                "生产环境未创建初始 admin：请设置 ADMIN_INITIAL_PASSWORD，"
                "或启动后用 `python -m app.cli create-admin --username admin` 手工创建"
            )
            return
        password = "123456"
    admin = models.User(username="admin", password_hash=hash_password(password),
                        nickname="超级管理员", phone="13800000000", status=1)
    db.add(admin)
    db.commit()
    super_role = db.query(models.Role).filter(models.Role.name == "super_admin").first()
    if super_role:
        db.add(models.UserRole(user_id=admin.id, role_id=super_role.id))
        db.commit()


def _seed_dicts(db) -> None:
    """幂等补齐内置字典。

    按 dict_type 逐个判断，而不是「有任意字典就整体跳过」：老库迁移过来通常只有
    user_status / menu_type / yes_no 三组，升级后要能自动补上课程阶段、报名状态。
    """
    dicts = [
        ("user_status", "用户状态", [("启用", "1", 1), ("禁用", "0", 2)]),
        ("menu_type", "菜单类型", [("目录", "M", 1), ("页面", "C", 2), ("按钮", "F", 3)]),
        ("yes_no", "是否", [("是", "1", 1), ("否", "0", 2)]),
        ("course_level", "课程阶段", [("启蒙", "启蒙", 1), ("入门", "入门", 2),
                                     ("进阶", "进阶", 3), ("竞赛", "竞赛", 4), ("冲刺", "冲刺", 5)]),
        ("enroll_status", "报名状态", [("待跟进", "0", 1), ("已联系", "1", 2),
                                      ("已成交", "2", 3), ("已失效", "3", 4)]),
    ]
    existing = {row[0] for row in db.query(models.DictType.dict_type).all()}
    added = 0
    for dtype, name, items in dicts:
        if dtype in existing:
            continue
        db.add(models.DictType(dict_type=dtype, name=name, remark="系统内置"))
        for label, value, sort in items:
            db.add(models.DictItem(dict_type=dtype, label=label, value=value, sort=sort))
        existing.add(dtype)
        added += 1
    if added:
        db.commit()
        logger.info("已补充内置字典 %s 组", added)


def _seed_edu_demo(db) -> None:
    """教培演示数据：分类、师资、课程、资讯、报名线索（仅在空库时灌入）。"""
    if db.query(models.CourseCategory).count() > 0:
        return

    categories = [
        ("少儿编程", "图形化编程 / Python / 信息学奥赛，6-15 岁", "Monitor", 1),
        ("学科辅导", "语数英同步提升与中考冲刺，小班教学", "Reading", 2),
        ("语言培训", "青少英语、雅思托福、日语入门", "ChatDotRound", 3),
        ("艺术素养", "少儿美术、硬笔书法、播音主持", "Brush", 4),
    ]
    for name, desc, icon, sort in categories:
        db.add(models.CourseCategory(name=name, desc=desc, icon=icon, sort=sort))
    db.commit()

    teachers = [
        ("王思远", "少儿编程教研组长", "前互联网公司后端工程师，8 年编程教学经验，"
                                     "带出 30+ 位信息学奥赛获奖学员。", "信息学奥赛,Python,Scratch", 8, 1),
        ("李静", "英语学科负责人", "剑桥大学 CELTA 认证教师，10 年一线教学，"
                                  "擅长雅思口语与青少英语自然拼读。", "雅思,口语,自然拼读", 10, 2),
        ("陈默", "数学竞赛教练", "省级数学竞赛一等奖指导教师，专注小学思维训练与中考压轴题拆解。",
         "思维训练,中考冲刺", 7, 3),
        ("赵一诺", "少儿美术讲师", "中国美术学院毕业，擅长水彩与创意手工，课堂氛围轻松。",
         "水彩,创意美术", 5, 4),
    ]
    for name, title, intro, tags, years, sort in teachers:
        db.add(models.Teacher(name=name, title=title, intro=intro, tags=tags, years=years, sort=sort))
    db.commit()

    cats = {c.name: c.id for c in db.query(models.CourseCategory).all()}
    teas = {t.name: t.id for t in db.query(models.Teacher).all()}

    courses = [
        dict(title="少儿编程 · Scratch 图形化启蒙班", subtitle="用积木式编程做动画和小游戏",
             category_id=cats["少儿编程"], teacher_id=teas["王思远"], price=1980, original_price=2680,
             lessons=24, duration="12 周 / 每周 2 次", level="启蒙", suitable="6-9 岁零基础",
             tags="小班课,零基础,作品结课", is_recommend=1, sort=1, status=1,
             summary="从零认识编程思维：顺序、循环、条件判断，每节课产出一个可玩的小作品。",
             description="【课程亮点】\n· 每节课都有可运行的小作品，孩子回家能演示给家长看\n"
                         "· 小班 6 人，主讲 + 助教双师，课堂节奏可控\n· 结课产出 3 个完整游戏作品，可用于后续比赛\n\n"
                         "【适合人群】\n6-9 岁、零编程基础、希望通过游戏化方式建立逻辑思维的孩子。\n\n"
                         "【课程大纲】\n第 1-4 周：认识 Scratch 界面与角色、事件与顺序\n"
                         "第 5-8 周：循环、条件判断、变量与分数系统\n第 9-12 周：综合项目《打地鼠》《跑酷小恐龙》"),
        dict(title="少儿编程 · Python 进阶与项目实战", subtitle="从语法到能独立完成的小项目",
             category_id=cats["少儿编程"], teacher_id=teas["王思远"], price=3980, original_price=4980,
             lessons=32, duration="16 周 / 每周 2 次", level="进阶", suitable="10-13 岁，有图形化基础",
             tags="Python,项目制,代码规范", is_recommend=1, sort=2, status=1,
             summary="系统学习 Python 语法与常用库，完成爬虫、小游戏、数据分析三类项目。",
             description="【课程亮点】\n· 真实项目驱动：爬虫抓取、Pygame 小游戏、成绩数据分析\n"
                         "· 每节课有代码 review，养成规范书写习惯\n· 结课可参加等级考试与校内科技节\n\n"
                         "【先修要求】\n完成 Scratch 启蒙或有同等图形化编程基础。"),
        dict(title="信息学奥赛 CSP-J 冲刺集训营", subtitle="面向初赛/复赛的系统集训",
             category_id=cats["少儿编程"], teacher_id=teas["王思远"], price=6800, original_price=8800,
             lessons=48, duration="暑期 6 周集训", level="竞赛", suitable="小学高年级至初二，数学基础扎实",
             tags="CSP-J,算法,集训营", is_recommend=1, sort=3, status=1,
             summary="按考纲拆解 12 大专题，真题精讲配模拟赛，赛前一对一复盘。",
             description="【课程亮点】\n· 12 大专题：枚举、递归、排序、贪心、动态规划入门等\n"
                         "· 每周一次全真模拟赛 + 赛后讲评\n· 赛前一对一复盘，按薄弱项定制训练计划\n\n"
                         "【往届成绩】\n近三年累计 30+ 人次获 CSP-J 一、二等奖。"),
        dict(title="小学数学思维 · 同步培优班", subtitle="校内同步 + 思维拓展双线并行",
             category_id=cats["学科辅导"], teacher_id=teas["陈默"], price=2380, original_price=2980,
             lessons=30, duration="15 周 / 每周 2 次", level="同步", suitable="小学 3-6 年级",
             tags="小班,同步培优,错题本", sort=4, status=1,
             summary="同步校内进度，配套思维拓展题，重点解决「会做但总丢分」的问题。",
             description="【课程亮点】\n· 校内同步 + 每周一道思维拓展，兼顾成绩与能力\n"
                         "· 专属错题本，按知识点归类复盘\n· 每月一次阶段测评，家长可查看学情报告\n\n"
                         "【适合人群】\n校内成绩中等偏上、希望稳步提升并建立解题体系的学生。"),
        dict(title="初中数学 · 中考冲刺一对一", subtitle="按薄弱模块定制冲刺方案",
             category_id=cats["学科辅导"], teacher_id=teas["陈默"], price=7800, original_price=9800,
             lessons=40, duration="20 周 / 每周 2 次", level="冲刺", suitable="初三学生",
             tags="一对一,中考,压轴题", is_recommend=1, sort=5, status=1,
             summary="入学测评定方案，聚焦函数、几何、压轴题三大得分模块。",
             description="【课程亮点】\n· 入学摸底测评，按模块得分率定制课时分配\n"
                         "· 压轴题专项：代数综合、几何辅助线、动点问题\n· 每两周一次模考，动态调整方案\n\n"
                         "【授课形式】\n一对一，每次 90 分钟，可协调周末与晚课时段。"),
        dict(title="青少英语 · 自然拼读与外教口语", subtitle="见词能读，敢开口说",
             category_id=cats["语言培训"], teacher_id=teas["李静"], price=3280, original_price=4280,
             lessons=32, duration="16 周 / 每周 2 次", level="入门", suitable="6-10 岁",
             tags="自然拼读,外教口语,双师", sort=6, status=1,
             summary="自然拼读打底 + 中教夯实 + 外教一对一开口练，解决「背单词难、不敢说」。",
             description="【课程亮点】\n· 自然拼读系统教学，掌握 44 个音与拼读规则\n"
                         "· 每周 1 次外教口语课，真实场景对话\n· 配套家庭磨耳朵计划与打卡小程序\n\n"
                         "【适合人群】\n英语启蒙 1-2 年、能认读字母但拼读与开口较弱的孩子。"),
        dict(title="雅思 6.5 分 · 小班冲刺班", subtitle="听力阅读技巧 + 写作口语批改",
             category_id=cats["语言培训"], teacher_id=teas["李静"], price=8800, original_price=11800,
             lessons=60, duration="10 周 / 每周 6 次", level="冲刺", suitable="目标 6.5 分，四级 500+ 或同等水平",
             tags="雅思,小班,作文批改", is_recommend=1, sort=7, status=1,
             summary="四科分项突破，写作口语逐句批改，考前全真模考与出分复盘。",
             description="【课程亮点】\n· 听力阅读：题型技巧 + 高频同义替换词库\n"
                         "· 写作：大作文思路框架 + 每篇逐句批改\n· 口语：Part1-3 话题库 + 一对一模拟\n\n"
                         "【赠送服务】\n考前全真模考 2 次、出分后一对一复盘 1 次。"),
        dict(title="少儿美术 · 水彩创作营", subtitle="从调色到独立完成一幅作品",
             category_id=cats["艺术素养"], teacher_id=teas["赵一诺"], price=1680, original_price=2280,
             lessons=20, duration="10 周 / 每周 2 次", level="启蒙", suitable="5-12 岁",
             tags="水彩,创意,作品集", sort=8, status=1,
             summary="认识色彩与笔触，结课完成 5 幅可装裱的水彩作品。",
             description="【课程亮点】\n· 每节课一个主题，从临摹到自由创作\n"
                         "· 结课作品可装裱带走，适合作为成长纪念\n· 材料全包，无需自备画具"),
        dict(title="硬笔书法 · 规范书写训练", subtitle="写好作业本上的每一个字",
             category_id=cats["艺术素养"], teacher_id=teas["赵一诺"], price=1280, original_price=1680,
             lessons=18, duration="9 周 / 每周 2 次", level="入门", suitable="小学生及成人零基础",
             tags="硬笔书法,坐姿执笔,卷面分", sort=9, status=0,
             summary="从坐姿执笔到间架结构，改善卷面书写，提升作业与考试卷面分。",
             description="【课程亮点】\n· 从执笔姿势、坐姿纠正开始，避免养成坏习惯\n"
                         "· 按字根拆分讲解结构规律，举一反三\n· 每周作业线上批改，逐字点评"),
    ]
    for item in courses:
        db.add(models.Course(**item))
    db.commit()

    articles = [
        ("2026 春季班课表发布：少儿编程新增 3 个班次", "机构动态",
         "春季班于 3 月 2 日开课，少儿编程新增周六上午与周日下午班次，报名可享早鸟价。",
         "各位家长：\n\n2026 年春季班将于 3 月 2 日正式开课，本季新增安排如下：\n\n"
         "· 少儿编程 Scratch 启蒙班：周六 09:00-10:30（新增）\n"
         "· Python 进阶班：周日 14:00-15:30（新增）\n· CSP-J 冲刺集训营：暑期班 7 月 6 日开营（新增）\n\n"
         "3 月 1 日前完成报名可享早鸟价 9 折，老学员续费额外赠送 2 课时。\n\n"
         "如需试听，可在官网课程页点击「预约试听」，课程顾问会在 24 小时内与你联系。"),
        ("喜报：我校学员在 CSP-J 2025 中斩获 12 个一等奖", "荣誉成果",
         "2025 年信息学奥赛 CSP-J 成绩公布，我校学员共获一等奖 12 人、二等奖 9 人。",
         "2025 年 CSP-J/S 认证成绩已于近日公布，我校学员再创佳绩：\n\n"
         "· 一等奖 12 人（其中 3 人为六年级在读）\n· 二等奖 9 人\n· 晋级复赛 21 人\n\n"
         "感谢王思远老师与教研团队的投入，也感谢家长们的长期配合。\n"
         "2026 年集训营报名通道已开启，名额 20 人，报满即止。"),
        ("家长课堂：如何陪孩子度过编程启蒙期", "家庭教育",
         "不急着看懂代码，先陪孩子把作品讲一遍——三个简单有效的陪伴方法。",
         "很多家长会问：我不懂编程，怎么陪孩子学？其实陪伴的核心不是「教」，而是「回应」。\n\n"
         "一、让孩子当老师\n每节课后请孩子把作品演示一遍并讲给你听，讲清楚「哪里最难」比写出代码更重要。\n\n"
         "二、关注过程而不是结果\n把「你怎么又错了」换成「这一步你是怎么想的」，孩子才愿意继续试错。\n\n"
         "三、固定 20 分钟练习时间\n编程是熟练度活，每周固定两次 20 分钟的自主练习，比周末突击 2 小时更有效。\n\n"
         "如果孩子连续两周抗拒上课，先别急着换课，和主讲老师聊一次往往能找到原因。"),
    ]
    base = datetime.now()
    for index, (title, category, summary, content) in enumerate(articles):
        db.add(models.Article(
            title=title, category=category, summary=summary, content=content,
            published_at=datetime(base.year, base.month, base.day) - timedelta(days=index * 3),
        ))
    db.commit()

    course_by_title = {c.title: c.id for c in db.query(models.Course).all()}
    enrollments = [
        ("少儿编程 · Scratch 图形化启蒙班", "周女士", "13800001111", "7 岁", "试听", 0,
         "孩子对游戏感兴趣，想先试听一节看看"),
        ("初中数学 · 中考冲刺一对一", "李先生", "13900002222", "15 岁", "官网", 1,
         "已电话沟通，约定周六到校做摸底测评"),
        ("雅思 6.5 分 · 小班冲刺班", "王同学", "13700003333", "21 岁", "活动", 2,
         "已报名缴费，3 月开班"),
    ]
    for title, name, phone, age, source, status, remark in enrollments:
        db.add(models.Enrollment(
            course_id=course_by_title.get(title, 0),
            course_title=title,
            name=name, phone=phone, age=age, source=source, status=status, remark=remark,
        ))
    db.commit()


def _seed_base() -> None:
    """基础数据：角色、admin、内置菜单、字典（幂等，生产也保留）。"""
    db = SessionLocal()
    try:
        _seed_roles(db)
        _seed_admin(db)
        _migrate_admin_paths(db)
        _ensure_builtin_menus(db)
        _hide_legacy_demo(db)
        _seed_dicts(db)
    finally:
        db.close()
    # 菜单结构变化后清空缓存，保证下次请求重建
    redis_client.redis_set("cache:menus:ver", uuid.uuid4().hex, ex=86400 * 30)


def _seed_demo() -> None:
    """教培演示数据：仅开发 / 演示环境开启（生产用真实数据）。"""
    db = SessionLocal()
    try:
        _seed_edu_demo(db)
    finally:
        db.close()


def _seed() -> None:
    """按开关执行种子数据；生产默认只跑基础数据，不灌演示内容。"""
    if settings.SEED_BASE_DATA:
        _seed_base()
    if settings.seed_demo_data:
        _seed_demo()


def _bootstrap_database() -> None:
    """启动时的建表 / 迁移校验。

    - dev / test：没跑迁移也能直接 create_all，降低本地启动门槛；
    - prod：不自动改表，要求部署流程先执行 `alembic upgrade head`（容器 entrypoint 已内置），
      这里只做一次「版本表是否存在」的兜底检查，缺表直接启动失败。
    """
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)
        logger.info("已按 models 自动建表（APP_ENV=%s）", settings.APP_ENV)
        return
    with engine.connect() as conn:
        version = conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).scalar()
    if not version:
        raise RuntimeError("数据库没有 Alembic 版本记录，请先执行 `alembic upgrade head`")
    logger.info("数据库迁移版本：%s", version)


# ================================================================ 应用
@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        _bootstrap_database()
        _seed()
    except Exception as exc:
        if settings.is_prod:
            logger.exception("数据库初始化失败，生产环境拒绝启动：%s", exc)
            raise
        # 开发环境数据库不可用时仍允许启动，便于打开 /api/health 排查
        logger.exception("数据库初始化失败：%s", exc)
    try:
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    except OSError as exc:
        logger.warning("上传目录不可用（%s）：%s", settings.UPLOAD_DIR, exc)
    logger.info("%s 启动完成（env=%s, api=%s）", settings.APP_NAME, settings.APP_ENV, settings.APP_VERSION)
    yield
    logger.info("%s 已停止", settings.APP_NAME)


_docs_enabled = settings.docs_enabled
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/api/docs" if _docs_enabled else None,
    redoc_url=None,
    openapi_url="/api/openapi.json" if _docs_enabled else None,
    lifespan=lifespan,
)

_cors_origins = settings.cors_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    # 浏览器规范：allow_origins=* 与 allow_credentials 不能同时为真
    allow_credentials="*" not in _cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

if settings.TRUSTED_HOSTS.strip() != "*":
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)

app.add_middleware(GZipMiddleware, minimum_size=800)

# 上传目录在启动前就绪，路由挂载放在模块级，避免启动后再 mount 带来的竞态
try:
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
except OSError:
    pass
if os.path.isdir(settings.UPLOAD_DIR):
    app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")


@app.middleware("http")
async def rate_limit_mw(request: Request, call_next):
    path = request.url.path
    if (settings.RATE_LIMIT_ENABLED and request.method in ("POST", "PUT", "DELETE")
            and path.startswith("/api")):
        ip = request.client.host if request.client else "unknown"
        if path in ("/api/auth/login", "/api/site/auth/login"):
            key = "site_login" if path.startswith("/api/site") else "login"
            allowed = allow(f"{key}:{ip}", 10, 60)
        elif path == "/api/site/auth/register":
            allowed = allow(f"register:{ip}", 5, 60)
        elif path == "/api/site/enroll":
            allowed = allow(f"enroll:{ip}", 8, 60)
        else:
            allowed = allow(f"{ip}:{request.method}:{path}", 60, 60)
        if not allowed:
            return JSONResponse({"code": 429, "msg": "请求过于频繁，请稍后再试", "data": None},
                                status_code=200)
    return await call_next(request)


# ---------------------------------------------------------------- 操作日志安全网
_MODULE_MAP = [
    ("/api/site/auth", "前台账号"),
    ("/api/site/me", "前台账号"),
    ("/api/site", "前台官网"),
    ("/api/dashboard", "首页看板"),
    ("/api/users", "用户管理"),
    ("/api/roles", "角色管理"),
    ("/api/menus", "菜单管理"),
    ("/api/dict", "数据字典"),
    ("/api/logs", "操作日志"),
    ("/api/course-categories", "课程分类"),
    ("/api/courses", "课程管理"),
    ("/api/teachers", "师资管理"),
    ("/api/enrollments", "报名线索"),
    ("/api/articles", "资讯管理"),
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
            is_site = path.startswith("/api/site")
            auth = request.headers.get("authorization", "")
            if auth.lower().startswith("bearer "):
                # 前台学员与后台管理员分开解析：学员 Token 不占用 sys_oper_log.user_id
                uid_s = decode_token(auth[7:], scope=SITE_SCOPE if is_site else ADMIN_SCOPE)
                if uid_s:
                    try:
                        uid_int = int(uid_s)
                        db = SessionLocal()
                        try:
                            if is_site:
                                su = db.query(models.SiteUser).filter(
                                    models.SiteUser.id == uid_int
                                ).first()
                                username = su.username if su else ""
                            else:
                                uid = uid_int
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


# 注册在最外层：先分配 request id，再让限流 / 操作日志 / 业务路由感知同一条链路
app.add_middleware(ObservabilityMiddleware)


@app.exception_handler(StarletteHTTPException)
async def http_exc(req: Request, exc: StarletteHTTPException):
    return JSONResponse(
        {"code": exc.status_code, "msg": exc.detail, "data": None, "request_id": request_id_ctx.get()},
        status_code=200,
    )


@app.exception_handler(RequestValidationError)
async def validation_exc(req: Request, exc: RequestValidationError):
    """把 Pydantic 校验错误转成统一返回体，前端可直接展示中文提示。"""
    detail = "参数校验失败"
    errors = exc.errors()
    if errors:
        first = errors[0]
        loc = ".".join(
            str(x) for x in first.get("loc", ())
            if x not in ("body", "query", "path", "header")
        )
        msg = str(first.get("msg", "参数错误"))
        msg = msg.replace("Value error, ", "").replace("Assertion failed, ", "")
        detail = f"{loc}: {msg}" if loc else msg
    return JSONResponse(
        {"code": 400, "msg": detail, "data": None, "request_id": request_id_ctx.get()},
        status_code=200,
    )


@app.exception_handler(Exception)
async def global_exc(req: Request, exc: Exception):
    logger.exception("未处理异常 %s %s", req.method, req.url.path)
    return JSONResponse(
        {"code": 500, "msg": "系统异常，请稍后重试", "data": None, "request_id": request_id_ctx.get()},
        status_code=200,
    )


app.include_router(system_router, prefix="/api")
app.include_router(edu_router, prefix="/api")
app.include_router(site_router, prefix="/api")


_STARTED_AT = time.time()


@app.get("/api/health")
def health():
    """存活探针：不依赖任何外部组件，进程能响应即 200。"""
    return {
        "code": 200,
        "msg": "ok",
        "data": {
            "status": "ok",
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "env": settings.APP_ENV,
            "uptime": int(time.time() - _STARTED_AT),
        },
    }


@app.get("/api/ready")
def ready():
    """就绪探针：检查数据库（及可选的 Redis），失败返回 503，供编排系统摘流量。"""
    db_ok = False
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception as exc:
        logger.error("就绪检查：数据库不可用 %s", exc)

    cache_mode = "memory"
    redis_ok: bool | None = None
    if settings.REDIS_REQUIRED:
        redis_ok = redis_client.ping()
        cache_mode = "redis" if redis_ok else "unavailable"
    else:
        cache_mode = "redis" if redis_client.available() else "memory"

    DB_UP.set(1 if db_ok else 0)
    REDIS_UP.set(1 if redis_client.available() else 0)
    healthy = db_ok and (redis_ok is not False)
    payload = {
        "code": 200 if healthy else 503,
        "msg": "ready" if healthy else "not_ready",
        "data": {"database": db_ok, "cache": cache_mode, "env": settings.APP_ENV},
    }
    return JSONResponse(payload, status_code=200 if healthy else 503)


@app.get("/metrics", include_in_schema=False)
def metrics():
    """Prometheus 抓取端点；生产建议只在内网 / 反代层放行。"""
    if not settings.METRICS_ENABLED:
        return Response(status_code=404)
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
