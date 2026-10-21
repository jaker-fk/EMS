# 企业后台管理系统（RBAC）

基于 **RBAC（用户 - 角色 - 菜单权限）** 模型的企业内部通用后台管理平台，前后端分离：
Vue3 + Element Plus + Pinia 生态 前端，FastAPI + SQLAlchemy + MySQL + Redis + JWT 后端，
Docker Compose 一键部署，Nginx 托管静态资源并反向代理接口。

> 适合作为全栈项目写进简历：覆盖数据库设计、权限模型、接口安全、缓存、日志审计、
> 动态菜单与按钮级权限、容器化部署等高频考点。

---

## 1. 功能一览

| 模块 | 能力 |
| --- | --- |
| 登录认证 | 账号密码 + 图形验证码、JWT 鉴权、退出登录（Redis Token 黑名单） |
| 用户管理 | 分页/关键字/状态筛选、新增、编辑、启用禁用、重置密码、分配角色、逻辑删除 |
| 角色管理 | 角色 CRUD、菜单权限分配（树形勾选）、已绑定用户禁止删除、超级管理员保护 |
| 菜单管理 | 目录 / 页面 / 按钮三类菜单、树形展示、父子级联校验（有子菜单禁止删除） |
| 数据字典 | 字典类型 + 字典项维护、下拉数据源、Redis 缓存 + 变更自动失效 |
| 操作日志 | 登录/增删改自动埋点，记录操作人、模块、类型、方法、地址、参数、IP、结果，支持多条件检索（只读） |
| 个人中心 | 查看个人信息与角色、修改密码、查看本人操作日志 |
| 系统工具 | Swagger 文档、统一返回体、全局异常处理、Redis 缓存、Nginx 反向代理 |

扩展演示：业务数据导出 Excel、文件上传（可裁剪，不属于核心 RBAC）。

---

## 2. 技术栈

- **前端**：Vue3 + TypeScript + Vue Router + Pinia + Element Plus + Axios + Vite
- **后端**：Python FastAPI + Pydantic v2 + SQLAlchemy 2.0 + python-jose(JWT) + bcrypt
- **数据库**：MySQL 8.0（本地可用 SQLite 直连调试）
- **缓存**：Redis 7（缓存菜单上下文、字典下拉、登出黑名单；不可用时自动降级为进程内存缓存）
- **部署**：Docker Compose（mysql / redis / backend / frontend）+ Nginx

---

## 3. 目录结构

```
Admin_Panel/
├── backend/
│   ├── app/
│   │   ├── api / routers     # 路由接口（auth/user/role/menu/dict/log/profile）
│   │   ├── core/             # 配置、数据库、JWT、响应体、验证码、Redis
│   │   ├── models/           # SQLAlchemy ORM 模型
│   │   ├── schemas/          # Pydantic 入参出参校验
│   │   └── main.py           # 应用入口、全局异常、种子数据
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/       # 递归侧边栏菜单
│   │   ├── utils/            # axios 封装、按钮权限判断
│   │   ├── views/            # Login / Layout / Users / Roles / Menus / Dicts / Logs / Profile
│   │   ├── router.ts
│   │   └── main.ts
│   ├── Dockerfile
│   ├── nginx.conf
│   └── vite.config.ts
├── mysql/init.sql            # 建表 + 种子数据
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 4. 快速开始

### 4.1 Docker 一键部署（推荐）

```bash
cp .env.example .env          # 按需修改密钥 / 数据库密码
docker compose up -d --build
```

- 前端：http://localhost
- 接口文档：http://localhost:8000/api/docs
- 默认账号：`admin / 123456`

### 4.2 本地开发

后端（默认 SQLite 直连，无需 MySQL；Windows / macOS / Linux 通用）：

```powershell
cd backend
$env:DB_URL="sqlite:///./local.db"      # PowerShell；Bash 用 export
$env:CAPTCHA_ENABLED="false"           # 需要验证码时去掉此行
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

> 若要用本地 MySQL / Redis，去掉 `DB_URL` 并设置 `MYSQL_HOST=127.0.0.1`、`REDIS_HOST=127.0.0.1` 即可，
> 首次启动会自动建表并灌入种子数据（也可手动执行 `mysql/init.sql`）。

