"""课程和考试进度只读 API。"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.api.catalog import _camel_row, _database, _execute, _rows

router = APIRouter(prefix="/education", tags=["progress"])


def _filter(order_id: str | None, tenant_id: str | None) -> tuple[str, list[str]]:
    """构造参数化的订单/租户过滤条件。"""
    where = ["1=1"]
    params: list[str] = []
    if order_id:
        where.append("order_id=%s")
        params.append(order_id)
    if tenant_id:
        where.append("tenant_id=%s")
        params.append(tenant_id)
    return " AND ".join(where), params


@router.get("/course-progress/list")
def list_course_progress(
    order_id: str | None = Query(default=None, alias="orderId"),
    tenant_id: str | None = Query(default=None, alias="tenantId"),
    student_account: str | None = Query(default=None, alias="studentAccount"),
    course_name: str | None = Query(default=None, alias="courseName"),
    term: str | None = Query(default=None),
    page_num: int = Query(default=1, ge=1, alias="pageNum"),
    page_size: int = Query(default=10, ge=1, le=10000, alias="pageSize"),
    database=Depends(_database),
) -> dict:
    """联表查询课程进度和学员资料，并按原管理端参数分页。"""
    clauses = ["1=1"]
    params: list[object] = []
    filters = [
        ("cp.order_id", order_id, False),
        ("cp.tenant_id", tenant_id, False),
        ("s.account", student_account, True),
        ("cp.course_name", course_name, True),
        ("cp.term", term, True),
    ]
    for column, value, fuzzy in filters:
        if value is None or value == "":
            continue
        clauses.append(f"{column} LIKE %s" if fuzzy else f"{column}=%s")
        params.append(f"%{value}%" if fuzzy else value)
    joins = (
        "ea_course_progress cp "
        "LEFT JOIN ea_order o ON o.order_id=cp.order_id "
        "LEFT JOIN ea_student s ON s.student_id=o.student_id"
    )
    predicate = " AND ".join(clauses)
    columns = (
        "cp.progress_id,cp.order_id,o.student_id,s.name AS student_name,"
        "s.account AS student_account,s.study_grade,s.major,s.login_status,"
        "s.login_message,s.login_checked_at,cp.tenant_id,cp.course_name,cp.term,"
        "cp.video_status,cp.video_note,cp.video_time,cp.work_status,cp.work_note,"
        "cp.work_time,cp.exam_status,cp.exam_note,cp.exam_time,cp.create_time,cp.update_time"
    )
    offset = (page_num - 1) * page_size
    with database.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) AS total FROM {joins} WHERE {predicate}", params)
            total = int(cursor.fetchone()["total"])
            cursor.execute(
                f"SELECT {columns} FROM {joins} WHERE {predicate} "
                "ORDER BY cp.create_time DESC,cp.progress_id DESC LIMIT %s OFFSET %s",
                [*params, page_size, offset],
            )
            rows = [_camel_row(row) for row in cursor.fetchall()]
    for row in rows:
        name = str(row.get("studentName") or "").strip()
        account = str(row.get("studentAccount") or "").strip()
        if not name or name == account or not any("\u4e00" <= char <= "\u9fff" for char in name):
            row["studentName"] = ""
    return {"code": 200, "msg": "操作成功", "rows": rows, "total": total}


@router.get("/exam-progress/list")
def list_exam_progress(
    order_id: str | None = Query(default=None, alias="orderId"),
    tenant_id: str | None = Query(default=None, alias="tenantId"),
    status: int | None = Query(default=None),
    page_num: int = Query(default=1, ge=1, alias="pageNum"),
    page_size: int = Query(default=10, ge=1, le=10000, alias="pageSize"),
    database=Depends(_database),
) -> dict:
    """按订单、租户和状态分页查询考试进度汇总。"""
    clauses = ["1=1"]
    params: list[object] = []
    for column, value in (("order_id", order_id), ("tenant_id", tenant_id), ("status", status)):
        if value is not None and value != "":
            clauses.append(f"{column}=%s")
            params.append(value)
    predicate = " AND ".join(clauses)
    offset = (page_num - 1) * page_size
    with database.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                f"SELECT COUNT(*) AS total FROM ea_exam_progress WHERE {predicate}", params
            )
            total = int(cursor.fetchone()["total"])
            cursor.execute(
                "SELECT * FROM ea_exam_progress WHERE " + predicate
                + " ORDER BY exam_progress_id DESC LIMIT %s OFFSET %s",
                [*params, page_size, offset],
            )
            rows = [_camel_row(row) for row in cursor.fetchall()]
    return {"code": 200, "msg": "操作成功", "rows": rows, "total": total}


@router.get("/course-progress/items")
def list_course_items(order_id: str | None = Query(default=None, alias="orderId"), tenant_id: str | None = Query(default=None, alias="tenantId"), limit: int = Query(default=500, ge=1, le=1000), database=Depends(_database)) -> dict:
    """查询课程进度明细。"""
    predicate, params = _filter(order_id, tenant_id)
    rows = _rows(database, "SELECT item_id, order_id, tenant_id, course_name, course_type, required_flag, term, learning_status, learning_percent, learning_text, work_status FROM ea_course_progress_item WHERE " + predicate + " ORDER BY item_id LIMIT %s", (*params, limit))
    return {"code": 200, "msg": "操作成功", "rows": [_camel_row(row) for row in rows], "total": len(rows)}


@router.get("/exam-progress/items")
def list_exam_items(order_id: str | None = Query(default=None, alias="orderId"), tenant_id: str | None = Query(default=None, alias="tenantId"), limit: int = Query(default=500, ge=1, le=1000), database=Depends(_database)) -> dict:
    """查询考试进度明细。"""
    predicate, params = _filter(order_id, tenant_id)
    rows = _rows(database, "SELECT item_id, order_id, tenant_id, exam_name, exam_status, score, remark, frozen_flag, frozen_reason FROM ea_exam_progress_item WHERE " + predicate + " ORDER BY item_id LIMIT %s", (*params, limit))
    return {"code": 200, "msg": "操作成功", "rows": [_camel_row(row) for row in rows], "total": len(rows)}


class ExamFreezeRequest(BaseModel):
    """考试明细冻结或解冻请求。"""

    orderId: str
    examName: str = Field(min_length=1, max_length=128)
    reason: str = Field(default="", max_length=255)


class CourseProgressRequest(BaseModel):
    """课程进度新增或修改请求。"""

    progressId: str | None = None
    orderId: str
    courseName: str | None = Field(default=None, max_length=128)
    term: str | None = Field(default=None, max_length=64)
    videoStatus: int = 0
    videoNote: str | None = Field(default=None, max_length=255)
    videoTime: str | None = None
    workStatus: int = 0
    workNote: str | None = Field(default=None, max_length=255)
    workTime: str | None = None
    examStatus: int = 0
    examNote: str | None = Field(default=None, max_length=255)
    examTime: str | None = None


class ExamProgressRequest(BaseModel):
    """考试进度新增或修改请求。"""

    examProgressId: str | None = None
    orderId: str
    status: int = 0
    score: float | None = None
    note: str | None = Field(default=None, max_length=255)
    finishedAt: str | None = None


def _tenant_for_order(order_id: str, database) -> str:
    """从订单读取租户，避免信任进度表单传入的租户。"""
    rows = _rows(database, "SELECT tenant_id FROM ea_order WHERE order_id=%s", (order_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="订单不存在")
    return str(rows[0]["tenant_id"])


def _delete_progress(database, table: str, id_column: str, raw_ids: str) -> dict:
    """删除逗号分隔的一组进度记录。"""
    ids = [item.strip() for item in raw_ids.split(",") if item.strip()]
    if not ids or any(not item.isdigit() for item in ids):
        raise HTTPException(status_code=400, detail="进度ID格式错误")
    placeholders = ",".join(["%s"] * len(ids))
    affected = _execute(
        database,
        f"DELETE FROM {table} WHERE {id_column} IN ({placeholders})",
        tuple(ids),
    )
    if affected < 1:
        raise HTTPException(status_code=404, detail="进度记录不存在")
    return {"code": 200, "msg": "操作成功", "data": {"count": affected}}


@router.get("/course-progress/{progress_id}")
def get_course_progress(progress_id: str, database=Depends(_database)) -> dict:
    """按主键返回课程进度详情。"""
    rows = _rows(database, "SELECT * FROM ea_course_progress WHERE progress_id=%s", (progress_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="课程进度不存在")
    return {"code": 200, "msg": "操作成功", "data": _camel_row(rows[0])}


def _course_values(request: CourseProgressRequest) -> tuple:
    """按课程进度表字段顺序生成写入值。"""
    return (
        request.orderId,
        request.courseName or None,
        request.term or None,
        request.videoStatus,
        request.videoNote or None,
        request.videoTime or None,
        request.workStatus,
        request.workNote or None,
        request.workTime or None,
        request.examStatus,
        request.examNote or None,
        request.examTime or None,
    )


@router.post("/course-progress")
def create_course_progress(request: CourseProgressRequest, database=Depends(_database)) -> dict:
    """创建课程进度并从订单继承租户。"""
    tenant_id = _tenant_for_order(request.orderId, database)
    now = datetime.now()
    with database.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO ea_course_progress (tenant_id,order_id,course_name,term,"
                "video_status,video_note,video_time,work_status,work_note,work_time,"
                "exam_status,exam_note,exam_time,create_time,update_time) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (tenant_id, *_course_values(request), now, now),
            )
            progress_id = str(cursor.lastrowid)
        conn.commit()
    return {"code": 200, "msg": "操作成功", "data": {"progressId": progress_id}}


@router.put("/course-progress")
def update_course_progress(request: CourseProgressRequest, database=Depends(_database)) -> dict:
    """修改课程进度并同步订单租户。"""
    if not request.progressId:
        raise HTTPException(status_code=400, detail="进度ID不能为空")
    tenant_id = _tenant_for_order(request.orderId, database)
    affected = _execute(
        database,
        "UPDATE ea_course_progress SET tenant_id=%s,order_id=%s,course_name=%s,term=%s,"
        "video_status=%s,video_note=%s,video_time=%s,work_status=%s,work_note=%s,work_time=%s,"
        "exam_status=%s,exam_note=%s,exam_time=%s,update_time=%s WHERE progress_id=%s",
        (tenant_id, *_course_values(request), datetime.now(), request.progressId),
    )
    if affected != 1:
        raise HTTPException(status_code=404, detail="课程进度不存在")
    return {"code": 200, "msg": "操作成功"}


@router.delete("/course-progress/{progress_id}")
def delete_course_progress(progress_id: str, database=Depends(_database)) -> dict:
    """删除一个或多个课程进度。"""
    return _delete_progress(database, "ea_course_progress", "progress_id", progress_id)


@router.get("/exam-progress/{exam_progress_id}")
def get_exam_progress(exam_progress_id: str, database=Depends(_database)) -> dict:
    """按主键返回考试进度详情。"""
    rows = _rows(
        database,
        "SELECT * FROM ea_exam_progress WHERE exam_progress_id=%s",
        (exam_progress_id,),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="考试进度不存在")
    return {"code": 200, "msg": "操作成功", "data": _camel_row(rows[0])}


@router.post("/exam-progress")
def create_exam_progress(request: ExamProgressRequest, database=Depends(_database)) -> dict:
    """创建考试进度并从订单继承租户。"""
    tenant_id = _tenant_for_order(request.orderId, database)
    now = datetime.now()
    with database.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO ea_exam_progress (tenant_id,order_id,status,score,note,finished_at,"
                "create_time,update_time) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                (tenant_id, request.orderId, request.status, request.score, request.note or None,
                 request.finishedAt or None, now, now),
            )
            exam_progress_id = str(cursor.lastrowid)
        conn.commit()
    return {
        "code": 200,
        "msg": "操作成功",
        "data": {"examProgressId": exam_progress_id},
    }


@router.put("/exam-progress")
def update_exam_progress(request: ExamProgressRequest, database=Depends(_database)) -> dict:
    """修改考试进度并同步订单租户。"""
    if not request.examProgressId:
        raise HTTPException(status_code=400, detail="考试进度ID不能为空")
    tenant_id = _tenant_for_order(request.orderId, database)
    affected = _execute(
        database,
        "UPDATE ea_exam_progress SET tenant_id=%s,order_id=%s,status=%s,score=%s,note=%s,"
        "finished_at=%s,update_time=%s WHERE exam_progress_id=%s",
        (tenant_id, request.orderId, request.status, request.score, request.note or None,
         request.finishedAt or None, datetime.now(), request.examProgressId),
    )
    if affected != 1:
        raise HTTPException(status_code=404, detail="考试进度不存在")
    return {"code": 200, "msg": "操作成功"}


@router.delete("/exam-progress/{exam_progress_id}")
def delete_exam_progress(exam_progress_id: str, database=Depends(_database)) -> dict:
    """删除一个或多个考试进度。"""
    return _delete_progress(
        database,
        "ea_exam_progress",
        "exam_progress_id",
        exam_progress_id,
    )


def _set_frozen(request: ExamFreezeRequest, frozen: bool, database) -> dict:
    """按订单和考试名原子更新冻结标记。"""
    with database.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE ea_exam_progress_item SET frozen_flag=%s,frozen_reason=%s,frozen_time=%s,update_time=%s WHERE order_id=%s AND exam_name=%s",
                (1 if frozen else 0, request.reason if frozen else None, datetime.now() if frozen else None, datetime.now(), request.orderId, request.examName),
            )
            affected = cursor.rowcount
        conn.commit()
    if affected < 1:
        raise HTTPException(status_code=404, detail="考试明细不存在")
    return {"code": 200, "msg": "操作成功"}


@router.post("/exam-progress-item/freeze")
def freeze_exam_item(request: ExamFreezeRequest, database=Depends(_database)) -> dict:
    """冻结考试明细，采集覆盖时保留人工冻结状态。"""
    return _set_frozen(request, True, database)


@router.post("/exam-progress-item/unfreeze")
def unfreeze_exam_item(request: ExamFreezeRequest, database=Depends(_database)) -> dict:
    """解除考试明细冻结。"""
    return _set_frozen(request, False, database)
