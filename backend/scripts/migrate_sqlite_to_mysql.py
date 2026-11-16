#!/usr/bin/env python
"""把本地 SQLite 库（默认 backend/local.db）的数据迁移到 MySQL。

背景：项目早期本地开发用 `DB_URL=sqlite:///./local.db`，现在统一改成 MySQL。
本脚本做三件事：

1. 确保目标 MySQL 库存在（不存在则按 utf8mb4 创建）；
2. 按 models.py 的当前定义重建目标表（--no-reset 时保留已有表，可能因主键冲突失败）；
3. 按外键依赖顺序把 SQLite 里的数据逐表写入 MySQL。

迁移完成后启动后端，`app.main._seed()` 会做幂等补齐：
旧菜单路径 `/users` → `/admin/users`、补建新模块菜单、灌入教培演示数据。

用法（在任意目录执行均可，脚本会切到 backend/ 以读取 backend/.env）：

    ..\\.venv-mysql\\Scripts\\python.exe scripts\\migrate_sqlite_to_mysql.py
    python scripts/migrate_sqlite_to_mysql.py --source local.db --no-reset
"""
from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys
from datetime import date, datetime
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
# app.core.config 的 env_file 相对当前工作目录解析（../.env、.env），固定在 backend/ 下运行最稳
os.chdir(BACKEND_DIR)
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import Date, DateTime, create_engine, text  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.database import Base, engine  # noqa: E402
from app.models import models  # noqa: F401,E402  仅为注册全部表到 Base.metadata

_DB_NAME_RE = re.compile(r"^[A-Za-z0-9_]+$")


def _check_target() -> None:
    if engine.dialect.name != "mysql":
        sys.exit(
            f"目标库不是 MySQL（当前为 {engine.dialect.name}）：{settings.DATABASE_URL}\n"
            "请先在 backend/.env 或环境变量里配置 MYSQL_HOST/PORT/USER/PASSWORD/DB，并确保 DB_URL 为空。"
        )


def _ensure_database() -> None:
    """目标库不存在时创建，避免首次迁移先 Manual 建库。"""
    url = make_url(settings.DATABASE_URL)
    db_name = url.database or ""
    if not _DB_NAME_RE.match(db_name):
        sys.exit(f"MYSQL_DB 不合法：{db_name!r}")
    server_engine = create_engine(url.set(database=""), pool_pre_ping=True)
    try:
        with server_engine.connect() as conn:
            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4"))
            conn.commit()
    finally:
        server_engine.dispose()


def _coerce(column, value):
    """SQLite 把时间存成字符串，MySQL 的 DATETIME 需要真正的 datetime。"""
    if value is None or not isinstance(value, str):
        return value
    if isinstance(column.type, DateTime):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    if isinstance(column.type, Date):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return value


def _reset_target() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _copy(source: Path) -> tuple[int, int]:
    if not source.is_file():
        sys.exit(f"源 SQLite 文件不存在：{source}")

    src = sqlite3.connect(f"file:{source}?mode=ro", uri=True)
    src.row_factory = sqlite3.Row
    try:
        src_tables = {
            row[0] for row in src.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        total_tables = total_rows = 0
        # sorted_tables 按外键依赖排序，先父后子，避免被外键挡住
        for table in Base.metadata.sorted_tables:
            if table.name not in src_tables:
                print(f"  跳过 {table.name:<18} 源库无此表（新模块，由启动时的种子数据补齐）")
                continue
            src_cols = {
                row[1] for row in src.execute(f'PRAGMA table_info("{table.name}")')
            }
            columns = [c for c in table.columns if c.name in src_cols]
            if not columns:
                continue
            col_sql = ", ".join(f'"{c.name}"' for c in columns)
            rows = src.execute(f'SELECT {col_sql} FROM "{table.name}"').fetchall()
            payload = [
                {c.name: _coerce(c, row[c.name]) for c in columns}
                for row in rows
            ]
            if payload:
                with engine.begin() as conn:
                    conn.execute(table.insert(), payload)
            print(f"  迁移 {table.name:<18} {len(payload):>5} 行（列 {len(columns)}）")
            total_tables += 1
            total_rows += len(payload)
        return total_tables, total_rows
    finally:
        src.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="SQLite → MySQL 数据迁移")
    parser.add_argument(
        "--source",
        default=str(BACKEND_DIR / "local.db"),
        help="源 SQLite 文件路径（默认 backend/local.db）",
    )
    parser.add_argument(
        "--no-reset",
        action="store_true",
        help="不删除目标库已有表（默认先 DROP 再按 models.py 重建，避免脏数据/主键冲突）",
    )
    args = parser.parse_args()

    _check_target()
    host = make_url(settings.DATABASE_URL).render_as_string(hide_password=True)
    print(f"源：{args.source}")
    print(f"目标：{host}")

    _ensure_database()
    if args.no_reset:
        Base.metadata.create_all(bind=engine)
    else:
        print("重建目标表……")
        _reset_target()

    print("开始迁移：")
    tables, rows = _copy(Path(args.source))

    with engine.connect() as conn:
        counts = {
            t.name: conn.execute(text(f"SELECT COUNT(*) FROM `{t.name}`")).scalar_one()
            for t in Base.metadata.sorted_tables
        }
    print(f"完成：{tables} 张表、{rows} 行写入 MySQL；目标表现有行数：")
    for name, count in counts.items():
        print(f"  {name:<18} {count:>5}")


if __name__ == "__main__":
    main()
