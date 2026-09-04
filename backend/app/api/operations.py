"""任务、执行配置、媒体和积分管理 API。"""

from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

from app.api.auth import _claims
from app.application.task_runner import TaskRunner
from app.config import Settings
from app.infrastructure.db import Database, TaskRepository

router = APIRouter(prefix="/education", tags=["operations"])


def _database() -> Database:
    """创建运行域查询连接。"""
    return Database(Settings.from_env())


def _format(value: Any) -> Any:
    """将时间转换成原管理端使用的格式。"""
    return value.strftime("%Y-%m-%d %H:%M:%S") if isinstance(value, datetime) else value


def _camel_row(row: dict[str, Any], id_fields: set[str]) -> dict[str, Any]:
    """把数据库字段转换为 camelCase，并把大整数标识保留为字符串。"""
    result: dict[str, Any] = {}
    for key, value in row.items():
        parts = key.split("_")
        name = parts[0] + "".join(part.title() for part in parts[1:])
        result[name] = str(value) if key in id_fields and value is not None else _format(value)
    return result


def _filters(values: list[tuple[str, Any, bool]]) -> tuple[str, list[Any]]:
    """从固定字段定义生成参数化筛选条件。"""
    clauses = ["1=1"]
    params: list[Any] = []
    for column, value, fuzzy in values:
        if value is None or value == "":
            continue
        clauses.append(f"{column} LIKE %s" if fuzzy else f"{column}=%s")
        params.append(f"%{value}%" if fuzzy else value)
    return " AND ".join(clauses), params


def _page(
    database: Database,
    table: str,
    columns: str,
    order_by: str,
    values: list[tuple[str, Any, bool]],
    page_num: int,
    page_size: int,
    id_fields: set[str],
) -> dict:
    """执行管理端分页查询并返回准确总数。"""
    predicate, params = _filters(values)
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
            rows = [_camel_row(row, id_fields) for row in cursor.fetchall()]
    return {"code": 200, "msg": "操作成功", "rows": rows, "total": total}


def _one(
    database: Database,
    table: str,
    columns: str,
    id_column: str,
    item_id: str,
    id_fields: set[str],
    missing: str,
) -> dict:
    """按主键读取单条管理记录。"""
    with database.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(f"SELECT {columns} FROM {table} WHERE {id_column}=%s", (item_id,))
            row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=missing)
    return {"code": 200, "msg": "操作成功", "data": _camel_row(row, id_fields)}


def _insert(database: Database, sql: str, params: tuple[Any, ...]) -> str:
    """执行新增并返回浏览器安全的主键字符串。"""
    with database.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            item_id = str(cursor.lastrowid)
        conn.commit()
    return item_id


def _execute(database: Database, sql: str, params: tuple[Any, ...]) -> int:
    """执行单条更新并返回受影响行数。"""
    with database.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            affected = cursor.rowcount
        conn.commit()
    return affected


def _delete_ids(
    database: Database,
    table: str,
    id_column: str,
    raw_ids: str,
    missing: str,
) -> dict:
    """兼容原前端逗号分隔的批量删除路径。"""
    ids = [item.strip() for item in raw_ids.split(",") if item.strip()]
    if not ids or any(not item.isdigit() for item in ids):
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


class TaskRequest(BaseModel):
    """任务新增或修改请求。"""

    taskId: str | None = None
    orderId: str
    taskType: int = Field(default=1, ge=0, le=99)
    status: int = Field(default=0, ge=0, le=3)
    triggerAt: str | None = None
    workerCode: str | None = Field(default=None, max_length=64)
    startedAt: str | None = None
    finishedAt: str | None = None
    heartbeatAt: str | None = None
    retryCount: int = Field(default=0, ge=0)
    lastError: str | None = Field(default=None, max_length=500)
    resultSummary: str | None = Field(default=None, max_length=1000)
    taskConfigJson: str | None = None


class RunnerNodeRequest(BaseModel):
    """执行节点新增或修改请求。"""

    nodeId: str | None = None
    workerCode: str = Field(min_length=1, max_length=64)
    version: str | None = Field(default=None, max_length=64)
    hostName: str | None = Field(default=None, max_length=128)
    status: int = Field(default=1, ge=0, le=2)
    currentTaskId: str | None = None
    currentOrderId: str | None = None
    lastError: str | None = Field(default=None, max_length=1000)
    heartbeatAt: str | None = None
    startedAt: str | None = None


