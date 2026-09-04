# 依赖调用映射

本文件记录目标项目已迁移边界与源项目审计结果。目标运行时不把源目录加入 `PYTHONPATH`，也不复制第三方 `site-packages`。

| 调用点 | 目标实现 | 包内实现/资源 | 外部资源与状态 |
| --- | --- | --- | --- |
| 学生、订单、任务和进度读取/写回 | `backend/app/infrastructure/db.py` | PyMySQL 1.1.1，参数化 SQL、事务和 BIGINT 字符串化 | 本地 MySQL；已完成结构检查，未连接生产 |
| 健康检查和 API | `backend/app/main.py`、`backend/app/api/*` | FastAPI 0.115.12、Uvicorn 0.34.3、Pydantic 2.11.5 | 仅监听本地/部署地址；已完成启动验证 |
| Redis 连接、key 前缀和可选会话 Cookie | `backend/app/infrastructure/redis_client.py`、`backend/app/adapters/chaoxing.py` | redis-py 5.0.4，JSON/TTL 存储 | 本地 Redis；已完成认证 PING，Cookie 仅在显式 session key 时保存，不写日志 |
| 成考云登录、验证码、考试列表、签到、答题保存和提交 | `backend/app/adapters/chengkaoyun.py` | Requests 2.32.3、Base64 图片协议、BeautifulSoup 题干清理、显式 TikuClient | 学校地址、验证码识别 URL/Token 和题库地址必须显式配置；未连接真实平台 |
| 超星登录表单 | `backend/app/adapters/chaoxing.py` | Requests、BeautifulSoup、`chaoxing_crypto.py` 的 SM4-CBC | `enToken` 来自登录页；验证码必须由受控流程提供，未自动调用识别服务 |
| 超星滑块验证码 | `backend/app/adapters/chaoxing.py` | JSONP 参数生成、图片下载、显式识别服务和坐标校验 | `captchaId`、识别服务 URL/Token 必须由请求或环境显式提供；不落盘图片和 Token |
| 超星课程/章节/任务与基础学习 | `backend/app/adapters/chaoxing_learning.py`、`backend/app/adapters/chaoxing.py` | Requests、HTML/JSON 解析、视频进度摘要 | 学习地址必须由任务或环境显式提供；视频、文档和阅读支持平台确认回写，作业/考试仍失败 |
| 超星密码字段加密 | `backend/app/adapters/chaoxing_crypto.py` | 项目内 SM4 S 盒、轮密钥和 CBC/PKCS7 | 无外部资源；两个源固定向量已通过 |
| 页面档案/课程/考试解析 | `backend/app/application/progress_parser.py` | BeautifulSoup 4.12.3、正则和状态归一化 | 输入为执行器内存快照；不保存原始 HTML |
| 超星字体解码 | `backend/app/adapters/font_decoder.py` | fontTools 4.60.1、glyf 轮廓 MD5 | `font_map_table.json` 在源目录未发现，目标仅接受显式路径，缺失时安全降级 |
| 题库答案归一化 | `backend/app/adapters/tiku.py` | Requests、结构化 JSON 解析 | URL 必须显式配置；不保留历史默认服务地址，未连接真实题库 |

## 未闭环资源

- 源项目超星验证码图片、滑块识别服务和令牌属于外部服务配置，目标没有硬编码或默认调用。
- 字体映射表缺失，无法证明其来源和再分发许可；因此超星字体相关真实页面仍不能验收。
- 课程视频、文档和阅读任务以及成考云考试提交协议已迁移平台确认回写；验证码、平台 Cookie、JavaScript 页面和第三方题库仍需隔离服务验证。
- 当前没有发现目标必须依赖 Chrome/Chromium、Selenium、Playwright 或动态库的已验证调用点；若后续平台流程需要，应单独增加锁定依赖和许可证审计。

在上述外部资源、许可证和隔离测试服务确认前，项目不满足公开发布或“完整重构”验收条件。
