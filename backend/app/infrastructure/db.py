"""MySQL 连接和学生查询仓储。"""

from contextlib import contextmanager
import json
from typing import Any, Iterator
from datetime import datetime, timedelta
import re

import pymysql
from pymysql.cursors import DictCursor

from app.config import Settings
from app.domain.task import TaskStatus


def _redact_error(value: str | None, limit: int = 500) -> str | None:
    """移除常见密码、Token、Cookie 片段，限制写入数据库的长度。"""
    if not value:
        return None
    text = re.sub(r"(?i)(password|passwd|token|cookie|secret)\s*[:=]\s*[^\s,;]+", r"\1=<redacted>", str(value))
    return text[:limit]


class Database:
    """按请求创建短生命周期 MySQL 连接。"""

    def __init__(self, settings: Settings):
        self.settings = settings

    @contextmanager
    def connection(self) -> Iterator[Any]:
        """建立连接并确保异常或正常返回时都关闭资源。"""
        conn = pymysql.connect(
            host=self.settings.db_host,
            port=self.settings.db_port,
            user=self.settings.db_user,
            password=self.settings.db_password,
            database=self.settings.db_name,
            charset="utf8mb4",
            connect_timeout=self.settings.db_connect_timeout,
            autocommit=True,
            cursorclass=DictCursor,
        )
        try:
            yield conn
        finally:
            conn.close()

    def ping(self) -> None:
        """执行轻量查询验证数据库可用性。"""
        with self.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()


class StudentRepository:
    """读取历史学生表，查询条件与旧服务保持一致。"""

    _columns = (
        "student_id, tenant_id, school_id, account, password, open_id, name, "
        "study_grade, major, phone, id_card, status, login_status, login_message, "
        "login_checked_at, create_time, update_time"
    )

    def __init__(self, database: Database):
        self.database = database

    def get_by_id(self, student_id: str, tenant_id: str | None = None) -> dict[str, Any] | None:
        """按学生 ID 查询一条记录，可选租户约束。"""
        sql = f"SELECT {self._columns} FROM ea_student WHERE student_id=%s"
        params: list[Any] = [student_id]
        if tenant_id:
            sql += " AND tenant_id=%s"
            params.append(tenant_id)
        with self.database.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.fetchone()

    def list_page(self, query: Any) -> tuple[list[dict[str, Any]], int]:
        """按旧系统规则筛选并按 student_id 升序分页。"""
        where = ["1=1"]
        params: list[Any] = []
        if query.tenant_id:
            where.append("tenant_id=%s")
            params.append(query.tenant_id)
        if query.school_id:
            where.append("school_id=%s")
            params.append(query.school_id)
        if query.account:
            where.append("account LIKE %s")
            params.append(f"%{query.account}%")
        if query.name:
            where.append("name LIKE %s")
            params.append(f"%{query.name}%")
        if query.phone:
            where.append("phone LIKE %s")
            params.append(f"%{query.phone}%")
        if query.status is not None:
            where.append("status=%s")
            params.append(query.status)
        predicate = " AND ".join(where)
        offset = (query.page_num - 1) * query.page_size
        with self.database.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"SELECT COUNT(*) AS total FROM ea_student WHERE {predicate}", params)
                total = int(cursor.fetchone()["total"])
                cursor.execute(
                    f"SELECT {self._columns} FROM ea_student WHERE {predicate} "
                    "ORDER BY student_id ASC LIMIT %s OFFSET %s",
                    [*params, query.page_size, offset],
                )
                return list(cursor.fetchall()), total

    def update_login_status(self, student_id: str, status: int, message: str) -> bool:
        """更新学生最近一次登录检测状态、消息和检测时间。"""
        now = datetime.now()
        with self.database.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE ea_student SET login_status=%s,login_message=%s,login_checked_at=%s,update_time=%s WHERE student_id=%s",
                    (status, _redact_error(message, 512), now, now, student_id),
                )
                conn.commit()
                return cursor.rowcount == 1


