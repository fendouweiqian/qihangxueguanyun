from contextlib import contextmanager

from fastapi.testclient import TestClient

from app.api.operations import _database
from app.main import app


class FakeCursor:
    """按 SQL 片段返回固定管理数据，并记录参数化查询。"""

    def __init__(self, database):
        self.database = database
        self.result = None
        self.rowcount = 1
        self.lastrowid = 99

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def execute(self, sql, params=()):
        self.database.calls.append((sql, tuple(params)))
        if "COUNT(*)" in sql:
            self.result = {"total": 1}
        elif "FROM ea_task WHERE task_id" in sql:
            self.result = {
                "task_id": 11,
                "order_id": 21,
                "tenant_id": "T10001",
                "task_type": 2,
                "status": 3,
            }
        elif "FROM ea_course_progress cp" in sql:
            self.result = [
                {
                    "progress_id": 51,
                    "order_id": 21,
                    "student_id": 81,
                    "student_name": "张三",
                    "student_account": "student-a",
                    "login_status": 1,
                    "course_name": "课程 A",
                }
            ]
        elif "FROM ea_course_progress_item" in sql:
            self.result = [{"item_id": 31, "order_id": 21, "course_name": "课程 A"}]
        elif "FROM ea_exam_progress_item" in sql:
            self.result = [{"item_id": 41, "order_id": 21, "exam_name": "考试 A"}]
        elif "FROM ea_course_progress" in sql:
            self.result = {"progress_id": 51, "order_id": 21, "video_status": 1}
        elif "FROM ea_exam_progress" in sql:
            self.result = {"exam_progress_id": 61, "order_id": 21, "status": 1}
        elif "FROM ea_task_log" in sql:
            self.result = [
                {
                    "log_id": 71,
                    "task_id": 11,
                    "order_id": 21,
                    "seq_no": 1,
                    "level": "INFO",
                    "biz_type": "course",
                    "biz_title": "课程 A",
                    "biz_status": 1,
                    "message": "完成",
                    "failure_reason": None,
                }
            ]
        elif "FROM ea_tiku_failure" in sql:
            self.result = []
        else:
            self.result = []

    def fetchone(self):
        if isinstance(self.result, list):
            return self.result[0] if self.result else None
        return self.result

    def fetchall(self):
        if isinstance(self.result, list):
            return self.result
        return [self.result] if self.result else []


class FakeConnection:
    def __init__(self, database):
        self.database = database

    def cursor(self):
        return FakeCursor(self.database)

    def commit(self):
        return None

    def rollback(self):
        return None

    def begin(self):
        return None


class FakeDatabase:
    def __init__(self):
        self.calls = []

    @contextmanager
    def connection(self):
        yield FakeConnection(self)


class OrderCursor(FakeCursor):
    """为订单事务提供租户、学校和学员固定数据。"""

    def execute(self, sql, params=()):
        self.database.calls.append((sql, tuple(params)))
        self.rowcount = 1
        if "SELECT tenant_id FROM ea_student" in sql:
            self.result = {"tenant_id": "T10001"}
        elif "SELECT balance_points FROM ea_tenant" in sql:
            self.result = {"balance_points": 100}
        elif "SELECT school_name,school_exam FROM ea_school" in sql:
            self.result = {"school_name": "测试学校", "school_exam": 1}
        else:
            self.result = None
        if "INSERT INTO ea_order" in sql:
            self.lastrowid = 101
        elif "INSERT INTO ea_task" in sql:
            self.lastrowid = 201


class OrderConnection(FakeConnection):
    def cursor(self):
        return OrderCursor(self.database)


class OrderDatabase(FakeDatabase):
    @contextmanager
    def connection(self):
        yield OrderConnection(self)


def test_original_management_routes_are_exposed():
    paths = app.openapi()["paths"]
    required = {
        "/education/task": {"post", "put"},
        "/education/task/{task_id}": {"get", "delete"},
        "/education/task/run-pending": {"post"},
        "/education/runner-node": {"post", "put"},
        "/education/runner-node/{node_id}": {"get", "delete"},
        "/education/runner-setting": {"post", "put"},
        "/education/runner-setting/{setting_id}": {"get", "delete"},
        "/education/school-cache": {"post", "put"},
        "/education/school-cache/{cache_id}": {"get", "delete"},
        "/education/face-media/upload": {"post"},
        "/education/student/import": {"post"},
        "/education/course-progress": {"post", "put"},
        "/education/course-progress/{progress_id}": {"get", "delete"},
        "/education/exam-progress": {"post", "put"},
        "/education/exam-progress/{exam_progress_id}": {"get", "delete"},
    }
    for path, methods in required.items():
        assert path in paths
        assert methods <= set(paths[path])