class RunnerSettingRequest(BaseModel):
    """执行器公共配置新增或修改请求。"""

    settingId: str | None = None
    tenantId: str = Field(min_length=1, max_length=20)
    aiType: str | None = Field(default=None, max_length=32)
    aiUrl: str | None = Field(default=None, max_length=255)
    aiModel: str | None = Field(default=None, max_length=128)
    aiApiKey: str | None = Field(default=None, max_length=255)
    externalQuestionUrl: str | None = Field(default=None, max_length=255)
    completionTone: int = Field(default=0, ge=0, le=1)
    colorLog: int = Field(default=0, ge=0, le=1)
    logLevel: str = Field(default="INFO", max_length=16)
    logModel: int = Field(default=0, ge=0, le=1)
    pollIntervalSeconds: int = Field(default=10, ge=1)
    maxParallelTasks: int = Field(default=1, ge=1)
    taskTimeoutSeconds: int = Field(default=1800, ge=1)
    logRetentionDays: int = Field(default=7, ge=1)
    remark: str | None = Field(default=None, max_length=255)


class SchoolCacheRequest(BaseModel):
    """学校能力缓存新增或修改请求。"""

    cacheId: str | None = None
    sourceSchoolId: str
    platformId: str
    platformName: str = Field(min_length=1, max_length=64)
    schoolName: str = Field(min_length=1, max_length=128)
    accessType: int = Field(default=1, ge=1, le=2)
    accessAddress: str | None = Field(default=None, max_length=255)
    schoolUrl: str | None = Field(default=None, max_length=255)
    schoolFid: str | None = Field(default=None, max_length=128)
    schoolCode: str | None = Field(default=None, max_length=255)
    schoolRemark: str | None = Field(default=None, max_length=255)
    enabled: int = Field(default=1, ge=0, le=1)
    videoSupported: int = Field(default=0, ge=0, le=2)
    workSupported: int = Field(default=0, ge=0, le=2)
    examSupported: int = Field(default=0, ge=0, le=2)
    examSpecialOrderRequired: int = Field(default=0, ge=0, le=2)
    faceRequired: int = Field(default=0, ge=0, le=2)
    examType: int = 0
    answerOk: int = 0
    examState: int = 0
    submitTime: int = 0
    ipNumber: int = 0


class FaceMediaRequest(BaseModel):
    """人脸媒体元数据新增或修改请求。"""

    faceMediaId: str | None = None
    tenantId: str = Field(min_length=1, max_length=20)
    studentId: str
    fileUrl: str = Field(min_length=1, max_length=500)
    fileType: str = Field(default="mp4", max_length=32)
    status: int = Field(default=0, ge=0, le=1)
    uploadedBy: str | None = None


TASK_COLUMNS = (
    "task_id,order_id,tenant_id,task_type,status,worker_code,retry_count,last_error,"
    "result_summary,task_config_json,trigger_at,started_at,heartbeat_at,finished_at,"
    "create_time,update_time"
)
NODE_COLUMNS = (
    "node_id,worker_code,version,host_name,status,current_task_id,current_order_id,"
    "last_error,heartbeat_at,started_at,create_time,update_time"
)
SETTING_COLUMNS = (
    "setting_id,tenant_id,ai_type,ai_url,ai_model,external_question_url,completion_tone,"
    "color_log,log_level,log_model,poll_interval_seconds,max_parallel_tasks,"
    "task_timeout_seconds,log_retention_days,remark,create_time,update_time"
)
CACHE_COLUMNS = (
    "cache_id,source_school_id,platform_id,platform_name,school_name,access_type,"
    "access_address,school_url,school_fid,school_code,school_remark,enabled,"
    "video_supported,work_supported,exam_supported,exam_special_order_required,"
    "face_required,exam_type,answer_ok,exam_state,submit_time,ip_number,create_time,update_time"
)
FACE_COLUMNS = (
    "face_media_id,tenant_id,student_id,file_url,file_type,status,uploaded_by,"
    "create_time,update_time"
)


@router.get("/runner/tasks/list")
def list_runner_tasks(
    limit: int = Query(default=100, ge=1, le=500),
    database: Database = Depends(_database),
) -> dict:
    """按执行器旧契约返回有限任务列表。"""
    return _page(
        database,
        "ea_task",
        TASK_COLUMNS,
        "task_id DESC",
        [],
        1,
        limit,
        {"task_id", "order_id"},
    )


@router.get("/task/list")
def list_tasks(
    order_id: str | None = Query(default=None, alias="orderId"),
    status: int | None = Query(default=None),
    task_type: int | None = Query(default=None, alias="taskType"),
    page_num: int = Query(default=1, ge=1, alias="pageNum"),
    page_size: int = Query(default=10, ge=1, le=10000, alias="pageSize"),
    database: Database = Depends(_database),
) -> dict:
    """按原管理端筛选和分页任务。"""
    return _page(
        database,
        "ea_task",
        TASK_COLUMNS,
        "task_id DESC",
        [
            ("order_id", order_id, False),
            ("status", status, False),
            ("task_type", task_type, False),
        ],
        page_num,
        page_size,
        {"task_id", "order_id"},
    )


@router.get("/task/{task_id}")
def get_task(task_id: str, database: Database = Depends(_database)) -> dict:
    """返回任务详情。"""
    return _one(
        database,
        "ea_task",
        "*",
        "task_id",
        task_id,
        {"task_id", "order_id"},
        "任务不存在",
    )


