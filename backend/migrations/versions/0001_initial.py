"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-12 15:17:06
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('biz_data',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('name', sa.String(length=128), nullable=False),
    sa.Column('category', sa.String(length=64), nullable=True),
    sa.Column('price', sa.Integer(), nullable=True),
    sa.Column('remark', sa.String(length=255), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('edu_article',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('title', sa.String(length=128), nullable=False),
    sa.Column('category', sa.String(length=32), nullable=True),
    sa.Column('cover', sa.String(length=512), nullable=True),
    sa.Column('summary', sa.String(length=500), nullable=True),
    sa.Column('content', sa.Text(), nullable=True),
    sa.Column('status', sa.SmallInteger(), nullable=True),
    sa.Column('is_deleted', sa.SmallInteger(), nullable=True),
    sa.Column('published_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('edu_category',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('name', sa.String(length=64), nullable=False),
    sa.Column('desc', sa.String(length=255), nullable=True),
    sa.Column('icon', sa.String(length=64), nullable=True),
    sa.Column('sort', sa.Integer(), nullable=True),
    sa.Column('status', sa.SmallInteger(), nullable=True),
    sa.Column('is_deleted', sa.SmallInteger(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('edu_course',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('category_id', sa.Integer(), nullable=True),
    sa.Column('teacher_id', sa.Integer(), nullable=True),
    sa.Column('title', sa.String(length=128), nullable=False),
    sa.Column('subtitle', sa.String(length=255), nullable=True),
    sa.Column('cover', sa.String(length=512), nullable=True),
    sa.Column('summary', sa.String(length=500), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('price', sa.Integer(), nullable=True),
    sa.Column('original_price', sa.Integer(), nullable=True),
    sa.Column('lessons', sa.Integer(), nullable=True),
    sa.Column('duration', sa.String(length=64), nullable=True),
    sa.Column('level', sa.String(length=32), nullable=True),
    sa.Column('suitable', sa.String(length=255), nullable=True),
    sa.Column('tags', sa.String(length=255), nullable=True),
    sa.Column('status', sa.SmallInteger(), nullable=True),
    sa.Column('is_recommend', sa.SmallInteger(), nullable=True),
    sa.Column('sort', sa.Integer(), nullable=True),
    sa.Column('view_count', sa.Integer(), nullable=True),
    sa.Column('is_deleted', sa.SmallInteger(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('update_time', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_edu_course_category_id'), 'edu_course', ['category_id'], unique=False)
    op.create_index(op.f('ix_edu_course_teacher_id'), 'edu_course', ['teacher_id'], unique=False)
    op.create_table('edu_enrollment',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('course_id', sa.Integer(), nullable=True),
    sa.Column('course_title', sa.String(length=128), nullable=True),
    sa.Column('name', sa.String(length=64), nullable=False),
    sa.Column('phone', sa.String(length=20), nullable=False),
    sa.Column('age', sa.String(length=16), nullable=True),
    sa.Column('source', sa.String(length=32), nullable=True),
    sa.Column('status', sa.SmallInteger(), nullable=True),
    sa.Column('remark', sa.String(length=500), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('update_time', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_edu_enrollment_course_id'), 'edu_enrollment', ['course_id'], unique=False)
    op.create_index(op.f('ix_edu_enrollment_phone'), 'edu_enrollment', ['phone'], unique=False)
    op.create_table('edu_teacher',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('name', sa.String(length=64), nullable=False),
    sa.Column('title', sa.String(length=64), nullable=True),
    sa.Column('avatar', sa.String(length=512), nullable=True),
    sa.Column('intro', sa.Text(), nullable=True),
    sa.Column('tags', sa.String(length=255), nullable=True),
    sa.Column('years', sa.Integer(), nullable=True),
    sa.Column('sort', sa.Integer(), nullable=True),
    sa.Column('status', sa.SmallInteger(), nullable=True),
    sa.Column('is_deleted', sa.SmallInteger(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('sys_dict_item',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('dict_type', sa.String(length=64), nullable=False),
    sa.Column('label', sa.String(length=64), nullable=False),
    sa.Column('value', sa.String(length=64), nullable=False),
    sa.Column('sort', sa.Integer(), nullable=True),
    sa.Column('status', sa.SmallInteger(), nullable=True),
    sa.Column('remark', sa.String(length=255), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sys_dict_item_dict_type'), 'sys_dict_item', ['dict_type'], unique=False)
    op.create_table('sys_dict_type',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('dict_type', sa.String(length=64), nullable=False),
    sa.Column('name', sa.String(length=64), nullable=False),
    sa.Column('status', sa.SmallInteger(), nullable=True),
    sa.Column('remark', sa.String(length=255), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('dict_type')
    )
    op.create_table('sys_file',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('filename', sa.String(length=255), nullable=False),
    sa.Column('filepath', sa.String(length=512), nullable=False),
    sa.Column('size', sa.Integer(), nullable=True),
    sa.Column('uploader', sa.String(length=64), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('sys_menu',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('parent_id', sa.Integer(), nullable=True),
    sa.Column('name', sa.String(length=64), nullable=False),
    sa.Column('menu_type', sa.String(length=1), nullable=True),
    sa.Column('path', sa.String(length=128), nullable=True),
    sa.Column('component', sa.String(length=128), nullable=True),
    sa.Column('perms', sa.String(length=128), nullable=True),
    sa.Column('icon', sa.String(length=64), nullable=True),
    sa.Column('sort', sa.Integer(), nullable=True),
    sa.Column('visible', sa.SmallInteger(), nullable=True),
    sa.Column('is_deleted', sa.SmallInteger(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('sys_oper_log',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('username', sa.String(length=64), nullable=True),
    sa.Column('module', sa.String(length=64), nullable=True),
    sa.Column('action', sa.String(length=32), nullable=True),
    sa.Column('method', sa.String(length=8), nullable=True),
    sa.Column('path', sa.String(length=255), nullable=True),
    sa.Column('ip', sa.String(length=64), nullable=True),
    sa.Column('params', sa.Text(), nullable=True),
    sa.Column('result', sa.String(length=16), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('sys_role',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('name', sa.String(length=64), nullable=False),
    sa.Column('code', sa.String(length=64), nullable=True),
    sa.Column('desc', sa.String(length=255), nullable=True),
    sa.Column('status', sa.SmallInteger(), nullable=True),
    sa.Column('is_deleted', sa.SmallInteger(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('update_time', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_table('sys_user',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('username', sa.String(length=64), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('nickname', sa.String(length=64), nullable=True),
    sa.Column('phone', sa.String(length=20), nullable=True),
    sa.Column('status', sa.SmallInteger(), nullable=True),
    sa.Column('is_deleted', sa.SmallInteger(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('update_time', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sys_user_username'), 'sys_user', ['username'], unique=True)
    op.create_table('sys_role_menu',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('role_id', sa.Integer(), nullable=False),
    sa.Column('menu_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['menu_id'], ['sys_menu.id'], ),
    sa.ForeignKeyConstraint(['role_id'], ['sys_role.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('sys_user_role',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('role_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['role_id'], ['sys_role.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['sys_user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('sys_user_role')
    op.drop_table('sys_role_menu')
    op.drop_index(op.f('ix_sys_user_username'), table_name='sys_user')
    op.drop_table('sys_user')
    op.drop_table('sys_role')
    op.drop_table('sys_oper_log')
    op.drop_table('sys_menu')
    op.drop_table('sys_file')
    op.drop_table('sys_dict_type')
    op.drop_index(op.f('ix_sys_dict_item_dict_type'), table_name='sys_dict_item')
    op.drop_table('sys_dict_item')
    op.drop_table('edu_teacher')
    op.drop_index(op.f('ix_edu_enrollment_phone'), table_name='edu_enrollment')
    op.drop_index(op.f('ix_edu_enrollment_course_id'), table_name='edu_enrollment')
    op.drop_table('edu_enrollment')
    op.drop_index(op.f('ix_edu_course_teacher_id'), table_name='edu_course')
    op.drop_index(op.f('ix_edu_course_category_id'), table_name='edu_course')
    op.drop_table('edu_course')
    op.drop_table('edu_category')
    op.drop_table('edu_article')
    op.drop_table('biz_data')
