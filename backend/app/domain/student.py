"""学生领域模型，显式保持大整数标识的字符串 JSON 语义。"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator


class Student(BaseModel):
    """与历史 `ea_student` 对齐的学生账号视图。"""

    model_config = ConfigDict(extra="ignore")

    student_id: str
    tenant_id: str
    school_id: str
    account: str
    password: str
    open_id: str | None = None
    name: str
    study_grade: str | None = None
    major: str | None = None
    phone: str | None = None
    id_card: str | None = None
    status: int
    login_status: int | None = None
    login_message: str | None = None
    login_checked_at: datetime | None = None
    create_time: datetime | None = None
    update_time: datetime | None = None

    @field_validator("student_id", "school_id", mode="before")
    @classmethod
    def _stringify_ids(cls, value: Any) -> str:
        """把 MySQL BIGINT 转成字符串，避免前端精度损失。"""
        return str(value)

    @field_validator("tenant_id", mode="before")
    @classmethod
    def _stringify_tenant(cls, value: Any) -> str:
        return "" if value is None else str(value)


class StudentListQuery(BaseModel):
    """学生分页和租户、学校、账号、姓名筛选条件。"""

    tenant_id: str | None = None
    school_id: str | None = None
    account: str | None = None
    name: str | None = None
    phone: str | None = None
    status: int | None = None
    page_num: int = 1
    page_size: int = 10

    @field_validator("page_num", "page_size")
    @classmethod
    def _positive_page(cls, value: int) -> int:
        return max(1, min(value, 10000))
