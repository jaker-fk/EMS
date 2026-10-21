from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, SmallInteger
from datetime import datetime

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
    created_at = Column(DateTime, default=datetime.now)


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
