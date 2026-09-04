from app.domain.task import TaskStatus, normalize_status


def test_task_status_normalization():
    assert normalize_status("0") is TaskStatus.PENDING
    assert normalize_status(1) is TaskStatus.RUNNING
    assert normalize_status(TaskStatus.SUCCESS) is TaskStatus.SUCCESS


def test_timeout_and_cancel_statuses_reuse_existing_values():
    assert TaskStatus.PENDING.value == 0
    assert TaskStatus.RUNNING.value == 1
    assert TaskStatus.FAILED.value == 3