@router.get("/task/detail/{task_id}")
def get_task_detail(task_id: str, database: Database = Depends(_database)) -> dict:
    """返回任务、进度明细、完整业务日志和题库失败聚合详情。"""
    task = get_task(task_id, database)["data"]
    with database.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM ea_course_progress WHERE order_id=%s "
                "ORDER BY progress_id DESC LIMIT 1",
                (task["orderId"],),
            )
            course_row = cursor.fetchone()
            cursor.execute(
                "SELECT * FROM ea_exam_progress WHERE order_id=%s "
                "ORDER BY exam_progress_id DESC LIMIT 1",
                (task["orderId"],),
            )
            exam_row = cursor.fetchone()
            cursor.execute(
                "SELECT * FROM ea_course_progress_item WHERE order_id=%s ORDER BY item_id",
                (task["orderId"],),
            )
            course_items = [
                _camel_row(row, {"item_id", "order_id"}) for row in cursor.fetchall()
            ]
            cursor.execute(
                "SELECT * FROM ea_exam_progress_item WHERE order_id=%s ORDER BY item_id",
                (task["orderId"],),
            )
            exam_items = [
                _camel_row(row, {"item_id", "order_id"}) for row in cursor.fetchall()
            ]
            cursor.execute(
                "SELECT log_id,task_id,order_id,tenant_id,worker_code,seq_no,level,"
                "biz_type,biz_title,biz_status,message,failure_reason,created_at,"
                "create_time,update_time FROM ea_task_log WHERE task_id=%s "
                "ORDER BY seq_no DESC LIMIT 100",
                (task_id,),
            )
            logs = [
                _camel_row(row, {"log_id", "task_id", "order_id"})
                for row in cursor.fetchall()
            ]
            cursor.execute(
                "SELECT * FROM ea_tiku_failure WHERE task_id=%s "
                "ORDER BY failure_id DESC LIMIT 100",
                (task_id,),
            )
            failures = [
                _camel_row(row, {"failure_id", "task_id", "order_id"})
                for row in cursor.fetchall()
            ]
    return {
        "code": 200,
        "msg": "操作成功",
        "data": {
            "task": task,
            "courseProgress": (
                _camel_row(course_row, {"progress_id", "order_id"}) if course_row else None
            ),
            "examProgress": (
                _camel_row(exam_row, {"exam_progress_id", "order_id"}) if exam_row else None
            ),
            "courseProgressItems": course_items,
            "examProgressItems": exam_items,
            "logs": logs,
            "tikuFailures": failures,
        },
    }


def _task_values(request: TaskRequest) -> tuple[Any, ...]:
    """按任务表字段顺序生成写入值，并把空日期归一化为 NULL。"""
    return (
        request.orderId,
        request.taskType,
        request.status,
        request.triggerAt or None,
        request.workerCode or None,
        request.startedAt or None,
        request.finishedAt or None,
        request.heartbeatAt or None,
        request.retryCount,
        request.lastError or None,
        request.resultSummary or None,
        request.taskConfigJson or None,
    )


@router.post("/task")
def create_task(request: TaskRequest, database: Database = Depends(_database)) -> dict:
    """为现有订单创建待执行任务，租户从订单读取。"""
    with database.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT tenant_id FROM ea_order WHERE order_id=%s", (request.orderId,))
            order = cursor.fetchone()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    now = datetime.now()
    task_id = _insert(
        database,
        "INSERT INTO ea_task (tenant_id,order_id,task_type,status,trigger_at,worker_code,"
        "started_at,finished_at,heartbeat_at,retry_count,last_error,result_summary,"
        "task_config_json,create_time,update_time) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,"
        "%s,%s,%s,%s,%s,%s)",
        (order["tenant_id"], *_task_values(request), now, now),
    )
    return {"code": 200, "msg": "操作成功", "data": {"taskId": task_id}}


@router.put("/task")
def update_task(request: TaskRequest, database: Database = Depends(_database)) -> dict:
    """修改任务配置和当前状态。"""
    if not request.taskId:
        raise HTTPException(status_code=400, detail="任务ID不能为空")
    affected = _execute(
        database,
        "UPDATE ea_task SET order_id=%s,task_type=%s,status=%s,trigger_at=%s,worker_code=%s,"
        "started_at=%s,finished_at=%s,heartbeat_at=%s,retry_count=%s,last_error=%s,"
        "result_summary=%s,task_config_json=%s,update_time=%s WHERE task_id=%s",
        (*_task_values(request), datetime.now(), request.taskId),
    )
    if affected != 1:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"code": 200, "msg": "操作成功"}


@router.delete("/task/{task_id}")
def delete_task(task_id: str, database: Database = Depends(_database)) -> dict:
    """删除一个或多个任务。"""
    return _delete_ids(database, "ea_task", "task_id", task_id, "任务不存在")


