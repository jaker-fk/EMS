# 部署与运维手册

面向「真正要上线」的场景：从零部署、日常发布、数据库迁移、备份恢复、监控告警和回滚。开发环境的快速启动见根目录 [README](../README.md)。

---

## 1. 架构与端口

```
浏览器
  │ HTTPS (443)
  ▼
Nginx（frontend 容器，静态资源 + /api 反代）
  │
  ▼
FastAPI（backend 容器，uvicorn 多 worker）
  ├── MySQL 8（mysql 容器，容器内 3306，宿主机仅绑定 127.0.0.1:3307）
  └── Redis 7（redis 容器，容器内 6379，宿主机仅绑定 127.0.0.1:6379）
```

| 组件 | 对外端口 | 说明 |
| --- | --- | --- |
| frontend | `80`（生产建议再套一层 TLS 反代） | N 静态资源 + `/api`、`/uploads` 反代 |
| backend | `8000` | `/api/*`，`/metrics` 仅内网 |
| mysql | `127.0.0.1:3307` | 生产不要暴露公网；备份走容器内 mysqldump |
| redis | `127.0.0.1:6379` | 多实例部署必须开启，并设 `REDIS_REQUIRED=true` |

数据卷：`mysql_data`、`redis_data`、`uploads`。**升级镜像不会丢数据，`docker compose down -v` 才会删卷。**

---

## 2. 环境要求

| 项 | 建议 |
| --- | --- |
| 服务器 | 2 vCPU / 4 GB 起步；磁盘按上传量与备份保留策略预留 |
| Docker | 24+，含 `docker compose` v2 |
| 域名与证书 | 生产必须 HTTPS；可用云负载均衡证书或 certbot |
| 备份存储 | 与数据库不同磁盘 / 对象存储，定期校验可恢复 |

---

## 3. 首次部署（Docker Compose）

```bash
git clone <repo> admin_panel && cd admin_panel

# 1) 准备环境变量
cp .env.example .env
openssl rand -hex 32          # 把输出填到 SECRET_KEY
# 编辑 .env：APP_ENV=prod、MySQL 强密码、CORS_ORIGINS、TRUSTED_HOSTS、ADMIN_INITIAL_PASSWORD

# 2) 构建并启动（首次会编译依赖，几分钟）
docker compose up -d --build

# 3) 等待 healthy
docker compose ps
curl -fsS http://127.0.0.1:8000/api/health
curl -fsS http://127.0.0.1:8000/api/ready

# 4) 登录后台修改初始密码（前台官网不提供入口）
#    http://<服务器IP>/admin/login
```

启动流程由 `backend/docker-entrypoint.sh` 完成：

1. `python -m app.cli wait-db` 等待 MySQL 可连；
2. `python -m app.cli migrate` 执行数据库迁移：空库直接建表；**老库（有表但没有 `alembic_version`）自动 stamp 初始基线后再升级**；
3. `uvicorn --workers ${WEB_CONCURRENCY}` 启动，默认 2 个 worker。

> 镜像以非 root 用户 `app` 运行；不要再用 `CMD` 覆盖 entrypoint，否则迁移不会执行。

---

## 4. 生产配置清单

| 变量 | 生产建议 | 说明 |
| --- | --- | --- |
| `APP_ENV` | `prod` | 关闭 Swagger/OpenAPI、默认不灌演示数据、强校验 SECRET_KEY |
| `SECRET_KEY` | 32 位以上随机串 | 泄露等于可伪造任意 JWT；轮换会使所有已签发 Token 失效 |
| `MYSQL_ROOT_PASSWORD` / `MYSQL_PASSWORD` | 强随机密码 | 不要沿用示例值 |
| `CORS_ORIGINS` | `https://your-domain.com` | 不要用 `*` |
| `TRUSTED_HOSTS` | `your-domain.com,www.your-domain.com` | 防止 Host 头攻击 |
| `REDIS_REQUIRED` | 多实例：`true`；单机：`false` | true 时 Redis 不可用会摘流量（503） |
| `CAPTCHA_ENABLED` | `true` | 登录防爆破 |
| `SEED_DEMO_DATA` | `false` | 不灌课程 / 资讯演示数据 |
| `SEED_BASE_DATA` | `true` | 角色 / 菜单 / 字典需要 |
| `ADMIN_INITIAL_PASSWORD` | 首次启动设置为强密码，建好后清空 | 仅当 admin 不存在时使用 |
| `LOG_FORMAT` | `json` | 便于 Loki/ELK 解析 |
| `WEB_CONCURRENCY` | CPU 核数 | 每个 worker 独立进程，共享 MySQL/Redis |
| `METRICS_ENABLED` | `true` | `/metrics` 只给内网 Prometheus 抓取 |

---

## 5. HTTPS 与反向代理

生产建议在前面再加一层 Nginx / 云 LB 处理 TLS，示例：

