"""学生账号查询 API。"""

from datetime import datetime
from io import BytesIO
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, UploadFile
from openpyxl import load_workbook
from pydantic import BaseModel, Field
import xlrd

from app.config import Settings
from app.domain.student import StudentListQuery
from app.infrastructure.db import Database, StudentRepository, TaskRepository
from app.api.auth import _claims
from app.api.internal_runner import LoginCheckRequest, _check, _response
from app.application.progress_parser import ProgressDetailParser

router = APIRouter(prefix="/education/student", tags=["student"])
logger = logging.getLogger(__name__)


class StudentRequest(BaseModel):
    """学生账号新增或修改请求。"""

    studentId: str | None = None
    tenantId: str | None = Field(default=None, max_length=20)
    schoolId: str
    account: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)
    openId: str | None = None
    name: str = Field(default="", max_length=64)
    studyGrade: str | None = None
    major: str | None = None
    phone: str | None = None
    idCard: str | None = None
    status: int = Field(default=0, ge=0, le=1)


class StudentLoginCheckRequest(BaseModel):
    """管理端登录检测请求；账号密码由学生和订单记录补齐。"""

    studentId: str | int
    orderId: str | int | None = None


def _load_login_context(request: StudentLoginCheckRequest, database: Database) -> LoginCheckRequest:
    """按学生和订单读取平台登录上下文，不向日志或响应暴露密码。"""
    student_id = str(request.studentId)
    order_id = str(request.orderId) if request.orderId is not None else ""
    # 登录检测的凭证和学校配置属于学员主记录。订单仅用于成功后的进度快照，
    # 不能因为历史订单被清理、跨租户或尚未同步而阻断账号登录检测。
    sql = (
        "SELECT s.tenant_id,s.student_id,s.school_id,s.account,s.password,s.open_id,"
        "sc.school_name,sc.school_url,sc.access_type,sc.access_address,sc.school_fid,p.platform_name "
        "FROM ea_student s LEFT JOIN ea_school sc ON sc.school_id=s.school_id "
        "LEFT JOIN ea_platform p ON p.platform_id=sc.platform_id WHERE s.student_id=%s"
    )
    params = (student_id,)
    try:
        with database.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                row = cursor.fetchone()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="数据库暂不可用") from exc
    if not row:
        raise HTTPException(status_code=404, detail="学员不存在")
    if not row.get("account") or not row.get("password"):
        raise HTTPException(status_code=400, detail="学员账号或密码为空")
    if not row.get("school_id"):
        raise HTTPException(status_code=400, detail="学员未配置学校")
    return LoginCheckRequest(
        tenantId=str(row.get("tenant_id") or ""),
        studentId=student_id,
        schoolId=str(row.get("school_id") or ""),
        account=str(row["account"]),
        password=str(row["password"]),
        openId=str(row.get("open_id") or ""),
        platformName=str(row.get("platform_name") or ""),
        schoolName=str(row.get("school_name") or ""),
        schoolUrl=str(row.get("school_url") or ""),
        schoolFid=str(row.get("school_fid") or ""),
        schoolAccessType=int(row.get("access_type") or 0),
        schoolAccessAddress=str(row.get("access_address") or ""),
        refreshSnapshots=bool(order_id),
    )


def repository() -> StudentRepository:
    """创建当前请求使用的学生仓储。"""
    return StudentRepository(Database(Settings.from_env()))


def _format_datetime(value: datetime | None) -> str | None:
    """按原 Java 管理接口格式序列化时间，空值保持 null。"""
    return value.strftime("%Y-%m-%d %H:%M:%S") if value is not None else None


def _student_payload(row: dict[str, Any]) -> dict[str, Any]:
    """将领域字段映射为原管理接口的 camelCase 兼容响应。"""
    return {
        "studentId": str(row["student_id"]),
        "tenantId": str(row["tenant_id"]),
        "schoolId": str(row["school_id"]),
        "account": row.get("account"),
        "password": row.get("password"),
        "openId": row.get("open_id"),
        "name": row.get("name"),
        "studyGrade": row.get("study_grade"),
        "major": row.get("major"),
        "phone": row.get("phone"),
        "idCard": row.get("id_card"),
        "status": row.get("status"),
        "loginStatus": row.get("login_status"),
        "loginMessage": row.get("login_message"),
        "loginCheckedAt": _format_datetime(row.get("login_checked_at")),
        "createTime": _format_datetime(row.get("create_time")),
        "updateTime": _format_datetime(row.get("update_time")),
    }


