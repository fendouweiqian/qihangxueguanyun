-- 目标项目当前复用已有 education_assistant 数据库，不执行破坏性迁移。
-- 本文件只记录学生读取契约，正式 schema 迁移须在确认字段差异后补充。
SELECT student_id, tenant_id, school_id, account, password, open_id, name,
       study_grade, major, phone, id_card, status, login_status, login_message,
       login_checked_at, create_time, update_time
FROM ea_student
ORDER BY student_id ASC;

