"""平台适配器统一协议。"""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol


class TaskKind(StrEnum):
    """任务类型。"""

    STUDY = "study"
    QUIZ = "quiz"
    EXAM = "exam"


@dataclass(frozen=True)
class AdapterContext:
    """平台登录和执行所需的账号上下文；禁止直接记录 password。"""

    tenant_id: str
    school_id: str
    student_id: str
    account: str
    password: str
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AdapterTask:
    """执行器传给平台适配器的任务值对象。"""

    task_id: str
    order_id: str
    tenant_id: str
    kind: TaskKind
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AdapterResult:
    """适配器执行结果及可写回的业务快照。"""

    ok: bool
    code: str = ""
    message: str = ""
    data: dict[str, Any] = field(default_factory=dict)


class PlatformAdapter(Protocol):
    """所有平台实现必须提供的最小协议。"""

    name: str

    def login(self, context: AdapterContext) -> AdapterResult: ...

    def execute(self, task: AdapterTask, context: AdapterContext) -> AdapterResult: ...