class UserRepository:
    """提供租户范围内的用户认证和管理操作。"""

    _columns = "user_id, tenant_id, username, nick_name, role, status, last_login_at, create_time, update_time"

    def __init__(self, database: Database):
        self.database = database

    def count(self) -> int:
        """返回用户总数，用于首次管理员初始化保护。"""
        with self.database.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) AS total FROM ea_user")
                return int(cursor.fetchone()["total"])

    def get_by_username(self, username: str, tenant_id: str | None = None) -> dict[str, Any] | None:
        """按用户名和可选租户读取用户及密码哈希。"""
        sql = f"SELECT {self._columns}, password_hash FROM ea_user WHERE username=%s"
        params: list[Any] = [username]
        if tenant_id:
            sql += " AND tenant_id=%s"
            params.append(tenant_id)
        with self.database.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                user = cursor.fetchone()
                if user:
                    return user
                return self._get_legacy_by_username(cursor, username, tenant_id)

    def get_by_id(self, user_id: str) -> dict[str, Any] | None:
        """按用户 ID 读取公开用户视图。"""
        with self.database.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"SELECT {self._columns} FROM ea_user WHERE user_id=%s", (user_id,))
                user = cursor.fetchone()
                return user or self._get_legacy_by_id(cursor, user_id)

    @staticmethod
    def _get_legacy_by_username(cursor: Any, username: str, tenant_id: str | None) -> dict[str, Any] | None:
        """从原管理用户表只读映射登录所需字段。"""
        predicate = "user_name=%s AND del_flag='0'"
        params: list[Any] = [username]
        if tenant_id:
            predicate += " AND tenant_id=%s"
            params.append(tenant_id)
        try:
            cursor.execute(
                "SELECT user_id, tenant_id, user_name AS username, nick_name, status, password AS legacy_password "
                "FROM sys_user WHERE " + predicate,
                params,
            )
        except pymysql.err.OperationalError:
            return None
        row = cursor.fetchone()
        if not row:
            return None
        row.update({"role": 1, "password_hash": None, "legacy_source": "sys_user"})
        return row

    @staticmethod
    def _get_legacy_by_id(cursor: Any, user_id: str) -> dict[str, Any] | None:
        """按原管理用户 ID 只读映射当前用户公开信息。"""
        try:
            cursor.execute(
                "SELECT user_id, tenant_id, user_name AS username, nick_name, status "
                "FROM sys_user WHERE user_id=%s AND del_flag='0'",
                (user_id,),
            )
        except pymysql.err.OperationalError:
            return None
        row = cursor.fetchone()
        if not row:
            return None
        row.update({"role": 1, "legacy_source": "sys_user"})
        return row

    def list_page(self, tenant_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        """按租户读取用户列表，不返回密码哈希。"""
        where = "WHERE tenant_id=%s" if tenant_id else ""
        params: list[Any] = [tenant_id] if tenant_id else []
        with self.database.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"SELECT {self._columns} FROM ea_user {where} ORDER BY user_id LIMIT %s", [*params, max(1, min(limit, 500))])
                return list(cursor.fetchall())

    def create(self, tenant_id: str | None, username: str, password_hash: str, nick_name: str | None, role: int, status: int) -> str:
        """创建用户并返回数据库生成的字符串 ID。"""
        with self.database.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO ea_user (tenant_id, username, password_hash, nick_name, role, status, create_time, update_time) VALUES (%s,%s,%s,%s,%s,%s,NOW(),NOW())",
                    (tenant_id, username, password_hash, nick_name, role, status),
                )
                conn.commit()
                return str(cursor.lastrowid)

    def update(self, user_id: str, tenant_id: str | None, nick_name: str | None, role: int | None, status: int | None, password_hash: str | None) -> bool:
        """更新用户可变字段，并在提供租户时执行范围约束。"""
        fields: dict[str, Any] = {"nick_name": nick_name, "role": role, "status": status, "password_hash": password_hash}
        fields = {key: value for key, value in fields.items() if value is not None}
        if not fields:
            return False
        where = "user_id=%s"
        values: list[Any] = [*fields.values(), user_id]
        if tenant_id:
            where += " AND tenant_id=%s"
            values.append(tenant_id)
        assignments = ", ".join(f"{key}=%s" for key in fields)
        with self.database.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"UPDATE ea_user SET {assignments}, update_time=NOW() WHERE {where}", values)
                conn.commit()
                return cursor.rowcount == 1

    def delete(self, user_id: str, tenant_id: str | None = None) -> bool:
        """删除指定用户，租户管理员只能删除本租户用户。"""
        where = "user_id=%s"
        params: list[Any] = [user_id]
        if tenant_id:
            where += " AND tenant_id=%s"
            params.append(tenant_id)
        with self.database.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"DELETE FROM ea_user WHERE {where}", params)
                conn.commit()
                return cursor.rowcount == 1

    def touch_login(self, user_id: str) -> None:
        """记录用户最近一次成功登录时间。"""
        with self.database.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("UPDATE ea_user SET last_login_at=NOW(), update_time=NOW() WHERE user_id=%s", (user_id,))
                conn.commit()


