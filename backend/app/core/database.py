from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

DB_URL = settings.DATABASE_URL

engine_kwargs: dict = {
    "pool_pre_ping": True,  # 取连接前 ping 一次，自动剔除被 MySQL 断开的空闲连接
    "pool_recycle": 3600,   # MySQL 默认 wait_timeout=8h，回收连接避免 "MySQL server has gone away"
    "pool_size": 10,
    "max_overflow": 20,
}
if DB_URL.startswith("sqlite"):
    # SQLite 仅用于测试 / 临时体验：单文件、无连接池语义
    engine_kwargs = {"connect_args": {"check_same_thread": False}}
else:
    # MySQL：显式声明 utf8mb4，保证中文 / emoji 正常存取
    engine_kwargs["connect_args"] = {"charset": "utf8mb4"}

engine = create_engine(DB_URL, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
