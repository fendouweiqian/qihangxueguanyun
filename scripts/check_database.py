"""只读检查目标数据库是否满足当前后端读取契约。"""

from __future__ import annotations

import os
import pymysql


REQUIRED_TABLES = {
    "ea_platform": {"platform_id", "platform_name"},
    "ea_school": {"school_id", "platform_id", "school_name", "access_type", "school_state", "school_fid", "school_exam2"},
    "ea_school_cache": {"cache_id", "source_school_id", "platform_id", "school_name", "enabled"},
    "ea_tenant": {"tenant_id", "tenant_name", "status", "balance_points"},
    "ea_user": {"user_id", "tenant_id", "username", "password_hash", "role", "status"},
    "ea_student": {"student_id", "tenant_id", "school_id", "account", "password", "name", "status"},
    "ea_order": {"order_id", "student_id", "tenant_id"},
    "ea_task": {"task_id", "order_id", "tenant_id", "task_type", "status"},
    "ea_course_progress": {"progress_id", "order_id", "tenant_id", "video_status", "work_status", "exam_status"},
    "ea_exam_progress": {"exam_progress_id", "order_id", "tenant_id", "status", "score"},
    "ea_course_progress_item": {"item_id", "order_id", "tenant_id", "course_name", "learning_status"},
    "ea_exam_progress_item": {"item_id", "order_id", "tenant_id", "exam_name", "exam_status", "frozen_flag"},
    "ea_task_log": {"log_id", "task_id", "tenant_id", "message"},
    "ea_tiku_failure": {"failure_id", "task_id", "tenant_id", "reason"},
    "ea_runner_node": {"node_id", "worker_code", "status", "heartbeat_at"},
    "ea_runner_setting": {"setting_id", "tenant_id", "external_question_url", "task_timeout_seconds"},
    "ea_face_media": {"face_media_id", "tenant_id", "student_id", "file_url", "status"},
    "ea_ledger": {"ledger_id", "tenant_id", "change_points", "type"},
    "ea_recharge": {"recharge_id", "tenant_id", "operator_user_id", "recharge_points"},
}


def main() -> int:
    """检查业务表和字段存在性，只输出结构摘要。"""
    conn = pymysql.connect(
        host=os.getenv("EDUCATION_DB_HOST", "127.0.0.1"),
        port=int(os.getenv("EDUCATION_DB_PORT", "3307")),
        user=os.getenv("EDUCATION_DB_USER", "root"),
        password=os.getenv("EDUCATION_DB_PASSWORD", ""),
        database=os.getenv("EDUCATION_DB_NAME", "education_assistant"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
        connect_timeout=5,
    )
    failures: list[str] = []
    try:
        with conn.cursor() as cursor:
            for table, required_columns in REQUIRED_TABLES.items():
                cursor.execute(
                    "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
                    "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=%s",
                    (table,),
                )
                actual = {row["COLUMN_NAME"] for row in cursor.fetchall()}
                missing = sorted(required_columns - actual)
                if missing:
                    failures.append(f"{table}: missing={','.join(missing)}")
                else:
                    print(f"table={table} columns=ok")
            cursor.execute("SELECT COUNT(*) AS total FROM ea_student")
            print(f"student_rows={cursor.fetchone()['total']}")
    finally:
        conn.close()
    if failures:
        print("database_contract=failed")
        for failure in failures:
            print(failure)
        return 1
    print("database_contract=passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
