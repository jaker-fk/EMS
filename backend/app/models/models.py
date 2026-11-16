from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, SmallInteger, String, Text

from app.core.database import Base


class User(Base):
    __tablename__ = "sys_user"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    nickname = Column(String(64), default="")
    phone = Column(String(20), default="")
    status = Column(SmallInteger, default=1)  # 1启用 0禁用
    is_deleted = Column(SmallInteger, default=0)  # 逻辑删除
    created_at = Column(DateTime, default=datetime.now)
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class Role(Base):
    __tablename__ = "sys_role"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), unique=True, nullable=False)
    code = Column(String(64), default="")
    desc = Column(String(255), default="")
    status = Column(SmallInteger, default=1)
    is_deleted = Column(SmallInteger, default=0)
    created_at = Column(DateTime, default=datetime.now)
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class UserRole(Base):
    __tablename__ = "sys_user_role"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("sys_user.id"), nullable=False)
    role_id = Column(Integer, ForeignKey("sys_role.id"), nullable=False)


class Menu(Base):
    __tablename__ = "sys_menu"
    id = Column(Integer, primary_key=True, autoincrement=True)
    parent_id = Column(Integer, default=0)
    name = Column(String(64), nullable=False)
    menu_type = Column(String(1), default="C")  # M目录 / C页面 / F按钮
    path = Column(String(128), default="")
    component = Column(String(128), default="")
    perms = Column(String(128), default="")  # 权限标识 如 system:user:list
    icon = Column(String(64), default="")
    sort = Column(Integer, default=0)
    visible = Column(SmallInteger, default=1)
    is_deleted = Column(SmallInteger, default=0)
    created_at = Column(DateTime, default=datetime.now)


class RoleMenu(Base):
    __tablename__ = "sys_role_menu"
    id = Column(Integer, primary_key=True, autoincrement=True)
    role_id = Column(Integer, ForeignKey("sys_role.id"), nullable=False)
    menu_id = Column(Integer, ForeignKey("sys_menu.id"), nullable=False)


class DictType(Base):
    __tablename__ = "sys_dict_type"
    id = Column(Integer, primary_key=True, autoincrement=True)
    dict_type = Column(String(64), unique=True, nullable=False)  # 如 user_status
    name = Column(String(64), nullable=False)
    status = Column(SmallInteger, default=1)
    remark = Column(String(255), default="")
    created_at = Column(DateTime, default=datetime.now)


class DictItem(Base):
    __tablename__ = "sys_dict_item"
    id = Column(Integer, primary_key=True, autoincrement=True)
    dict_type = Column(String(64), nullable=False, index=True)
    label = Column(String(64), nullable=False)
    value = Column(String(64), nullable=False)
    sort = Column(Integer, default=0)
    status = Column(SmallInteger, default=1)
    remark = Column(String(255), default="")
    created_at = Column(DateTime, default=datetime.now)


class OperationLog(Base):
    __tablename__ = "sys_oper_log"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=True)
    username = Column(String(64), default="")
    module = Column(String(64), default="")
    action = Column(String(32), default="")  # 新增/修改/删除/登录/导出
    method = Column(String(8), default="")
    path = Column(String(255), default="")
    ip = Column(String(64), default="")
    params = Column(Text, default="")
    result = Column(String(16), default="成功")
    created_at = Column(DateTime, default=datetime.now, index=True)


class BusinessData(Base):
    __tablename__ = "biz_data"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    category = Column(String(64), default="")
    price = Column(Integer, default=0)
    remark = Column(String(255), default="")
    created_at = Column(DateTime, default=datetime.now)


class FileRecord(Base):
    __tablename__ = "sys_file"
    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255), nullable=False)
    filepath = Column(String(512), nullable=False)
    size = Column(Integer, default=0)
    uploader = Column(String(64), default="")
    created_at = Column(DateTime, default=datetime.now)


# ================================================================ 前台学员账号
class SiteUser(Base):
    """前台学员账号：与后台 sys_user 完全隔离。

    只用于官网登录、报名进度查询与资料维护；即使被创建也没有任何管理端菜单 /
    接口权限。后台账号同理不能登录前台学员中心（靠 Token scope 区分）。
    """

    __tablename__ = "site_user"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(32), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    nickname = Column(String(64), default="")
    phone = Column(String(20), default="", index=True)
    status = Column(SmallInteger, default=1)  # 1启用 0禁用
    is_deleted = Column(SmallInteger, default=0)
    created_at = Column(DateTime, default=datetime.now)
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)