def _requeue_where(database: Database, field: str, value: str) -> int:
    """把失败或已结束任务恢复为待执行，清除上次执行租约。"""
    if field not in {"task_id", "order_id"}:
        raise ValueError("unsupported requeue field")
    return _execute(
        database,
        f"UPDATE ea_task SET status=0,worker_code=NULL,started_at=NULL,heartbeat_at=NULL,"
        f"finished_at=NULL,last_error=NULL,update_time=%s WHERE {field}=%s AND status<>1",
        (datetime.now(), value),
    )


@router.post("/task/run/{task_id}")
def requeue_task(task_id: str, database: Database = Depends(_database)) -> dict:
    """恢复单个非运行中任务。"""
    if _requeue_where(database, "task_id", task_id) != 1:
        raise HTTPException(status_code=409, detail="任务不存在或正在执行")
    return {"code": 200, "msg": "任务已重新入队"}


@router.post("/task/run-order/{order_id}")
def requeue_order_tasks(order_id: str, database: Database = Depends(_database)) -> dict:
    """恢复订单下全部非运行中任务。"""
    affected = _requeue_where(database, "order_id", order_id)
    if affected < 1:
        raise HTTPException(status_code=409, detail="订单无可重新入队任务")
    return {"code": 200, "msg": "订单任务已重新入队", "data": {"count": affected}}


@router.post("/task/run-pending")
def run_pending(
    limit: int = Query(default=5, ge=1, le=20),
    database: Database = Depends(_database),
) -> dict:
    """使用 Python 平台适配器同步执行一批待执行任务。"""
    count = TaskRunner(TaskRepository(database)).run_once(limit, "manual-api")
    return {"code": 200, "msg": "执行完成", "data": {"count": count}}


@router.get("/runner-node/list")
def list_runner_nodes(
    worker_code: str | None = Query(default=None, alias="workerCode"),
    host_name: str | None = Query(default=None, alias="hostName"),
    status: int | None = Query(default=None),
    page_num: int = Query(default=1, ge=1, alias="pageNum"),
    page_size: int = Query(default=10, ge=1, le=10000, alias="pageSize"),
    database: Database = Depends(_database),
) -> dict:
    """筛选和分页执行节点。"""
    return _page(
        database,
        "ea_runner_node",
        NODE_COLUMNS,
        "node_id DESC",
        [
            ("worker_code", worker_code, True),
            ("host_name", host_name, True),
            ("status", status, False),
        ],
        page_num,
        page_size,
        {"node_id", "current_task_id", "current_order_id"},
    )


@router.get("/runner-node/{node_id}")
def get_runner_node(node_id: str, database: Database = Depends(_database)) -> dict:
    """返回执行节点详情。"""
    return _one(
        database,
        "ea_runner_node",
        NODE_COLUMNS,
        "node_id",
        node_id,
        {"node_id", "current_task_id", "current_order_id"},
        "执行节点不存在",
    )


def _node_values(request: RunnerNodeRequest) -> tuple[Any, ...]:
    """按执行节点表字段顺序生成写入值。"""
    return (
        request.workerCode,
        request.version or None,
        request.hostName or None,
        request.status,
        request.currentTaskId or None,
        request.currentOrderId or None,
        request.lastError or None,
        request.heartbeatAt or None,
        request.startedAt or None,
    )


@router.post("/runner-node")
def create_runner_node(
    request: RunnerNodeRequest,
    database: Database = Depends(_database),
) -> dict:
    """创建执行节点记录。"""
    now = datetime.now()
    node_id = _insert(
        database,
        "INSERT INTO ea_runner_node (worker_code,version,host_name,status,current_task_id,"
        "current_order_id,last_error,heartbeat_at,started_at,create_time,update_time) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (*_node_values(request), now, now),
    )
    return {"code": 200, "msg": "操作成功", "data": {"nodeId": node_id}}


@router.put("/runner-node")
def update_runner_node(
    request: RunnerNodeRequest,
    database: Database = Depends(_database),
) -> dict:
    """修改执行节点记录。"""
    if not request.nodeId:
        raise HTTPException(status_code=400, detail="节点ID不能为空")
    affected = _execute(
        database,
        "UPDATE ea_runner_node SET worker_code=%s,version=%s,host_name=%s,status=%s,"
        "current_task_id=%s,current_order_id=%s,last_error=%s,heartbeat_at=%s,started_at=%s,"
        "update_time=%s WHERE node_id=%s",
        (*_node_values(request), datetime.now(), request.nodeId),
    )
    if affected != 1:
        raise HTTPException(status_code=404, detail="执行节点不存在")
    return {"code": 200, "msg": "操作成功"}


@router.delete("/runner-node/{node_id}")
def delete_runner_node(node_id: str, database: Database = Depends(_database)) -> dict:
    """删除一个或多个执行节点。"""
    return _delete_ids(
        database,
        "ea_runner_node",
        "node_id",
        node_id,
        "执行节点不存在",
    )


