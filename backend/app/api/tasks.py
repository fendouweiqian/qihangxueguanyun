"""执行任务内部 API。"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Body, Depends, Query
from pydantic import BaseModel, Field, field_validator

from app.config import Settings
from app.application.progress_parser import ProgressDetailParser
from app.infrastructure.db import Database, TaskRepository

router = APIRouter(prefix="/education/runner/tasks", tags=["runner"])
runner_router = APIRouter(prefix="/education/runner", tags=["runner"])


def _string_id(value: Any) -> str | None:
    """将历史接口中的数值或字符串 ID 统一转换为字符串。"""
    return None if value is None else str(value)


def task_repository() -> TaskRepository:
    """创建任务仓储。"""
    return TaskRepository(Database(Settings.from_env()))


class TaskResultRequest(BaseModel):
    """任务执行结果请求。"""

    success: bool
    code: str = Field(default="", max_length=64)
    message: str = Field(default="", max_length=500)
    retryDelta: int = Field(default=1, ge=0, le=10)
    runnerId: str = Field(default="", max_length=128)


class TaskClaimRequest(BaseModel):
    """任务领取请求，与历史内部 API 的 JSON 契约保持一致。"""

    limit: int = Field(default=1, ge=1, le=50)
    taskTypes: list[int] | None = None
    runnerId: str = Field(default="", max_length=128)


class TaskHeartbeatRequest(BaseModel):
    """任务心跳请求。"""

    runnerId: str = Field(min_length=1, max_length=128)


class CourseProgressItemsRequest(BaseModel):
    """课程进度明细批量写回请求。"""

    orderId: str
    tenantId: str = Field(min_length=1, max_length=20)
    items: list[dict] = Field(default_factory=list, max_length=1000)

    @field_validator("orderId", mode="before")
    @classmethod
    def normalize_order_id(cls, value: Any) -> str:
        """兼容旧执行器发送的数值订单 ID。"""
        return _string_id(value) or ""


class CourseProgressRequest(BaseModel):
    """课程进度汇总写回请求。"""

    orderId: str
    tenantId: str = Field(min_length=1, max_length=20)
    courseName: str | None = Field(default=None, max_length=128)
    term: str | None = Field(default=None, max_length=64)
    videoStatus: int = 0
    videoNote: str | None = Field(default=None, max_length=255)
    videoTime: datetime | None = None
    workStatus: int = 0
    workNote: str | None = Field(default=None, max_length=255)
    workTime: datetime | None = None
    examStatus: int = 0
    examNote: str | None = Field(default=None, max_length=255)
    examTime: datetime | None = None

    @field_validator("orderId", mode="before")
    @classmethod
    def normalize_order_id(cls, value: Any) -> str:
        """兼容旧执行器发送的数值订单 ID。"""
        return _string_id(value) or ""


class ExamProgressItemsRequest(BaseModel):
    """考试进度明细批量写回请求。"""

    orderId: str
    tenantId: str = Field(min_length=1, max_length=20)
    items: list[dict] = Field(default_factory=list, max_length=1000)

    @field_validator("orderId", mode="before")
    @classmethod
    def normalize_order_id(cls, value: Any) -> str:
        """兼容旧执行器发送的数值订单 ID。"""
        return _string_id(value) or ""


class ExamProgressRequest(BaseModel):
    """考试进度汇总写回请求。"""

    orderId: str
    tenantId: str = Field(min_length=1, max_length=20)
    status: int = 0
    score: float | None = None
    note: str | None = Field(default=None, max_length=255)
    finishedAt: datetime | None = None

    @field_validator("orderId", mode="before")
    @classmethod
    def normalize_order_id(cls, value: Any) -> str:
        """兼容旧执行器发送的数值订单 ID。"""
        return _string_id(value) or ""


class StudentProfileRequest(BaseModel):
    """学生档案可读字段写回请求。"""

    studentId: str
    tenantId: str = Field(min_length=1, max_length=20)
    studentName: str | None = Field(default=None, max_length=64)
    studyGrade: str | None = Field(default=None, max_length=64)
    major: str | None = Field(default=None, max_length=128)
    profileSnapshot: str | None = Field(default=None, max_length=200000)

    @field_validator("studentId", mode="before")
    @classmethod
    def normalize_student_id(cls, value: Any) -> str:
        """兼容旧执行器发送的数值学生 ID。"""
        return _string_id(value) or ""


class ProgressSnapshotRequest(BaseModel):
    """课程和考试页面快照写回请求。"""

    orderId: str
    tenantId: str = Field(min_length=1, max_length=20)
    courseSnapshot: str | None = Field(default=None, max_length=500000)
    examSnapshot: str | None = Field(default=None, max_length=500000)

    @field_validator("orderId", mode="before")
    @classmethod
    def normalize_order_id(cls, value: Any) -> str:
        """兼容旧执行器发送的数值订单 ID。"""
        return _string_id(value) or ""


class TikuFailureRequest(BaseModel):
    """题库失败记录请求。"""

    taskId: str | None = None
    orderId: str | None = None
    tenantId: str | None = None
    provider: str = ""
    question: str = ""
    optionsJson: str = ""
    reason: str = ""
    rawResponse: str = ""

    @field_validator("taskId", "orderId", "tenantId", mode="before")
    @classmethod
    def normalize_optional_ids(cls, value: Any) -> str | None:
        """兼容旧执行器发送的数值关联 ID。"""
        return _string_id(value)


class TaskCancelRequest(BaseModel):
    """任务取消请求。"""

    reason: str = Field(default="任务已取消", max_length=255)


@router.post("/claim")
def claim_tasks(
    request: TaskClaimRequest | None = Body(default=None),
    limit: int = Query(default=1, ge=1, le=50),
    runnerId: str = Query(default="", max_length=128),
    repo: TaskRepository = Depends(task_repository),
) -> dict:
    """领取待执行任务并返回脱离源项目的账号快照。"""
    claim_request = request or TaskClaimRequest(limit=limit, runnerId=runnerId)
    tasks = repo.claim(claim_request.limit, claim_request.runnerId, claim_request.taskTypes)
    return {"code": 200, "msg": "操作成功", "data": {"claimedCount": len(tasks), "tasks": tasks}}


@router.post("/recycle-timeout")
def recycle_timeouts(timeoutSeconds: int = Query(default=1800, ge=1, le=86400), repo: TaskRepository = Depends(task_repository)) -> dict:
    """回收心跳超时任务，保持源执行器的状态语义。"""
    return {"code": 200, "msg": "操作成功", "data": {"recycled": repo.recycle_timeouts(timeoutSeconds)}}


@router.post("/{task_id}/result")
def submit_result(task_id: str, request: TaskResultRequest, repo: TaskRepository = Depends(task_repository)) -> dict:
    """幂等提交任务结果。"""
    accepted = repo.submit_result(task_id, request.success, request.code, request.message, request.retryDelta)
    return {"code": 200 if accepted else 404, "msg": "操作成功" if accepted else "任务不存在或已结束", "data": {"accepted": accepted}}


@router.post("/{task_id}/heartbeat")
def touch_task_heartbeat(task_id: str, request: TaskHeartbeatRequest, repo: TaskRepository = Depends(task_repository)) -> dict:
    """续租执行节点持有的任务心跳。"""
    accepted = repo.touch_heartbeat(task_id, request.runnerId)
    return {"code": 200 if accepted else 404, "msg": "操作成功" if accepted else "任务不存在或不属于该执行节点", "data": {"accepted": accepted}}


@runner_router.post("/course-progress/items")
def replace_course_progress_items(request: CourseProgressItemsRequest, repo: TaskRepository = Depends(task_repository)) -> dict:
    """替换订单课程进度明细。"""
    count = repo.replace_course_progress_items(request.model_dump())
    return {"code": 200, "msg": "操作成功", "data": {"written": count}}


@runner_router.post("/course-progress/upsert")
def upsert_course_progress(request: CourseProgressRequest, repo: TaskRepository = Depends(task_repository)) -> dict:
    """幂等写回课程进度汇总。"""
    repo.upsert_course_progress(request.model_dump())
    return {"code": 200, "msg": "操作成功"}


@runner_router.post("/exam-progress/items")
def replace_exam_progress_items(request: ExamProgressItemsRequest, repo: TaskRepository = Depends(task_repository)) -> dict:
    """替换订单考试进度明细。"""
    count = repo.replace_exam_progress_items(request.model_dump())
    return {"code": 200, "msg": "操作成功", "data": {"written": count}}


@runner_router.post("/exam-progress/upsert")
def upsert_exam_progress(request: ExamProgressRequest, repo: TaskRepository = Depends(task_repository)) -> dict:
    """幂等写回考试进度汇总。"""
    repo.upsert_exam_progress(request.model_dump())
    return {"code": 200, "msg": "操作成功"}


@runner_router.post("/students/profile")
def update_student_profile(request: StudentProfileRequest, repo: TaskRepository = Depends(task_repository)) -> dict:
    """更新学生档案可读字段。"""
    payload = request.model_dump()
    if request.profileSnapshot:
        payload.update(ProgressDetailParser().parse_student_profile(request.profileSnapshot))
    accepted = repo.update_student_profile(payload)
    return {"code": 200 if accepted else 404, "msg": "操作成功" if accepted else "学员不存在或没有可更新字段", "data": {"accepted": accepted}}


@runner_router.post("/progress/snapshot")
def update_progress_snapshot(request: ProgressSnapshotRequest, repo: TaskRepository = Depends(task_repository)) -> dict:
    """解析课程/考试快照并写回结构化明细，不保存原始 HTML。"""
    parser = ProgressDetailParser()
    course_items = parser.parse_course_items(request.courseSnapshot)
    exam_items = parser.parse_exam_items(request.examSnapshot)
    course_count = repo.replace_course_progress_items({"orderId": request.orderId, "tenantId": request.tenantId, "items": course_items}) if request.courseSnapshot else 0
    exam_count = repo.replace_exam_progress_items({"orderId": request.orderId, "tenantId": request.tenantId, "items": exam_items}) if request.examSnapshot else 0
    return {"code": 200, "msg": "操作成功", "data": {"courseItems": course_count, "examItems": exam_count}}


@router.post("/{task_id}/cancel")
def cancel_task(task_id: str, request: TaskCancelRequest, repo: TaskRepository = Depends(task_repository)) -> dict:
    """取消任务；已完成任务不会被覆盖。"""
    accepted = repo.cancel(task_id, request.reason)
    return {"code": 200 if accepted else 404, "msg": "操作成功" if accepted else "任务不存在或已结束", "data": {"accepted": accepted}}


@runner_router.post("/tiku-failures")
def record_tiku_failure(request: TikuFailureRequest, repo: TaskRepository = Depends(task_repository)) -> dict:
    """记录题库失败，不返回原始响应内容。"""
    repo.record_tiku_failure(request.model_dump())
    return {"code": 200, "msg": "操作成功"}
