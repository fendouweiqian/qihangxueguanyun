"""集中加载运行配置，禁止在源码中硬编码凭证。"""

from dataclasses import dataclass
import os
from pathlib import Path


def _int_env(name: str, default: int, minimum: int = 1) -> int:
    raw = os.getenv(name)
    try:
        return max(minimum, int(raw)) if raw is not None else default
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc


@dataclass(frozen=True)
class Settings:
    """应用、MySQL 和 Redis 的环境变量配置。"""

    app_env: str = "local"
    host: str = "127.0.0.1"
    port: int = 8281
    db_host: str = "127.0.0.1"
    db_port: int = 3307
    db_name: str = "education_assistant"
    db_user: str = "root"
    db_password: str = ""
    db_connect_timeout: int = 5
    redis_url: str = "redis://127.0.0.1:6379/1"
    redis_password: str = ""
    redis_key_prefix: str = "education:"
    internal_token: str = ""
    auth_secret: str = ""
    auth_token_ttl_seconds: int = 28800
    bootstrap_token: str = ""
    upload_dir: str = str(Path(__file__).resolve().parents[1] / "data" / "uploads")

    @classmethod
    def from_env(cls) -> "Settings":
        """从环境变量构造配置；未提供密码时保持为空。"""
        return cls(
            app_env=os.getenv("EDUCATION_APP_ENV", "local"),
            host=os.getenv("EDUCATION_HOST", "127.0.0.1"),
            port=_int_env("EDUCATION_PORT", 8281),
            db_host=os.getenv("EDUCATION_DB_HOST", "127.0.0.1"),
            db_port=_int_env("EDUCATION_DB_PORT", 3307),
            db_name=os.getenv("EDUCATION_DB_NAME", "education_assistant"),
            db_user=os.getenv("EDUCATION_DB_USER", "root"),
            db_password=os.getenv("EDUCATION_DB_PASSWORD", ""),
            db_connect_timeout=_int_env("EDUCATION_DB_CONNECT_TIMEOUT", 5),
            redis_url=os.getenv("EDUCATION_REDIS_URL", "redis://127.0.0.1:6379/1"),
            redis_password=os.getenv("EDUCATION_REDIS_PASSWORD", ""),
            redis_key_prefix=os.getenv("EDUCATION_REDIS_KEY_PREFIX", "education:"),
            internal_token=os.getenv("EDUCATION_INTERNAL_TOKEN", ""),
            auth_secret=os.getenv("EDUCATION_AUTH_SECRET", ""),
            auth_token_ttl_seconds=_int_env("EDUCATION_AUTH_TOKEN_TTL_SECONDS", 28800),
            bootstrap_token=os.getenv("EDUCATION_BOOTSTRAP_TOKEN", ""),
            upload_dir=os.getenv(
                "EDUCATION_UPLOAD_DIR",
                str(Path(__file__).resolve().parents[1] / "data" / "uploads"),
            ),
        )
