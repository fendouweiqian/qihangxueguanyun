"""本地开发和测试使用的确定性适配器。"""

from app.adapters.base import AdapterContext, AdapterResult, AdapterTask


class MockAdapter:
    """不访问外部平台的模拟适配器。"""

    name = "mock"

    def login(self, context: AdapterContext) -> AdapterResult:
        """验证模拟上下文并返回脱敏的成功结果。"""
        if not context.account or not context.password:
            return AdapterResult(False, "credentials_empty", "账号或密码为空")
        return AdapterResult(True, "mock_login_ok", "模拟登录成功", {"studentName": context.extra.get("studentName", "")})

    def execute(self, task: AdapterTask, context: AdapterContext) -> AdapterResult:
        """按任务类型生成可重复的课程/考试结果。"""
        if task.kind.value == "exam":
            return AdapterResult(True, "mock_exam_ok", "模拟考试完成", {"exam_progress": {"orderId": task.order_id, "tenantId": task.tenant_id, "status": 1, "note": "模拟完成"}})
        return AdapterResult(True, "mock_study_ok", "模拟学习完成", {"course_progress": {"orderId": task.order_id, "tenantId": task.tenant_id, "videoStatus": 1, "workStatus": 1, "examStatus": 0}})

