"""认证、当前用户和租户用户管理 API。"""

from __future__ import annotations

import hmac
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from app.application.auth import AuthService, _verify_legacy_password
from app.config import Settings
from app.domain.user import User
from app.infrastructure.db import Database, UserRepository


router = APIRouter(prefix="/education/auth", tags=["auth"])
user_router = APIRouter(prefix="/education/user", tags=["user"])


class LoginRequest(BaseModel):
    """用户名密码登录请求。"""

    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)
    tenantId: str | None = Field(default=None, max_length=20)


class UserCreateRequest(BaseModel):
    """创建租户用户请求。"""

    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=8, max_length=256)
    tenantId: str | None = Field(default=None, max_length=20)
    nickName: str | None = Field(default=None, max_length=64)
    role: int = Field(default=1, ge=1, le=99)
    status: int = Field(default=0, ge=0, le=1)


class UserUpdateRequest(BaseModel):
    """更新用户请求。"""

    nickName: str | None = Field(default=None, max_length=64)
    password: str | None = Field(default=None, min_length=8, max_length=256)
    role: int | None = Field(default=None, ge=1, le=99)
    status: int | None = Field(default=None, ge=0, le=1)


class BootstrapRequest(UserCreateRequest):
    """首次管理员初始化请求，角色固定为平台管理员。"""

    role: int = Field(default=9, ge=9, le=9)


def _repo() -> UserRepository:
    """创建用户仓储。"""
    return UserRepository(Database(Settings.from_env()))


def _auth() -> AuthService:
    """创建令牌服务。"""
    settings = Settings.from_env()
    return AuthService(settings.auth_secret, settings.auth_token_ttl_seconds)


def _bearer(authorization: str | None) -> str:
    """提取 Bearer 令牌，不接受其他认证方案。"""
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(status_code=401, detail="未授权")
    return token.strip()


def _claims(authorization: str | None) -> dict[str, Any]:
    """验证请求令牌并转换验证失败为 401。"""
    try:
        return _auth().verify(_bearer(authorization))
    except (RuntimeError, ValueError):
        raise HTTPException(status_code=401, detail="登录已失效")


def _admin_user(authorization: str | None, repo: UserRepository) -> dict[str, Any]:
    """验证用户存在、启用并拥有用户管理角色。"""
    claims = _claims(authorization)
    user = repo.get_by_id(str(claims["sub"]))
    if not user or int(user.get("status", 1)) != 0 or int(user.get("role", 0)) < 1:
        raise HTTPException(status_code=403, detail="无用户管理权限")
    return user


@router.post("/login")
def login(request: LoginRequest, repo: UserRepository = Depends(_repo)) -> dict[str, Any]:
    """校验租户用户密码并签发短期访问令牌。"""
    try:
        service = _auth()
        service.ensure_enabled()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    user = repo.get_by_username(request.username, request.tenantId)
    password_hash = str(user.get("password_hash") or "") if user else ""
    password_ok = bool(user and service.verify_password(request.password, password_hash))
    if user and not password_ok and user.get("legacy_password"):
        password_ok = _verify_legacy_password(request.password, str(user["legacy_password"]))
    if not user or int(user.get("status", 1)) != 0 or not password_ok:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    repo.touch_login(str(user["user_id"]))
    token = service.issue(user)
    return {
        "code": 200,
        "msg": "登录成功",
        "data": {
            "accessToken": token,
            "access_token": token,
            "user": User.model_validate(user).model_dump(mode="json"),
        },
    }


@router.get("/code")
def login_code() -> dict[str, Any]:
    """告知原管理端登录页本地环境不启用图片验证码。"""
    return {"code": 200, "msg": "操作成功", "data": {"captchaEnabled": False}}


@router.get("/tenant/list")
def login_tenants(repo: UserRepository = Depends(_repo)) -> dict[str, Any]:
    """返回登录页可选租户，不包含余额或其他业务数据。"""
    try:
        with repo.database.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT tenant_id, tenant_name FROM ea_tenant WHERE status=0 ORDER BY tenant_id")
                rows = list(cursor.fetchall())
    except Exception as exc:
        raise HTTPException(status_code=503, detail="数据库暂不可用") from exc
    tenants = [
        {"tenantId": str(row["tenant_id"]), "companyName": row.get("tenant_name") or str(row["tenant_id"])}
        for row in rows
    ]
    return {"code": 200, "msg": "操作成功", "data": {"tenantEnabled": True, "voList": tenants}}


@router.get("/info")
def info(authorization: str | None = Header(default=None), repo: UserRepository = Depends(_repo)) -> dict[str, Any]:
    """按原 Vue 管理端契约返回当前用户、角色和权限。"""
    claims = _claims(authorization)
    user = repo.get_by_id(str(claims["sub"]))
    if not user or int(user.get("status", 1)) != 0:
        raise HTTPException(status_code=401, detail="登录已失效")
    role = int(user.get("role", 0))
    user_view = {
        "userId": str(user["user_id"]),
        "tenantId": user.get("tenant_id"),
        "userName": user.get("username"),
        "nickName": user.get("nick_name") or user.get("username"),
        "avatar": "",
    }
    permissions = ["*:*:*"] if role >= 9 else ["education:*:*"]
    roles = ["admin"] if role >= 9 else ["tenant_admin"]
    return {"code": 200, "msg": "操作成功", "data": {"user": user_view, "roles": roles, "permissions": permissions}}


