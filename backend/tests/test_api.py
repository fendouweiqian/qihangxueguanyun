from datetime import datetime

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.main import app
from app.api.students import repository
from app.api.tasks import task_repository
from app.api.auth import _repo as auth_repository


class FakeRepository:
    def list_page(self, query):
        assert query.page_num == 2
        assert query.page_size == 3
        return ([{"student_id": 9000000000000000001, "tenant_id": "DEMO", "school_id": 38,
                  "account": "masked", "password": "masked", "open_id": None, "name": "测试",
                  "study_grade": "2024", "major": None, "phone": None, "id_card": None,
                  "status": 0, "login_status": 1, "login_message": "通过",
                  "login_checked_at": datetime(2026, 9, 1, 9, 0, 0),
                  "create_time": datetime(2026, 8, 1, 10, 0, 0),
                  "update_time": datetime(2026, 8, 2, 11, 0, 0)}], 1)

    def get_by_id(self, student_id, tenant_id=None):
        return {"student_id": int(student_id), "tenant_id": "DEMO", "school_id": 38,
                "account": "masked", "password": "masked", "name": "测试", "status": 0}


def test_healthz():
    assert TestClient(app).get("/healthz").json() == {"status": "ok"}


def test_student_list_matches_java_field_names_types_and_dates():
    app.dependency_overrides[repository] = lambda: FakeRepository()
    try:
        response = TestClient(app).get("/education/student/list?pageNum=2&pageSize=3")
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["rows"][0]["studentId"] == "9000000000000000001"
        assert body["rows"][0]["schoolId"] == "38"
        assert set(body["rows"][0]) == {
            "studentId", "tenantId", "schoolId", "account", "password", "openId", "name",
            "studyGrade", "major", "phone", "idCard", "status", "loginStatus", "loginMessage",
            "loginCheckedAt", "createTime", "updateTime",
        }
        assert body["rows"][0]["loginCheckedAt"] == "2026-09-01 09:00:00"
    finally:
        app.dependency_overrides.clear()


def test_readyz_checks_dependencies(monkeypatch):
    class Healthy:
        def __init__(self, settings):
            pass

        def ping(self):
            return True

    monkeypatch.setattr(main_module, "Database", Healthy)
    monkeypatch.setattr(main_module, "RedisStore", Healthy)
    response = TestClient(app).get("/readyz")
    assert response.status_code == 200
    assert response.json()["mysql"] == "ok"
    assert response.json()["redis"] == "ok"


def test_tiku_failure_route_is_under_runner_prefix():
    calls = []

    class FakeTaskRepository:
        def record_tiku_failure(self, payload):
            calls.append(payload)

    app.dependency_overrides[task_repository] = lambda: FakeTaskRepository()
    try:
        response = TestClient(app).post("/education/runner/tiku-failures", json={"reason": "not found"})
        assert response.status_code == 200
        assert calls[0]["reason"] == "not found"
    finally:
        app.dependency_overrides.clear()


