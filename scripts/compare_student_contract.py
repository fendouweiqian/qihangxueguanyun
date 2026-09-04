"""审计工具：比较原 Java 管理接口与目标 Python 接口的学生契约。

该脚本仅访问本地服务，认证信息只从环境变量读取，且不会输出学生字段值。
"""

from __future__ import annotations

import argparse
import json
import os
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


COMMON_FIELDS = (
    "studentId",
    "tenantId",
    "schoolId",
    "account",
    "password",
    "openId",
    "name",
    "studyGrade",
    "major",
    "phone",
    "idCard",
    "status",
    "loginStatus",
    "loginMessage",
    "loginCheckedAt",
    "createTime",
    "updateTime",
)
STRING_FIELDS = {
    "studentId",
    "tenantId",
    "account",
    "password",
    "openId",
    "name",
    "studyGrade",
    "major",
    "phone",
    "idCard",
    "loginMessage",
    "loginCheckedAt",
    "createTime",
    "updateTime",
}
INTEGER_FIELDS = {"status", "loginStatus"}
NORMALIZED_ID_FIELDS = {"schoolId"}


def _request_json(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """请求本地 JSON 接口，不记录请求体、响应体或认证头。"""
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request_headers = {"Content-Type": "application/json", **(headers or {})}
    request = Request(url, data=data, headers=request_headers, method=method)
    with urlopen(request, timeout=15) as response:
        if response.status >= 400:
            raise RuntimeError(f"local api returned HTTP {response.status}")
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("local api returned a non-object JSON response")
    return payload


def _source_headers(source_url: str) -> dict[str, str]:
    """登录原 Java 管理端并返回后续只读查询所需的认证头。"""
    tenant_id = os.getenv("EDUCATION_SOURCE_TENANT_ID", "")
    username = os.getenv("EDUCATION_SOURCE_USERNAME", "")
    password = os.getenv("EDUCATION_SOURCE_PASSWORD", "")
    client_id = os.getenv("EDUCATION_SOURCE_CLIENT_ID", "")
    if not all((tenant_id, username, password, client_id)):
        raise RuntimeError(
            "missing source login environment: EDUCATION_SOURCE_TENANT_ID, "
            "EDUCATION_SOURCE_USERNAME, EDUCATION_SOURCE_PASSWORD, EDUCATION_SOURCE_CLIENT_ID"
        )
    response = _request_json(
        f"{source_url.rstrip('/')}/auth/login",
        method="POST",
        body={
            "tenantId": tenant_id,
            "username": username,
            "password": password,
            "clientId": client_id,
            "grantType": "password",
        },
    )
    if response.get("code") != 200:
        raise RuntimeError(f"source login business code mismatch: {response.get('code')}")
    data = response.get("data")
    token = data.get("access_token") if isinstance(data, dict) else None
    if not token and isinstance(data, dict):
        token = data.get("accessToken")
    if not isinstance(token, str) or not token:
        raise RuntimeError("source login response did not contain an access token")
    return {"Authorization": f"Bearer {token}", "clientid": client_id}


def _validate_record(
    record_id: str,
    label: str,
    source: Any,
    target: Any,
    failures: list[str],
) -> None:
    """比较单条记录的字段集合、JSON 类型和值，不暴露字段内容。"""
    if not isinstance(source, dict) or not isinstance(target, dict):
        failures.append(f"{record_id}: {label}: invalid_record")
        return
    missing_found = False
    for side, record in (("source", source), ("target", target)):
        missing = sorted(set(COMMON_FIELDS) - record.keys())
        if missing:
            failures.append(f"{record_id}: {label}: {side}_missing={','.join(missing)}")
            missing_found = True
    if missing_found:
        return
    for field in COMMON_FIELDS:
        source_value = source.get(field)
        target_value = target.get(field)
        if field in NORMALIZED_ID_FIELDS:
            if source_value is not None and not isinstance(source_value, (int, str)):
                failures.append(f"{record_id}: {label}: source_type={field}:expected=id")
            if target_value is not None and not isinstance(target_value, str):
                failures.append(f"{record_id}: {label}: target_type={field}:expected=string")
            if source_value is not None:
                source_value = str(source_value)
        for side, value in (("source", source_value), ("target", target_value)):
            if field in STRING_FIELDS and value is not None and not isinstance(value, str):
                failures.append(f"{record_id}: {label}: {side}_type={field}:expected=string")
            if field in INTEGER_FIELDS and value is not None and not isinstance(value, int):
                failures.append(f"{record_id}: {label}: {side}_type={field}:expected=int")
        if source_value != target_value:
            failures.append(f"{record_id}: {label}: field={field}")


def _rows_by_id(body: dict[str, Any], label: str, expected_count: int) -> dict[str, dict[str, Any]]:
    """校验分页包络并按字符串学生 ID 建立索引。"""
    if body.get("code") != 200:
        raise RuntimeError(f"{label} list business code mismatch: {body.get('code')}")
    rows = body.get("rows")
    if not isinstance(rows, list) or len(rows) != expected_count:
        raise RuntimeError(f"{label} list count mismatch: expected={expected_count}")
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict) or row.get("studentId") is None:
            raise RuntimeError(f"{label} list contains a row without studentId")
        result[str(row["studentId"])] = row
    return result


def compare(source_url: str, target_url: str, limit: int) -> int:
    """通过原 Java 和目标 Python HTTP 接口比较列表及详情契约。"""
    headers = _source_headers(source_url)
    source_query = urlencode({"pageNum": 1, "pageSize": limit})
    target_query = urlencode({"page_num": 1, "page_size": limit})
    source_body = _request_json(
        f"{source_url.rstrip('/')}/education/student/list?{source_query}", headers=headers
    )
    target_body = _request_json(f"{target_url.rstrip('/')}/education/student/list?{target_query}")
    source_rows = _rows_by_id(source_body, "source", limit)
    target_rows = _rows_by_id(target_body, "target", limit)

    failures: list[str] = []
    for student_id, source_row in source_rows.items():
        target_row = target_rows.get(student_id)
        if target_row is None:
            failures.append(f"{student_id}: list: target_missing")
            continue
        _validate_record(student_id, "list", source_row, target_row, failures)

    for student_id in source_rows:
        source_detail = _request_json(
            f"{source_url.rstrip('/')}/education/student/{student_id}", headers=headers
        )
        target_detail = _request_json(f"{target_url.rstrip('/')}/education/student/{student_id}")
        if source_detail.get("code") != 200 or target_detail.get("code") != 200:
            failures.append(f"{student_id}: detail: business_code")
            continue
        _validate_record(
            student_id,
            "detail",
            source_detail.get("data"),
            target_detail.get("data"),
            failures,
        )

    if failures:
        print(f"comparison=failed records={len(source_rows)} differences={len(failures)}")
        for item in failures[:20]:
            print(item)
        return 1
    print(f"comparison=passed records={len(source_rows)} fields={len(COMMON_FIELDS)} views=list,detail")
    return 0


def main() -> int:
    """解析本地服务地址并执行契约对比。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-url", default="http://127.0.0.1:8280")
    parser.add_argument("--target-url", default="http://127.0.0.1:8281")
    parser.add_argument("--limit", type=int, default=3)
    args = parser.parse_args()
    return compare(args.source_url, args.target_url, max(1, min(args.limit, 3)))


if __name__ == "__main__":
    raise SystemExit(main())