def _cell_text(value: Any) -> str:
    """把 Excel 单元格转换成稳定文本，避免整数账号出现 .0。"""
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _parse_student_rows(content: bytes, suffix: str) -> list[tuple[str, str, str]]:
    """解析原导入模板中的账号、密码和姓名列。"""
    if suffix == ".xlsx":
        workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
        values = list(workbook.active.iter_rows(values_only=True))
        workbook.close()
    elif suffix == ".xls":
        workbook = xlrd.open_workbook(file_contents=content)
        sheet = workbook.sheet_by_index(0)
        values = [sheet.row_values(index) for index in range(sheet.nrows)]
    else:
        raise ValueError("仅允许导入 xls、xlsx 文件")
    if not values:
        raise ValueError("导入文件不能为空")
    headers = {_cell_text(value): index for index, value in enumerate(values[0])}
    if "账号" not in headers or "密码" not in headers:
        raise ValueError("导入文件必须包含账号、密码列")
    result: list[tuple[str, str, str]] = []
    for row_number, row in enumerate(values[1:], start=2):
        account = _cell_text(row[headers["账号"]] if headers["账号"] < len(row) else None)
        password = _cell_text(row[headers["密码"]] if headers["密码"] < len(row) else None)
        name_index = headers.get("姓名")
        name = _cell_text(row[name_index] if name_index is not None and name_index < len(row) else None)
        if not account and not password and not name:
            continue
        if not account or not password:
            raise ValueError(f"第 {row_number} 行账号和密码不能为空")
        result.append((account, password, name))
    if not result:
        raise ValueError("导入文件没有有效学员数据")
    return result


@router.get("/list")
def list_students(
    tenant_id: str | None = Query(default=None, alias="tenantId"),
    school_id: str | None = Query(default=None, alias="schoolId"),
    account: str | None = Query(default=None),
    name: str | None = Query(default=None),
    phone: str | None = Query(default=None),
    status: int | None = Query(default=None),
    page_num: int = Query(default=1, ge=1, alias="pageNum"),
    page_size: int = Query(default=10, ge=1, le=10000, alias="pageSize"),
    repo: StudentRepository = Depends(repository),
) -> dict:
    """返回与旧管理接口一致的学生分页字段。"""
    query = StudentListQuery(
        tenant_id=tenant_id,
        school_id=school_id,
        account=account,
        name=name,
        phone=phone,
        status=status,
        page_num=page_num,
        page_size=page_size,
    )
    rows, total = repo.list_page(query)
    return {"code": 200, "msg": "操作成功", "rows": [_student_payload(row) for row in rows], "total": total}


@router.post("/import")
async def import_students(
    file: UploadFile = File(...),
    school_id: str = Query(alias="schoolId"),
    authorization: str | None = Header(default=None),
    repo: StudentRepository = Depends(repository),
) -> dict:
    """导入学员表格，学校来自表单，租户来自已验证登录令牌。"""
    claims = _claims(authorization)
    suffix = Path(file.filename or "").suffix.lower()
    content = await file.read(10 * 1024 * 1024 + 1)
    await file.close()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="导入文件不能超过 10MB")
    try:
        rows = _parse_student_rows(content, suffix)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    now = datetime.now()
    values = [
        (str(claims["tenant"]), school_id, account, password, name, 0, now, now)
        for account, password, name in rows
    ]
    with repo.database.connection() as conn:
        with conn.cursor() as cursor:
            cursor.executemany(
                "INSERT INTO ea_student (tenant_id,school_id,account,password,name,status,"
                "create_time,update_time) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                values,
            )
        conn.commit()
    return {"code": 200, "msg": f"成功导入 {len(values)} 条学员数据", "data": {"count": len(values)}}


@router.get("/{student_id}")
def get_student(student_id: str, tenant_id: str | None = Query(default=None), repo: StudentRepository = Depends(repository)) -> dict:
    """返回单个学生账号的兼容视图。"""
    row = repo.get_by_id(student_id, tenant_id)
    if row is None:
        raise HTTPException(status_code=404, detail="学员不存在")
    return {"code": 200, "msg": "操作成功", "data": _student_payload(row)}


@router.post("")
def create_student(
    request: StudentRequest,
    authorization: str | None = Header(default=None),
    repo: StudentRepository = Depends(repository),
) -> dict:
    """创建学生账号记录，未传租户时使用登录租户。"""
    database = repo.database
    tenant_id = request.tenantId or str(_claims(authorization)["tenant"])
    now = datetime.now()
    with database.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("INSERT INTO ea_student (tenant_id,school_id,account,password,open_id,name,study_grade,major,phone,id_card,status,create_time,update_time) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", (tenant_id, request.schoolId, request.account, request.password, request.openId, request.name, request.studyGrade, request.major, request.phone, request.idCard, request.status, now, now))
            student_id = str(cursor.lastrowid)
        conn.commit()
    return {"code": 200, "msg": "操作成功", "data": {"studentId": student_id}}


