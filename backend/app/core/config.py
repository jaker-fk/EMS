import logging
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("admin_panel.config")

_INSECURE_SECRETS = {"change-me-super-secret-key", "please-change-this-secret", "secret", ""}


class Settings(BaseSettings):
    # 依次加载：项目根目录 .env（docker compose 用）→ backend/.env（本地开发用），后者优先；
    # 真实环境变量始终覆盖文件。extra="ignore" 让 compose 的 MYSQL_ROOT_PASSWORD 等键不报错。
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    APP_NAME: str = "Admin Panel API"
    APP_VERSION: str = "2.1.0"
    # dev / test / prod：决定文档开关、日志格式、种子数据、启动建表策略
    APP_ENV: Literal["dev", "test", "prod"] = "dev"

    SECRET_KEY: str = "change-me-super-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 720

    MYSQL_HOST: str = "mysql"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "admin"
    MYSQL_PASSWORD: str = "123456"
    MYSQL_DB: str = "admin_panel"

    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    # 生产多实例部署建议 true：Redis 不可用直接判定未就绪，避免缓存不一致
    REDIS_REQUIRED: bool = False

    UPLOAD_DIR: str = "/app/uploads"
    MAX_UPLOAD_MB: int = 10
    ALLOWED_EXTS: str = ".jpg,.jpeg,.png,.gif,.webp,.pdf,.xls,.xlsx,.doc,.docx,.txt,.zip"
    CORS_ORIGINS: str = "*"
    TRUSTED_HOSTS: str = "*"

    # 图形验证码开关（关闭后登录不校验验证码，便于本地调试）
    CAPTCHA_ENABLED: bool = True
    # 菜单 / 字典缓存时长（秒）
    CACHE_TTL: int = 300

    # 密码强度：最小长度 + 至少包含几类字符（小写 / 大写 / 数字 / 符号）
    PASSWORD_MIN_LEN: int = 8
    PASSWORD_MIN_CLASSES: int = 2
    # 连续登录失败达到该次数后锁定账号一段时间（分钟）
    LOGIN_MAX_FAILS: int = 5
    LOGIN_LOCK_MINUTES: int = 10

    LOG_LEVEL: str = "INFO"
    # text / json：容器化部署建议 json，便于 Loki / ELK 采集
    LOG_FORMAT: Literal["text", "json"] = "text"
    # 接口限流开关（压测 / 自动化测试时可关闭）
    RATE_LIMIT_ENABLED: bool = True

    # 可观测性
    METRICS_ENABLED: bool = True

    # 数据库启动策略：None = 按 APP_ENV 推断（prod 关闭，dev/test 自动建表）
    AUTO_CREATE_TABLES: bool | None = None
    # 生产环境首启时创建 admin 用的初始密码；留空则跳过（用 `python -m app.cli create-admin` 手工建）
    ADMIN_INITIAL_PASSWORD: str = ""
    # 系统基础数据（角色 / 菜单 / 字典 / admin）：默认开启
    SEED_BASE_DATA: bool = True
    # 教培演示数据：None = 按 APP_ENV 推断（prod 关闭，dev/test 开启）
    SEED_DEMO_DATA: bool | None = None

    # 本地启动时可设置 DB_URL=sqlite:///./local.db 直连，无需 MySQL
    DB_URL: str = ""

    @property
    def DATABASE_URL(self) -> str:
        if self.DB_URL:
            return self.DB_URL
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DB}?charset=utf8mb4"
        )

    @property
    def ALLOWED_EXT_SET(self) -> set[str]:
        return {x.strip().lower() for x in self.ALLOWED_EXTS.split(",") if x.strip()}

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def trusted_hosts(self) -> list[str]:
        return [h.strip() for h in self.TRUSTED_HOSTS.split(",") if h.strip()]

    @property
    def is_prod(self) -> bool:
        return self.APP_ENV == "prod"

    @property
    def docs_enabled(self) -> bool:
        """生产默认关闭 Swagger / OpenAPI，减少攻击面。"""
        return self.APP_ENV != "prod"

    @property
    def auto_create_tables(self) -> bool:
        if self.AUTO_CREATE_TABLES is not None:
            return self.AUTO_CREATE_TABLES
        return self.APP_ENV != "prod"

    @property
    def seed_demo_data(self) -> bool:
        if self.SEED_DEMO_DATA is not None:
            return self.SEED_DEMO_DATA
        return self.APP_ENV != "prod"

    @model_validator(mode="after")
    def _validate_production(self):
        """生产环境做「宁可启动失败，也不带默认密钥上线」的硬校验。"""
        if not self.is_prod:
            return self
        if self.SECRET_KEY in _INSECURE_SECRETS or len(self.SECRET_KEY) < 32:
            raise ValueError(
                "生产环境 SECRET_KEY 必须是至少 32 位的随机字符串（可用 `openssl rand -hex 32` 生成）"
            )
        if self.CORS_ORIGINS.strip() == "*":
            logger.warning("生产环境 CORS_ORIGINS 为 *，建议改成具体域名")
        if self.CAPTCHA_ENABLED is False:
            logger.warning("生产环境已关闭图形验证码，请确认这是有意的")
        if self.DB_URL.startswith("sqlite"):
            raise ValueError("生产环境不支持 SQLite，请配置 MySQL")
        return self


settings = Settings()
