import re
from typing import Optional

from pydantic import BaseModel, Field, field_validator

USERNAME_RE = re.compile(r"^[A-Za-z0-9_.\-]{3,64}$")
PHONE_RE = re.compile(r"^[0-9+\-\s]{6,20}$")


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)
    captcha_key: str = ""
    captcha_code: str = ""


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=128)
    nickname: str = Field(default="", max_length=64)
    phone: str = Field(default="", max_length=20)
    status: int = Field(default=1, ge=0, le=1)
    role_ids: list[int] = Field(default_factory=list)

    @field_validator("username")
    @classmethod
    def _check_username(cls, v: str) -> str:
        if not USERNAME_RE.match(v):
            raise ValueError("账号只能包含字母、数字、下划线、点或短横线，长度 3-64")
        return v

    @field_validator("phone")
    @classmethod
    def _check_phone(cls, v: str) -> str:
        if v and not PHONE_RE.match(v):
            raise ValueError("手机号格式不正确")
        return v


class UserUpdate(BaseModel):
    nickname: Optional[str] = Field(default=None, max_length=64)
    phone: Optional[str] = Field(default=None, max_length=20)
    status: Optional[int] = Field(default=None, ge=0, le=1)
    role_ids: Optional[list[int]] = None

    @field_validator("phone")
    @classmethod
    def _check_phone(cls, v: Optional[str]) -> Optional[str]:
        if v and not PHONE_RE.match(v):
            raise ValueError("手机号格式不正确")
        return v


class BatchStatusIn(BaseModel):
    ids: list[int] = Field(default_factory=list)
    status: int = Field(ge=0, le=1)


class ResetPwdIn(BaseModel):
    password: str = Field(min_length=8, max_length=128)


class ChangePwdIn(BaseModel):
    old_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class ProfileUpdate(BaseModel):
    nickname: Optional[str] = Field(default=None, max_length=64)
    phone: Optional[str] = Field(default=None, max_length=20)

    @field_validator("phone")
    @classmethod
    def _check_phone(cls, v: Optional[str]) -> Optional[str]:
        if v and not PHONE_RE.match(v):
            raise ValueError("手机号格式不正确")
        return v


class RoleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    code: str = Field(default="", max_length=64)
    desc: str = Field(default="", max_length=255)
    status: int = Field(default=1, ge=0, le=1)
    menu_ids: list[int] = Field(default_factory=list)


class MenuCreate(BaseModel):
    parent_id: int = 0
    name: str = Field(min_length=1, max_length=64)
    menu_type: str = "C"
    path: str = Field(default="", max_length=128)
    component: str = Field(default="", max_length=128)
    perms: str = Field(default="", max_length=128)
    icon: str = Field(default="", max_length=64)
    sort: int = 0
    visible: int = Field(default=1, ge=0, le=1)

    @field_validator("menu_type")
    @classmethod
    def _check_type(cls, v: str) -> str:
        if v not in ("M", "C", "F"):
            raise ValueError("菜单类型只能是 M / C / F")
        return v


class DictTypeCreate(BaseModel):
    dict_type: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=64)
    status: int = Field(default=1, ge=0, le=1)
    remark: str = Field(default="", max_length=255)


class DictItemCreate(BaseModel):
    dict_type: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=64)
    value: str = Field(min_length=1, max_length=64)
    sort: int = 0
    status: int = Field(default=1, ge=0, le=1)
    remark: str = Field(default="", max_length=255)


class BizCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    category: str = Field(default="", max_length=64)
    price: int = Field(default=0, ge=0)
    remark: str = Field(default="", max_length=255)


# ---------------------------------------------------------------- 教培业务
class CategoryIn(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    desc: str = Field(default="", max_length=255)
    icon: str = Field(default="", max_length=64)
    sort: int = 0
    status: int = Field(default=1, ge=0, le=1)


class TeacherIn(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    title: str = Field(default="", max_length=64)
    avatar: str = Field(default="", max_length=512)
    intro: str = Field(default="", max_length=2000)
    tags: str = Field(default="", max_length=255)
    years: int = Field(default=0, ge=0, le=60)
    sort: int = 0
    status: int = Field(default=1, ge=0, le=1)


class CourseIn(BaseModel):
    title: str = Field(min_length=1, max_length=128)
    subtitle: str = Field(default="", max_length=255)
    cover: str = Field(default="", max_length=512)
    summary: str = Field(default="", max_length=500)
    description: str = Field(default="", max_length=20000)
    category_id: int = 0
    teacher_id: int = 0
    price: int = Field(default=0, ge=0)
    original_price: int = Field(default=0, ge=0)
    lessons: int = Field(default=0, ge=0)
    duration: str = Field(default="", max_length=64)
    level: str = Field(default="", max_length=32)
    suitable: str = Field(default="", max_length=255)
    tags: str = Field(default="", max_length=255)
    status: int = Field(default=0, ge=0, le=1)
    is_recommend: int = Field(default=0, ge=0, le=1)
    sort: int = 0


class CourseStatusIn(BaseModel):
    status: int = Field(ge=0, le=1)


class ArticleIn(BaseModel):
    title: str = Field(min_length=1, max_length=128)
    category: str = Field(default="机构动态", max_length=32)
    cover: str = Field(default="", max_length=512)
    summary: str = Field(default="", max_length=500)
    content: str = Field(default="", max_length=20000)
    status: int = Field(default=1, ge=0, le=1)


class EnrollIn(BaseModel):
    """前台报名 / 预约试听"""

    course_id: int = 0
    name: str = Field(min_length=1, max_length=32)
    phone: str = Field(min_length=6, max_length=20)
    age: str = Field(default="", max_length=16)
    source: str = Field(default="官网", max_length=32)
    remark: str = Field(default="", max_length=500)

    @field_validator("phone")
    @classmethod
    def _check_phone(cls, v: str) -> str:
        if not PHONE_RE.match(v):
            raise ValueError("请填写正确的手机号")
        return v


class EnrollmentUpdate(BaseModel):
    status: int = Field(ge=0, le=3)
    remark: Optional[str] = Field(default=None, max_length=500)


# ---------------------------------------------------------------- 前台学员账号
class SiteRegisterIn(BaseModel):
    """前台注册：账号 + 密码 + 手机号（手机号用于匹配历史报名线索）。"""

    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8, max_length=128)
    nickname: str = Field(default="", max_length=64)
    phone: str = Field(min_length=6, max_length=20)

    @field_validator("username")
    @classmethod
    def _check_username(cls, v: str) -> str:
        # 前台账号与后台账号共用同一套字符规则，避免出现无法输入 / 易混淆的账号
        if not USERNAME_RE.match(v):
            raise ValueError("账号只能包含字母、数字、下划线、点或短横线，长度 3-32")
        return v

    @field_validator("phone")
    @classmethod
    def _check_phone(cls, v: str) -> str:
        if not PHONE_RE.match(v):
            raise ValueError("请填写正确的手机号")
        return v


class SiteLoginIn(BaseModel):
    """前台登录：账号或手机号 + 密码。"""

    account: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class SiteProfileUpdate(BaseModel):
    nickname: Optional[str] = Field(default=None, max_length=64)
    phone: Optional[str] = Field(default=None, max_length=20)

    @field_validator("phone")
    @classmethod
    def _check_phone(cls, v: Optional[str]) -> Optional[str]:
        if v and not PHONE_RE.match(v):
            raise ValueError("手机号格式不正确")
        return v


class SiteChangePwdIn(BaseModel):
    old_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)

