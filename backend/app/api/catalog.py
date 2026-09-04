"""租户、平台、学校和订单管理 API。"""

from datetime import datetime
import json

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field

from app.api.auth import _claims
from app.config import Settings
from app.infrastructure.db import Database

router = APIRouter(prefix="/education", tags=["catalog"])


def _database() -> Database:
    """创建目录查询使用的数据库连接工厂。"""
    return Database(Settings.from_env())


def _rows(database: Database, sql: str, params: tuple = ()) -> list[dict]:
    """执行静态 SQL 并返回字典行；SQL 不接收用户拼接片段。"""
    with database.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            return list(cursor.fetchall())


def _camel_row(row: dict) -> dict:
    """将数据库字段转换为旧管理端使用的 camelCase，并保护大整数标识。"""
    result = {}
    for key, value in row.items():
        parts = key.split("_")
        name = parts[0] + "".join(part.title() for part in parts[1:])
        if key.endswith("_id") and value is not None:
            value = str(value)
        if isinstance(value, datetime):
            value = value.strftime("%Y-%m-%d %H:%M:%S")
        result[name] = value
    return result


def _execute(database: Database, sql: str, params: tuple = ()) -> int:
    """执行单条写入并提交事务，返回受影响行数。"""
    with database.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            affected = cursor.rowcount
        conn.commit()
    return affected


def _page(
    database: Database,
    table: str,
    columns: str,
    order_by: str,
    filters: list[tuple[str, object, bool]],
    page_num: int,
    page_size: int,
) -> dict:
    """按固定字段构造参数化筛选，并返回准确分页总数。"""
    clauses = ["1=1"]
    params: list[object] = []
    for column, value, fuzzy in filters:
        if value is None or value == "":
            continue
        clauses.append(f"{column} LIKE %s" if fuzzy else f"{column}=%s")
        params.append(f"%{value}%" if fuzzy else value)
    predicate = " AND ".join(clauses)
    offset = (page_num - 1) * page_size
    with database.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) AS total FROM {table} WHERE {predicate}", params)
            total = int(cursor.fetchone()["total"])
            cursor.execute(
                f"SELECT {columns} FROM {table} WHERE {predicate} "
                f"ORDER BY {order_by} LIMIT %s OFFSET %s",
                [*params, page_size, offset],
            )
            rows = [_camel_row(row) for row in cursor.fetchall()]
    return {"code": 200, "msg": "操作成功", "rows": rows, "total": total}


def _delete_many(
    database: Database,
    table: str,
    id_column: str,
    raw_ids: str,
    missing: str,
    numeric: bool = True,
) -> dict:
    """兼容原管理端逗号分隔的批量删除路径。"""
    ids = [item.strip() for item in raw_ids.split(",") if item.strip()]
    if not ids or (numeric and any(not item.isdigit() for item in ids)):
        raise HTTPException(status_code=400, detail="标识格式错误")
    placeholders = ",".join(["%s"] * len(ids))
    affected = _execute(
        database,
        f"DELETE FROM {table} WHERE {id_column} IN ({placeholders})",
        tuple(ids),
    )
    if affected < 1:
        raise HTTPException(status_code=404, detail=missing)
    return {"code": 200, "msg": "操作成功", "data": {"count": affected}}


class PlatformRequest(BaseModel):
    """平台新增或修改请求。"""

    platformId: str | None = None
    platformName: str = Field(min_length=1, max_length=64)
    remark: str | None = Field(default=None, max_length=255)


class SchoolRequest(BaseModel):
    """学校配置新增或修改请求。"""

    schoolId: str | None = None
    platformId: str
    schoolName: str = Field(min_length=1, max_length=128)
    accessType: int = Field(default=1, ge=1, le=2)
    accessAddress: str | None = None
    schoolUrl: str | None = None
    schoolState: int = 0
    schoolVideo: int = 0
    schoolWork: int = 0
    schoolExam: int = 0
    schoolFace: int = 0
    schoolExam2: int = 0
    schoolExamType: int = 0
    schoolAnswerOk: int = 0
    schoolExamState: int = 0
    schoolSumbitTime: int = 0
    schoolIpNumber: int = 0
    schoolFid: str | None = None
    schoolCode: str | None = None
    schoolRemark: str | None = None


