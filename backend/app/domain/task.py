"""任务状态和值对象。"""

from enum import IntEnum


class TaskStatus(IntEnum):
    """与历史 ea_task.status 对齐：待执行、执行中、成功、失败。"""

    PENDING = 0
    RUNNING = 1
    SUCCESS = 2
    FAILED = 3


def normalize_status(value: int | str | TaskStatus) -> TaskStatus:
    """把数据库或请求中的状态归一化为统一枚举。"""
    return value if isinstance(value, TaskStatus) else TaskStatus(int(value))