@router.get("/runner-setting/list")
def list_runner_settings(
    tenant_id: str | None = Query(default=None, alias="tenantId"),
    ai_type: str | None = Query(default=None, alias="aiType"),
    page_num: int = Query(default=1, ge=1, alias="pageNum"),
    page_size: int = Query(default=10, ge=1, le=10000, alias="pageSize"),
    database: Database = Depends(_database),
) -> dict:
    """返回不含密钥的执行配置分页列表。"""
    return _page(
        database,
        "ea_runner_setting",
        SETTING_COLUMNS,
        "setting_id",
        [("tenant_id", tenant_id, False), ("ai_type", ai_type, True)],
        page_num,
        page_size,
        {"setting_id"},
    )


@router.get("/runner-setting/{setting_id}")
def get_runner_setting(setting_id: str, database: Database = Depends(_database)) -> dict:
    """返回不包含 AI 密钥的执行配置详情。"""
    return _one(
        database,
        "ea_runner_setting",
        SETTING_COLUMNS,
        "setting_id",
        setting_id,
        {"setting_id"},
        "执行配置不存在",
    )


def _setting_values(request: RunnerSettingRequest) -> tuple[Any, ...]:
    """按执行配置表字段顺序生成非密钥写入值。"""
    return (
        request.tenantId,
        request.aiType or None,
        request.aiUrl or None,
        request.aiModel or None,
        request.externalQuestionUrl or None,
        request.completionTone,
        request.colorLog,
        request.logLevel.upper(),
        request.logModel,
        request.pollIntervalSeconds,
        request.maxParallelTasks,
        request.taskTimeoutSeconds,
        request.logRetentionDays,
        request.remark or None,
    )


@router.post("/runner-setting")
def create_runner_setting(
    request: RunnerSettingRequest,
    database: Database = Depends(_database),
) -> dict:
    """创建执行配置，密钥仅写入且不在响应中回显。"""
    now = datetime.now()
    values = _setting_values(request)
    setting_id = _insert(
        database,
        "INSERT INTO ea_runner_setting (tenant_id,ai_type,ai_url,ai_model,ai_api_key,"
        "external_question_url,completion_tone,color_log,log_level,log_model,"
        "poll_interval_seconds,max_parallel_tasks,task_timeout_seconds,log_retention_days,"
        "remark,create_time,update_time) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,"
        "%s,%s,%s,%s,%s)",
        (*values[:4], request.aiApiKey or None, *values[4:], now, now),
    )
    return {"code": 200, "msg": "操作成功", "data": {"settingId": setting_id}}


@router.put("/runner-setting")
def update_runner_setting(
    request: RunnerSettingRequest,
    database: Database = Depends(_database),
) -> dict:
    """修改执行配置；空密钥保留数据库中的既有值。"""
    if not request.settingId:
        raise HTTPException(status_code=400, detail="配置ID不能为空")
    affected = _execute(
        database,
        "UPDATE ea_runner_setting SET tenant_id=%s,ai_type=%s,ai_url=%s,ai_model=%s,"
        "external_question_url=%s,completion_tone=%s,color_log=%s,log_level=%s,log_model=%s,"
        "poll_interval_seconds=%s,max_parallel_tasks=%s,task_timeout_seconds=%s,"
        "log_retention_days=%s,remark=%s,ai_api_key=COALESCE(NULLIF(%s,''),ai_api_key),"
        "update_time=%s WHERE setting_id=%s",
        (*_setting_values(request), request.aiApiKey, datetime.now(), request.settingId),
    )
    if affected != 1:
        raise HTTPException(status_code=404, detail="执行配置不存在")
    return {"code": 200, "msg": "操作成功"}


@router.delete("/runner-setting/{setting_id}")
def delete_runner_setting(setting_id: str, database: Database = Depends(_database)) -> dict:
    """删除一个或多个执行配置。"""
    return _delete_ids(
        database,
        "ea_runner_setting",
        "setting_id",
        setting_id,
        "执行配置不存在",
    )


@router.get("/school-cache/list")
def list_school_cache(
    source_school_id: str | None = Query(default=None, alias="sourceSchoolId"),
    platform_id: str | None = Query(default=None, alias="platformId"),
    platform_name: str | None = Query(default=None, alias="platformName"),
    school_name: str | None = Query(default=None, alias="schoolName"),
    enabled: int | None = Query(default=None),
    page_num: int = Query(default=1, ge=1, alias="pageNum"),
    page_size: int = Query(default=10, ge=1, le=10000, alias="pageSize"),
    database: Database = Depends(_database),
) -> dict:
    """筛选和分页学校能力缓存。"""
    return _page(
        database,
        "ea_school_cache",
        CACHE_COLUMNS,
        "cache_id",
        [
            ("source_school_id", source_school_id, False),
            ("platform_id", platform_id, False),
            ("platform_name", platform_name, True),
            ("school_name", school_name, True),
            ("enabled", enabled, False),
        ],
        page_num,
        page_size,
        {"cache_id", "source_school_id", "platform_id"},
    )