```nginx
server {
  listen 443 ssl http2;
  server_name your-domain.com;
  ssl_certificate     /etc/letsencrypt/live/your-domain.com/fullchain.pem;
  ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

  client_max_body_size 12m;

  location / {
    proxy_pass http://127.0.0.1:80;   # compose 里的 frontend
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto https;
  }
}
server {
  listen 80;
  server_name your-domain.com;
  return 301 https://$host$request_uri;
}
```

要点：

- 后端信任 `X-Forwarded-*` 的开关在 `docker-entrypoint.sh`（`--proxy-headers`），需要与最外层代理一致；
- 应用在 `https` 请求下会返回 `Strict-Transport-Security`（HSTS）；
- `/metrics` 不要暴露到公网，Prometheus 走内网抓 `http://backend:8000/metrics`。

---

## 6. 数据库迁移（Alembic）

**表结构的唯一事实来源是 `backend/app/models/models.py`**，`mysql/init.sql` 只负责建库；应用不再用 `create_all` 改生产库。

常用命令（在 `backend/` 下，或容器内）：

```bash
alembic current                     # 当前版本
alembic upgrade head                # 升级到最新
alembic check                       # 模型与库是否漂移（CI 会跑）
alembic history                     # 迁移历史

# 容器内执行
docker compose exec backend alembic upgrade head
docker compose exec backend alembic current
```

新增一次迁移：

```bash
cd backend
# 1) 改 models.py
# 2) 自动生成（务必人工 review，尤其是删列/改类型）
alembic revision --autogenerate -m "add xxx index"
# 3) 本地验证
alembic upgrade head && alembic check
```

回滚：

```bash
alembic downgrade -1     # 回滚一版
```

> 回滚前先备份；跨版本回滚要和镜像版本一起回退，避免「新代码 + 旧表结构」。

从 v2.1（`create_all` 时代）升级上来的老库，基线接管是自动的：容器 entrypoint / `python -m app.cli migrate` 检测到「有表但没有 alembic_version」会先 `stamp 0001_initial` 再升级。手工执行等价命令：

```bash
docker compose exec backend python -m app.cli migrate
# 或者：
docker compose exec backend alembic stamp 0001_initial
docker compose exec backend alembic upgrade head
```

全新库直接 `python -m app.cli migrate`（或 `alembic upgrade head`）即可。

---

## 7. 初始管理员与种子数据

- 生产首次启动：在 `.env` 设置 `ADMIN_INITIAL_PASSWORD`，应用会创建 `admin` 并绑定 `super_admin` 角色；**登录后立即改密码，并从 .env 删除该变量**。
- 不想在环境变量里留初始密码：启动后执行

  ```bash
  docker compose exec backend python -m app.cli create-admin --username admin
  # 交互输入密码，不会进入 shell 历史
  ```

- 基础数据（角色 / 菜单 / 字典）幂等补齐；演示数据由 `SEED_DEMO_DATA` 控制。
- 手工补种子：`docker compose exec backend python -m app.cli seed`。

---

## 8. 备份与恢复

### 8.1 备份

Docker 部署（宿主机 cron 每天 03:00）：

```bash
0 3 * * * cd /srv/admin_panel && BACKUP_DIR=/data/backups RETAIN_DAYS=14 \
  bash scripts/backup_mysql.sh >> /var/log/admin_panel_backup.log 2>&1
```

本机 Windows 实例：

```powershell
.\scripts\backup_mysql.ps1 -OutDir D:\backups -RetainDays 14
```

备份使用 `--single-transaction`，对业务无锁；默认保留 14 天。

### 8.2 恢复

```bash
# 1) 停后端，避免恢复过程中继续写入
docker compose stop backend

# 2) 解压并导入（会覆盖同名库，确认无误再执行）
gunzip -c /data/backups/admin_panel_20260101_030000.sql.gz \
  | docker compose exec -T mysql sh -c 'exec mysql -uroot -p"$MYSQL_ROOT_PASSWORD"'

# 3) 起后端
docker compose start backend
curl -fsS http://127.0.0.1:8000/api/ready
```

每季度至少做一次「备份 → 恢复到临时库 → 校验行数」演练。

---

## 9. 监控、日志与告警

### 9.1 探针

| 端点 | 用途 | 说明 |
| --- | --- | --- |
| `GET /api/health` | 存活探针 | 不依赖 DB/Redis，进程能响应即 200 |
| `GET /api/ready` | 就绪探针 | 检查 DB（及可选的 Redis），失败 503 |
| `GET /metrics` | Prometheus | 仅内网；Nginx 公网入口已返回 404 |

Prometheus 抓取示例：

```yaml
scrape_configs:
  - job_name: admin-panel
    metrics_path: /metrics
    static_configs:
      - targets: ["backend:8000"]
```

### 9.2 指标

`http_requests_total{method,path,status}`、`http_request_duration_seconds`、`http_requests_in_progress`、`database_up`、`redis_up`。`path` 使用路由模板（如 `/api/courses/{cid}`），不会因为 id 撑爆时间序列。

