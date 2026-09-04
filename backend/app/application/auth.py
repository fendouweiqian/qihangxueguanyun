"""认证服务：密码哈希、令牌签发和验证。"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any


def _verify_legacy_password(password: str, encoded: str) -> bool:
    """验证原管理用户表中的 BCrypt 哈希；缺少可选库时安全失败。"""
    if not encoded or not encoded.startswith("$2"):
        return False
    try:
        import bcrypt

        return bool(bcrypt.checkpw(password.encode("utf-8"), encoded.encode("utf-8")))
    except (ImportError, ValueError, TypeError):
        return False


class AuthService:
    """使用标准库实现无外部依赖的 PBKDF2 和 HMAC 令牌。"""

    _iterations = 310_000

    def __init__(self, secret: str, ttl_seconds: int = 28800):
        self.secret = secret.encode("utf-8") if secret else b""
        self.ttl_seconds = max(60, int(ttl_seconds))

    def ensure_enabled(self) -> None:
        """拒绝在未配置签名密钥时签发或验证令牌。"""
        if not self.secret:
            raise RuntimeError("EDUCATION_AUTH_SECRET is required")

    @classmethod
    def hash_password(cls, password: str) -> str:
        """使用随机盐生成 PBKDF2-SHA256 哈希，不保存明文密码。"""
        if not password:
            raise ValueError("password is required")
        salt = secrets.token_bytes(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, cls._iterations)
        return f"pbkdf2_sha256${cls._iterations}${cls._encode_bytes(salt)}${cls._encode_bytes(digest)}"

    @classmethod
    def verify_password(cls, password: str, encoded: str) -> bool:
        """恒定时间验证目标 PBKDF2 哈希；未知历史格式返回 False。"""
        try:
            algorithm, iterations, salt_text, digest_text = encoded.split("$", 3)
            if algorithm != "pbkdf2_sha256":
                return False
            salt = cls._decode_bytes(salt_text)
            expected = cls._decode_bytes(digest_text)
            actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
            return hmac.compare_digest(actual, expected)
        except (AttributeError, TypeError, ValueError, UnicodeError):
            return False

    def issue(self, user: dict[str, Any]) -> str:
        """签发包含用户和租户范围的短期 HMAC 令牌。"""
        self.ensure_enabled()
        payload = {"sub": str(user["user_id"]), "tenant": user.get("tenant_id"), "username": user["username"], "exp": int(time.time()) + self.ttl_seconds}
        body = self._encode(payload)
        signature = hmac.new(self.secret, body.encode("ascii"), hashlib.sha256).digest()
        return f"{body}.{self._encode_bytes(signature)}"

    def verify(self, token: str) -> dict[str, Any]:
        """验证令牌签名和有效期，失败时抛出 ValueError。"""
        self.ensure_enabled()
        try:
            body, signature = token.split(".", 1)
            expected = hmac.new(self.secret, body.encode("ascii"), hashlib.sha256).digest()
            if not hmac.compare_digest(signature, self._encode_bytes(expected)):
                raise ValueError("invalid token")
            payload = json.loads(self._decode(body))
            if int(payload.get("exp", 0)) < int(time.time()):
                raise ValueError("token expired")
            if not payload.get("sub") or not payload.get("username"):
                raise ValueError("invalid token claims")
            return payload
        except (AttributeError, TypeError, ValueError, UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError("invalid token") from exc

    @staticmethod
    def _encode(value: dict[str, Any]) -> str:
        """生成无填充 Base64URL JSON。"""
        raw = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

    @staticmethod
    def _encode_bytes(value: bytes) -> str:
        """生成无填充 Base64URL 字节串。"""
        return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")

    @staticmethod
    def _decode_bytes(value: str) -> bytes:
        """按长度补齐 Base64URL 填充并解码。"""
        return base64.urlsafe_b64decode(value + ("=" * (-len(value) % 4)))

    @staticmethod
    def _decode(value: str) -> str:
        """解码 Base64URL JSON。"""
        return AuthService._decode_bytes(value).decode("utf-8")