@router.get("/school-cache/{cache_id}")
def get_school_cache(cache_id: str, database: Database = Depends(_database)) -> dict:
    """返回学校能力缓存详情。"""
    return _one(
        database,
        "ea_school_cache",
        CACHE_COLUMNS,
        "cache_id",
        cache_id,
        {"cache_id", "source_school_id", "platform_id"},
        "学校缓存不存在",
    )


def _cache_values(request: SchoolCacheRequest) -> tuple[Any, ...]:
    """按学校缓存表字段顺序生成写入值。"""
    return (
        request.sourceSchoolId,
        request.platformId,
        request.platformName,
        request.schoolName,
        request.accessType,
        request.accessAddress or None,
        request.schoolUrl or None,
        request.schoolFid or None,
        request.schoolCode or None,
        request.schoolRemark or None,
        request.enabled,
        request.videoSupported,
        request.workSupported,
        request.examSupported,
        request.examSpecialOrderRequired,
        request.faceRequired,
        request.examType,
        request.answerOk,
        request.examState,
        request.submitTime,
        request.ipNumber,
    )


@router.post("/school-cache")
def create_school_cache(
    request: SchoolCacheRequest,
    database: Database = Depends(_database),
) -> dict:
    """创建学校能力缓存。"""
    now = datetime.now()
    cache_id = _insert(
        database,
        "INSERT INTO ea_school_cache (source_school_id,platform_id,platform_name,school_name,"
        "access_type,access_address,school_url,school_fid,school_code,school_remark,enabled,"
        "video_supported,work_supported,exam_supported,exam_special_order_required,"
        "face_required,exam_type,answer_ok,exam_state,submit_time,ip_number,create_time,"
        "update_time) VALUES (" + ",".join(["%s"] * 23) + ")",
        (*_cache_values(request), now, now),
    )
    return {"code": 200, "msg": "操作成功", "data": {"cacheId": cache_id}}


@router.put("/school-cache")
def update_school_cache(
    request: SchoolCacheRequest,
    database: Database = Depends(_database),
) -> dict:
    """修改学校能力缓存。"""
    if not request.cacheId:
        raise HTTPException(status_code=400, detail="缓存ID不能为空")
    assignments = (
        "source_school_id=%s,platform_id=%s,platform_name=%s,school_name=%s,access_type=%s,"
        "access_address=%s,school_url=%s,school_fid=%s,school_code=%s,school_remark=%s,"
        "enabled=%s,video_supported=%s,work_supported=%s,exam_supported=%s,"
        "exam_special_order_required=%s,face_required=%s,exam_type=%s,answer_ok=%s,"
        "exam_state=%s,submit_time=%s,ip_number=%s"
    )
    affected = _execute(
        database,
        f"UPDATE ea_school_cache SET {assignments},update_time=%s WHERE cache_id=%s",
        (*_cache_values(request), datetime.now(), request.cacheId),
    )
    if affected != 1:
        raise HTTPException(status_code=404, detail="学校缓存不存在")
    return {"code": 200, "msg": "操作成功"}


@router.delete("/school-cache/{cache_id}")
def delete_school_cache(cache_id: str, database: Database = Depends(_database)) -> dict:
    """删除一个或多个学校能力缓存。"""
    return _delete_ids(
        database,
        "ea_school_cache",
        "cache_id",
        cache_id,
        "学校缓存不存在",
    )


@router.get("/face-media/list")
def list_face_media(
    student_id: str | None = Query(default=None, alias="studentId"),
    status: int | None = Query(default=None),
    page_num: int = Query(default=1, ge=1, alias="pageNum"),
    page_size: int = Query(default=10, ge=1, le=10000, alias="pageSize"),
    database: Database = Depends(_database),
) -> dict:
    """按学员和状态筛选媒体元数据。"""
    return _page(
        database,
        "ea_face_media",
        FACE_COLUMNS,
        "face_media_id DESC",
        [("student_id", student_id, False), ("status", status, False)],
        page_num,
        page_size,
        {"face_media_id", "student_id", "uploaded_by"},
    )


@router.get("/face-media/{media_id}")
def get_face_media(media_id: str, database: Database = Depends(_database)) -> dict:
    """返回人脸媒体元数据详情。"""
    return _one(
        database,
        "ea_face_media",
        FACE_COLUMNS,
        "face_media_id",
        media_id,
        {"face_media_id", "student_id", "uploaded_by"},
        "媒体记录不存在",
    )


@router.post("/face-media")
def create_face_media(
    request: FaceMediaRequest,
    database: Database = Depends(_database),
) -> dict:
    """创建已有媒体文件的元数据记录。"""
    now = datetime.now()
    media_id = _insert(
        database,
        "INSERT INTO ea_face_media (tenant_id,student_id,file_url,file_type,status,uploaded_by,"
        "create_time,update_time) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
        (
            request.tenantId,
            request.studentId,
            request.fileUrl,
            request.fileType,
            request.status,
            request.uploadedBy,
            now,
            now,
        ),
    )
    return {"code": 200, "msg": "操作成功", "data": {"faceMediaId": media_id}}


