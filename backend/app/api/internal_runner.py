"""执行节点内部登录检测接口。"""

from __future__ import annotations

import hmac
from typing import Any

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.adapters.base import AdapterContext
from app.adapters.registry import AdapterRegistry
from app.config import Settings


router = APIRouter(prefix="/internal/runner", tags=["internal-runner"])


class LoginCheckRequest(BaseModel):
    """历史执行节点登录检测请求；凭证只在当前请求内存中使用。"""

    tenantId: str = ""
    studentId: str
    schoolId: str = ""
    account: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=256)
    openId: str = ""
    platformName: str = ""
    schoolName: str = ""
    schoolUrl: str = ""
    schoolFid: str = ""
    schoolAccessType: int = 0
    schoolAccessAddress: str = ""
    verifyCode: str = ""
    captchaId: str = ""
    captchaType: str = "slide"
    captchaVersion: str = "1.1.20"
    captchaX: int | None = None
    captchaApiUrl: str = ""
    captchaApiToken: str = ""
    captchaApiType: str = "10110"
    refreshSnapshots: bool = False


def _authorize(provided: str | None, settings: Settings) -> None:
    """校验可选的内部调用令牌；未配置令牌时保持本地兼容模式。"""
    expected = settings.internal_token
    if expected and not hmac.compare_digest(provided or "", expected):
        raise HTTPException(status_code=401, detail="未授权的执行节点请求")


def _context(request: LoginCheckRequest) -> AdapterContext:
    """把历史请求转换为统一适配器上下文，不记录密码。"""
    return AdapterContext(
        tenant_id=str(request.tenantId or "manual"),
        school_id=str(request.schoolId or ""),
        student_id=str(request.studentId),
        account=request.account,
        password=request.password,
        extra={
            "studentName": request.account,
            "studentOpenId": request.openId,
            "platformName": request.platformName,
            "schoolName": request.schoolName,
            "schoolUrl": request.schoolUrl,
            "schoolFid": request.schoolFid,
            "schoolAccessType": request.schoolAccessType,
            "schoolAccessAddress": request.schoolAccessAddress,
            "verifyCode": request.verifyCode,
            "captchaId": request.captchaId,
            "captchaType": request.captchaType,
            "captchaVersion": request.captchaVersion,
            "captchaX": request.captchaX,
            "captchaApiUrl": request.captchaApiUrl,
            "captchaApiToken": request.captchaApiToken,
            "captchaApiType": request.captchaApiType,
            "refreshSnapshots": request.refreshSnapshots,
        },
    )


def _check(request: LoginCheckRequest) -> tuple[str, Any]:
    """解析平台适配器并执行登录检测。"""
    registry = AdapterRegistry()
    adapter_name = registry.resolve_name(request.model_dump())
    if not adapter_name:
        return "", None
    result = registry.get(adapter_name).login(_context(request))
    return adapter_name, result


def _response(adapter_name: str, result: Any, *, include_snapshots: bool) -> dict[str, Any]:
    """生成与历史内部执行节点兼容的脱敏响应。"""
    data = result.data if result is not None and isinstance(result.data, dict) else {}
    ok = bool(result is not None and result.ok)
    body: dict[str, Any] = {
        "ok": ok,
        "code": result.code if result is not None and result.code else ("OK" if ok else "LOGIN_FAILED"),
        "adapter": adapter_name,
        "message": result.message if result is not None else "未识别的平台适配器",
    }
    if include_snapshots:
        for key in ("studentName", "profileSnapshot", "courseSnapshot", "examSnapshot"):
            value = data.get(key)
            if isinstance(value, str) and value:
                body[key] = value
    else:
        value = data.get("studentName")
        body["name"] = value if isinstance(value, str) else ""
    return body


@router.post("/login-check")
def login_check(request: LoginCheckRequest, x_runner_token: str | None = Header(default=None)) -> dict[str, Any]:
    """执行账号登录检测并返回平台档案快照；异常不回显凭证。"""
    _authorize(x_runner_token, Settings.from_env())
    adapter_name, result = _check(request)
    body = _response(adapter_name, result, include_snapshots=True)
    if not body["ok"]:
        raise HTTPException(status_code=400, detail=body)
    return body


@router.post("/fetch-name")
def fetch_name(request: LoginCheckRequest, x_runner_token: str | None = Header(default=None)) -> dict[str, Any]:
    """执行账号登录并返回可读姓名；不把账号回填为姓名。"""
    _authorize(x_runner_token, Settings.from_env())
    adapter_name, result = _check(request)
    body = _response(adapter_name, result, include_snapshots=False)
    if not body["ok"]:
        raise HTTPException(status_code=400, detail=body)
    return body