def test_internal_login_check_uses_registry_and_does_not_echo_credentials(monkeypatch):
    class Result:
        ok = True
        code = "login_ok"
        message = "登录检测通过"
        data = {"studentName": "测试学生"}

    class Adapter:
        def login(self, context):
            assert context.password == "masked-password"
            return Result()

    class Registry:
        def resolve_name(self, payload):
            return "mock"

        def get(self, name):
            return Adapter()

    monkeypatch.setattr("app.api.internal_runner.AdapterRegistry", Registry)
    response = TestClient(app).post(
        "/internal/runner/login-check",
        json={"studentId": "9000000000000000001", "account": "masked-account", "password": "masked-password", "platformName": "未知平台"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["studentName"] == "测试学生"
    assert "password" not in body


def test_internal_login_check_rejects_wrong_configured_token(monkeypatch):
    monkeypatch.setenv("EDUCATION_INTERNAL_TOKEN", "expected-token")
    response = TestClient(app).post(
        "/internal/runner/login-check",
        json={"studentId": "1", "account": "a", "password": "b"},
        headers={"X-Runner-Token": "wrong-token"},
    )
    assert response.status_code == 401


def test_student_login_check_uses_go_and_persists_personal_info(monkeypatch):
    import app.api.students as students_module
    from app.api.internal_runner import LoginCheckRequest

    calls = []

    class FakeDatabase:
        pass

    class FakeStudentRepository:
        def __init__(self, database):
            self.database = database

        def update_login_status(self, student_id, status, message):
            calls.append(("login-status", student_id, status, message))
            return True

    class FakeTaskRepository:
        def __init__(self, database):
            self.database = database

        def update_student_profile(self, payload):
            calls.append(("profile", payload))
            return True

        def upsert_course_progress(self, payload):
            calls.append(("course", payload))

        def upsert_exam_progress(self, payload):
            calls.append(("exam", payload))

        def replace_course_progress_items(self, payload):
            calls.append(("course-items", payload))
            return 0

        def replace_exam_progress_items(self, payload):
            calls.append(("exam-items", payload))
            return 0

    login_request = LoginCheckRequest(
        tenantId="T",
        studentId="1",
        schoolId="38",
        account="real-account",
        password="real-password",
        platformName="学习通",
    )
    go_response = {
        "ok": True,
        "code": "OK",
        "adapter": "XUEXITONG",
        "message": "登录检测通过",
        "studentName": "真实学生",
        "profileSnapshot": '{"studentName":"真实学生"}',
    }

    monkeypatch.setattr(students_module, "Database", lambda settings: FakeDatabase())
    monkeypatch.setattr(students_module, "_load_login_context", lambda request, database: login_request)
    monkeypatch.setattr(students_module, "StudentRepository", FakeStudentRepository)
    monkeypatch.setattr(students_module, "TaskRepository", FakeTaskRepository)
    go_calls = []
    monkeypatch.setattr(students_module, "go_runner_login_check", lambda request: (go_calls.append(request) or go_response))
    monkeypatch.setattr(students_module, "_check", lambda request: (_ for _ in ()).throw(AssertionError("Python adapter must not be used")))

    response = TestClient(app).post(
        "/education/student/login-check",
        json={"studentId": "1", "orderId": "9000000000000000003"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["studentName"] == "真实学生"
    assert go_calls[0]["studentId"] == 1
    assert go_calls[0]["schoolId"] == 38
    assert calls[0][0:3] == ("login-status", "1", 1)
    assert calls[1][0] == "profile"


def test_student_login_check_rejects_order_student_mismatch(monkeypatch):
    import app.api.students as students_module
    from fastapi import HTTPException

    monkeypatch.setattr(
        students_module,
        "_load_login_context",
        lambda request, database: (_ for _ in ()).throw(HTTPException(status_code=400, detail="订单与学员不匹配")),
    )
    response = TestClient(app).post(
        "/education/student/login-check",
        json={"studentId": "1", "orderId": "9000000000000000003"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "订单与学员不匹配"


def test_load_login_context_uses_order_school_and_rejects_mismatch():
    import app.api.students as students_module
    from fastapi import HTTPException
    from app.api.students import StudentLoginCheckRequest

    class Cursor:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def execute(self, sql, params):
            self.params = params

        def fetchone(self):
            return {
                "order_tenant_id": "T",
                "student_id": 2,
                "school_id": 88,
                "account": "account",
                "password": "password",
                "open_id": None,
                "school_name": "订单学校",
                "school_url": "https://school.example",
                "access_type": 1,
                "access_address": "https://school.example/login",
                "school_fid": "fid",
                "platform_name": "学习通",
            }

    class Connection:
        def cursor(self):
            return Cursor()

    class FakeDatabase:
        def connection(self):
            class Context:
                def __enter__(self_inner):
                    return Connection()

                def __exit__(self_inner, *_):
                    return False

            return Context()

    with pytest.raises(HTTPException) as exc_info:
        students_module._load_login_context(
            StudentLoginCheckRequest(studentId="1", orderId="9000000000000000003"),
            FakeDatabase(),
        )
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "订单与学员不匹配"


def test_auth_login_and_me_do_not_expose_password_hash(monkeypatch):
    from app.application.auth import AuthService

    stored = {"user_id": 9000000000000000001, "tenant_id": "T", "username": "admin", "password_hash": AuthService.hash_password("correct-password"), "nick_name": "管理员", "role": 9, "status": 0}

    class FakeUserRepository:
        def get_by_username(self, username, tenant_id=None):
            return stored if username == "admin" and (tenant_id is None or tenant_id == "T") else None

        def get_by_id(self, user_id):
            return stored if str(user_id) == str(stored["user_id"]) else None

        def touch_login(self, user_id):
            return None

    monkeypatch.setenv("EDUCATION_AUTH_SECRET", "unit-secret")
    app.dependency_overrides[auth_repository] = lambda: FakeUserRepository()
    try:
        client = TestClient(app)
        response = client.post("/education/auth/login", json={"username": "admin", "password": "correct-password", "tenantId": "T"})
        assert response.status_code == 200
        body = response.json()
        assert body["data"]["access_token"] == body["data"]["accessToken"]
        assert body["data"]["user"]["user_id"] == "9000000000000000001"
        assert "password_hash" not in body["data"]["user"]
        me = client.get("/education/auth/me", headers={"Authorization": f"Bearer {body['data']['accessToken']}"})
        assert me.status_code == 200
        assert me.json()["data"]["username"] == "admin"
        info = client.get("/education/auth/info", headers={"Authorization": f"Bearer {body['data']['accessToken']}"})
        assert info.status_code == 200
        assert info.json()["data"]["user"]["userId"] == "9000000000000000001"
        assert info.json()["data"]["roles"] == ["admin"]
        assert client.get("/education/auth/code").json()["data"]["captchaEnabled"] is False
        assert client.post("/education/auth/logout").status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_auth_login_accepts_legacy_sys_user_repository(monkeypatch):
    from app.application.auth import AuthService

    class LegacyUserRepository:
        def get_by_username(self, username, tenant_id=None):
            return {
                "user_id": 10001,
                "tenant_id": "T10001",
                "username": "tenant_admin",
                "password_hash": AuthService.hash_password("wrong-format"),
                "nick_name": "管理员",
                "role": 9,
                "status": 0,
                "legacy_password": "$2b$12$placeholder",
            }

        def touch_login(self, user_id):
            return None

    monkeypatch.setenv("EDUCATION_AUTH_SECRET", "unit-secret")
    monkeypatch.setattr("app.api.auth._verify_legacy_password", lambda password, encoded: password == "123456" and encoded.startswith("$2"))
    app.dependency_overrides[auth_repository] = lambda: LegacyUserRepository()
    try:
        client = TestClient(app)
        response = client.post("/education/auth/login", json={"username": "tenant_admin", "password": "123456", "tenantId": "T10001"})
        assert response.status_code == 200
        assert response.json()["data"]["user"]["username"] == "tenant_admin"
    finally:
        app.dependency_overrides.clear()


def test_auth_bootstrap_requires_token_and_only_allows_empty_user_store(monkeypatch):
    calls = []

    class EmptyRepository:
        def count(self):
            return 0

        def create(self, tenant_id, username, password_hash, nick_name, role, status):
            calls.append((tenant_id, username, password_hash.startswith("pbkdf2_sha256$"), role, status))
            return "9000000000000000002"

    monkeypatch.setenv("EDUCATION_BOOTSTRAP_TOKEN", "bootstrap-secret")
    app.dependency_overrides[auth_repository] = lambda: EmptyRepository()
    try:
        client = TestClient(app)
        denied = client.post("/education/auth/bootstrap", json={"username": "admin", "password": "long-password", "tenantId": "T"})
        assert denied.status_code == 401
        created = client.post("/education/auth/bootstrap", json={"username": "admin", "password": "long-password", "tenantId": "T"}, headers={"X-Bootstrap-Token": "bootstrap-secret"})
        assert created.status_code == 200
        assert created.json()["data"]["userId"] == "9000000000000000002"
        assert calls == [("T", "admin", True, 9, 0)]
    finally:
        app.dependency_overrides.clear()


def test_claim_accepts_legacy_json_contract():
    calls = []

    class FakeTaskRepository:
        def claim(self, limit, runner_id, task_types=None):
            calls.append((limit, runner_id, task_types))
            return [{"taskId": "1"}]

    app.dependency_overrides[task_repository] = lambda: FakeTaskRepository()
    try:
        response = TestClient(app).post(
            "/education/runner/tasks/claim",
            json={"limit": 3, "taskTypes": [1, 2], "runnerId": "runner-a"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["claimedCount"] == 1
        assert calls == [(3, "runner-a", [1, 2])]
    finally:
        app.dependency_overrides.clear()


def test_heartbeat_requires_runner_id():
    class FakeTaskRepository:
        def touch_heartbeat(self, task_id, runner_id):
            return task_id == "1" and runner_id == "runner-a"

    app.dependency_overrides[task_repository] = lambda: FakeTaskRepository()
    try:
        response = TestClient(app).post("/education/runner/tasks/1/heartbeat", json={"runnerId": "runner-a"})
        assert response.status_code == 200
        assert response.json()["data"]["accepted"] is True
    finally:
        app.dependency_overrides.clear()


def test_progress_item_and_profile_routes_delegate_to_repository():
    calls = []

    class FakeTaskRepository:
        def upsert_course_progress(self, payload):
            calls.append(("course-summary", payload))

        def upsert_exam_progress(self, payload):
            calls.append(("exam-summary", payload))

        def replace_course_progress_items(self, payload):
            calls.append(("course", payload))
            return 2

        def replace_exam_progress_items(self, payload):
            calls.append(("exam", payload))
            return 1

        def update_student_profile(self, payload):
            calls.append(("profile", payload))
            return True

    app.dependency_overrides[task_repository] = lambda: FakeTaskRepository()
    try:
        client = TestClient(app)
        assert client.post("/education/runner/course-progress/upsert", json={"orderId": "1", "tenantId": "T"}).status_code == 200
        assert client.post("/education/runner/exam-progress/upsert", json={"orderId": "1", "tenantId": "T"}).status_code == 200
        assert client.post("/education/runner/course-progress/items", json={"orderId": "1", "tenantId": "T", "items": [{"courseName": "课程"}]}).json()["data"]["written"] == 2
        assert client.post("/education/runner/exam-progress/items", json={"orderId": "1", "tenantId": "T", "items": []}).json()["data"]["written"] == 1
        assert client.post("/education/runner/students/profile", json={"studentId": "1", "tenantId": "T", "studentName": "新名"}).json()["data"]["accepted"] is True
        snapshot = client.post(
            "/education/runner/progress/snapshot",
            json={
                "orderId": "1",
                "tenantId": "T",
                "courseSnapshot": '<div class="course"><span class="course-name">课程</span>100%</div>',
                "examSnapshot": '<table><tr><th>考试名称</th></tr><tr><td>期末</td></tr></table>',
            },
        )
        assert snapshot.status_code == 200
        assert snapshot.json()["data"] == {"courseItems": 2, "examItems": 1}
        assert [item[0] for item in calls] == ["course-summary", "exam-summary", "course", "exam", "profile", "course", "exam"]
    finally:
        app.dependency_overrides.clear()


def test_progress_routes_accept_numeric_legacy_ids_and_normalize_them():
    calls = []

    class FakeTaskRepository:
        def upsert_course_progress(self, payload):
            calls.append(payload)

    app.dependency_overrides[task_repository] = lambda: FakeTaskRepository()
    try:
        response = TestClient(app).post(
            "/education/runner/course-progress/upsert",
            json={"orderId": 1001, "tenantId": "T", "videoStatus": 1},
        )
        assert response.status_code == 200
        assert calls == [{"orderId": "1001", "tenantId": "T", "courseName": None, "term": None,
                          "videoStatus": 1, "videoNote": None, "videoTime": None, "workStatus": 0,
                          "workNote": None, "workTime": None, "examStatus": 0, "examNote": None,
                          "examTime": None}]
    finally:
        app.dependency_overrides.clear()