@router.put("")
def update_student(
    request: StudentRequest,
    authorization: str | None = Header(default=None),
    repo: StudentRepository = Depends(repository),
) -> dict:
    """更新学生账号资料，未传租户时使用登录租户。"""
    if not request.studentId:
        raise HTTPException(status_code=400, detail="学生ID不能为空")
    database = repo.database
    tenant_id = request.tenantId or str(_claims(authorization)["tenant"])
    with database.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE ea_student SET tenant_id=%s,school_id=%s,account=%s,password=%s,open_id=%s,name=%s,study_grade=%s,major=%s,phone=%s,id_card=%s,status=%s,update_time=%s WHERE student_id=%s", (tenant_id, request.schoolId, request.account, request.password, request.openId, request.name, request.studyGrade, request.major, request.phone, request.idCard, request.status, datetime.now(), request.studentId))
            affected = cursor.rowcount
        conn.commit()
    if affected != 1:
        raise HTTPException(status_code=404, detail="学员不存在")
    return {"code": 200, "msg": "操作成功"}


@router.delete("/{student_id}")
def delete_student(student_id: str, repo: StudentRepository = Depends(repository)) -> dict:
    """删除一个或多个学生账号记录。"""
    ids = [item.strip() for item in student_id.split(",") if item.strip()]
    if not ids or any(not item.isdigit() for item in ids):
        raise HTTPException(status_code=400, detail="学生ID格式错误")
    placeholders = ",".join(["%s"] * len(ids))
    database = repo.database
    with database.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                f"DELETE FROM ea_student WHERE student_id IN ({placeholders})",
                tuple(ids),
            )
            affected = cursor.rowcount
        conn.commit()
    if affected < 1:
        raise HTTPException(status_code=404, detail="学员不存在")
    return {"code": 200, "msg": "操作成功", "data": {"count": affected}}


@router.post("/login-check")
def check_student_login(request: StudentLoginCheckRequest) -> dict:
    """按订单补齐账号信息，验证平台账号并写回登录与进度快照。"""
    database = Database(Settings.from_env())
    login_request = _load_login_context(request, database)
    logger.info(
        "student login-check request: student_id=%s order_id=%s school_id=%s",
        login_request.studentId,
        str(request.orderId) if request.orderId is not None else "",
        login_request.schoolId,
    )
    adapter_name, result = _check(login_request)
    body = _response(adapter_name, result, include_snapshots=True)
    result_data = result.data if result is not None and isinstance(result.data, dict) else {}
    student_repo = StudentRepository(database)
    message = body.get("message", "登录检测失败")
    logger.info(
        "student login-check result: student_id=%s order_id=%s adapter=%s ok=%s code=%s",
        login_request.studentId,
        str(request.orderId) if request.orderId is not None else "",
        adapter_name or "",
        body["ok"],
        body.get("code", ""),
    )
    student_repo.update_login_status(login_request.studentId, 1 if body["ok"] else 2, message)
    if body["ok"]:
        task_repo = TaskRepository(database)
        profile = ProgressDetailParser().parse_student_profile(result_data.get("profileSnapshot"))
        candidate_name = str(result_data.get("studentName") or profile.get("studentName") or "").strip()
        if candidate_name == login_request.account or not any("\u4e00" <= char <= "\u9fff" for char in candidate_name):
            candidate_name = ""
        profile_payload = {
            "studentId": login_request.studentId,
            "tenantId": login_request.tenantId,
            "studentName": candidate_name,
            "studyGrade": profile.get("studyGrade"),
            "major": profile.get("major"),
        }
        if any(profile_payload.get(key) for key in ("studentName", "studyGrade", "major")):
            task_repo.update_student_profile(profile_payload)
        if request.orderId:
            order_id = str(request.orderId)
            tenant_id = login_request.tenantId
            for key, method in (
                ("course_progress", task_repo.upsert_course_progress),
                ("exam_progress", task_repo.upsert_exam_progress),
                ("course_progress_items", task_repo.replace_course_progress_items),
                ("exam_progress_items", task_repo.replace_exam_progress_items),
            ):
                payload = result_data.get(key)
                if isinstance(payload, dict):
                    payload.setdefault("orderId", order_id)
                    payload.setdefault("tenantId", tenant_id)
                    method(payload)
            course_snapshot = result_data.get("courseSnapshot")
            exam_snapshot = result_data.get("examSnapshot")
            if course_snapshot or exam_snapshot:
                parser = ProgressDetailParser()
                if course_snapshot:
                    task_repo.replace_course_progress_items({
                        "orderId": order_id,
                        "tenantId": tenant_id,
                        "items": parser.parse_course_items(course_snapshot),
                    })
                if exam_snapshot:
                    task_repo.replace_exam_progress_items({
                        "orderId": order_id,
                        "tenantId": tenant_id,
                        "items": parser.parse_exam_items(exam_snapshot),
                    })
    if not body["ok"]:
        raise HTTPException(status_code=400, detail=body)
    return {"code": 200, "msg": "校验成功", "data": body}


@router.post("/fetch-name")
def fetch_student_name(request: LoginCheckRequest) -> dict:
    """通过 Python 平台适配器登录并提取学生姓名。"""
    adapter_name, result = _check(request)
    body = _response(adapter_name, result, include_snapshots=False)
    if not body["ok"]:
        raise HTTPException(status_code=400, detail=body)
    return {"code": 200, "msg": "获取成功", "data": {"name": body.get("name", ""), "validated": True, "adapter": adapter_name}}
