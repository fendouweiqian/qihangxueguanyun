"""FastAPI 应用入口。"""

from pathlib import Path
import logging
import sys

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from app.api.students import router as student_router
from app.api.tasks import router as task_router, runner_router
from app.api.catalog import router as catalog_router
from app.api.progress import router as progress_router
from app.api.internal_runner import router as internal_runner_router
from app.api.auth import router as auth_router, user_router
from app.api.operations import router as operations_router
from app.config import Settings
from app.infrastructure.db import Database
from app.infrastructure.redis_client import RedisStore

app = FastAPI(title="教育业务系统", version="0.1.0")
# Uvicorn 默认将应用日志级别设为 WARNING；业务请求需要保留阶段和状态码。
# 适配器日志只写安全元数据，具体账号、密码、Cookie 和 Token 不进入日志。
_app_logger = logging.getLogger("app")
_app_logger.setLevel(logging.INFO)
if not _app_logger.handlers:
    _app_handler = logging.StreamHandler(sys.stdout)
    _app_handler.setLevel(logging.INFO)
    _app_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    _app_logger.addHandler(_app_handler)
_app_logger.propagate = False
_upload_dir = Path(Settings.from_env().upload_dir).resolve()
_upload_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=_upload_dir), name="uploads")
app.include_router(student_router)
app.include_router(task_router)
app.include_router(runner_router)
app.include_router(catalog_router)
app.include_router(progress_router)
app.include_router(internal_runner_router)
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(operations_router)


@app.get("/healthz", tags=["system"])
def healthz() -> dict[str, str]:
    """返回进程健康状态，不主动连接外部服务。"""
    return {"status": "ok"}


@app.get("/readyz", tags=["system"])
def readyz() -> dict[str, str]:
    """探测 MySQL 和 Redis，依赖不可用时返回 503。"""
    settings = Settings.from_env()
    checks: dict[str, str] = {}
    try:
        Database(settings).ping()
        checks["mysql"] = "ok"
    except Exception:
        checks["mysql"] = "unavailable"
    try:
        RedisStore(settings).ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "unavailable"
    if any(value != "ok" for value in checks.values()):
        raise HTTPException(status_code=503, detail={"status": "not_ready", "checks": checks})
    return {"status": "ready", "environment": settings.app_env, **checks}
