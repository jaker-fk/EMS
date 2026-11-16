#!/bin/sh
# 容器启动入口：等数据库 → 执行迁移 → 启动 uvicorn
set -e

echo "[entrypoint] waiting for database..."
python -m app.cli wait-db --timeout "${DB_WAIT_TIMEOUT:-60}"

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  echo "[entrypoint] running alembic migrations..."
  # 统一入口：空库直接建表；老库（有表无 alembic_version）自动 stamp 基线后再升级
  python -m app.cli migrate
fi

echo "[entrypoint] starting uvicorn (workers=${WEB_CONCURRENCY:-2})..."
exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --workers "${WEB_CONCURRENCY:-2}" \
  --proxy-headers \
  --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-*}"