@router.put("/face-media")
def update_face_media(
    request: FaceMediaRequest,
    database: Database = Depends(_database),
) -> dict:
    """修改人脸媒体元数据。"""
    if not request.faceMediaId:
        raise HTTPException(status_code=400, detail="媒体ID不能为空")
    affected = _execute(
        database,
        "UPDATE ea_face_media SET tenant_id=%s,student_id=%s,file_url=%s,file_type=%s,"
        "status=%s,uploaded_by=%s,update_time=%s WHERE face_media_id=%s",
        (
            request.tenantId,
            request.studentId,
            request.fileUrl,
            request.fileType,
            request.status,
            request.uploadedBy,
            datetime.now(),
            request.faceMediaId,
        ),
    )
    if affected != 1:
        raise HTTPException(status_code=404, detail="媒体记录不存在")
    return {"code": 200, "msg": "操作成功"}


@router.post("/face-media/upload")
async def upload_face_media(
    file: UploadFile = File(...),
    student_id: str = Form(..., alias="studentId"),
    authorization: str | None = Header(default=None),
    database: Database = Depends(_database),
) -> dict:
    """校验并归档 MP4，人脸记录租户和上传人从登录令牌确定。"""
    claims = _claims(authorization)
    if Path(file.filename or "").suffix.lower() != ".mp4":
        raise HTTPException(status_code=400, detail="仅允许上传 mp4 文件")
    with database.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT tenant_id FROM ea_student WHERE student_id=%s", (student_id,))
            student = cursor.fetchone()
    if not student or str(student["tenant_id"]) != str(claims.get("tenant") or ""):
        raise HTTPException(status_code=404, detail="学员不存在")

    upload_dir = Path(Settings.from_env().upload_dir).resolve()
    upload_dir.mkdir(parents=True, exist_ok=True)
    destination = upload_dir / f"{uuid4().hex}.mp4"
    size = 0
    try:
        with destination.open("wb") as output:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > 50 * 1024 * 1024:
                    raise HTTPException(status_code=413, detail="文件不能超过 50MB")
                output.write(chunk)
        now = datetime.now()
        media_id = _insert(
            database,
            "INSERT INTO ea_face_media (tenant_id,student_id,file_url,file_type,status,"
            "uploaded_by,create_time,update_time) VALUES (%s,%s,%s,'mp4',1,%s,%s,%s)",
            (
                student["tenant_id"],
                student_id,
                f"/uploads/{destination.name}",
                str(claims["sub"]),
                now,
                now,
            ),
        )
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    finally:
        await file.close()
    return {
        "code": 200,
        "msg": "上传成功",
        "data": f"/uploads/{destination.name}",
        "faceMediaId": media_id,
    }


@router.delete("/face-media/{media_id}")
def delete_face_media(media_id: str, database: Database = Depends(_database)) -> dict:
    """删除一个或多个人脸媒体数据库记录。"""
    return _delete_ids(
        database,
        "ea_face_media",
        "face_media_id",
        media_id,
        "媒体记录不存在",
    )


@router.get("/ledger/list")
def list_ledger(
    tenant_id: str | None = Query(default=None, alias="tenantId"),
    order_id: str | None = Query(default=None, alias="orderId"),
    ledger_type: int | None = Query(default=None, alias="type"),
    page_num: int = Query(default=1, ge=1, alias="pageNum"),
    page_size: int = Query(default=10, ge=1, le=10000, alias="pageSize"),
    database: Database = Depends(_database),
) -> dict:
    """筛选和分页积分流水。"""
    columns = (
        "ledger_id,tenant_id,order_id,change_points,gift_points,type,operator_user_id,"
        "remark,create_time"
    )
    return _page(
        database,
        "ea_ledger",
        columns,
        "ledger_id DESC",
        [
            ("tenant_id", tenant_id, False),
            ("order_id", order_id, False),
            ("type", ledger_type, False),
        ],
        page_num,
        page_size,
        {"ledger_id", "order_id", "operator_user_id"},
    )


@router.get("/ledger/{ledger_id}")
def get_ledger(ledger_id: str, database: Database = Depends(_database)) -> dict:
    """返回积分流水详情。"""
    return _one(
        database,
        "ea_ledger",
        "*",
        "ledger_id",
        ledger_id,
        {"ledger_id", "order_id", "operator_user_id"},
        "积分流水不存在",
    )