class TaskRepository:
    """负责任务领取和结果回写，所有状态更新都在数据库事务内完成。"""

    def __init__(self, database: Database):
        self.database = database

    def claim(self, limit: int, runner_id: str, task_types: list[int] | None = None) -> list[dict[str, Any]]:
        """锁定待执行任务并返回订单、学生账号快照。"""
        now = datetime.now()
        claimed: list[dict[str, Any]] = []
        with self.database.connection() as conn:
            conn.begin()
            try:
                with conn.cursor() as cursor:
                    predicates = ["status=%s"]
                    query_params: list[Any] = [TaskStatus.PENDING]
                    normalized_types = sorted({int(value) for value in (task_types or [])})
                    if normalized_types:
                        placeholders = ",".join(["%s"] * len(normalized_types))
                        predicates.append(f"task_type IN ({placeholders})")
                        query_params.extend(normalized_types)
                    cursor.execute(
                        "SELECT task_id, order_id, tenant_id, task_type, retry_count, task_config_json "
                        f"FROM ea_task WHERE {' AND '.join(predicates)} ORDER BY task_id ASC LIMIT %s FOR UPDATE",
                        [*query_params, limit],
                    )
                    tasks = list(cursor.fetchall())
                    for task in tasks:
                        updated = cursor.execute(
                            "UPDATE ea_task SET status=%s, worker_code=%s, trigger_at=%s, started_at=%s, "
                            "heartbeat_at=%s, last_error=NULL, result_summary=NULL, update_time=%s "
                            "WHERE task_id=%s AND status=%s",
                            (TaskStatus.RUNNING, runner_id or None, now, now, now, now,
                             task["task_id"], TaskStatus.PENDING),
                        )
                        if updated != 1:
                            continue
                        cursor.execute(
                            "SELECT o.order_id, o.order_type, o.course_name, o.course_code, o.term, "
                            "o.school_id, o.platform_id, o.student_id, s.account, s.password, s.name, "
                            "s.open_id, sc.school_name, sc.school_url, sc.access_type, sc.access_address, p.platform_name "
                            "FROM ea_order o JOIN ea_student s ON s.student_id=o.student_id "
                            "LEFT JOIN ea_school sc ON sc.school_id=o.school_id "
                            "LEFT JOIN ea_platform p ON p.platform_id=o.platform_id "
                            "WHERE o.order_id=%s",
                            (task["order_id"],),
                        )
                        order = cursor.fetchone()
                        if not order:
                            cursor.execute(
                                "UPDATE ea_task SET status=%s, finished_at=%s, last_error=%s, update_time=%s WHERE task_id=%s",
                                (TaskStatus.FAILED, now, "订单或学生不存在", now, task["task_id"]),
                            )
                            continue
                        task_config = task.get("task_config_json")
                        if isinstance(task_config, str):
                            try:
                                task_config = json.loads(task_config)
                            except (TypeError, ValueError):
                                task_config = {}
                        if not isinstance(task_config, dict):
                            task_config = {}
                        adapter_name = str(task_config.get("adapter") or "").strip()
                        claimed_task = {
                            "taskId": str(task["task_id"]), "orderId": str(task["order_id"]),
                            "tenantId": str(task["tenant_id"]), "taskType": int(task["task_type"]),
                            "retryCount": int(task["retry_count"]),
                            "orderType": order.get("order_type"), "courseName": order.get("course_name"),
                            "courseCode": order.get("course_code"), "term": order.get("term"),
                            "schoolId": str(order["school_id"]) if order.get("school_id") is not None else None,
                            "platformId": str(order["platform_id"]) if order.get("platform_id") is not None else None,
                            "studentId": str(order["student_id"]) if order.get("student_id") is not None else None,
                            "studentAccount": order.get("account"),
                            "studentPassword": order.get("password"),
                            "studentName": order.get("name"),
                            "studentOpenId": order.get("open_id"),
                            "schoolUrl": order.get("school_url"),
                            "schoolName": order.get("school_name"),
                            "schoolAccessType": order.get("access_type"),
                            "schoolAccessAddress": order.get("access_address"),
                            "platformName": order.get("platform_name"),
                            "adapter": adapter_name or None,
                        }
                        # 仅转发平台执行所需的白名单配置，避免把任意任务 JSON 或凭证带入执行上下文。
                        for key in ("operation", "action", "learningBaseUrl", "course", "chapterId", "courseId", "clazzId", "cpi", "tiku", "fontMapPath", "semesterId", "semester_id", "examId", "crsId", "stuId", "signCode", "submitExam", "captchaApiUrl", "captchaApiToken", "captchaApiType", "autoExam", "cxExamSw", "cxNode", "cxWorkSw", "examAutoSubmit", "excludeCourses", "includeCourses", "videoModel"):
                            if key in task_config:
                                claimed_task[key] = task_config[key]
                        claimed.append(claimed_task)
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        return claimed

    def submit_result(self, task_id: str, success: bool, code: str, message: str, retry_delta: int) -> bool:
        """幂等写回任务结果；已完成任务不会被重复请求覆盖。"""
        now = datetime.now()
        status = TaskStatus.SUCCESS if success else TaskStatus.FAILED
        error = None if success else _redact_error(f"{code}: {message}" if code and message else (message or code or "任务执行失败"))
        summary = _redact_error(message or code or "") or ""
        with self.database.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT status FROM ea_task WHERE task_id=%s FOR UPDATE", (task_id,))
                current = cursor.fetchone()
                if not current:
                    return False
                if int(current["status"]) == TaskStatus.SUCCESS:
                    conn.commit()
                    return True
                cursor.execute(
                    "UPDATE ea_task SET status=%s, finished_at=%s, last_error=%s, "
                    "result_summary=%s, retry_count=retry_count+%s, update_time=%s "
                    "WHERE task_id=%s AND status IN (%s,%s)",
                    (status, now, error, summary, max(0, retry_delta), now,
                     task_id, TaskStatus.RUNNING, TaskStatus.PENDING),
                )
                conn.commit()
                return cursor.rowcount == 1

    def upsert_course_progress(self, payload: dict[str, Any]) -> None:
        """幂等写回课程进度快照，唯一键沿用 order_id。"""
        now = datetime.now()
        with self.database.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO ea_course_progress (order_id, tenant_id, course_name, term, video_status, video_note, video_time, work_status, work_note, work_time, exam_status, exam_note, exam_time, create_time, update_time) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE tenant_id=VALUES(tenant_id), course_name=VALUES(course_name), term=VALUES(term), video_status=VALUES(video_status), video_note=VALUES(video_note), video_time=VALUES(video_time), work_status=VALUES(work_status), work_note=VALUES(work_note), work_time=VALUES(work_time), exam_status=VALUES(exam_status), exam_note=VALUES(exam_note), exam_time=VALUES(exam_time), update_time=VALUES(update_time)",
                    (payload.get("orderId"), payload.get("tenantId"), payload.get("courseName"), payload.get("term"), payload.get("videoStatus", 0), _redact_error(payload.get("videoNote"), 255), payload.get("videoTime") or (now if payload.get("videoStatus") else None), payload.get("workStatus", 0), _redact_error(payload.get("workNote"), 255), payload.get("workTime") or (now if payload.get("workStatus") else None), payload.get("examStatus", 0), _redact_error(payload.get("examNote"), 255), payload.get("examTime") or (now if payload.get("examStatus") else None), now, now),
                )

    def upsert_exam_progress(self, payload: dict[str, Any]) -> None:
        """幂等写回考试进度快照，唯一键沿用 order_id。"""
        now = datetime.now()
        with self.database.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO ea_exam_progress (order_id, tenant_id, status, score, note, finished_at, create_time, update_time) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE tenant_id=VALUES(tenant_id), status=VALUES(status), score=VALUES(score), note=VALUES(note), finished_at=VALUES(finished_at), update_time=VALUES(update_time)",
                    (payload.get("orderId"), payload.get("tenantId"), payload.get("status", 0), payload.get("score"), _redact_error(payload.get("note"), 255), payload.get("finishedAt") or (now if payload.get("status") else None), now, now),
                )

    def replace_course_progress_items(self, payload: dict[str, Any]) -> int:
        """按订单替换课程进度明细，返回实际写入数量。"""
        now = datetime.now()
        items = payload.get("items") if isinstance(payload.get("items"), list) else []
        written = 0
        with self.database.connection() as conn:
            conn.begin()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "DELETE FROM ea_course_progress_item WHERE order_id=%s AND tenant_id=%s",
                        (payload.get("orderId"), payload.get("tenantId")),
                    )
                    cursor.execute("SELECT item_id FROM ea_course_progress_item ORDER BY item_id DESC LIMIT 1 FOR UPDATE")
                    row = cursor.fetchone()
                    next_item_id = int(row["item_id"] if row else 0) + 1
                    for item in items:
                        if not isinstance(item, dict) or not str(item.get("courseName") or "").strip():
                            continue
                        cursor.execute(
                            "INSERT INTO ea_course_progress_item "
                            "(item_id, order_id, tenant_id, course_name, course_type, required_flag, term, learning_status, "
                            "learning_percent, learning_text, work_status, latest_time, create_time, update_time) "
                            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                            (next_item_id, payload.get("orderId"), payload.get("tenantId"), _redact_error(item.get("courseName"), 128),
                             _redact_error(item.get("courseType"), 32), item.get("requiredFlag", 0),
                             _redact_error(item.get("term"), 64), item.get("learningStatus", 0),
                             item.get("learningPercent"), _redact_error(item.get("learningText"), 64),
                             item.get("workStatus", 0), item.get("latestTime") or now, now, now),
                        )
                        next_item_id += 1
                        written += 1
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        return written

    def replace_exam_progress_items(self, payload: dict[str, Any]) -> int:
        """按订单替换考试进度明细，并保留已有冻结项标记。"""
        now = datetime.now()
        items = payload.get("items") if isinstance(payload.get("items"), list) else []
        written = 0
        with self.database.connection() as conn:
            conn.begin()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT exam_name, frozen_reason, frozen_time FROM ea_exam_progress_item "
                        "WHERE order_id=%s AND tenant_id=%s AND frozen_flag=1",
                        (payload.get("orderId"), payload.get("tenantId")),
                    )
                    frozen = {str(row["exam_name"]).strip(): row for row in cursor.fetchall()}
                    cursor.execute(
                        "DELETE FROM ea_exam_progress_item WHERE order_id=%s AND tenant_id=%s",
                        (payload.get("orderId"), payload.get("tenantId")),
                    )
                    cursor.execute("SELECT item_id FROM ea_exam_progress_item ORDER BY item_id DESC LIMIT 1 FOR UPDATE")
                    row = cursor.fetchone()
                    next_item_id = int(row["item_id"] if row else 0) + 1
                    for item in items:
                        if not isinstance(item, dict) or not str(item.get("examName") or "").strip():
                            continue
                        exam_name = _redact_error(item.get("examName"), 128) or ""
                        old = frozen.get(exam_name.strip())
                        cursor.execute(
                            "INSERT INTO ea_exam_progress_item "
                            "(item_id, order_id, tenant_id, exam_name, exam_status, score, exam_time, latest_time, remark, "
                            "frozen_flag, frozen_reason, frozen_time, create_time, update_time) "
                            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                            (next_item_id, payload.get("orderId"), payload.get("tenantId"), exam_name, item.get("examStatus", 0),
                             item.get("score"), item.get("examTime"), item.get("latestTime") or now,
                             _redact_error(item.get("remark"), 255), 1 if old else 0,
                             old.get("frozen_reason") if old else None, old.get("frozen_time") if old else None,
                             now, now),
                        )
                        next_item_id += 1
                        written += 1
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        return written

    def update_student_profile(self, payload: dict[str, Any]) -> bool:
        """按租户更新学生可采集档案字段，不触碰账号和密码。"""
        fields: dict[str, Any] = {}
        for name, limit in (("studentName", 64), ("studyGrade", 64), ("major", 128)):
            value = str(payload.get(name) or "").strip()
            if value:
                fields[{"studentName": "name", "studyGrade": "study_grade", "major": "major"}[name]] = value[:limit]
        if not fields:
            return False
        assignments = ", ".join(f"{column}=%s" for column in fields)
        values = [*fields.values(), datetime.now(), payload.get("studentId"), payload.get("tenantId")]
        with self.database.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"UPDATE ea_student SET {assignments}, update_time=%s WHERE student_id=%s AND tenant_id=%s",
                    values,
                )
                conn.commit()
                return cursor.rowcount == 1

    def record_tiku_failure(self, payload: dict[str, Any]) -> None:
        """记录题库查询失败，限制字段长度并脱敏。"""
        now = datetime.now()
        with self.database.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO ea_tiku_failure (task_id, order_id, tenant_id, provider, question, options_json, reason, raw_response, create_time, update_time) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (payload.get("taskId"), payload.get("orderId"), payload.get("tenantId"), _redact_error(payload.get("provider"), 64), _redact_error(payload.get("question"), 1000), _redact_error(payload.get("optionsJson"), 2000), _redact_error(payload.get("reason"), 255), _redact_error(payload.get("rawResponse"), 4000), now, now),
                )

    def insert_task_log(self, payload: dict[str, Any]) -> None:
        """写入脱敏任务日志，日志内容不允许携带凭证。"""
        now = datetime.now()
        with self.database.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO ea_task_log (task_id, order_id, tenant_id, worker_code, seq_no, level, message, created_at, create_time, update_time) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (payload.get("taskId"), payload.get("orderId"), payload.get("tenantId"), _redact_error(payload.get("workerCode"), 64), payload.get("seqNo", 0), _redact_error(payload.get("level"), 16) or "INFO", _redact_error(payload.get("message"), 4000) or "", now, now, now),
                )

    def cancel(self, task_id: str, reason: str) -> bool:
        """取消待执行或执行中的任务，复用失败状态且不增加重试次数。"""
        now = datetime.now()
        with self.database.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE ea_task SET status=%s, finished_at=%s, heartbeat_at=NULL, last_error=%s, update_time=%s WHERE task_id=%s AND status IN (%s,%s)",
                    (TaskStatus.FAILED, now, _redact_error(reason or "任务已取消"), now, task_id, TaskStatus.PENDING, TaskStatus.RUNNING),
                )
                conn.commit()
                return cursor.rowcount == 1

    def touch_heartbeat(self, task_id: str, runner_id: str) -> bool:
        """更新执行节点持有任务的心跳，拒绝跨节点或非执行中任务。"""
        if not runner_id:
            return False
        now = datetime.now()
        with self.database.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE ea_task SET heartbeat_at=%s, update_time=%s "
                    "WHERE task_id=%s AND worker_code=%s AND status=%s",
                    (now, now, task_id, runner_id, TaskStatus.RUNNING),
                )
                conn.commit()
                return cursor.rowcount == 1

    def recycle_timeouts(self, timeout_seconds: int) -> int:
        """回收心跳超时任务，恢复待执行状态并增加一次重试。"""
        cutoff = datetime.now() - timedelta(seconds=max(1, timeout_seconds))
        with self.database.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE ea_task SET status=%s, worker_code=NULL, heartbeat_at=NULL, started_at=NULL, result_summary=NULL, last_error=%s, retry_count=retry_count+1, update_time=NOW() WHERE status=%s AND heartbeat_at IS NOT NULL AND heartbeat_at < %s",
                    (TaskStatus.PENDING, "执行心跳超时，任务已回收", TaskStatus.RUNNING, cutoff),
                )
                conn.commit()
                return cursor.rowcount
