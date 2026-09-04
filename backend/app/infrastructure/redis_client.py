"""Redis 连接封装；客户端按需导入，避免健康接口依赖 Redis 服务启动。"""

import json
from typing import Any

from app.config import Settings


class RedisStore:
    """提供带统一前缀的 Redis 基础操作。"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._client: Any | None = None

    def _get_client(self) -> Any:
        """延迟创建 Redis 客户端并应用项目 key 前缀。"""
        if self._client is None:
            try:
                import redis
            except ImportError as exc:
                raise RuntimeError("redis package is required for Redis operations") from exc
            self._client = redis.Redis.from_url(
                self.settings.redis_url,
                password=self.settings.redis_password or None,
                decode_responses=True,
                health_check_interval=30,
            )
        return self._client

    def ping(self) -> bool:
        """探测 Redis 是否可用。"""
        return bool(self._get_client().ping())

    def key(self, value: str) -> str:
        """为业务 key 添加统一前缀，避免多项目互相覆盖。"""
        return f"{self.settings.redis_key_prefix}{value}"

    def get_json(self, value: str) -> dict[str, Any] | list[Any] | None:
        """读取带前缀的 JSON 值；损坏或空值按不存在处理。"""
        raw = self._get_client().get(self.key(value))
        if not raw:
            return None
        try:
            parsed = json.loads(raw)
        except (TypeError, ValueError):
            return None
        return parsed if isinstance(parsed, (dict, list)) else None

    def set_json(self, value: str, payload: dict[str, Any] | list[Any], ttl_seconds: int) -> None:
        """以 TTL 写入带前缀 JSON 值，不输出内容。"""
        ttl = max(1, int(ttl_seconds))
        self._get_client().setex(self.key(value), ttl, json.dumps(payload, ensure_ascii=False))

    def delete(self, value: str) -> None:
        """删除带前缀的 Redis 值。"""
        self._get_client().delete(self.key(value))
