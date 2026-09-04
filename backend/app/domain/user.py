"""用户认证领域模型。"""

from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator


class User(BaseModel):
    """管理用户公开视图，不包含密码哈希。"""

    model_config = ConfigDict(extra="ignore")
    user_id: str
    tenant_id: str | None = None
    username: str
    nick_name: str | None = None
    role: int
    status: int

    @field_validator("user_id", mode="before")
    @classmethod
    def _id_as_string(cls, value: Any) -> str:
        """将用户大整数标识序列化为字符串。"""
        return str(value)
