import os
import sys

# if getattr(sys, "frozen", False):
#     basedir = os.path.dirname(sys.executable)
# else:
#     basedir = os.path.abspath(os.path.dirname(__file__))

basedir = os.getcwd()


class Config:
    # 基础安全配置
    SECRET_KEY = os.environ.get("SECRET_KEY") or "student-sys-secret-123456"
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    # --- 数据库配置 (已切换为 SQLite) ---
    # 数据库文件 'school.db' 将生成在后端项目根目录下
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(basedir, "school.db")

    # 性能优化配置
    SQLALCHEMY_TRACK_MODIFICATIONS = False  # 禁用追踪以节省内存

    # SQLite 配置项
    # 注意：SQLite 通常不需要 MySQL 的 pool_recycle 配置
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        # 写锁等待时间，降低并发写入场景下的 "database is locked" 触发概率
        "connect_args": {
            "timeout": 30,
            "check_same_thread": False,
        },
    }

    # SQLite PRAGMA 开关（直接在代码中控制，适合打包 exe 使用）
    # 可选: "conservative" / "performance"
    SQLITE_MODE_PROFILE = "conservative"

    if SQLITE_MODE_PROFILE == "performance":
        SQLITE_JOURNAL_MODE = "WAL"
        SQLITE_SYNCHRONOUS = "NORMAL"
    else:
        # 默认保守模式：更适合担心异常关机/断电场景
        SQLITE_JOURNAL_MODE = "DELETE"
        SQLITE_SYNCHRONOUS = "FULL"

    # JWT 或 Session 过期时间设置（可选）
    AUTH_TOKEN_EXPIRES_SECONDS = int(
        os.environ.get("AUTH_TOKEN_EXPIRES_SECONDS", 12 * 60 * 60)
    )
