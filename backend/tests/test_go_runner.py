"""Go 执行器 YAML 配置和内部 HTTP 客户端测试。"""

from pathlib import Path

import pytest

from app.infrastructure.go_runner import (
    GoRunnerClient,
    GoRunnerConfig,
    GoRunnerUnavailable,
    load_go_runner_config,
)


def test_load_go_runner_config_resolves_relative_paths_and_token_from_go_yaml(tmp_path: Path):
    go_config = tmp_path / "runner.yaml"
    go_config.write_text(
        "internalHttp:\n  addr: '127.0.0.1:18089'\n  token: 'runner-token'\n",
        encoding="utf-8",
    )
    integration = tmp_path / "runner-integration.yaml"
    integration.write_text(
        "goRunner:\n"
        "  enabled: true\n"
        "  binary: './bin/runner'\n"
        "  config: './runner.yaml'\n"
        "  internalUrl: 'http://127.0.0.1:18089'\n",
        encoding="utf-8",
    )

    config = load_go_runner_config(integration)

    assert config.enabled is True
    assert config.binary == (tmp_path / "bin" / "runner").resolve()
    assert config.config == go_config.resolve()
    assert config.internal_url == "http://127.0.0.1:18089"
    assert config.internal_token == "runner-token"


def test_load_go_runner_config_missing_file_is_disabled(tmp_path: Path):
    config = load_go_runner_config(tmp_path / "missing.yaml")

    assert config.enabled is False


def test_go_runner_client_posts_token_and_returns_personal_info(monkeypatch):
    calls = []

    class Response:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "ok": True,
                "code": "OK",
                "adapter": "XUEXITONG",
                "message": "登录检测通过",
                "studentName": "测试学生",
                "profileSnapshot": "{\"studentName\":\"测试学生\"}",
            }

    def post(url, *, json, headers, timeout, **kwargs):
        calls.append((url, json, headers, timeout, kwargs))
        return Response()

    monkeypatch.setattr("app.infrastructure.go_runner.requests.post", post)
    client = GoRunnerClient(
        GoRunnerConfig(
            enabled=True,
            binary=Path("runner"),
            config=Path("config.yaml"),
            internal_url="http://127.0.0.1:18089",
            internal_token="runner-token",
            request_timeout_seconds=30,
        )
    )

    result = client.login_check({"studentId": "1", "account": "account", "password": "password"})

    assert result["ok"] is True
    assert result["studentName"] == "测试学生"
    assert calls[0][0] == "http://127.0.0.1:18089/internal/runner/login-check"
    assert calls[0][1]["password"] == "password"
    assert calls[0][2] == {"X-Runner-Token": "runner-token"}
    assert calls[0][3] == 30


def test_go_runner_client_reports_unavailable(monkeypatch):
    def post(*args, **kwargs):
        raise OSError("connection refused")

    monkeypatch.setattr("app.infrastructure.go_runner.requests.post", post)
    client = GoRunnerClient(
        GoRunnerConfig(
            enabled=True,
            binary=Path("runner"),
            config=Path("config.yaml"),
            internal_url="http://127.0.0.1:18089",
            internal_token="runner-token",
        )
    )

    with pytest.raises(GoRunnerUnavailable):
        client.login_check({"studentId": "1", "account": "a", "password": "p"})
