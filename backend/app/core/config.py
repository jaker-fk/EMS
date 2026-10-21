from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Admin Panel API"
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

    UPLOAD_DIR: str = "/app/uploads"
    MAX_UPLOAD_MB: int = 10
    ALLOWED_EXTS: str = ".jpg,.jpeg,.png,.gif,.webp,.pdf,.xls,.xlsx,.doc,.docx,.txt,.zip"
    CORS_ORIGINS: str = "*"

    # 图形验证码开关（关闭后登录不校验验证码，便于本地调试）
    CAPTCHA_ENABLED: bool = True
    # 菜单 / 字典缓存时长（秒）
    CACHE_TTL: int = 300

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


settings = Settings()
