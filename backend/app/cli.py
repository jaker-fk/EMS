"""运维 CLI：数据库等待、创建管理员、手动补种子数据。

用法（在 backend/ 目录执行，自动读取 backend/.env）：

    python -m app.cli wait-db --timeout 60
    python -m app.cli create-admin --username admin        # 交互输入密码
    python -m app.cli create-admin --username admin --password 'S3cure!Pass'
    python -m app.cli seed
"""
from __future__ import annotations

import argparse
import getpass
import sys
import time
from pathlib import Path

from sqlalchemy import inspect, text

from app.core.config import settings
from app.core.database import SessionLocal, engine
from app.core.security import hash_password, password_policy_error

BACKEND_DIR = Path(__file__).resolve().parents[1]
# 老版本（create_all 时代）建出来的库没有 alembic_version，首次接管时按初始版本打基线
LEGACY_BASELINE = "0001_initial"


def cmd_wait_db(args: argparse.Namespace) -> int:
    deadline = time.time() + args.timeout
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print(f"database ready: {settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DB}")
            return 0
        except Exception as exc:  # 数据库容器启动比后端慢是常态
            last_error = exc
            time.sleep(1)
    print(f"database not ready after {args.timeout}s: {last_error}", file=sys.stderr)
    return 1


def cmd_seed(_args: argparse.Namespace) -> int:
    from app.main import _seed

    _seed()
    print("seed done")
    return 0


def cmd_migrate(_args: argparse.Namespace) -> int:
    """执行迁移；老库（有表但没有 alembic_version）自动打初始基线，避免升级时手工 stamp。"""
    from alembic import command
    from alembic.config import Config

    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))

    inspector = inspect(engine)
    has_version = inspector.has_table("alembic_version")
    has_schema = inspector.has_table("sys_user")

    if not has_version and has_schema:
        print(f"legacy database detected, stamping baseline {LEGACY_BASELINE}")
        command.stamp(config, LEGACY_BASELINE)
    elif not has_version and not has_schema:
        print("empty database detected, running full migrations")

    command.upgrade(config, "head")
    print("migrations applied: head")
    return 0


def cmd_create_admin(args: argparse.Namespace) -> int:
    from app.models import models

    password = args.password or getpass.getpass("password: ")
    error = password_policy_error(password)
    if error:
        print(f"password rejected: {error}", file=sys.stderr)
        return 2

    db = SessionLocal()
    try:
        if db.query(models.User).filter(models.User.username == args.username).first():
            print(f"user {args.username!r} already exists", file=sys.stderr)
            return 2
        role = db.query(models.Role).filter(models.Role.name == "super_admin").first()
        if not role:
            print("super_admin role missing, run `python -m app.cli seed` first", file=sys.stderr)
            return 2
        user = models.User(
            username=args.username,
            password_hash=hash_password(password),
            nickname=args.nickname,
            status=1,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        db.add(models.UserRole(user_id=user.id, role_id=role.id))
        db.commit()
        print(f"created super admin: id={user.id}, username={user.username}")
        return 0
    finally:
        db.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description="Admin Panel 运维命令")
    sub = parser.add_subparsers(dest="command", required=True)

    wait_db = sub.add_parser("wait-db", help="等待数据库可连接")
    wait_db.add_argument("--timeout", type=int, default=60)
    wait_db.set_defaults(func=cmd_wait_db)

    create_admin = sub.add_parser("create-admin", help="创建超级管理员")
    create_admin.add_argument("--username", required=True)
    create_admin.add_argument("--password", default="", help="不传则交互输入，避免密码进入 shell 历史")
    create_admin.add_argument("--nickname", default="超级管理员")
    create_admin.set_defaults(func=cmd_create_admin)

    seed = sub.add_parser("seed", help="幂等补齐内置数据（角色 / 菜单 / 字典）")
    seed.set_defaults(func=cmd_seed)

    migrate = sub.add_parser("migrate", help="执行数据库迁移（老库自动打基线）")
    migrate.set_defaults(func=cmd_migrate)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
