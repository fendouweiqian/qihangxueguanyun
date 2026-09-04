# 教育业务系统

这是一个可脱离源工程运行的 Python + Vue/TypeScript 教育业务系统。当前覆盖配置、认证、教育业务管理台、学生/学校/平台/订单管理、任务生命周期、进度与日志、积分与充值、执行节点、超星课程和考试任务、成考云考试协议。

## 版本与目录

- Python 3.11+
- FastAPI 0.115.12、Uvicorn 0.34.3、PyMySQL 1.1.1、Redis 客户端 5.0.4、Requests 2.32.3
- Node.js 20+、Vue 3、TypeScript、Vite
- MySQL 8+、Redis 7+

`backend/` 是分层 Python 后端；`frontend/` 是 Vue 前端；`database/` 保存迁移；`docs/` 保存只读审计、依赖映射和迁移记录；`scripts/` 保存启动与检查脚本。

数据库迁移按顺序执行 `database/migrations/0001_core_schema.sql` 和 `0002_operational_domain.sql`。完整迁移创建 19 张教育领域表，字段统一使用 `utf8mb4_unicode_ci` 并带有业务注释。

## 本地安装与启动

```powershell
cd F:\project\earn\education\backend
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8281
```

也可以从目标项目根目录启动：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_backend.ps1
```

### edctl 本地控制命令

`scripts\edctl.cmd` 是参考 `momctl` 生成的本地统一入口，只管理目标项目自身的 Python 后端和 Vue 前端。命令直接使用本机 MySQL/Redis，不启动 Docker，不包含 SSH、生产部署或远程 SQL 操作。

```powershell
.\scripts\edctl.cmd help
.\scripts\edctl.cmd doctor
.\scripts\edctl.cmd install
.\scripts\edctl.cmd service all start
.\scripts\edctl.cmd service backend restart
.\scripts\edctl.cmd service all status
.\scripts\edctl.cmd logs backend -f
.\scripts\edctl.cmd browser
.\scripts\edctl.cmd test all
.\scripts\edctl.cmd worker --limit 1 --runner-id local
```

服务端口固定为后端 `8281`、前端 `5180`。`edctl` 启动时会读取 `backend\.env`（如存在）并传给子进程；运行时日志和 PID 文件写入目标项目下的 `.edctl\`，该目录已加入 `.gitignore`。

### 注册全局命令

在 Windows 上执行一次：

```powershell
.\scripts\install_edctl.ps1
```

安装脚本会在 `F:\environment` 注册 `edctl.ps1` 和 `edctl.cmd`，并把该目录加入当前用户 PATH（已存在时不会重复添加）。重新打开 PowerShell 后即可在任意目录运行 `edctl help`、`edctl doctor` 等命令；当前项目目录变化时，全局入口仍指向本项目脚本，不会复制运行代码。

前端：

```powershell
cd F:\project\earn\education\frontend
npm install
npm run dev
```

本地运行和验收不使用 Docker，直接启动 Python 后端和 Vue 前端，并连接现有 MySQL/Redis。

配置只从环境变量读取，`.env.example` 不含真实凭证。学生账号密码、Cookie、Token 和个人信息只能用于本地验证，不得写入日志或 Git。

认证接口为 `POST /education/auth/login`、`POST /education/auth/bootstrap`、`GET /education/auth/me`；用户管理接口为 `GET /education/user/list`、`POST /education/user`、`PATCH /education/user/{user_id}` 和 `DELETE /education/user/{user_id}`。认证使用 `EDUCATION_AUTH_SECRET` 签发短期 HMAC Bearer Token，用户密码使用 PBKDF2-SHA256 哈希；未配置签名密钥时登录返回 503。首次初始化仅在 `ea_user` 为空时允许调用 `/education/auth/bootstrap`，并要求独立的 `X-Bootstrap-Token` 与 `EDUCATION_BOOTSTRAP_TOKEN` 匹配。用户状态 `0` 表示启用，角色大于等于 `1` 才能管理用户，角色大于等于 `9` 可跨租户管理。

成考云适配器默认不访问任何外部地址；仅在本地联调时通过 `EDUCATION_CHENGKAOYUN_BASE_URL` 或学校记录中的 `school_url` 显式配置地址，并使用测试账号和隔离服务。

超星适配器登录后支持 `list_courses`、`list_chapters`、`list_jobs`、`study` 和考试任务。默认任务会读取订单配置中的 `includeCourses`、`excludeCourses`、`cxWorkSw`、`videoModel` 等字段，自动发现课程和章节，执行视频、文档、阅读、作业/考试并写回汇总与明细。验证码标识会从登录页或 `loadSlide.js` 自动解析；识别服务地址和令牌仍必须通过环境变量或任务配置提供。作业和考试必须配置题库，平台未确认时不会伪造完成。

成考云考试任务需要在任务配置中提供 `semesterId`、可选的 `examId`/`crsId`、`stuId`、一次性 `signCode` 或显式验证码识别服务 `captchaApiUrl`/`captchaApiToken`、题库配置 `tiku`，并可用 `submitExam` 显式开启最终提交；缺少任一必要条件时只返回失败状态。

`GET /healthz` 只检查进程；`GET /readyz` 会真实探测 MySQL 和 Redis，任一依赖不可用时返回 HTTP 503。

执行节点使用 `python -m app.workers.run_once --limit 1 --runner-id <node>` 执行一轮任务。适配器必须来自任务元数据或显式 `--adapter` 参数；未配置适配器会失败回写，默认不会使用模拟适配器。内部登录检测接口为 `POST /internal/runner/login-check` 和 `POST /internal/runner/fetch-name`；配置 `EDUCATION_INTERNAL_TOKEN` 后必须携带 `X-Runner-Token`。

## 验证

```powershell
cd F:\project\earn\education\backend
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall app tests
```

学生查询兼容接口为 `GET /education/student/list` 和 `GET /education/student/{student_id}`，响应保留原系统的 `code/msg/data` 或 `code/msg/rows/total` 包络，并使用 Java 管理端的 camelCase 字段（如 `studentId`、`schoolId`）；大整数 ID 在 JSON 中按字符串返回，时间按 `yyyy-MM-dd HH:mm:ss` 返回。分页同时接受 `pageNum/pageSize` 和内部 snake_case 参数。

任务执行基础接口为 `POST /education/runner/tasks/claim`、`/{task_id}/heartbeat`、`/{task_id}/result`、`/{task_id}/cancel` 和 `/recycle-timeout`；领取接口兼容历史 JSON 请求体，支持任务类型过滤，领取、心跳、回写和超时回收使用事务及状态幂等保护。进度汇总、明细、快照和学生档案写回接口分别为 `/education/runner/course-progress/upsert`、`/exam-progress/upsert`、`/course-progress/items`、`/exam-progress/items`、`/progress/snapshot`、`/students/profile`。成考云登录及考试接口协议、超星 SM4/enToken 登录、验证码、课程/章节/任务发现、视频/文档/阅读/作业协议、字体解码、题库答案归一化和快照解析层均由目标 Python 后端独立实现。外部地址和令牌默认不配置，真实执行时通过运行环境注入。

管理接口与源管理端路径兼容，覆盖 `/education/student`、`/school`、`/platform`、`/order`、`/task`、`/course-progress`、`/exam-progress`、`/runner-node`、`/runner-setting`、`/school-cache`、`/face-media`、`/tenant`、`/recharge`、`/ledger` 和 `/tiku-failure`。

迁移验收时先在 `8280` 启动原 Java 管理端、在 `8281` 启动目标 Python 后端，并通过 `EDUCATION_SOURCE_TENANT_ID`、`EDUCATION_SOURCE_USERNAME`、`EDUCATION_SOURCE_PASSWORD`、`EDUCATION_SOURCE_CLIENT_ID` 环境变量提供本地测试账号，然后执行 `F:\project\earn\education\backend\.venv\Scripts\python.exe F:\project\earn\education\scripts\compare_student_contract.py`。该一次性审计工具会通过两套真实 HTTP 接口对最多 3 条记录的列表和详情执行 17 字段、类型及值比较；原 Java 返回为数字的 `schoolId` 会按十进制字符串归一化后比较，目标端仍强制使用字符串以避免大整数精度丢失。脚本不属于目标运行时依赖，也不会保存或输出账号字段值。

数据库结构检查使用 `F:\project\earn\education\backend\.venv\Scripts\python.exe F:\project\earn\education\scripts\check_database.py`，只读验证 `ea_student`、`ea_order`、`ea_task` 的必需字段和学生记录数。

依赖许可证检查使用 `F:\project\earn\education\backend\.venv\Scripts\python.exe F:\project\earn\education\scripts\license_scan.py`，应在安装 `backend/requirements.lock` 后执行。

## 当前限制与发布风险

依赖包实际来源、许可证和资源审计见 `docs/source-audit.md`。本地已完成 3 条学生账号字段等价性、管理端与 Python API 浏览器闭环、适配器无网络协议测试。2026-09-01 真实平台登录检测在两所学校的登录页请求阶段均收到 HTTP 403，账号尚未提交，因此真实学习/考试仍不能作为本次已通过项；恢复访问或提供学校允许的测试出口后，应重新执行平台登录、课程发现和一条隔离测试任务。公开发布前还需由项目方复核自定义非商业许可证与所有上游依赖许可证的兼容性。

QQ群：1107350553

请勿在群内发送密码、Token、Cookie、学生信息、考试数据、生产日志或数据库备份。

本项目仅限非商业学习和研究用途；第三方组件继续遵守其各自许可证，不能据此替换为标准开源许可证。