def test_task_detail_contains_progress_items_and_complete_log_fields():
    database = FakeDatabase()
    app.dependency_overrides[_database] = lambda: database
    try:
        response = TestClient(app).get("/education/task/detail/11")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    detail = response.json()["data"]
    assert detail["courseProgressItems"][0]["itemId"] == "31"
    assert detail["examProgressItems"][0]["itemId"] == "41"
    assert detail["logs"][0]["bizType"] == "course"
    assert detail["logs"][0]["bizStatus"] == 1
    assert "failureReason" in detail["logs"][0]


def test_task_list_accepts_original_camel_case_filters_and_pagination():
    database = FakeDatabase()
    app.dependency_overrides[_database] = lambda: database
    try:
        response = TestClient(app).get(
            "/education/task/list?orderId=21&status=3&taskType=2&pageNum=2&pageSize=10"
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["total"] == 1
    count_sql, count_params = database.calls[0]
    assert "order_id=%s" in count_sql
    assert "status=%s" in count_sql
    assert "task_type=%s" in count_sql
    assert count_params == ("21", 3, 2)
    assert database.calls[1][1][-2:] == (10, 10)


def test_original_student_and_order_forms_do_not_require_tenant_id():
    from app.api.catalog import OrderRequest
    from app.api.students import StudentRequest

    student = StudentRequest.model_validate(
        {"schoolId": "38", "account": "student-a", "password": "secret"}
    )
    order = OrderRequest.model_validate(
        {"studentId": "1", "schoolId": "38", "platformId": "1"}
    )

    assert student.tenantId is None
    assert order.tenantId is None


def test_catalog_lists_use_camel_case_filters_and_real_pagination():
    from app.api.catalog import _database as catalog_database

    database = FakeDatabase()
    app.dependency_overrides[catalog_database] = lambda: database
    try:
        response = TestClient(app).get(
            "/education/order/list?studentId=21&schoolId=38&status=0&pageNum=3&pageSize=5"
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["total"] == 1
    count_sql, count_params = database.calls[0]
    assert "student_id=%s" in count_sql
    assert "school_id=%s" in count_sql
    assert "status=%s" in count_sql
    assert count_params == ("21", "38", 0)
    assert database.calls[1][1][-2:] == (5, 10)


def test_course_progress_list_joins_student_fields_and_filters_original_query():
    from app.api.catalog import _database as catalog_database

    database = FakeDatabase()
    app.dependency_overrides[catalog_database] = lambda: database
    try:
        response = TestClient(app).get(
            "/education/course-progress/list?studentAccount=student-a&courseName=课程"
            "&term=2026&pageNum=1&pageSize=10"
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    row = response.json()["rows"][0]
    assert row["studentId"] == "81"
    assert row["studentName"] == "张三"
    count_sql, count_params = database.calls[0]
    assert "JOIN ea_order" in count_sql
    assert "s.account LIKE %s" in count_sql
    assert "cp.course_name LIKE %s" in count_sql
    assert "cp.term LIKE %s" in count_sql
    assert count_params == ("%student-a%", "%课程%", "%2026%")


def test_create_order_reproduces_original_transaction_side_effects(monkeypatch):
    from app.api.catalog import OrderRequest, create_order

    database = OrderDatabase()
    monkeypatch.setattr("app.api.catalog._claims", lambda authorization: {"sub": "9001"})
    response = create_order(
        OrderRequest.model_validate(
            {
                "studentId": "81",
                "schoolId": "38",
                "platformId": "1",
                "orderType": 1,
                "courseName": "高等数学",
                "term": "2026春",
                "costPoints": 10,
            }
        ),
        authorization="Bearer test",
        database=database,
    )

    assert response["data"]["orderId"] == "101"
    sql = "\n".join(call[0] for call in database.calls)
    assert "UPDATE ea_tenant SET balance_points=balance_points-%s" in sql
    assert "INSERT INTO ea_ledger" in sql
    assert "INSERT INTO ea_task" in sql
    assert "INSERT INTO ea_course_progress" in sql
    task_call = next(call for call in database.calls if "INSERT INTO ea_task" in call[0])
    assert '"includeCourses":["高等数学"]' in task_call[1][4]
