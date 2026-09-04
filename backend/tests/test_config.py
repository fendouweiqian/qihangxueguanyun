from app.config import Settings
from app.infrastructure.redis_client import RedisStore
from app.application.auth import AuthService


def test_settings_defaults(monkeypatch):
    monkeypatch.delenv("EDUCATION_DB_PASSWORD", raising=False)
    settings = Settings.from_env()
    assert settings.db_port == 3307
    assert settings.db_password == ""


def test_bigint_ids_are_strings():
    from app.domain.student import Student

    student = Student.model_validate({
        "student_id": 9000000000000000001,
        "tenant_id": "DEMO",
        "school_id": 38,
        "account": "masked",
        "password": "masked",
        "name": "测试",
        "status": 0,
    })
    assert student.student_id == "9000000000000000001"
    assert student.school_id == "38"


def test_redis_password_is_environment_only(monkeypatch):
    monkeypatch.setenv("EDUCATION_REDIS_PASSWORD", "temporary")
    assert Settings.from_env().redis_password == "temporary"


def test_redis_json_store_applies_prefix_and_ttl(monkeypatch):
    calls = []

    class Client:
        def get(self, key):
            calls.append(("get", key))
            return '{"cookie":"value"}'

        def setex(self, key, ttl, value):
            calls.append(("setex", key, ttl, value))

        def delete(self, key):
            calls.append(("delete", key))

    store = RedisStore(Settings(redis_key_prefix="education:"))
    monkeypatch.setattr(store, "_get_client", lambda: Client())
    assert store.get_json("session") == {"cookie": "value"}
    store.set_json("session", {"cookie": "new"}, 0)
    store.delete("session")
    assert calls[0] == ("get", "education:session")
    assert calls[1][0:3] == ("setex", "education:session", 1)
    assert calls[2] == ("delete", "education:session")


def test_auth_password_hash_and_signed_token_round_trip():
    password_hash = AuthService.hash_password("correct-password")
    assert AuthService.verify_password("correct-password", password_hash) is True
    assert AuthService.verify_password("wrong-password", password_hash) is False
    service = AuthService("unit-test-secret", ttl_seconds=300)
    token = service.issue({"user_id": 9000000000000000001, "tenant_id": "T", "username": "admin"})
    assert service.verify(token)["sub"] == "9000000000000000001"
    body, signature = token.split(".")
    tampered = body + "x." + signature
    try:
        service.verify(tampered)
    except ValueError:
        pass
    else:
        raise AssertionError("tampered token must be rejected")