前端：

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173  （/api 已代理到 8000）
```

---

## 5. 权限模型设计（RBAC）

```
sys_user ──< sys_user_role >── sys_role ──< sys_role_menu >── sys_menu
                                              │
                                    menu_type: M 目录 / C 页面 / F 按钮
                                    perms:     system:user:list / system:user:add ...
```

- **菜单动态渲染**：登录后 `GET /api/auth/menus` 返回当前用户可访问的菜单树 + 按钮权限标识，
  前端据此渲染侧边栏，并使用 `hasPerm('system:user:add')` 控制按钮显隐。
- **权限缓存**：菜单上下文按用户缓存到 Redis；角色菜单、用户角色、菜单发生变化时统一递增缓存版本号，
  下一次请求自动重建，避免“改完权限不生效”。
- **祖先补全**：角色只勾选页面或按钮时，后端自动补齐祖先目录，保证菜单树完整可导航。
- **超级管理员**：`super_admin` 角色绕过菜单关联，直接拥有全部菜单与权限。
- **软删除**：用户/角色/菜单均为逻辑删除（`is_deleted`），避免误删与历史外键悬空。

> 行级数据权限扩展思路：在角色/用户上预留 `dept_id`，查询层统一注入
> `WHERE dept_id IN (...)` 的数据范围过滤，即可实现“不同管理员只看本部门数据”。

---

## 6. 安全与可靠性

- 密码 bcrypt 哈希存储，接口不返回密码字段。
- JWT 携带 `jti`，退出登录写入 Redis 黑名单，实现 Token 主动失效。
- 图形验证码（SVG 动态生成，答案存 Redis，2 分钟过期）。
- Pydantic 统一入参校验；SQLAlchemy ORM 参数化查询，杜绝字符串拼接 SQL 注入。
- 接口限流（滑动窗口）：登录按 IP 限制 10 次/分钟，写操作 60 次/分钟，防刷与防重复提交。
- 统一返回体 `{ code, msg, data }`：200 成功 / 400 参数业务错误 / 401 未登录 / 403 无权限 / 429 请求过频 / 500 异常。
- 全局异常捕获，前端 401 自动跳转登录页。
- 分页查询强制 `limit`，避免全表扫描；关键读接口使用 Redis 缓存。
- 操作日志自动埋点（登录、增删改、上传、导出），日志只读不可删除。

---

## 7. 主要接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/auth/captcha` | 获取图形验证码 |
| POST | `/api/auth/login` | 登录（返回 JWT） |
| POST | `/api/auth/logout` | 退出登录（Token 加入黑名单） |
| GET | `/api/auth/menus` | 当前用户菜单树 + 按钮权限 |
| GET/POST/PUT/DELETE | `/api/users` | 用户管理 |
| PUT | `/api/users/{id}/password` | 重置密码 |
| GET/POST/PUT/DELETE | `/api/roles` | 角色管理 |
| POST | `/api/roles/{id}/menus` | 分配菜单权限（见 `/api/roles/{id}`） |
| GET/POST/PUT/DELETE | `/api/menus` | 菜单管理 |
| GET/POST/PUT/DELETE | `/api/dict/types`、`/api/dict/items` | 数据字典 |
| GET | `/api/dict/data/{dict_type}` | 字典下拉数据源（缓存） |
| GET | `/api/logs` | 操作日志（多条件分页） |
| GET/PUT | `/api/profile`、`/api/profile/password` | 个人信息 / 修改密码 |

---

## 8. 面试可讲的设计点

1. **RBAC 多对多建模**：用户-角色、角色-菜单两张中间表解耦权限，菜单表用 `menu_type` 区分目录/页面/按钮。
2. **动态菜单 + 按钮权限**：后端下发菜单树与 `perms`，前端递归渲染 + 指令式 `hasPerm` 控制按钮。
3. **权限缓存一致性**：版本号 + Redis key 前缀失效策略，避免逐 key 清理遗漏。
4. **JWT 主动失效**：`jti` + Redis 黑名单解决“JWT 签发后无法注销”的痛点。
5. **安全防护**：bcrypt、验证码、Pydantic 校验、ORM 防注入、软删除、统一错误码。
6. **树形结构性能**：菜单一次查询后在内存组树，避免递归查库；结果缓存 Redis。
7. **容器化部署**：Compose 编排 MySQL/Redis/后端/前端，Nginx 反向代理，`.env` 区分环境。
