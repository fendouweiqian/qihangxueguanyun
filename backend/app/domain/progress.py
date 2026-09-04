"""课程和考试进度领域视图。"""

from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator


class ProgressView(BaseModel):
    """进度字段的通用基础模型。"""

    model_config = ConfigDict(extra="ignore")

    @field_validator("progress_id", "exam_progress_id", "item_id", "order_id", mode="before", check_fields=False)
    @classmethod
    def _ids_as_strings(cls, value: Any) -> str | None:
        return None if value is None else str(value)


class CourseProgress(ProgressView):
    """课程进度汇总。"""

    progress_id: str
    order_id: str
    tenant_id: str
    course_name: str | None = None
    term: str | None = None
    video_status: int
    video_note: str | None = None
    work_status: int
    work_note: str | None = None
    exam_status: int
    exam_note: str | None = None


class ExamProgress(ProgressView):
    """考试进度汇总。"""

    exam_progress_id: str
    order_id: str
    tenant_id: str
    status: int
    score: float | None = None
    note: str | None = None


class CourseProgressItem(ProgressView):
    """课程进度明细。"""

    item_id: str
    order_id: str
    tenant_id: str
    course_name: str
    course_type: str | None = None
    required_flag: int = 0
    term: str | None = None
    learning_status: int = 0
    learning_percent: float | None = None
    learning_text: str | None = None
    work_status: int = 0


class ExamProgressItem(ProgressView):
    """考试进度明细。"""

    item_id: str
    order_id: str
    tenant_id: str
    exam_name: str
    exam_status: int = 0
    score: float | None = None
    remark: str | None = None
    frozen_flag: int = 0
    frozen_reason: str | None = None

