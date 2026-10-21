from typing import Optional
from pydantic import BaseModel, Field


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)
    captcha_key: str = ""
    captcha_code: str = ""


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    nickname: str = ""
    phone: str = ""
    status: int = 1
    role_ids: list[int] = []


class UserUpdate(BaseModel):
    nickname: Optional[str] = None
    phone: Optional[str] = None
    status: Optional[int] = None
    role_ids: Optional[list[int]] = None


class ResetPwdIn(BaseModel):
    password: str = Field(min_length=6, max_length=128)


class ChangePwdIn(BaseModel):
    old_password: str
    new_password: str = Field(min_length=6, max_length=128)


class RoleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    code: str = ""
    desc: str = ""
    status: int = 1
    menu_ids: list[int] = []


class MenuCreate(BaseModel):
    parent_id: int = 0
    name: str = Field(min_length=1, max_length=64)
    menu_type: str = "C"
    path: str = ""
    component: str = ""
    perms: str = ""
    icon: str = ""
    sort: int = 0
    visible: int = 1


class DictTypeCreate(BaseModel):
    dict_type: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=64)
    status: int = 1
    remark: str = ""


class DictItemCreate(BaseModel):
    dict_type: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=64)
    value: str = Field(min_length=1, max_length=64)
    sort: int = 0
    status: int = 1
    remark: str = ""


class BizCreate(BaseModel):
    name: str
    category: str = ""
    price: int = 0
    remark: str = ""
