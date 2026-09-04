"""一次性任务 worker 命令。"""

import argparse

from app.config import Settings
from app.infrastructure.db import Database, TaskRepository
from app.application.task_runner import TaskRunner


def main() -> int:
    """从环境配置创建任务 runner 并执行一轮。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=1)
    parser.add_argument("--runner-id", default="local-worker")
    parser.add_argument("--adapter", default="", help="仅本地测试时显式指定适配器")
    args = parser.parse_args()
    count = TaskRunner(TaskRepository(Database(Settings.from_env()))).run_once(args.limit, args.runner_id, args.adapter)
    print(f"claimed={count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
