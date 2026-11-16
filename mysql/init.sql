SET NAMES utf8mb4;
-- MySQL 8.0 初始化脚本。
--
-- 说明：表结构由后端 Alembic 迁移统一创建（容器 entrypoint 会先执行 `alembic upgrade head`），
-- 这样「代码里的模型」只有一份事实来源，不再维护第二份 DDL。
-- 本脚本只负责确保数据库以 utf8mb4 存在；角色 / 菜单 / 字典 / 管理员由应用启动时的幂等种子补齐。
CREATE DATABASE IF NOT EXISTS admin_panel CHARACTER SET utf8mb4;
