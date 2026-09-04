# 源项目只读审计（第一阶段）

审计对象：`F:\project\earn\educationAssistant`。本文件只记录已观察到的事实，不复制源项目 Git 历史或运行代码。

## 调用链

管理端 `EaStudentController` 的 `/education/student/list`、`/{studentId}` 委托 `EaStudentServiceImpl`；分页查询按租户、学校、账号、姓名过滤并按 `student_id` 升序。任务执行链为 `school/source/jobs/dispatcher.py -> core/admin_client.py -> /education/runner/tasks/claim`，数据库回退读取 `ea_task -> ea_order -> ea_student`，执行结果写回 `ea_task`、`ea_course_progress`、`ea_exam_progress` 和 `ea_tiku_failure`。登录检测链为 Java 学生服务调用历史执行器 HTTP 接口，平台选择在 `school/source/tools/fetch_student_name.py` 和 dispatcher 中完成。

Java/Go 边界：Java `EaRunnerInternalController` 暴露任务领取、结果、课程/考试进度和题库失败接口；Go 执行器的 `runner/db.go` 直接读写任务数据库，`runner/http.go` 暴露登录检测接口，`runner/progress_items.go` 将课程/考试明细和学生档案快照回 POST 到 Java 管理接口。两条链路都依赖同一数据库状态字段（0待执行、1执行中、2成功、3失败），目标 Python worker 已采用相同常量，但尚未替代 Go 的平台执行实现。

## Python 依赖与来源

`school/source/adapters/chaoxing/requirements.txt` 声明 `requests==2.28.1`、`redis==5.0.4`、`beautifulsoup4==4.12.3`、`fonttools==4.60.1`、`pymysql==1.1.1`。当前本机 Python 3.11.5 实际安装目录为 `F:\environment\python\python311\Lib\site-packages`；实际版本为 requests 2.31.0、beautifulsoup4 4.12.3、fonttools 4.61.1、PyMySQL 1.1.0，`redis` 未安装。目标虚拟环境已按锁定版本完成依赖导入、许可证元数据和 `Requires-Dist` 核查；FastAPI/Uvicorn 是本次目标项目新增运行时，源码不复制 site-packages。

关键历史模块：超星 `login.py`、`study_tasks.py`、`task_runner.py`、`course_list.py`、`font_decoder.py`、`tiku_client.py`、`db_access.py`；成考云 `client.py`、`run_chengkaoyun.py`；公共调度 `dispatcher.py`、`admin_client.py`。这些模块可能依赖浏览器、验证码服务、字体文件、网络平台和数据库，许可证和可再分发性尚未完成逐包确认，因此是公开发布阻塞项。

## 数据库与学生账号

本地只读核查连接 `127.0.0.1:3307/education_assistant` 成功，发现 `ea_student` 现有 3 条记录，字段包括 `student_id` BIGINT、`tenant_id`、`school_id` BIGINT、`account`、`password`、`open_id`、`name`、`study_grade`、`major`、`phone`、`id_card`、`status`、登录状态和时间字段。租户和学生标识未写入目标项目；账号、姓名等敏感值仅在终端掩码显示。

业务表清单及关键字段：`ea_platform(platform_id, platform_name)`、`ea_school(school_id, platform_id, school_name, access_type, school_url)`、`ea_school_cache(cache_id, source_school_id, platform_id, enabled)`、`ea_tenant(tenant_id, tenant_name, status, balance_points)`、`ea_user(user_id, tenant_id, username, role, status)`、`ea_student(见上)`、`ea_order(order_id, tenant_id, student_id, school_id, platform_id, order_type, course_name, course_code, term, status)`、`ea_task(task_id, order_id, tenant_id, task_type, status, worker_code, retry_count, last_error, task_config_json)`、`ea_task_log(log_id, task_id, order_id, tenant_id, level, biz_type, biz_status, message)`、`ea_runner_node(node_id, worker_code, status, current_task_id, heartbeat_at)`、`ea_runner_setting(setting_id, tenant_id, ai_type, external_question_url, task_timeout_seconds)`、`ea_course_progress(progress_id, order_id, tenant_id, video_status, work_status, exam_status)`、`ea_exam_progress(exam_progress_id, order_id, tenant_id, status, score)`、`ea_face_media(face_media_id, tenant_id, student_id, file_url, status)`、`ea_ledger(ledger_id, tenant_id, order_id, change_points, type)`、`ea_recharge(recharge_id, tenant_id, recharge_points, gift_points)`、`ea_tiku_failure(failure_id, task_id, order_id, tenant_id, provider, question, reason)`。目标 `database/migrations/0001_core_schema.sql` 与 `0002_operational_domain.sql` 已覆盖上述 19 张领域表；迁移脚本只面向目标数据库，不会自动修改源项目数据库。