@router.post("/logout")
def logout() -> dict[str, Any]:
    """结束前端会话；访问令牌为无状态短期令牌，由前端立即清除。"""
    return {"code": 200, "msg": "退出成功"}


@router.post("/bootstrap")
def bootstrap(request: BootstrapRequest, x_bootstrap_token: str | None = Header(default=None), repo: UserRepository = Depends(_repo)) -> dict[str, Any]:
    """只在用户表为空时创建首个跨租户管理员。"""
    settings = Settings.from_env()
    if not settings.bootstrap_token:
        raise HTTPException(status_code=503, detail="EDUCATION_BOOTSTRAP_TOKEN is required")
    if not hmac.compare_digest(x_bootstrap_token or "", settings.bootstrap_token):
        raise HTTPException(status_code=401, detail="未授权")
    if repo.count() != 0:
        raise HTTPException(status_code=409, detail="初始管理员已存在")
    try:
        user_id = repo.create(request.tenantId, request.username, AuthService.hash_password(request.password), request.nickName, 9, 0)
    except Exception as exc:
        if "Duplicate" in str(exc) or "duplicate" in str(exc):
            raise HTTPException(status_code=409, detail="用户名已存在")
        raise
    return {"code": 200, "msg": "初始管理员创建成功", "data": {"userId": user_id}}


@router.get("/me")
def me(authorization: str | None = Header(default=None), repo: UserRepository = Depends(_repo)) -> dict[str, Any]:
    """返回当前登录用户公开信息。"""
    claims = _claims(authorization)
    user = repo.get_by_id(str(claims["sub"]))
    if not user or int(user.get("status", 1)) != 0:
        raise HTTPException(status_code=401, detail="登录已失效")
    return {"code": 200, "msg": "操作成功", "data": User.model_validate(user).model_dump(mode="json")}


@user_router.get("/list")
def list_users(tenant_id: str | None = None, limit: int = 100, authorization: str | None = Header(default=None), repo: UserRepository = Depends(_repo)) -> dict[str, Any]:
    """返回当前管理员租户范围内的用户列表。"""
    current = _admin_user(authorization, repo)
    scope = tenant_id if int(current.get("role", 0)) >= 9 and tenant_id else current.get("tenant_id")
    rows = repo.list_page(scope, limit)
    return {"code": 200, "msg": "操作成功", "rows": [User.model_validate(row).model_dump(mode="json") for row in rows], "total": len(rows)}


@user_router.post("")
def create_user(request: UserCreateRequest, authorization: str | None = Header(default=None), repo: UserRepository = Depends(_repo)) -> dict[str, Any]:
    """创建用户并仅返回公开字段。"""
    current = _admin_user(authorization, repo)
    if int(current.get("role", 0)) < 9 and request.tenantId != current.get("tenant_id"):
        raise HTTPException(status_code=403, detail="不能创建其他租户用户")
    try:
        user_id = repo.create(request.tenantId, request.username, AuthService.hash_password(request.password), request.nickName, request.role, request.status)
    except Exception as exc:
        if "Duplicate" in str(exc) or "duplicate" in str(exc):
            raise HTTPException(status_code=409, detail="用户名已存在")
        raise
    return {"code": 200, "msg": "操作成功", "data": {"userId": user_id}}


@user_router.patch("/{user_id}")
def update_user(user_id: str, request: UserUpdateRequest, authorization: str | None = Header(default=None), repo: UserRepository = Depends(_repo)) -> dict[str, Any]:
    """更新用户状态、角色、昵称或密码。"""
    current = _admin_user(authorization, repo)
    target = repo.get_by_id(user_id)
    if not target or (int(current.get("role", 0)) < 9 and target.get("tenant_id") != current.get("tenant_id")):
        raise HTTPException(status_code=404, detail="用户不存在")
    password_hash = AuthService.hash_password(request.password) if request.password else None
    accepted = repo.update(user_id, None if int(current.get("role", 0)) >= 9 else str(current.get("tenant_id") or ""), request.nickName, request.role, request.status, password_hash)
    return {"code": 200 if accepted else 404, "msg": "操作成功" if accepted else "用户不存在", "data": {"accepted": accepted}}


@user_router.delete("/{user_id}")
def delete_user(user_id: str, authorization: str | None = Header(default=None), repo: UserRepository = Depends(_repo)) -> dict[str, Any]:
    """删除租户范围内用户。"""
    current = _admin_user(authorization, repo)
    accepted = repo.delete(user_id, None if int(current.get("role", 0)) >= 9 else str(current.get("tenant_id") or ""))
    return {"code": 200 if accepted else 404, "msg": "操作成功" if accepted else "用户不存在", "data": {"accepted": accepted}}
