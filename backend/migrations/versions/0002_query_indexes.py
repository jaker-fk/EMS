"""add query indexes

Revision ID: 0002_query_indexes
Revises: 0001_initial
Create Date: 2026-11-12 15:20:00
"""
from collections.abc import Sequence

from alembic import op
from sqlalchemy import inspect

revision: str = "0002_query_indexes"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _existing_indexes(table: str) -> set[str]:
    return {index["name"] for index in inspect(op.get_bind()).get_indexes(table)}


def _create_index_if_missing(index_name: str, table: str, columns: list[str]) -> None:
    # 兼容「开发环境 create_all 已经建过索引」的数据库，避免升级时报 Duplicate key name
    if index_name not in _existing_indexes(table):
        op.create_index(op.f(index_name), table, columns, unique=False)


def upgrade() -> None:
    # 看板按天聚合操作日志、前台/后台按状态筛课程与报名线索，这三个字段需要索引
    _create_index_if_missing("ix_sys_oper_log_created_at", "sys_oper_log", ["created_at"])
    _create_index_if_missing("ix_edu_course_status", "edu_course", ["status"])
    _create_index_if_missing("ix_edu_enrollment_status", "edu_enrollment", ["status"])


def downgrade() -> None:
    # 只删除本迁移负责的索引；若索引不存在则跳过
    for index_name, table in (
        ("ix_edu_enrollment_status", "edu_enrollment"),
        ("ix_edu_course_status", "edu_course"),
        ("ix_sys_oper_log_created_at", "sys_oper_log"),
    ):
        if index_name in _existing_indexes(table):
            op.drop_index(op.f(index_name), table_name=table)
