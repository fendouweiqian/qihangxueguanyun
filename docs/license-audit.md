# 依赖许可证审计

以下是基于目标项目 `backend/.venv` 和本机 Python 3.11 环境的核对。版本锁定以 `backend/requirements.lock` 为准；发布前仍需保存每个发行包的官方 SPDX 证据。

| 包 | 目标锁定版本 | 实际本机版本 | 来源 | 许可证（元数据） | 处理 |
| --- | --- | --- | --- | --- | --- |
| FastAPI | 0.115.12 | 0.115.12 | PyPI/site-packages | MIT（官方 License 分类器） | 仅声明依赖，不复制源码 |
| Uvicorn | 0.34.3 | 0.34.3 | PyPI/site-packages | BSD-3-Clause（官方 License 分类器） | 仅声明依赖，不复制源码 |
| Pydantic | 2.11.5 | 2.11.5 | PyPI/site-packages | MIT（官方 License 分类器） | 仅声明依赖，不复制源码 |
| PyMySQL | 1.1.1 | 1.1.1 | PyPI/site-packages | MIT | 仅声明依赖，不复制源码 |
| redis-py | 5.0.4 | 5.0.4 | PyPI/site-packages | MIT | 目标虚拟环境已安装并完成 PING 验证 |
| requests | 2.32.3 | 2.32.3 | PyPI/site-packages | Apache-2.0 | 成考云 HTTP 客户端依赖，仅声明依赖，不复制源码 |
| beautifulsoup4 | 4.12.3 | 4.12.3 | PyPI/site-packages | MIT | 超星 HTML/字体样式解析依赖，仅声明依赖 |
| fonttools | 4.60.1 | 4.60.1 | PyPI/site-packages | MIT | 超星字体轮廓解析依赖，仅声明依赖 |
| requests | 2.28.1（历史声明） | 2.31.0 | PyPI/site-packages | Apache-2.0 | 目标适配器锁定 2.32.3；不复制历史 site-packages |
| beautifulsoup4 | 4.12.3 | 4.12.3 | PyPI/site-packages | MIT | 目标适配器锁定同版本；不复制历史 site-packages |
| fonttools | 4.60.1（历史声明） | 4.61.1 | PyPI/site-packages | MIT | 目标适配器锁定 4.60.1；字体映射资源仍缺失 |

历史平台代码还可能调用浏览器驱动、验证码服务和系统字体；这些不是当前目标后端的隐式依赖，必须完成调用点到资源的逐项审计后才能公开发布。当前环境没有 `pipdeptree`，已通过 `importlib.metadata` 读取每个锁定包的安装位置和 `Requires-Dist` 元数据作为等效依赖树核查；该核查只能证明可安装 Python 包，不能替代外部资源和上游代码许可证确认。

## 关键资源审计结果

- 超星登录模块直接发起验证码配置、图片和校验请求，并把 Cookie 写入 Redis 或本地 JSON；验证码服务地址和令牌来自配置，不能写入目标仓库。
- 超星字体解码通过 `fontTools.ttLib.TTFont` 解析页面内嵌字体，并期待 `resource/font_map_table.json`；当前源目录未发现该资源文件，迁移前必须确认其来源和许可证。
- 课程学习模块依赖 HTML 页面、内嵌 JavaScript、Cookie、平台固定接口和本地快照文件；未发现项目自带浏览器脚本或动态库，但运行环境可能需要浏览器/系统字体。
- 成考云模块使用 HTTP 登录、授权 Token、验证码识别服务和课程/考试接口；当前只保留适配器边界，未复制实现。
- 本机额外安装了 Playwright、Selenium、DecryptLogin 等包，但历史 `school/source` 代码未直接 import 它们；不能将它们默认为目标项目依赖，仍需用干净环境复核。

结论：当前目标项目没有 vendor 第三方源码，也没有复制 Cookie、字体、HTML、JavaScript 或动态库；平台执行器公开发布仍被外部服务凭证、缺失字体映射资源和许可证核验阻塞。

目标环境执行 `scripts/license_scan.py` 的结果为 `license_scan=passed`；许可证结论来自安装发行包的官方元数据分类器，公开发布前仍应保留对应 PyPI 发行页和上游 LICENSE 链接作为审计证据。
