"""锁定运行时依赖的最小导入和连接封装测试。"""

import importlib

from app.config import Settings
from app.infrastructure.db import Database


def test_runtime_dependencies_import():
    """确保干净安装能加载后端声明的运行时包。"""
    for module_name in ("fastapi", "uvicorn", "pydantic", "pymysql", "redis", "dotenv", "requests", "bs4", "fontTools"):
        assert importlib.import_module(module_name) is not None


def test_database_ping_uses_short_read_query(monkeypatch):
    """数据库健康检查只执行 SELECT 1 并关闭连接。"""
    calls = []

    class Cursor:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def execute(self, sql):
            calls.append(sql)

        def fetchone(self):
            return {"1": 1}

    class Connection:
        def cursor(self):
            return Cursor()

        def close(self):
            calls.append("closed")

    monkeypatch.setattr("app.infrastructure.db.pymysql.connect", lambda **_: Connection())
    Database(Settings.from_env()).ping()
    assert calls == ["SELECT 1", "closed"]
