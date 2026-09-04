"""任务执行应用服务。"""

from typing import Any, Protocol

from app.adapters.base import AdapterContext, AdapterTask, TaskKind
from app.adapters.registry import AdapterRegistry


class TaskGateway(Protocol):
    """任务领取和结果回写端口。"""

    def claim(self, limit: int, runner_id: str, task_types: list[int] | None = None) -> list[dict[str, Any]]: ...

    def submit_result(self, task_id: str, success: bool, code: str, message: str, retry_delta: int) -> bool: ...

    def upsert_course_progress(self, payload: dict[str, Any]) -> None: ...

    def upsert_exam_progress(self, payload: dict[str, Any]) -> None: ...

    def replace_course_progress_items(self, payload: dict[str, Any]) -> int: ...

    def replace_exam_progress_items(self, payload: dict[str, Any]) -> int: ...

    def record_tiku_failure(self, payload: dict[str, Any]) -> None: ...


class TaskRunner:
    """编排任务生命周期，不包含任何具体平台判断。"""

    def __init__(self, gateway: TaskGateway, registry: AdapterRegistry | None = None):
        self.gateway = gateway
        self.registry = registry or AdapterRegistry()

    def run_once(self, limit: int = 1, runner_id: str = "", adapter_name: str = "") -> int:
        """领取一批任务，执行并幂等提交结果；返回领取数量。"""
        tasks = self.gateway.claim(limit, runner_id)
        for raw in tasks:
            self._run_one(raw, adapter_name)
        return len(tasks)

    def _run_one(self, raw: dict[str, Any], adapter_name: str) -> None:
        """执行单个任务，并确保异常也写回失败状态。"""
        task_id = str(raw["taskId"])
        try:
            kind = {2: TaskKind.EXAM, 3: TaskKind.QUIZ}.get(int(raw.get("taskType", 1)), TaskKind.STUDY)
            task = AdapterTask(task_id, str(raw["orderId"]), str(raw["tenantId"]), kind, raw)
            context = AdapterContext(
                tenant_id=str(raw["tenantId"]), school_id=str(raw.get("schoolId") or ""),
                student_id=str(raw.get("studentId") or ""), account=str(raw.get("studentAccount") or ""),
                password=str(raw.get("studentPassword") or ""),
                extra={
                    key: raw.get(key)
                    for key in (
                        "studentName",
                        "studentOpenId",
                        "schoolUrl",
                        "schoolName",
                        "schoolAccessType",
                        "schoolAccessAddress",
                        "platformName",
                        "captchaId",
                        "captchaType",
                        "captchaVersion",
                        "captchaX",
                        "captchaApiUrl",
                        "captchaApiToken",
                        "captchaApiType",
                    )
                },
            )
            selected_adapter = self.registry.resolve_name(raw, adapter_name)
            if not selected_adapter:
                self.gateway.submit_result(task_id, False, "adapter_missing", "任务未配置平台适配器", 1)
                return
            adapter = self.registry.get(selected_adapter)
            login = adapter.login(context)
            result = login if not login.ok else adapter.execute(task, context)
            self._flush_progress(result.data)
            self.gateway.submit_result(task_id, result.ok, result.code, result.message, 0 if result.ok else 1)
        except Exception as exc:
            self.gateway.submit_result(task_id, False, "runner_exception", type(exc).__name__, 1)

    def _flush_progress(self, data: dict[str, Any]) -> None:
        """把适配器快照写回对应仓储端口。"""
        course = data.get("course_progress") if isinstance(data, dict) else None
        exam = data.get("exam_progress") if isinstance(data, dict) else None
        course_items = data.get("course_progress_items") if isinstance(data, dict) else None
        exam_items = data.get("exam_progress_items") if isinstance(data, dict) else None
        failure = data.get("tiku_failure") if isinstance(data, dict) else None
        if isinstance(course, dict) and hasattr(self.gateway, "upsert_course_progress"):
            self.gateway.upsert_course_progress(course)
        if isinstance(exam, dict) and hasattr(self.gateway, "upsert_exam_progress"):
            self.gateway.upsert_exam_progress(exam)
        if isinstance(course_items, dict) and hasattr(self.gateway, "replace_course_progress_items"):
            self.gateway.replace_course_progress_items(course_items)
        if isinstance(exam_items, dict) and hasattr(self.gateway, "replace_exam_progress_items"):
            self.gateway.replace_exam_progress_items(exam_items)
        if isinstance(failure, dict) and hasattr(self.gateway, "record_tiku_failure"):
            self.gateway.record_tiku_failure(failure)
