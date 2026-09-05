from app.api.students import StudentLoginCheckRequest, _load_login_context


class _Cursor:
    def __init__(self):
        self.sql = ""
        self.params = ()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params):
        self.sql = sql
        self.params = params

    def fetchone(self):
        return {
            "tenant_id": "T1",
            "student_id": "9001",
            "school_id": "38",
            "account": "account",
            "password": "password",
            "open_id": "",
            "school_name": "测试学校",
            "school_url": "https://school.example",
            "access_type": 0,
            "access_address": "",
            "school_fid": "",
            "platform_name": "mock",
        }


class _Connection:
    def __init__(self):
        self.cursor_instance = _Cursor()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return self.cursor_instance


class _Database:
    def __init__(self):
        self.connection_instance = _Connection()

    def connection(self):
        return self.connection_instance


def test_login_context_uses_order_record_when_order_id_is_present():
    database = _Database()

    context = _load_login_context(
        StudentLoginCheckRequest(studentId="9001", orderId="missing-order"),
        database,
    )

    assert context.studentId == "9001"
    assert context.schoolId == "38"
    assert context.refreshSnapshots is True
    assert database.connection_instance.cursor_instance.params == ("missing-order",)
    assert "FROM ea_order" in database.connection_instance.cursor_instance.sql