class TenantRequest(BaseModel):
    """租户新增或修改请求。"""

    tenantId: str = Field(min_length=1, max_length=20)
    tenantName: str = Field(min_length=1, max_length=64)
    status: int = Field(default=0, ge=0, le=1)
    balancePoints: int = 0
    remark: str | None = None


class OrderRequest(BaseModel):
    """订单新增或修改请求。"""

    orderId: str | None = None
    tenantId: str | None = None
    studentId: str
    schoolId: str
    platformId: str
    orderType: int = 1
    courseName: str | None = None
    courseCode: str | None = None
    term: str | None = None
    examStartAt: str | None = None
    examEndAt: str | None = None
    status: int = 0
    costPoints: int = 0
    paidAt: str | None = None
    remark: str | None = None


@router.get("/tenant/list")
def list_tenants(
    tenant_id: str | None = Query(default=None, alias="tenantId"),
    tenant_name: str | None = Query(default=None, alias="tenantName"),
    status: int | None = Query(default=None),
    page_num: int = Query(default=1, ge=1, alias="pageNum"),
    page_size: int = Query(default=10, ge=1, le=10000, alias="pageSize"),
    database: Database = Depends(_database),
) -> dict:
    """筛选和分页租户。"""
    return _page(
        database,
        "ea_tenant",
        "tenant_id,tenant_name,status,balance_points,remark,create_time,update_time",
        "tenant_id",
        [
            ("tenant_id", tenant_id, True),
            ("tenant_name", tenant_name, True),
            ("status", status, False),
        ],
        page_num,
        page_size,
    )