> 多 worker 说明：当前指标是「单进程视角」，uvicorn 起多个 worker 时每次抓取只会命中其中一个进程。对精确聚合有要求时，可后续接入 `prometheus_client` 多进程模式（`PROMETHEUS_MULTIPROC_DIR` + `MultiProcessCollector`），或先用单 worker 部署并靠横向扩展多副本。

### 9.3 建议告警

- `rate(http_requests_total{status=~"5.."}[5m]) > 0` 持续 5 分钟；
- `database_up == 0`；
- `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1`；
- `/api/ready` 连续失败（编排层会自动摘流量）。

### 9.4 日志

- 容器日志 `json-file`，单文件 10MB × 3 份（compose 已配置）；
- `LOG_FORMAT=json` 时字段固定：`ts/level/logger/msg/request_id/method/path/status/duration_ms/client_ip`；
- 响应头 `X-Request-ID` 与日志里的 `request_id` 一致，Nginx 透传的 `$request_id` 也可直接对齐；
- 错误响应体会带 `request_id`，排查时让用户提供该值即可定位整条链路。

---

## 10. 性能与扩容

- 后端无状态，`docker compose up -d --scale backend=2` 前需将 `REDIS_REQUIRED=true`（限流 / 登录锁定 / JWT 黑名单都依赖 Redis 共享状态），并让 Nginx upstream 轮询多个实例；
- `WEB_CONCURRENCY` 建议 = CPU 核数；每个 worker 有独立连接池（`pool_size=10, max_overflow=20`）；
- 课程 / 报名列表的 N+1 已改为分组统计；`sys_oper_log.created_at`、`edu_course.status`、`edu_enrollment.status` 已加索引；
- 静态资源走 Nginx 长缓存（`/assets/` 30 天，index.html 不缓存）；
- 上传目录是本地卷，多实例或多主机部署时需换成对象存储（OSS/S3）或共享 NAS。

---

## 11. 安全清单（上线前逐项确认）

- [ ] `APP_ENV=prod`，Swagger 已关闭；
- [ ] `SECRET_KEY` 为随机强密钥，未出现在仓库 / 镜像层；
- [ ] MySQL / Redis 未暴露公网（compose 已绑定 127.0.0.1）；
- [ ] `CORS_ORIGINS` / `TRUSTED_HOSTS` 为具体域名；
- [ ] HTTPS 全站启用，HTTP 自动跳转；
- [ ] 登录验证码开启，失败锁定阈值符合预期；
- [ ] 初始 `admin` 密码已修改，`ADMIN_INITIAL_PASSWORD` 已清空；
- [ ] 数据库每日自动备份并演练过恢复；
- [ ] 容器以非 root 运行（backend 已 `USER app`，compose 已 `no-new-privileges`）；
- [ ] 依赖漏洞扫描 / Dependabot 已开启；
- [ ] 日志与指标接入监控，5xx / ready / 延迟有告警；
- [ ] 限流与登录锁定在多实例下共享（Redis）。

---

## 12. 发版与回滚

```bash
# 1) 备份
BACKUP_DIR=/data/backups bash scripts/backup_mysql.sh

# 2) 拉代码（确认迁移是向后兼容的：先加列/表，后删旧字段）
git pull

# 3) 构建并滚动更新（compose 会重建变化的容器）
docker compose up -d --build

# 4) 验收
curl -fsS http://127.0.0.1:8000/api/ready
docker compose ps
```

回滚：

```bash
git checkout <上一个 tag>
docker compose up -d --build
# 如果本次包含破坏性迁移：
docker compose exec backend alembic downgrade -1
```

> 数据库迁移遵循「先扩展后收缩」：新字段可空、旧字段先保留一个版本，避免回滚时丢数据。

---

## 13. 故障排查

| 现象 | 排查 |
| --- | --- |
| `backend` 反复重启 | `docker compose logs backend`；确认 `SECRET_KEY` 长度 ≥ 32、MySQL 密码正确 |
| `/api/ready` 503 | 看返回的 `data.database`；检查 MySQL 健康状态与连接数 |
| 迁移失败 | `alembic current`；确认没有手工改过表；必要时从备份恢复后重试 |
| 502 Bad Gateway | frontend 到 backend 不通：`docker compose ps`、`docker compose logs backend` |
| 上传 413 | 外层 Nginx `client_max_body_size` 与 `MAX_UPLOAD_MB` 是否一致 |
| 时间显示差 8 小时 | 容器 `TZ=Asia/Shanghai`；数据库连接时区保持一致 |
| 登录一直锁定 | 等待 `LOGIN_LOCK_MINUTES`；确认 Redis/内存计数未被异常放大 |

---

## 14. 参考

- FastAPI 部署：<https://fastapi.tiangolo.com/deployment/>
- Alembic 文档：<https://alembic.sqlalchemy.org/>
- Docker 构建最佳实践：<https://docs.docker.com/build/building/best-practices/>
- Prometheus Python client：<https://github.com/prometheus/client_python>
- OWASP API Security Top 10：<https://owasp.org/API-Security/>
