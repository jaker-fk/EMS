"""add front-site student accounts

Revision ID: 0003_site_accounts
Revises: 0002_query_indexes
Create Date: 2026-11-16 11:30:00

前台学员账号落在独立表 ``site_user``，与后台 ``sys_user`` 完全隔离；
``edu_enrollment`` 增加 ``site_user_id`` 以支持「我的报名」按账号查询。
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0003_site_accounts"
down_revision: str | None = "0002_query_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _table_names() -> set[str]:
    return set(inspect(op.get_bind()).get_table_names())


def _column_names(table: str) -> set[str]:
    return {column["name"] for column in inspect(op.get_bind()).get_columns(table)}


def _index_names(table: str) -> set[str]:
    return {index["name"] for index in inspect(op.get_bind()).get_indexes(table)}


def upgrade() -> None:
    # 兼容「开发环境 create_all 已经建过表 / 索引」的数据库，重复执行不会报错
    if "site_user" not in _table_names():
        op.create_table(
            "site_user",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("username", sa.String(length=32), nullable=False),
            sa.Column("password_hash", sa.String(length=255), nullable=False),
            sa.Column("nickname", sa.String(length=64), nullable=True),
            sa.Column("phone", sa.String(length=20), nullable=True),
            sa.Column("status", sa.SmallInteger(), nullable=True),
            sa.Column("is_deleted", sa.SmallInteger(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("update_time", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
    if "ix_site_user_username" not in _index_names("site_user"):
        op.create_index(op.f("ix_site_user_username"), "site_user", ["username"], unique=True)
    if "ix_site_user_phone" not in _index_names("site_user"):
        op.create_index(op.f("ix_site_user_phone"), "site_user", ["phone"], unique=False)

    if "site_user_id" not in _column_names("edu_enrollment"):
        op.add_column(
            "edu_enrollment",
            sa.Column("site_user_id", sa.Integer(), nullable=True),
        )
    if "ix_edu_enrollment_site_user_id" not in _index_names("edu_enrollment"):
        op.create_index(
            op.f("ix_edu_enrollment_site_user_id"), "edu_enrollment", ["site_user_id"], unique=False
        )


def downgrade() -> None:
    if "ix_edu_enrollment_site_user_id" in _index_names("edu_enrollment"):
        op.drop_index(op.f("ix_edu_enrollment_site_user_id"), table_name="edu_enrollment")
    if "site_user_id" in _column_names("edu_enrollment"):
        with op.batch_alter_table("edu_enrollment") as batch:
            batch.drop_column("site_user_id")
    if "site_user" in _table_names():
        # 索引随表一起删除
        op.drop_table("site_user")