@router.get("/recharge/list")
def list_recharge(
    tenant_id: str | None = Query(default=None, alias="tenantId"),
    page_num: int = Query(default=1, ge=1, alias="pageNum"),
    page_size: int = Query(default=10, ge=1, le=10000, alias="pageSize"),
    database: Database = Depends(_database),
) -> dict:
    """筛选和分页充值记录。"""
    columns = (
        "recharge_id,tenant_id,operator_user_id,recharge_points,gift_points,remark,create_time"
    )
    return _page(
        database,
        "ea_recharge",
        columns,
        "recharge_id DESC",
        [("tenant_id", tenant_id, False)],
        page_num,
        page_size,
        {"recharge_id", "operator_user_id"},
    )


@router.get("/recharge/{recharge_id}")
def get_recharge(recharge_id: str, database: Database = Depends(_database)) -> dict:
    """返回充值记录详情。"""
    return _one(
        database,
        "ea_recharge",
        "*",
        "recharge_id",
        recharge_id,
        {"recharge_id", "operator_user_id"},
        "充值记录不存在",
    )


class RechargeRequest(BaseModel):
    """租户积分充值请求。"""

    tenantId: str = Field(min_length=1, max_length=20)
    operatorUserId: str | None = None
    rechargePoints: int = Field(gt=0)
    giftPoints: int = Field(default=0, ge=0)
    remark: str | None = Field(default=None, max_length=255)


@router.post("/recharge")
def create_recharge(
    request: RechargeRequest,
    authorization: str | None = Header(default=None),
    database: Database = Depends(_database),
) -> dict:
    """在一个事务中写入充值、流水并增加租户余额。"""
    claims = _claims(authorization)
    operator_id = request.operatorUserId or str(claims["sub"])
    now = datetime.now()
    total = request.rechargePoints + request.giftPoints
    with database.connection() as conn:
        conn.begin()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE ea_tenant SET balance_points=balance_points+%s,update_time=%s "
                    "WHERE tenant_id=%s",
                    (total, now, request.tenantId),
                )
                if cursor.rowcount != 1:
                    raise HTTPException(status_code=404, detail="租户不存在")
                cursor.execute(
                    "INSERT INTO ea_recharge (tenant_id,operator_user_id,recharge_points,"
                    "gift_points,remark,create_time,update_time) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                    (
                        request.tenantId,
                        operator_id,
                        request.rechargePoints,
                        request.giftPoints,
                        request.remark,
                        now,
                        now,
                    ),
                )
                recharge_id = str(cursor.lastrowid)
                cursor.execute(
                    "INSERT INTO ea_ledger (tenant_id,change_points,gift_points,type,"
                    "operator_user_id,remark,create_time,update_time) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                    (
                        request.tenantId,
                        request.rechargePoints,
                        request.giftPoints,
                        1,
                        operator_id,
                        request.remark,
                        now,
                        now,
                    ),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    return {"code": 200, "msg": "操作成功", "data": {"rechargeId": recharge_id}}


@router.get("/tiku-failure/list")
def list_tiku_failures(
    task_id: str | None = Query(default=None, alias="taskId"),
    order_id: str | None = Query(default=None, alias="orderId"),
    tenant_id: str | None = Query(default=None, alias="tenantId"),
    provider: str | None = Query(default=None),
    page_num: int = Query(default=1, ge=1, alias="pageNum"),
    page_size: int = Query(default=10, ge=1, le=10000, alias="pageSize"),
    database: Database = Depends(_database),
) -> dict:
    """筛选和分页题库失败记录。"""
    columns = (
        "failure_id,task_id,order_id,tenant_id,provider,question,options_json,reason,"
        "raw_response,create_time,update_time"
    )
    return _page(
        database,
        "ea_tiku_failure",
        columns,
        "failure_id DESC",
        [
            ("task_id", task_id, False),
            ("order_id", order_id, False),
            ("tenant_id", tenant_id, False),
            ("provider", provider, True),
        ],
        page_num,
        page_size,
        {"failure_id", "task_id", "order_id"},
    )


@router.get("/task-log/list")
def list_task_logs(
    task_id: str | None = Query(default=None, alias="taskId"),
    order_id: str | None = Query(default=None, alias="orderId"),
    tenant_id: str | None = Query(default=None, alias="tenantId"),
    worker_code: str | None = Query(default=None, alias="workerCode"),
    level: str | None = Query(default=None),
    page_num: int = Query(default=1, ge=1, alias="pageNum"),
    page_size: int = Query(default=10, ge=1, le=10000, alias="pageSize"),
    database: Database = Depends(_database),
) -> dict:
    """筛选和分页完整任务日志。"""
    columns = (
        "log_id,task_id,order_id,tenant_id,worker_code,seq_no,level,biz_type,biz_title,"
        "biz_status,message,failure_reason,created_at,create_time,update_time"
    )
    return _page(
        database,
        "ea_task_log",
        columns,
        "log_id DESC",
        [
            ("task_id", task_id, False),
            ("order_id", order_id, False),
            ("tenant_id", tenant_id, False),
            ("worker_code", worker_code, True),
            ("level", level, False),
        ],
        page_num,
        page_size,
        {"log_id", "task_id", "order_id"},
    )
