"""Go 执行器的 YAML 配置、进程管理和内部登录客户端。"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
import time
from typing import Any

import requests
import yaml


class GoRunnerError(RuntimeError):
    """Go 执行器配置或调用失败。"""


class GoRunnerUnavailable(GoRunnerError):
    """Go 执行器当前不可访问。"""


@dataclass(frozen=True)
class GoRunnerConfig:
    """Go Worker 运行时配置。"""

    enabled: bool
    binary: Path
    config: Path
    internal_url: str
    internal_token: str
    start_timeout_seconds: int = 15
    request_timeout_seconds: int = 120


def _project_root() -> Path:
    """返回业务项目根目录。"""
    return Path(__file__).resolve().parents[3]


def _resolve_path(value: str, root: Path) -> Path:
    """按集成 YAML 所在目录解析其中的相对路径。"""
    path = Path(value).expanduser()
    return path if path.is_absolute() else (root / path).resolve()


def _go_internal_token(config_path: Path) -> str:
    """从 Go 配置读取内部 HTTP 令牌，避免在两份配置中重复保存。"""
    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return ""
    internal = raw.get("internalHttp") if isinstance(raw, dict) else None
    return str(internal.get("token") or "").strip() if isinstance(internal, dict) else ""


def load_go_runner_config(path: str | Path | None = None) -> GoRunnerConfig:
    """读取 Go Worker 集成 YAML；配置不存在时返回禁用配置。"""
    config_file = Path(path) if path is not None else _project_root() / "config" / "runner-integration.yaml"
    config_file = config_file.expanduser().resolve()
    disabled = GoRunnerConfig(False, Path(""), Path(""), "", "")
    if not config_file.is_file():
        return disabled
    try:
        raw = yaml.safe_load(config_file.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise GoRunnerError(f"读取 Go Worker YAML 失败: {config_file}") from exc
    section = raw.get("goRunner") if isinstance(raw, dict) else None
    if not isinstance(section, dict):
        return disabled
    root = config_file.parent
    binary_value = str(section.get("binary") or "").strip()
    go_config_value = str(section.get("config") or "").strip()
    if not binary_value or not go_config_value:
        raise GoRunnerError("Go Worker YAML 必须配置 binary 和 config")
    go_config = _resolve_path(go_config_value, root)
    token = str(section.get("internalToken") or "").strip() or _go_internal_token(go_config)
    internal_url = str(section.get("internalUrl") or "").strip().rstrip("/")
    if not internal_url:
        raise GoRunnerError("Go Worker YAML 必须配置 internalUrl")
    return GoRunnerConfig(
        enabled=bool(section.get("enabled", True)),
        binary=_resolve_path(binary_value, root),
        config=go_config,
        internal_url=internal_url,
        internal_token=token,
        start_timeout_seconds=max(1, int(section.get("startTimeoutSeconds", 15))),
        request_timeout_seconds=max(1, int(section.get("requestTimeoutSeconds", 120))),
    )


class GoRunnerClient:
    """调用 Go Worker 内部登录接口的客户端。"""

    def __init__(self, config: GoRunnerConfig):
        self.config = config

    def login_check(self, payload: dict[str, Any]) -> dict[str, Any]:
        """执行真实平台登录检测并返回 Go 的脱敏响应。"""
        headers = {"X-Runner-Token": self.config.internal_token} if self.config.internal_token else {}
        try:
            response = requests.post(
                f"{self.config.internal_url}/internal/runner/login-check",
                json=payload,
                headers=headers,
                timeout=self.config.request_timeout_seconds,
                proxies={"http": "", "https": ""},
            )
        except (requests.RequestException, OSError) as exc:
            raise GoRunnerUnavailable("Go Worker 登录接口不可访问") from exc
        try:
            body = response.json()
        except (ValueError, json.JSONDecodeError) as exc:
            raise GoRunnerError(f"Go Worker 返回了无效响应（HTTP {response.status_code}）") from exc
        if not isinstance(body, dict):
            raise GoRunnerError("Go Worker 返回格式错误")
        if response.status_code >= 400:
            body.setdefault("ok", False)
        return body


class GoRunnerProcess:
    """管理由 Python 后端启动的 Go Worker 子进程。"""

    def __init__(self, config: GoRunnerConfig):
        self.config = config
        self.process: subprocess.Popen[bytes] | None = None

    def _reachable(self) -> bool:
        """通过允许 404/405 的探测确认内部 HTTP 端口已监听。"""
        try:
            response = requests.get(
                f"{self.config.internal_url}/internal/runner/login-check",
                timeout=1,
                proxies={"http": "", "https": ""},
            )
            return response.status_code in range(200, 500)
        except (requests.RequestException, OSError):
            return False

    def start(self) -> None:
        """启动 Go Worker，或复用已经监听相同地址的进程。"""
        if not self.config.enabled:
            return
        if self.process is not None and self.process.poll() is None:
            return
        if self._reachable():
            return
        if not self.config.binary.is_file():
            raise GoRunnerUnavailable(f"Go Worker 二进制不存在: {self.config.binary}")
        if not self.config.config.is_file():
            raise GoRunnerUnavailable(f"Go Worker 配置不存在: {self.config.config}")
        try:
            self.process = subprocess.Popen(
                [str(self.config.binary), "worker", f"--config={self.config.config}"],
                cwd=str(self.config.binary.parent),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError as exc:
            raise GoRunnerUnavailable("Go Worker 子进程启动失败") from exc
        deadline = time.monotonic() + self.config.start_timeout_seconds
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise GoRunnerUnavailable("Go Worker 启动后立即退出")
            if self._reachable():
                return
            time.sleep(0.2)
        self.stop()
        raise GoRunnerUnavailable("Go Worker 启动超时")

    def stop(self) -> None:
        """终止由当前后端启动的 Go Worker。"""
        if self.process is None or self.process.poll() is not None:
            return
        self.process.terminate()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=5)


class GoRunnerService:
    """组合 YAML 配置、进程管理和登录调用。"""

    def __init__(self, config_path: str | Path | None = None):
        self.config_path = config_path
        self.config = load_go_runner_config(config_path)
        self.process = GoRunnerProcess(self.config)
        self.client = GoRunnerClient(self.config)

    def start(self) -> None:
        """按 YAML 配置启动 Go Worker。"""
        self.process.start()

    def stop(self) -> None:
        """停止当前后端启动的 Go Worker。"""
        self.process.stop()

    def login_check(self, payload: dict[str, Any]) -> dict[str, Any]:
        """确保 Go Worker 可用后执行真实登录检测。"""
        if not self.config.enabled:
            raise GoRunnerUnavailable("Go Worker 未启用，请配置 config/runner-integration.yaml")
        self.start()
        return self.client.login_check(payload)


_service = GoRunnerService()


def go_runner_login_check(payload: dict[str, Any]) -> dict[str, Any]:
    """使用默认 YAML 配置调用 Go Worker 登录检测。"""
    return _service.login_check(payload)


def start_go_runner() -> None:
    """应用启动时启动 Go Worker。"""
    _service.start()


def stop_go_runner() -> None:
    """应用关闭时停止 Go Worker。"""
    _service.stop()
