"""平台适配器注册表。"""

from app.adapters.base import PlatformAdapter
from app.adapters.chaoxing import ChaoxingAdapter
from app.adapters.chengkaoyun import ChengKaoYunAdapter
from app.adapters.mock import MockAdapter


class AdapterRegistry:
    """按名称解析适配器，调度器不写死平台判断。"""

    def __init__(self, adapters: list[PlatformAdapter] | None = None):
        self._adapters = {adapter.name: adapter for adapter in (adapters or [MockAdapter(), ChengKaoYunAdapter(), ChaoxingAdapter()])}

    def get(self, name: str) -> PlatformAdapter:
        """获取适配器，不存在时抛出明确错误。"""
        try:
            return self._adapters[name]
        except KeyError as exc:
            raise ValueError(f"未注册的平台适配器: {name}") from exc

    def resolve_name(self, task: dict[str, object], preferred: str = "") -> str:
        """按任务显式配置和学校平台元数据解析适配器名称。"""
        explicit = str(task.get("adapter") or preferred or "").strip().lower()
        if explicit:
            return explicit
        platform_name = str(task.get("platformName") or "").strip().lower()
        school_name = str(task.get("schoolName") or "").strip().lower()
        course_name = str(task.get("courseName") or "").strip().lower()
        school_url = str(task.get("schoolUrl") or "").strip().lower()
        access_address = str(task.get("schoolAccessAddress") or "").strip().lower()
        try:
            access_type = int(task.get("schoolAccessType") or 0)
        except (TypeError, ValueError):
            access_type = 0
        if (
            "成教" in platform_name
            or "成考云" in platform_name
            or "成考云" in school_name
            or "成考云" in course_name
            or access_type == 2
            or "成人教育学生平台" in access_address
        ):
            return "chengkaoyun"
        if "超星" in platform_name or "chaoxing" in school_url:
            return "chaoxing"
        return ""
