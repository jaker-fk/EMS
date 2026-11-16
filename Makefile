# 常用工程命令（Linux / macOS / Git Bash）。Windows 用 .\tasks.ps1 <action>
.DEFAULT_GOAL := help
PY ?= python

.PHONY: help install lint test test-mysql migrate seed dev up down logs backup

help: ## 显示可用命令
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## 安装后端依赖（含开发工具）
	cd backend && $(PY) -m pip install -r requirements-dev.txt

lint: ## 代码规范检查
	cd backend && ruff check .

test: ## 后端测试（临时 SQLite）
	cd backend && pytest -q

test-mysql: ## 后端测试（MySQL，需先设置 TEST_DB_URL）
	cd backend && pytest -q

migrate: ## 执行数据库迁移到最新版本（老库自动打基线）
	cd backend && $(PY) -m app.cli migrate

seed: ## 幂等补齐内置数据
	cd backend && $(PY) -m app.cli seed

dev: ## 本地启动后端（热重载）
	cd backend && $(PY) -m uvicorn app.main:app --reload --port 8000

up: ## docker compose 构建并启动
	docker compose up -d --build

down: ## 停止 compose（保留数据卷）
	docker compose down

logs: ## 查看后端日志
	docker compose logs -f --tail=100 backend

backup: ## 备份 MySQL（Docker 部署）
	bash scripts/backup_mysql.sh