@router.get("/tenant/{tenant_id}")
def get_tenant(tenant_id: str, database: Database = Depends(_database)) -> dict:
    """返回租户详情。"""
    rows = _rows(database, "SELECT tenant_id, tenant_name, status, balance_points, remark FROM ea_tenant WHERE tenant_id=%s", (tenant_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="租户不存在")
    return {"code": 200, "msg": "操作成功", "data": _camel_row(rows[0])}


@router.post("/tenant")
def create_tenant(request: TenantRequest, database: Database = Depends(_database)) -> dict:
    """创建租户。"""
    now = datetime.now()
    _execute(database, "INSERT INTO ea_tenant (tenant_id, tenant_name, status, balance_points, remark, create_time, update_time) VALUES (%s,%s,%s,%s,%s,%s,%s)", (request.tenantId, request.tenantName, request.status, request.balancePoints, request.remark, now, now))
    return {"code": 200, "msg": "操作成功"}


@router.put("/tenant")
def update_tenant(request: TenantRequest, database: Database = Depends(_database)) -> dict:
    """修改租户配置。"""
    affected = _execute(database, "UPDATE ea_tenant SET tenant_name=%s,status=%s,balance_points=%s,remark=%s,update_time=%s WHERE tenant_id=%s", (request.tenantName, request.status, request.balancePoints, request.remark, datetime.now(), request.tenantId))
    if affected != 1:
        raise HTTPException(status_code=404, detail="租户不存在")
    return {"code": 200, "msg": "操作成功"}


@router.delete("/tenant/{tenant_id}")
def delete_tenant(tenant_id: str, database: Database = Depends(_database)) -> dict:
    """删除一个或多个租户。"""
    return _delete_many(database, "ea_tenant", "tenant_id", tenant_id, "租户不存在", False)


@router.get("/platform/list")
def list_platforms(
    platform_name: str | None = Query(default=None, alias="platformName"),
    page_num: int = Query(default=1, ge=1, alias="pageNum"),
    page_size: int = Query(default=10, ge=1, le=10000, alias="pageSize"),
    database: Database = Depends(_database),
) -> dict:
    """筛选和分页平台。"""
    return _page(
        database,
        "ea_platform",
        "platform_id,platform_name,remark,create_time,update_time",
        "platform_id",
        [("platform_name", platform_name, True)],
        page_num,
        page_size,
    )


@router.get("/platform/{platform_id}")
def get_platform(platform_id: str, database: Database = Depends(_database)) -> dict:
    """返回平台详情。"""
    rows = _rows(database, "SELECT platform_id, platform_name, remark FROM ea_platform WHERE platform_id=%s", (platform_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="平台不存在")
    row = _camel_row(rows[0])
    return {"code": 200, "msg": "操作成功", "data": row}


@router.post("/platform")
def create_platform(request: PlatformRequest, database: Database = Depends(_database)) -> dict:
    """创建教育平台。"""
    now = datetime.now()
    _execute(database, "INSERT INTO ea_platform (platform_name, remark, create_time, update_time) VALUES (%s,%s,%s,%s)", (request.platformName, request.remark, now, now))
    return {"code": 200, "msg": "操作成功"}


@router.put("/platform")
def update_platform(request: PlatformRequest, database: Database = Depends(_database)) -> dict:
    """修改教育平台。"""
    if not request.platformId or _execute(database, "UPDATE ea_platform SET platform_name=%s,remark=%s,update_time=%s WHERE platform_id=%s", (request.platformName, request.remark, datetime.now(), request.platformId)) != 1:
        raise HTTPException(status_code=404, detail="平台不存在")
    return {"code": 200, "msg": "操作成功"}


@router.delete("/platform/{platform_id}")
def delete_platform(platform_id: str, database: Database = Depends(_database)) -> dict:
    """删除一个或多个教育平台。"""
    return _delete_many(database, "ea_platform", "platform_id", platform_id, "平台不存在")


@router.get("/school/list")
def list_schools(
    platform_id: str | None = Query(default=None, alias="platformId"),
    school_name: str | None = Query(default=None, alias="schoolName"),
    school_state: int | None = Query(default=None, alias="schoolState"),
    page_num: int = Query(default=1, ge=1, alias="pageNum"),
    page_size: int = Query(default=10, ge=1, le=10000, alias="pageSize"),
    database: Database = Depends(_database),
) -> dict:
    """筛选和分页学校及平台配置。"""
    return _page(
        database,
        "ea_school",
        "*",
        "school_id",
        [
            ("platform_id", platform_id, False),
            ("school_name", school_name, True),
            ("school_state", school_state, False),
        ],
        page_num,
        page_size,
    )


@router.get("/school/{school_id}")
def get_school(school_id: str, database: Database = Depends(_database)) -> dict:
    """返回学校完整配置。"""
    rows = _rows(database, "SELECT * FROM ea_school WHERE school_id=%s", (school_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="学校不存在")
    return {"code": 200, "msg": "操作成功", "data": _camel_row(rows[0])}


@router.post("/school")
def create_school(request: SchoolRequest, database: Database = Depends(_database)) -> dict:
    """创建学校配置。"""
    now = datetime.now()
    values = request.model_dump(exclude={"schoolId"})
    columns = {"platformId":"platform_id","schoolName":"school_name","accessType":"access_type","accessAddress":"access_address","schoolUrl":"school_url","schoolState":"school_state","schoolVideo":"school_video","schoolWork":"school_work","schoolExam":"school_exam","schoolFace":"school_face","schoolExam2":"school_exam2","schoolExamType":"school_exam_type","schoolAnswerOk":"school_answer_ok","schoolExamState":"school_exam_state","schoolSumbitTime":"school_sumbit_time","schoolIpNumber":"school_ip_number","schoolFid":"school_fid","schoolCode":"school_code","schoolRemark":"school_remark"}
    names = [columns[key] for key in values]
    _execute(database, f"INSERT INTO ea_school ({','.join(names)},create_time,update_time) VALUES ({','.join(['%s']*len(names))},%s,%s)", tuple(values[key] for key in values) + (now, now))
    return {"code": 200, "msg": "操作成功"}


@router.put("/school")
def update_school(request: SchoolRequest, database: Database = Depends(_database)) -> dict:
    """修改学校配置。"""
    if not request.schoolId:
        raise HTTPException(status_code=400, detail="学校ID不能为空")
    values = request.model_dump(exclude={"schoolId"})
    columns = {"platformId":"platform_id","schoolName":"school_name","accessType":"access_type","accessAddress":"access_address","schoolUrl":"school_url","schoolState":"school_state","schoolVideo":"school_video","schoolWork":"school_work","schoolExam":"school_exam","schoolFace":"school_face","schoolExam2":"school_exam2","schoolExamType":"school_exam_type","schoolAnswerOk":"school_answer_ok","schoolExamState":"school_exam_state","schoolSumbitTime":"school_sumbit_time","schoolIpNumber":"school_ip_number","schoolFid":"school_fid","schoolCode":"school_code","schoolRemark":"school_remark"}
    assignments = ','.join(f"{columns[key]}=%s" for key in values)
    if _execute(database, f"UPDATE ea_school SET {assignments},update_time=%s WHERE school_id=%s", tuple(values[key] for key in values) + (datetime.now(), request.schoolId)) != 1:
        raise HTTPException(status_code=404, detail="学校不存在")
    return {"code": 200, "msg": "操作成功"}


@router.delete("/school/{school_id}")
def delete_school(school_id: str, database: Database = Depends(_database)) -> dict:
    """删除一个或多个学校配置。"""
    return _delete_many(database, "ea_school", "school_id", school_id, "学校不存在")


@router.get("/order/list")
def list_orders(
    tenant_id: str | None = Query(default=None, alias="tenantId"),
    order_id: str | None = Query(default=None, alias="orderId"),
    student_id: str | None = Query(default=None, alias="studentId"),
    school_id: str | None = Query(default=None, alias="schoolId"),
    platform_id: str | None = Query(default=None, alias="platformId"),
    status: int | None = Query(default=None),
    page_num: int = Query(default=1, ge=1, alias="pageNum"),
    page_size: int = Query(default=10, ge=1, le=10000, alias="pageSize"),
    database: Database = Depends(_database),
) -> dict:
    """按原管理端条件筛选和分页订单。"""
    columns = (
        "order_id,tenant_id,student_id,school_id,platform_id,order_type,course_name,"
        "course_code,term,exam_start_at,exam_end_at,status,cost_points,paid_at,remark,"
        "create_time,update_time"
    )
    return _page(
        database,
        "ea_order",
        columns,
        "order_id DESC",
        [
            ("tenant_id", tenant_id, False),
            ("order_id", order_id, False),
            ("student_id", student_id, False),
            ("school_id", school_id, False),
            ("platform_id", platform_id, False),
            ("status", status, False),
        ],
        page_num,
        page_size,
    )


@router.get("/order/{order_id}")
def get_order(order_id: str, database: Database = Depends(_database)) -> dict:
    """返回订单详情。"""
    rows = _rows(database, "SELECT * FROM ea_order WHERE order_id=%s", (order_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="订单不存在")
    return {"code": 200, "msg": "操作成功", "data": _camel_row(rows[0])}


@router.get("/order/detail/{order_id}")
def get_order_detail(order_id: str, database: Database = Depends(_database)) -> dict:
    """返回订单、学员、学校、平台、进度、任务和日志的聚合详情。"""
    order_rows = _rows(database, "SELECT * FROM ea_order WHERE order_id=%s", (order_id,))
    if not order_rows:
        raise HTTPException(status_code=404, detail="订单不存在")
    order = order_rows[0]

    def first(sql: str, params: tuple) -> dict | None:
        rows = _rows(database, sql, params)
        return _camel_row(rows[0]) if rows else None

    student = first("SELECT * FROM ea_student WHERE student_id=%s", (order["student_id"],))
    school = first("SELECT * FROM ea_school WHERE school_id=%s", (order["school_id"],))
    platform = first("SELECT * FROM ea_platform WHERE platform_id=%s", (order["platform_id"],))
    course_progress = first("SELECT * FROM ea_course_progress WHERE order_id=%s ORDER BY progress_id DESC LIMIT 1", (order_id,))
    exam_progress = first("SELECT * FROM ea_exam_progress WHERE order_id=%s ORDER BY exam_progress_id DESC LIMIT 1", (order_id,))
    course_items = [_camel_row(row) for row in _rows(database, "SELECT * FROM ea_course_progress_item WHERE order_id=%s ORDER BY item_id", (order_id,))]
    exam_items = [_camel_row(row) for row in _rows(database, "SELECT * FROM ea_exam_progress_item WHERE order_id=%s ORDER BY item_id", (order_id,))]
    tasks = [_camel_row(row) for row in _rows(database, "SELECT * FROM ea_task WHERE order_id=%s ORDER BY task_id", (order_id,))]
    logs = [_camel_row(row) for row in _rows(database, "SELECT * FROM ea_task_log WHERE order_id=%s ORDER BY seq_no, log_id", (order_id,))]
    return {
        "code": 200,
        "msg": "操作成功",
        "data": {
            "order": _camel_row(order),
            "student": student,
            "school": school,
            "platform": platform,
            "courseProgress": course_progress,
            "examProgress": exam_progress,
            "courseProgressItems": course_items,
            "examProgressItems": exam_items,
            "tasks": tasks,
            "logs": logs,
        },
    }


@router.post("/order")
def create_order(
    request: OrderRequest,
    authorization: str | None = Header(default=None),
    database: Database = Depends(_database),
) -> dict:
    """在单一事务中创建订单，并同步扣费、任务、流水和初始进度。"""
    claims = _claims(authorization)
    now = datetime.now()
    with database.connection() as conn:
        conn.begin()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT tenant_id FROM ea_student WHERE student_id=%s",
                    (request.studentId,),
                )
                student = cursor.fetchone()
                if not student:
                    raise HTTPException(status_code=404, detail="学员不存在")

                student_tenant = str(student["tenant_id"])
                login_tenant = claims.get("tenant")
                if login_tenant and request.tenantId and str(login_tenant) != request.tenantId:
                    raise HTTPException(status_code=403, detail="不能跨租户创建订单")
                tenant_id = str(login_tenant or request.tenantId or student_tenant)
                if student_tenant != tenant_id:
                    raise HTTPException(status_code=400, detail="学员不属于当前租户")

                cursor.execute(
                    "SELECT balance_points FROM ea_tenant WHERE tenant_id=%s FOR UPDATE",
                    (tenant_id,),
                )
                tenant = cursor.fetchone()
                if not tenant:
                    raise HTTPException(status_code=404, detail="租户不存在")
                balance = int(tenant.get("balance_points") or 0)
                if balance < request.costPoints:
                    raise HTTPException(status_code=400, detail="余额不足")

                cursor.execute(
                    "UPDATE ea_tenant SET balance_points=balance_points-%s,update_time=%s "
                    "WHERE tenant_id=%s",
                    (request.costPoints, now, tenant_id),
                )
                cursor.execute(
                    "INSERT INTO ea_order (tenant_id,student_id,school_id,platform_id,order_type,"
                    "course_name,course_code,term,exam_start_at,exam_end_at,status,cost_points,"
                    "paid_at,remark,create_time,update_time) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,"
                    "%s,%s,%s,%s,%s,%s,%s,%s)",
                    (
                        tenant_id,
                        request.studentId,
                        request.schoolId,
                        request.platformId,
                        request.orderType,
                        request.courseName,
                        request.courseCode,
                        request.term,
                        request.examStartAt or None,
                        request.examEndAt or None,
                        request.status,
                        request.costPoints,
                        now,
                        request.remark,
                        now,
                        now,
                    ),
                )
                order_id = str(cursor.lastrowid)
                cursor.execute(
                    "INSERT INTO ea_ledger (tenant_id,order_id,change_points,gift_points,type,"
                    "operator_user_id,remark,create_time,update_time) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (
                        tenant_id,
                        order_id,
                        -request.costPoints,
                        0,
                        2,
                        str(claims["sub"]),
                        "下单扣费",
                        now,
                        now,
                    ),
                )

                cursor.execute(
                    "SELECT school_name,school_exam FROM ea_school WHERE school_id=%s",
                    (request.schoolId,),
                )
                school = cursor.fetchone() or {}
                exam_supported = int(school.get("school_exam") or 0) == 1
                include_courses = []
                if request.courseName and request.courseName != school.get("school_name"):
                    include_courses.append(request.courseName)
                task_config = json.dumps(
                    {
                        "videoModel": 1,
                        "autoExam": 3 if request.orderType == 1 else 1,
                        "examAutoSubmit": 1,
                        "cxWorkSw": 1,
                        "cxExamSw": 1 if exam_supported else 0,
                        "cxNode": 3,
                        "includeCourses": include_courses,
                        "excludeCourses": [],
                    },
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                cursor.execute(
                    "INSERT INTO ea_task (tenant_id,order_id,task_type,status,task_config_json,"
                    "create_time,update_time) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                    (tenant_id, order_id, request.orderType, 0, task_config, now, now),
                )
                cursor.execute(
                    "INSERT INTO ea_course_progress (order_id,tenant_id,course_name,term,"
                    "video_status,video_note,work_status,work_note,exam_status,exam_note,"
                    "create_time,update_time) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (
                        order_id,
                        tenant_id,
                        request.courseName,
                        request.term,
                        3,
                        "等待执行器获取学习进度",
                        3,
                        "等待执行器获取作业进度",
                        3 if exam_supported else 0,
                        "等待执行器获取考试进度" if exam_supported else "考试未开始",
                        now,
                        now,
                    ),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    return {"code": 200, "msg": "操作成功", "data": {"orderId": order_id}}


@router.put("/order")
def update_order(request: OrderRequest, database: Database = Depends(_database)) -> dict:
    """修改学习订单。"""
    if not request.orderId:
        raise HTTPException(status_code=400, detail="订单ID不能为空")
    tenant_id = request.tenantId
    if not tenant_id:
        rows = _rows(database, "SELECT tenant_id FROM ea_order WHERE order_id=%s", (request.orderId,))
        tenant_id = str(rows[0]["tenant_id"]) if rows else None
    affected = _execute(database, "UPDATE ea_order SET tenant_id=%s,student_id=%s,school_id=%s,platform_id=%s,order_type=%s,course_name=%s,course_code=%s,term=%s,exam_start_at=%s,exam_end_at=%s,status=%s,cost_points=%s,paid_at=%s,remark=%s,update_time=%s WHERE order_id=%s", (tenant_id, request.studentId, request.schoolId, request.platformId, request.orderType, request.courseName, request.courseCode, request.term, request.examStartAt or None, request.examEndAt or None, request.status, request.costPoints, request.paidAt or None, request.remark, datetime.now(), request.orderId))
    if affected != 1:
        raise HTTPException(status_code=404, detail="订单不存在")
    return {"code": 200, "msg": "操作成功"}


@router.delete("/order/{order_id}")
def delete_order(order_id: str, database: Database = Depends(_database)) -> dict:
    """删除一个或多个学习订单。"""
    return _delete_many(database, "ea_order", "order_id", order_id, "订单不存在")
