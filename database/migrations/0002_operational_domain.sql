-- 运行域补全迁移。与 0001_core_schema.sql 配套执行，不连接源项目数据库。
-- 所有新增字段保留历史业务含义；标识字段在 API 层仍按字符串序列化。

CREATE TABLE IF NOT EXISTS ea_school_cache (
  cache_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '学校缓存ID',
  tenant_id VARCHAR(20) DEFAULT NULL COMMENT '租户编号；为空表示公共缓存',
  source_school_id BIGINT UNSIGNED NOT NULL COMMENT '源学校ID',
  platform_id BIGINT UNSIGNED NOT NULL COMMENT '平台ID',
  platform_name VARCHAR(64) NOT NULL COMMENT '平台名称快照',
  school_name VARCHAR(128) NOT NULL COMMENT '学校名称快照',
  access_type TINYINT NOT NULL DEFAULT 1 COMMENT '访问类型：1网页 2小程序',
  access_address VARCHAR(255) DEFAULT NULL COMMENT '访问地址或入口说明',
  school_url VARCHAR(255) DEFAULT NULL COMMENT '学校网址',
  school_fid VARCHAR(128) DEFAULT NULL COMMENT '学校平台 FID',
  school_code VARCHAR(255) DEFAULT NULL COMMENT '学校平台编码',
  school_remark VARCHAR(255) DEFAULT NULL COMMENT '学校备注',
  enabled TINYINT NOT NULL DEFAULT 1 COMMENT '启用状态：1启用 0停用',
  video_supported TINYINT NOT NULL DEFAULT 0 COMMENT '是否支持视频',
  work_supported TINYINT NOT NULL DEFAULT 0 COMMENT '是否支持作业',
  exam_supported TINYINT NOT NULL DEFAULT 0 COMMENT '是否支持考试',
  exam_special_order_required TINYINT NOT NULL DEFAULT 0 COMMENT '是否需要独立考试下单',
  face_required TINYINT NOT NULL DEFAULT 0 COMMENT '是否需要人脸核验',
  exam_type TINYINT NOT NULL DEFAULT 0 COMMENT '考试类型',
  answer_ok TINYINT NOT NULL DEFAULT 0 COMMENT '答案可用状态',
  exam_state TINYINT NOT NULL DEFAULT 0 COMMENT '考试状态',
  submit_time INT NOT NULL DEFAULT 0 COMMENT '提交时间限制',
  ip_number INT NOT NULL DEFAULT 0 COMMENT 'IP 数量限制',
  create_time DATETIME DEFAULT NULL COMMENT '创建时间',
  update_time DATETIME DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (cache_id),
  UNIQUE KEY uk_school_cache_source (source_school_id),
  KEY idx_school_cache_tenant_enabled (tenant_id, enabled),
  KEY idx_school_cache_platform (platform_id),
  KEY idx_school_cache_name (school_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='学校配置缓存表';

CREATE TABLE IF NOT EXISTS ea_runner_node (
  node_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '执行节点ID',
  worker_code VARCHAR(64) NOT NULL COMMENT '执行节点编码',
  version VARCHAR(64) DEFAULT NULL COMMENT '节点版本',
  host_name VARCHAR(128) DEFAULT NULL COMMENT '主机名称',
  status TINYINT NOT NULL DEFAULT 0 COMMENT '节点状态：0离线 1在线 2异常',
  current_task_id BIGINT UNSIGNED DEFAULT NULL COMMENT '当前任务ID',
  current_order_id BIGINT UNSIGNED DEFAULT NULL COMMENT '当前订单ID',
  last_error VARCHAR(1000) DEFAULT NULL COMMENT '最后错误信息（已脱敏）',
  heartbeat_at DATETIME DEFAULT NULL COMMENT '最后心跳时间',
  started_at DATETIME DEFAULT NULL COMMENT '启动时间',
  create_time DATETIME DEFAULT NULL COMMENT '创建时间',
  update_time DATETIME DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (node_id),
  UNIQUE KEY uk_runner_node_worker (worker_code),
  KEY idx_runner_node_status (status),
  KEY idx_runner_node_heartbeat (heartbeat_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='任务执行节点表';

CREATE TABLE IF NOT EXISTS ea_runner_setting (
  setting_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '执行配置ID',
  tenant_id VARCHAR(20) NOT NULL COMMENT '租户编号',
  ai_type VARCHAR(32) DEFAULT NULL COMMENT 'AI 服务类型',
  ai_url VARCHAR(255) DEFAULT NULL COMMENT 'AI 服务地址',
  ai_model VARCHAR(128) DEFAULT NULL COMMENT 'AI 模型名称',
  ai_api_key VARCHAR(255) DEFAULT NULL COMMENT 'AI 接口密钥（仅服务端读取）',
  external_question_url VARCHAR(255) DEFAULT NULL COMMENT '外部题库地址',
  completion_tone TINYINT NOT NULL DEFAULT 0 COMMENT '完成提示语气',
  color_log TINYINT NOT NULL DEFAULT 0 COMMENT '彩色日志开关',
  log_level VARCHAR(16) NOT NULL DEFAULT 'INFO' COMMENT '日志级别',
  log_model TINYINT NOT NULL DEFAULT 0 COMMENT '日志模式',
  poll_interval_seconds INT NOT NULL DEFAULT 10 COMMENT '轮询间隔秒数',
  max_parallel_tasks INT NOT NULL DEFAULT 1 COMMENT '最大并行任务数',
  task_timeout_seconds INT NOT NULL DEFAULT 1800 COMMENT '任务超时秒数',
  log_retention_days INT NOT NULL DEFAULT 7 COMMENT '日志保留天数',
  remark VARCHAR(255) DEFAULT NULL COMMENT '配置备注',
  create_time DATETIME DEFAULT NULL COMMENT '创建时间',
  update_time DATETIME DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (setting_id),
  UNIQUE KEY uk_runner_setting_tenant (tenant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='任务执行配置表';

CREATE TABLE IF NOT EXISTS ea_face_media (
  face_media_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '人脸媒体ID',
  tenant_id VARCHAR(20) NOT NULL COMMENT '租户编号',
  student_id BIGINT UNSIGNED NOT NULL COMMENT '学生ID',
  file_url VARCHAR(500) NOT NULL COMMENT '媒体文件地址',
  file_type VARCHAR(32) NOT NULL DEFAULT 'mp4' COMMENT '媒体文件类型',
  status TINYINT NOT NULL DEFAULT 0 COMMENT '媒体状态：0待处理 1可用 2失效',
  uploaded_by BIGINT UNSIGNED DEFAULT NULL COMMENT '上传用户ID',
  create_time DATETIME DEFAULT NULL COMMENT '创建时间',
  update_time DATETIME DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (face_media_id),
  KEY idx_face_media_student (student_id),
  KEY idx_face_media_tenant (tenant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='人脸核验媒体表';

CREATE TABLE IF NOT EXISTS ea_ledger (
  ledger_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '积分流水ID',
  tenant_id VARCHAR(20) NOT NULL COMMENT '租户编号',
  order_id BIGINT UNSIGNED DEFAULT NULL COMMENT '关联订单ID',
  change_points BIGINT NOT NULL COMMENT '变动积分，扣减为负数',
  gift_points BIGINT NOT NULL DEFAULT 0 COMMENT '赠送积分',
  type TINYINT NOT NULL COMMENT '流水类型',
  operator_user_id BIGINT UNSIGNED DEFAULT NULL COMMENT '操作用户ID',
  remark VARCHAR(255) DEFAULT NULL COMMENT '流水备注',
  create_dept BIGINT DEFAULT NULL COMMENT '创建部门',
  create_by BIGINT DEFAULT NULL COMMENT '创建者',
  create_time DATETIME DEFAULT NULL COMMENT '创建时间',
  update_by BIGINT DEFAULT NULL COMMENT '更新者',
  update_time DATETIME DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (ledger_id),
  KEY idx_ledger_tenant (tenant_id),
  KEY idx_ledger_order (order_id),
  KEY idx_ledger_type (type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='租户积分流水表';

CREATE TABLE IF NOT EXISTS ea_recharge (
  recharge_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '充值记录ID',
  tenant_id VARCHAR(20) NOT NULL COMMENT '租户编号',
  operator_user_id BIGINT UNSIGNED NOT NULL COMMENT '操作用户ID',
  recharge_points BIGINT NOT NULL COMMENT '充值积分',
  gift_points BIGINT NOT NULL DEFAULT 0 COMMENT '赠送积分',
  remark VARCHAR(255) DEFAULT NULL COMMENT '充值备注',
  create_time DATETIME DEFAULT NULL COMMENT '创建时间',
  update_time DATETIME DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (recharge_id),
  KEY idx_recharge_tenant (tenant_id),
  KEY idx_recharge_operator (operator_user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='租户充值记录表';