# ================================================================ 教培业务
class CourseCategory(Base):
    """课程分类：少儿编程 / 学科辅导 / 语言培训 ..."""

    __tablename__ = "edu_category"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False)
    desc = Column(String(255), default="")
    icon = Column(String(64), default="")
    sort = Column(Integer, default=0)
    status = Column(SmallInteger, default=1)  # 1启用 0停用
    is_deleted = Column(SmallInteger, default=0)
    created_at = Column(DateTime, default=datetime.now)


class Teacher(Base):
    """师资团队"""

    __tablename__ = "edu_teacher"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False)
    title = Column(String(64), default="")  # 头衔，如「高级讲师 / 前大厂工程师」
    avatar = Column(String(512), default="")
    intro = Column(Text)  # 讲师简介
    tags = Column(String(255), default="")  # 逗号分隔的标签
    years = Column(Integer, default=0)  # 教龄
    sort = Column(Integer, default=0)
    status = Column(SmallInteger, default=1)
    is_deleted = Column(SmallInteger, default=0)
    created_at = Column(DateTime, default=datetime.now)


class Course(Base):
    """课程（前台展示的核心内容，后台可上架 / 下架）"""

    __tablename__ = "edu_course"
    id = Column(Integer, primary_key=True, autoincrement=True)
    category_id = Column(Integer, default=0, index=True)
    teacher_id = Column(Integer, default=0, index=True)
    title = Column(String(128), nullable=False)
    subtitle = Column(String(255), default="")
    cover = Column(String(512), default="")
    summary = Column(String(500), default="")  # 列表页摘要
    description = Column(Text)  # 详情页富文本（纯文本 / 简单 HTML）
    price = Column(Integer, default=0)  # 现价（元）
    original_price = Column(Integer, default=0)  # 原价（元）
    lessons = Column(Integer, default=0)  # 课时数
    duration = Column(String(64), default="")  # 上课周期，如「16 周 / 每周 2 次」
    level = Column(String(32), default="")  # 适合阶段
    suitable = Column(String(255), default="")  # 适合人群
    tags = Column(String(255), default="")
    status = Column(SmallInteger, default=0, index=True)  # 0 未上架 / 1 已上架
    is_recommend = Column(SmallInteger, default=0)  # 首页推荐
    sort = Column(Integer, default=0)
    view_count = Column(Integer, default=0)
    is_deleted = Column(SmallInteger, default=0)
    created_at = Column(DateTime, default=datetime.now)
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class Enrollment(Base):
    """报名 / 试听线索：前台提交后进入后台跟进池"""

    __tablename__ = "edu_enrollment"
    id = Column(Integer, primary_key=True, autoincrement=True)
    course_id = Column(Integer, default=0, index=True)
    course_title = Column(String(128), default="")  # 快照，课程改名后仍可追溯
    site_user_id = Column(Integer, default=0, index=True)  # 提交人（前台账号），0 = 游客提交
    name = Column(String(64), nullable=False)
    phone = Column(String(20), nullable=False, index=True)
    age = Column(String(16), default="")
    source = Column(String(32), default="官网")  # 官网 / 试听 / 活动
    status = Column(SmallInteger, default=0, index=True)  # 0 待跟进 / 1 已联系 / 2 已成交 / 3 已失效
    remark = Column(String(500), default="")
    created_at = Column(DateTime, default=datetime.now)
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class Article(Base):
    """机构资讯 / 公告"""

    __tablename__ = "edu_article"
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(128), nullable=False)
    category = Column(String(32), default="机构动态")
    cover = Column(String(512), default="")
    summary = Column(String(500), default="")
    content = Column(Text)
    status = Column(SmallInteger, default=1)  # 1发布 0隐藏
    is_deleted = Column(SmallInteger, default=0)
    published_at = Column(DateTime, default=datetime.now)
    created_at = Column(DateTime, default=datetime.now)
