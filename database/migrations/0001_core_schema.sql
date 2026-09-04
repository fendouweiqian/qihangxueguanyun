-- 核心领域表初始化。仅在隔离目标数据库执行，不会修改源项目数据库。
-- 所有标识字段沿用 BIGINT，应用层 JSON 序列化为字符串。

CREATE TABLE IF NOT EXISTS ea_platform (
  platform_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '平台ID',
  platform_name VARCHAR(64) NOT NULL COMMENT '平台名称',
  remark VARCHAR(255) DEFAULT NULL COMMENT '备注',
  create_time DATETIME DEFAULT NULL COMMENT '创建时间',
  update_time DATETIME DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (platform_id), UNIQUE KEY uk_platform_name (platform_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='教育平台表';

CREATE TABLE IF NOT EXISTS ea_school (
  school_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '学校ID',
  platform_id BIGINT UNSIGNED NOT NULL COMMENT '平台ID',
  school_name VARCHAR(128) NOT NULL COMMENT '学校名称',
  access_type TINYINT NOT NULL DEFAULT 1 COMMENT '访问类型：1网页 2小程序',
  access_address VARCHAR(255) DEFAULT NULL COMMENT '访问地址或入口说明',
  school_url VARCHAR(255) DEFAULT NULL COMMENT '学校网址',
  school_state TINYINT NOT NULL DEFAULT 0 COMMENT '学校状态',
  school_video TINYINT NOT NULL DEFAULT 0 COMMENT '视频支持状态',
  school_work TINYINT NOT NULL DEFAULT 0 COMMENT '作业支持状态',
  school_exam TINYINT NOT NULL DEFAULT 0 COMMENT '考试支持状态',
  school_face TINYINT NOT NULL DEFAULT 0 COMMENT '人脸核验要求',
  school_exam2 TINYINT NOT NULL DEFAULT 0 COMMENT '是否需要独立考试下单',
  school_exam_type TINYINT NOT NULL DEFAULT 0 COMMENT '考试类型',
  school_answer_ok TINYINT NOT NULL DEFAULT 0 COMMENT '答案可用状态',
  school_exam_state TINYINT NOT NULL DEFAULT 0 COMMENT '考试状态',
  school_sumbit_time INT NOT NULL DEFAULT 0 COMMENT '提交时间限制（保留历史字段拼写）',
  school_ip_number INT NOT NULL DEFAULT 0 COMMENT 'IP 数量限制',
  school_fid VARCHAR(128) DEFAULT NULL COMMENT '学校平台 FID',
  school_code VARCHAR(255) DEFAULT NULL COMMENT '学校平台编码',
  school_remark VARCHAR(255) DEFAULT NULL COMMENT '学校备注',
  create_time DATETIME DEFAULT NULL COMMENT '创建时间',
  update_time DATETIME DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (school_id), KEY idx_school_platform (platform_id), KEY idx_school_name (school_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='学校配置表';

CREATE TABLE IF NOT EXISTS ea_tenant (
  tenant_id VARCHAR(20) NOT NULL COMMENT '租户编号',
  tenant_name VARCHAR(64) NOT NULL COMMENT '租户名称',
  status TINYINT NOT NULL DEFAULT 0 COMMENT '租户状态',
  balance_points BIGINT NOT NULL DEFAULT 0 COMMENT '积分余额',
  remark VARCHAR(255) DEFAULT NULL COMMENT '备注',
  create_dept BIGINT DEFAULT NULL COMMENT '创建部门',
  create_by BIGINT DEFAULT NULL COMMENT '创建者',
  create_time DATETIME DEFAULT NULL COMMENT '创建时间',
  update_by BIGINT DEFAULT NULL COMMENT '更新者',
  update_time DATETIME DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (tenant_id), UNIQUE KEY uk_tenant_name (tenant_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='教育租户表';

CREATE TABLE IF NOT EXISTS ea_user (
  user_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '用户ID',
  tenant_id VARCHAR(20) DEFAULT NULL COMMENT '租户编号',
  username VARCHAR(64) NOT NULL COMMENT '用户名',
  password_hash VARCHAR(128) NOT NULL COMMENT '密码哈希',
  nick_name VARCHAR(64) DEFAULT NULL COMMENT '用户昵称',
  role TINYINT NOT NULL COMMENT '用户角色',
  status TINYINT NOT NULL DEFAULT 0 COMMENT '用户状态',
  last_login_at DATETIME DEFAULT NULL COMMENT '最后登录时间',
  create_time DATETIME DEFAULT NULL COMMENT '创建时间',
  update_time DATETIME DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (user_id), UNIQUE KEY uk_user_username (username), KEY idx_user_tenant (tenant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='教育用户表';

CREATE TABLE IF NOT EXISTS ea_student (
  student_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '学生ID',
  tenant_id VARCHAR(20) NOT NULL COMMENT '租户编号',
  school_id BIGINT UNSIGNED NOT NULL COMMENT '学校ID',
  account VARCHAR(64) NOT NULL COMMENT '学生账号',
  password VARCHAR(128) NOT NULL COMMENT '学生登录密码（仅内部执行使用）',
  open_id VARCHAR(128) DEFAULT NULL COMMENT '开放平台OpenID',
  name VARCHAR(64) NOT NULL COMMENT '学生姓名',
  study_grade VARCHAR(64) DEFAULT NULL COMMENT '学籍年级',
  major VARCHAR(128) DEFAULT NULL COMMENT '培养专业',
  phone VARCHAR(32) DEFAULT NULL COMMENT '手机号',
  id_card VARCHAR(64) DEFAULT NULL COMMENT '身份证号',
  status TINYINT NOT NULL DEFAULT 0 COMMENT '学生状态',
  login_status TINYINT DEFAULT 0 COMMENT '登录状态：0未检测 1成功 2失败 3检测中',
  login_message VARCHAR(512) DEFAULT NULL COMMENT '最近一次登录检测结果或失败原因',
  login_checked_at DATETIME DEFAULT NULL COMMENT '最近一次登录检测时间',
  create_time DATETIME DEFAULT NULL COMMENT '创建时间',
  update_time DATETIME DEFAULT NULL COMMENT '更新时间',
  create_dept BIGINT DEFAULT NULL COMMENT '创建部门',
  create_by BIGINT DEFAULT NULL COMMENT '创建者',
  update_by BIGINT DEFAULT NULL COMMENT '更新者',
  PRIMARY KEY (student_id),
  UNIQUE KEY uk_student_account (tenant_id, school_id, account),
  KEY idx_student_tenant (tenant_id),
  KEY idx_student_school (school_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='学生账号表';

CREATE TABLE IF NOT EXISTS ea_order (
  order_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '订单ID',
  tenant_id VARCHAR(20) NOT NULL COMMENT '租户编号',
  student_id BIGINT UNSIGNED NOT NULL COMMENT '学生ID',
  school_id BIGINT UNSIGNED NOT NULL COMMENT '学校ID',
  platform_id BIGINT UNSIGNED NOT NULL COMMENT '平台ID',
  order_type TINYINT NOT NULL COMMENT '订单类型',
  course_name VARCHAR(128) DEFAULT NULL COMMENT '课程名称',
  course_code VARCHAR(128) DEFAULT NULL COMMENT '课程编码',
  term VARCHAR(64) DEFAULT NULL COMMENT '学期',
  exam_start_at DATETIME DEFAULT NULL COMMENT '考试开始时间',
  exam_end_at DATETIME DEFAULT NULL COMMENT '考试结束时间',
  status TINYINT NOT NULL DEFAULT 0 COMMENT '订单状态',
  cost_points BIGINT NOT NULL DEFAULT 0 COMMENT '消耗积分',
  paid_at DATETIME DEFAULT NULL COMMENT '支付时间',
  remark VARCHAR(255) DEFAULT NULL COMMENT '订单备注',
  create_time DATETIME DEFAULT NULL COMMENT '创建时间',
  update_time DATETIME DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (order_id), KEY idx_order_student (student_id), KEY idx_order_tenant (tenant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='订单表';

CREATE TABLE IF NOT EXISTS ea_task (
  task_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '任务ID',
  order_id BIGINT UNSIGNED NOT NULL COMMENT '订单ID',
  tenant_id VARCHAR(20) NOT NULL COMMENT '租户编号',
  task_type TINYINT NOT NULL COMMENT '任务类型：1学习 2考试 3作业',
  status TINYINT NOT NULL DEFAULT 0 COMMENT '任务状态：0待执行 1执行中 2成功 3失败',
  trigger_at DATETIME DEFAULT NULL COMMENT '触发时间',
  worker_code VARCHAR(64) DEFAULT NULL COMMENT '执行节点编码',
  started_at DATETIME DEFAULT NULL COMMENT '开始时间',
  finished_at DATETIME DEFAULT NULL COMMENT '结束时间',
  heartbeat_at DATETIME DEFAULT NULL COMMENT '心跳时间',
  retry_count INT NOT NULL DEFAULT 0 COMMENT '重试次数',
  last_error VARCHAR(500) DEFAULT NULL COMMENT '最后错误信息（已脱敏）',
  result_summary VARCHAR(1000) DEFAULT NULL COMMENT '执行摘要',
  task_config_json JSON DEFAULT NULL COMMENT '任务配置快照',
  create_time DATETIME DEFAULT NULL COMMENT '创建时间',
  update_time DATETIME DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (task_id), KEY idx_task_order (order_id), KEY idx_task_status (status), KEY idx_task_heartbeat (status, heartbeat_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='任务表';

CREATE TABLE IF NOT EXISTS ea_course_progress (
  progress_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '课程进度ID',
  order_id BIGINT UNSIGNED NOT NULL COMMENT '订单ID',
  tenant_id VARCHAR(20) NOT NULL COMMENT '租户编号',
  course_name VARCHAR(128) DEFAULT NULL COMMENT '课程名称',
  term VARCHAR(64) DEFAULT NULL COMMENT '学期',
  video_status TINYINT DEFAULT 0 COMMENT '视频进度状态',
  video_note VARCHAR(255) DEFAULT NULL COMMENT '视频进度备注',
  video_time DATETIME DEFAULT NULL COMMENT '视频完成时间',
  work_status TINYINT DEFAULT 0 COMMENT '作业进度状态',
  work_note VARCHAR(255) DEFAULT NULL COMMENT '作业进度备注',
  work_time DATETIME DEFAULT NULL COMMENT '作业完成时间',
  exam_status TINYINT DEFAULT 0 COMMENT '考试进度状态',
  exam_note VARCHAR(255) DEFAULT NULL COMMENT '考试进度备注',
  exam_time DATETIME DEFAULT NULL COMMENT '考试完成时间',
  create_time DATETIME DEFAULT NULL COMMENT '创建时间',
  update_time DATETIME DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (progress_id), UNIQUE KEY uk_course_progress_order (order_id), KEY idx_course_progress_tenant (tenant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='课程进度表';

CREATE TABLE IF NOT EXISTS ea_exam_progress (
  exam_progress_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '考试进度ID',
  order_id BIGINT UNSIGNED NOT NULL COMMENT '订单ID',
  tenant_id VARCHAR(20) NOT NULL COMMENT '租户编号',
  status TINYINT DEFAULT 0 COMMENT '考试状态',
  score DECIMAL(10,2) DEFAULT NULL COMMENT '考试成绩',
  note VARCHAR(255) DEFAULT NULL COMMENT '考试备注',
  finished_at DATETIME DEFAULT NULL COMMENT '完成时间',
  create_time DATETIME DEFAULT NULL COMMENT '创建时间',
  update_time DATETIME DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (exam_progress_id), UNIQUE KEY uk_exam_progress_order (order_id), KEY idx_exam_progress_tenant (tenant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='考试进度表';

CREATE TABLE IF NOT EXISTS ea_course_progress_item (
  item_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '课程进度明细ID',
  order_id BIGINT UNSIGNED NOT NULL COMMENT '订单ID',
  tenant_id VARCHAR(20) NOT NULL COMMENT '租户编号',
  course_name VARCHAR(128) NOT NULL COMMENT '课程名称',
  course_type VARCHAR(32) DEFAULT NULL COMMENT '课程类型',
  required_flag TINYINT DEFAULT 0 COMMENT '是否必修课：1是 0否',
  term VARCHAR(64) DEFAULT NULL COMMENT '课程所属学期',
  learning_status TINYINT DEFAULT 0 COMMENT '学习状态：0未开始 1完成 2失败 3处理中',
  learning_percent DECIMAL(5,2) DEFAULT NULL COMMENT '学习进度百分比',
  learning_text VARCHAR(64) DEFAULT NULL COMMENT '学习进度原始文本',
  work_status TINYINT DEFAULT 0 COMMENT '作业状态：0未开始 1完成 2失败 3处理中',
  latest_time DATETIME DEFAULT NULL COMMENT '明细最新更新时间',
  create_time DATETIME DEFAULT NULL COMMENT '创建时间',
  update_time DATETIME DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (item_id), KEY idx_course_item_order (tenant_id, order_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='课程进度明细表';

CREATE TABLE IF NOT EXISTS ea_exam_progress_item (
  item_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '考试进度明细ID',
  order_id BIGINT UNSIGNED NOT NULL COMMENT '订单ID',
  tenant_id VARCHAR(20) NOT NULL COMMENT '租户编号',
  exam_name VARCHAR(128) NOT NULL COMMENT '考试名称',
  exam_status TINYINT DEFAULT 0 COMMENT '考试状态：0未开始 1完成 2失败 3处理中',
  score DECIMAL(8,2) DEFAULT NULL COMMENT '考试成绩',
  exam_time DATETIME DEFAULT NULL COMMENT '考试完成时间',
  latest_time DATETIME DEFAULT NULL COMMENT '明细最新更新时间',
  remark VARCHAR(255) DEFAULT NULL COMMENT '考试备注',
  frozen_flag TINYINT DEFAULT 0 COMMENT '是否冻结：0否 1是',
  frozen_reason VARCHAR(255) DEFAULT NULL COMMENT '冻结原因',
  frozen_time DATETIME DEFAULT NULL COMMENT '冻结时间',
  create_time DATETIME DEFAULT NULL COMMENT '创建时间',
  update_time DATETIME DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (item_id), KEY idx_exam_item_order (tenant_id, order_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='考试进度明细表';

CREATE TABLE IF NOT EXISTS ea_task_log (
  log_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '日志ID',
  task_id BIGINT UNSIGNED NOT NULL COMMENT '任务ID',
  order_id BIGINT UNSIGNED DEFAULT NULL COMMENT '订单ID',
  tenant_id VARCHAR(20) DEFAULT NULL COMMENT '租户编号',
  worker_code VARCHAR(64) DEFAULT NULL COMMENT '执行节点编码',
  seq_no BIGINT NOT NULL DEFAULT 0 COMMENT '日志序号',
  level VARCHAR(16) NOT NULL DEFAULT 'INFO' COMMENT '日志级别',
  message VARCHAR(4000) NOT NULL COMMENT '日志内容（不得包含凭证）',
  created_at DATETIME DEFAULT NULL COMMENT '日志产生时间',
  create_time DATETIME DEFAULT NULL COMMENT '创建时间',
  update_time DATETIME DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (log_id), KEY idx_task_log_task (task_id, seq_no), KEY idx_task_log_tenant (tenant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='任务执行日志表';

CREATE TABLE IF NOT EXISTS ea_tiku_failure (
  failure_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '题库失败记录ID',
  task_id BIGINT UNSIGNED DEFAULT NULL COMMENT '任务ID',
  order_id BIGINT UNSIGNED DEFAULT NULL COMMENT '订单ID',
  tenant_id VARCHAR(20) DEFAULT NULL COMMENT '租户编号',
  provider VARCHAR(64) DEFAULT NULL COMMENT '题库服务商',
  question VARCHAR(1000) DEFAULT NULL COMMENT '题目内容',
  options_json VARCHAR(2000) DEFAULT NULL COMMENT '题目选项JSON',
  reason VARCHAR(255) DEFAULT NULL COMMENT '失败原因',
  raw_response VARCHAR(4000) DEFAULT NULL COMMENT '原始响应（不得包含凭证）',
  create_time DATETIME DEFAULT NULL COMMENT '创建时间',
  update_time DATETIME DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (failure_id), KEY idx_tiku_failure_task (task_id), KEY idx_tiku_failure_order (order_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='题库失败记录表';