目标接口的本地基线（直接复用本地数据库）为 HTTP 200、业务码 200、返回 3 条记录；字段集合与 `ea_student` 查询列一致，BIGINT 标识以字符串序列化。审计脚本已调用源项目历史 `fetch_student` 查询函数，并与目标 HTTP 接口自动对比 3 条记录的 7 个公共字段，结果 `comparison=passed`；这不是完整 Java 管理接口等价性证明。

## 迁移表

| 旧模块 | 目标模块 | 状态 |
| --- | --- | --- |
| `school/source/core/config_loader.py` | `backend/app/config.py` | 基础配置已迁移 |
| `school/source/core/admin_client.py` | `backend/app/infrastructure/db.py`、`backend/app/api/internal_runner.py`、`application/workers` | 学生查询、内部登录检测、任务领取和回写边界已迁移 |
| `EaStudentServiceImpl` | `backend/app/api/students.py`、`backend/app/api/internal_runner.py` | 查询兼容接口和登录检测接口已实现 |
| `school/source/adapters/*` | `backend/app/adapters` | 成考云登录/考试接口协议、超星 SM4/enToken 登录、课程/章节/任务发现及视频/文档/阅读协议已迁移；验证码、字体映射资源和真实页面联调仍需资源与许可证闭环 |
| Java/Go 执行链 | `backend/app/workers`、`backend/app/api/tasks.py`、`backend/app/api/internal_runner.py`、`backend/app/application/progress_parser.py` | 任务领取/心跳/回写/取消/超时回收、登录检测、进度明细/快照和学生档案写回边界已迁移；目标 Python worker 已通过 mock 适配器验证，真实平台执行仍待隔离环境验收 |

## 已知阻塞

1. 原项目完整启动基线尚未执行，不能伪造等价性结果；当前仅完成历史学生查询函数与目标 HTTP 接口的 3 条记录自动对比。
2. 关键平台依赖的源码、资源、许可证和外部服务契约仍需逐包审计。
3. 目标项目已覆盖健康检查、学生账号读取、任务领取/心跳/回写/取消/超时回收、适配器推断、内部登录检测、进度汇总写回、成考云登录/验证码/考试接口协议、超星课程/章节/任务发现、视频/文档/阅读/作业协议、滑块验证码协议、字体解码边界和题库答案归一化；真实识别服务、字体映射资源和真实页面闭环仍未完成。

当前状态更新：目标项目已增加任务幂等回写、任务取消/心跳和超时回收、适配器推断、内部登录检测、课程/考试汇总 upsert、模拟适配器和一次性 worker，补齐租户/用户/平台/学校/订单只读目录接口；`/readyz` 会检查 MySQL/Redis。平台登录、题库查询和明细快照的协议边界已实现并有 mock 覆盖，但真实服务、验证码、字体资源和页面联调仍未验收。

认证补充：目标项目新增 PBKDF2-SHA256 密码哈希、HMAC Bearer Token、租户范围用户列表和用户 CRUD；源 Java 使用 Sa-Token、客户端标识和图形/短信验证码，无法在未运行源服务的情况下证明令牌字节级兼容，因此目标认证属于独立实现，不声称与源登录协议等价。

基线补充：源项目 `school/source/tests/run_mock_chain.py` 在显式设置 `PYTHONPATH=school/source` 后通过，结果为 `claim -> execute(mock) -> progress -> result`；直接从脚本目录启动会因模块路径缺失失败。目标项目没有复制源项目 Python、Go 或 Java 运行产物，源目录未发现 `font_map_table.json`。Docker Compose 配置已静态校验，但当前机器 Docker daemon 不可用，未完成容器实际启动验收。

跨项目隔离 E2E 补充：在临时数据库 `education_e2e_contract` 和目标后端 8282 上，使用源调度器一次性领取任务并执行 mock 适配器；目标 API 接受历史调度器发送的数值订单 ID（在请求边界归一化为字符串），最终验证 `ea_task.status=2`，课程进度和考试进度均完成写回。临时后端和数据库已在验证后删除，主库未执行写入。

验证补充：目标 DDL 已在本机临时隔离数据库执行，19 张表均为 `utf8mb4_unicode_ci`，新增学校兼容字段和运行域表均通过检查；临时数据库已删除。目标虚拟环境中的 Redis 客户端在本机认证 Redis 上 PING 成功。源数据库仅执行了只读结构和记录数查询。
