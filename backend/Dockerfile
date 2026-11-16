# syntax=docker/dockerfile:1
# ---------- 构建阶段：只在镜像里编译依赖，最终镜像不带编译工具链 ----------
FROM python:3.11-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 国内网络默认走清华源，海外构建可传 --build-arg PIP_INDEX_URL=https://pypi.org/simple
ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
WORKDIR /build
COPY requirements.txt .
RUN pip wheel --wheel-dir=/wheels -r requirements.txt -i "$PIP_INDEX_URL"

# ---------- 运行阶段 ----------
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=Asia/Shanghai

# 非 root 运行
RUN groupadd --system app \
    && useradd --system --gid app --home-dir /app --shell /usr/sbin/nologin app

WORKDIR /app

COPY --from=builder /wheels /wheels
COPY requirements.txt ./
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt \
    && rm -rf /wheels

COPY --chown=app:app . .
RUN mkdir -p /app/uploads && chown -R app:app /app

USER app
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3)"

# 入口脚本：等数据库 → alembic upgrade head → uvicorn（见 docker-entrypoint.sh）
ENTRYPOINT ["/bin/sh", "/app/docker-entrypoint.sh"]
