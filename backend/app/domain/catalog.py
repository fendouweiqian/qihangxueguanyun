"""租户、学校、平台和订单领域视图。"""

from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator


class _View(BaseModel):
    model_config = ConfigDict(extra="ignore")

    @field_validator("platform_id", "school_id", "order_id", "student_id", mode="before", check_fields=False)
    @classmethod
    def _ids_as_strings(cls, value: Any) -> str | None:
        return None if value is None else str(value)


class Platform(_View):
    """教育平台视图。"""

    platform_id: str
    platform_name: str
    remark: str | None = None


class School(_View):
    """学校平台配置视图。"""

    school_id: str
    platform_id: str
    school_name: str
    access_type: int
    access_address: str | None = None
    school_url: str | None = None
    school_state: int


class Tenant(BaseModel):
    """租户视图。"""

    tenant_id: str
    tenant_name: str
    status: int
    balance_points: int


class Order(_View):
    """课程订单视图。"""

    order_id: str
    tenant_id: str
    student_id: str
    school_id: str
    platform_id: str
    order_type: int
    course_name: str | None = None
    course_code: str | None = None
    term: str | None = None
    status: int

