"""超星登录协议适配器；验证码必须由受控外部流程显式提供。"""

from __future__ import annotations

import os
import re
import time
import base64
import hashlib
import json
import uuid
import logging
from typing import Any, Protocol
from urllib.parse import urlencode, urljoin

import requests
from bs4 import BeautifulSoup

from app.adapters.base import AdapterContext, AdapterResult, AdapterTask, TaskKind
from app.adapters.chaoxing_crypto import encrypt_login
from app.adapters.chaoxing_learning import ChaoxingLearningClient
from app.adapters.tiku import TikuClient


logger = logging.getLogger(__name__)


class _Response(Protocol):
    status_code: int
    headers: Any
    text: str

    def raise_for_status(self) -> None: ...


class ChaoxingClient:
    """封装超星登录页、enToken 和登录表单提交。"""

    def __init__(
        self,
        base_url: str,
        session: requests.Session | None = None,
        timeout: int = 15,
        cookie_store: Any | None = None,
        session_key: str | None = None,
        cookie_ttl_seconds: int = 43200,
    ):
        if not base_url.startswith(("http://", "https://")):
            raise ValueError("chaoxing base_url must be an explicit http(s) URL")
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()
        if hasattr(self.session, "headers"):
            self.session.headers.setdefault(
                "User-Agent",
                "Mozilla/5.0",
            )
        self.timeout = max(1, timeout)
        self.cookie_store = cookie_store
        self.session_key = session_key
        self.cookie_ttl_seconds = max(1, cookie_ttl_seconds)

    def login(self, username: str, password: str, verify_code: str, role_status: str = "0") -> _Response:
        """获取登录令牌并提交 SM4 加密后的账号字段。"""
        self._load_cookies()
        logger.info("chaoxing login request: method=GET path=/login host=%s", self.base_url.split("//", 1)[-1].split("/", 1)[0])
        page = self.session.get(
            f"{self.base_url}/login",
            headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Referer": f"{self.base_url}/login",
            },
            timeout=self.timeout,
        )
        logger.info("chaoxing login response: method=GET path=/login status=%s", getattr(page, "status_code", "unknown"))
        page.raise_for_status()
        token = self.extract_en_token(page.text)
        if not token:
            raise ValueError("chaoxing enToken is missing")
        encoded_user = encrypt_login(username)
        encoded_password = encrypt_login(password)
        body = {
            "enToken": token,
            "elserolestustatus": role_status,
            "isphone": "1",
            "userName": encoded_user,
            "passWord": encoded_password,
            "verifyCode": verify_code,
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": self.base_url,
            "Referer": f"{self.base_url}/login",
        }
        response = self.session.post(
            f"{self.base_url}/commonlogin/commonlogin?{urlencode({'tmp': str(int(time.time() * 1000)), **{key: value for key, value in body.items() if key != 'enToken'}})}",
            data=urlencode(body),
            headers=headers,
            allow_redirects=False,
            timeout=self.timeout,
        )
        logger.info(
            "chaoxing login response: method=POST path=/commonlogin/commonlogin status=%s location=%s",
            response.status_code,
            bool(response.headers.get("Location")),
        )
        if 200 <= response.status_code < 400:
            self._save_cookies()
        return response

    def resolve_captcha_id(self) -> str:
        """从登录页或其 loadSlide.js 脚本解析滑块验证码标识。"""
        logger.info("chaoxing login request: method=GET path=/login host=%s", self.base_url.split("//", 1)[-1].split("/", 1)[0])
        page = self.session.get(
            f"{self.base_url}/login",
            headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Referer": f"{self.base_url}/login",
            },
            timeout=self.timeout,
        )
        logger.info("chaoxing login response: method=GET path=/login status=%s", getattr(page, "status_code", "unknown"))
        page.raise_for_status()
        captcha = re.search(r"captchaId\s*:\s*['\"]([^'\"]+)['\"]", page.text or "", re.I)
        if captcha:
            return captcha.group(1).strip()
        script = re.search(r"<script[^>]+src=['\"]([^'\"]*loadSlide\.js[^'\"]*)['\"]", page.text or "", re.I)
        if not script:
            return ""
        response = self.session.get(
            urljoin(f"{self.base_url}/login", script.group(1)),
            headers={"Accept": "*/*", "Referer": f"{self.base_url}/login"},
            timeout=self.timeout,
        )
        logger.info("chaoxing login response: stage=resolve_captcha_script status=%s", getattr(response, "status_code", "unknown"))
        response.raise_for_status()
        captcha = re.search(r"captchaId\s*:\s*['\"]([^'\"]+)['\"]", response.text or "", re.I)
        return captcha.group(1).strip() if captcha else ""

    def fetch_captcha(self, captcha_id: str, captcha_type: str = "slide", version: str = "1.1.20") -> dict[str, str]:
        """获取超星验证码图片地址和校验参数，不保存图片或令牌。"""
        callback = f"jsonp_{int(time.time() * 1000)}"
        conf_response = self.session.get(
            "https://captcha.chaoxing.com/captcha/get/conf",
            params={"callback": callback, "captchaId": captcha_id, "_": str(int(time.time() * 1000))},
            timeout=self.timeout,
        )
        logger.info("chaoxing login response: stage=captcha_config status=%s", getattr(conf_response, "status_code", "unknown"))
        conf_response.raise_for_status()
        conf = self._parse_jsonp(conf_response.text)
        server_time = int(conf.get("t") or 0)
        if server_time <= 0:
            raise ValueError("chaoxing captcha server time is missing")
        nonce = str(uuid.uuid4())
        captcha_key = hashlib.md5(f"{server_time}{nonce}".encode()).hexdigest()
        token = hashlib.md5(f"{server_time}{captcha_id}{captcha_type}{captcha_key}".encode()).hexdigest() + f":{server_time + 300000}"
        iv = hashlib.md5(f"{captcha_id}{captcha_type}{int(time.time() * 1000)}{uuid.uuid4()}".encode()).hexdigest()
        image_response = self.session.get(
            "https://captcha.chaoxing.com/captcha/get/verification/image",
            params={"callback": callback, "captchaId": captcha_id, "type": captcha_type, "version": version,
                    "captchaKey": captcha_key, "token": token, "referer": f"{self.base_url}/login", "iv": iv,
                    "_": str(int(time.time() * 1000))},
            timeout=self.timeout,
        )
        logger.info("chaoxing login response: stage=captcha_image status=%s", getattr(image_response, "status_code", "unknown"))
        image_response.raise_for_status()
        data = self._parse_jsonp(image_response.text)
        image = data.get("imageVerificationVo") if isinstance(data.get("imageVerificationVo"), dict) else {}
        if not data.get("token") or not image.get("shadeImage") or not image.get("cutoutImage"):
            raise ValueError("chaoxing captcha image response is incomplete")
        return {"token": str(data["token"]), "shadeImage": str(image["shadeImage"]), "cutoutImage": str(image["cutoutImage"]), "iv": iv}

    def solve_captcha_x(self, captcha_token: str, shade_url: str, cutout_url: str, api_url: str, api_token: str, api_type: str = "10110") -> int:
        """调用显式配置的验证码识别服务获取滑块横坐标。"""
        if not api_url.startswith(("http://", "https://")) or not api_token:
            raise ValueError("captcha solver URL and token are required")
        headers = {"Referer": f"{self.base_url}/login", "Accept": "*/*"}
        shade = self.session.get(shade_url, headers=headers, timeout=self.timeout)
        shade.raise_for_status()
        cutout = self.session.get(cutout_url, headers=headers, timeout=self.timeout)
        cutout.raise_for_status()
        response = self.session.post(api_url, json={"slide_image": base64.b64encode(cutout.content).decode("ascii"), "background_image": base64.b64encode(shade.content).decode("ascii"), "token": api_token, "type": api_type}, timeout=self.timeout)
        response.raise_for_status()
        payload = response.json()
        result = payload.get("data") if isinstance(payload, dict) else None
        if payload.get("code") != 10000 or not isinstance(result, dict) or result.get("data") is None:
            raise ValueError("captcha solver rejected request")
        return int(float(result["data"]))

    def verify_captcha(self, captcha_id: str, captcha_type: str, version: str, captcha_token: str, x: int, iv: str) -> str:
        """校验滑块坐标并返回登录需要的 validate 字符串。"""
        callback = f"jsonp_{int(time.time() * 1000)}"
        response = self.session.get(
            "https://captcha.chaoxing.com/captcha/check/verification/result",
            params={"callback": callback, "captchaId": captcha_id, "type": captcha_type, "token": captcha_token,
                    "textClickArr": json.dumps([{"x": int(x)}], separators=(",", ":")), "coordinate": "[]", "runEnv": "10", "version": version, "iv": iv},
            timeout=self.timeout,
        )
        logger.info("chaoxing login response: stage=captcha_verify status=%s", getattr(response, "status_code", "unknown"))
        response.raise_for_status()
        data = self._parse_jsonp(response.text)
        if not data.get("result"):
            raise ValueError("chaoxing captcha verification failed")
        try:
            validate = json.loads(str(data.get("extraData") or "{}")).get("validate", "")
        except (TypeError, ValueError):
            validate = ""
        if not validate:
            raise ValueError("chaoxing captcha validate is missing")
        return str(validate)

    @staticmethod
    def _parse_jsonp(text: str) -> dict[str, Any]:
        """解析超星验证码接口返回的 JSONP。"""
        raw = str(text or "").strip()
        raw = re.sub(r"^[^(]*\(", "", raw, count=1)
        raw = re.sub(r"\);?\s*$", "", raw)
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise ValueError("captcha response is not an object")
        return value

    def _load_cookies(self) -> None:
        """从显式配置的 Redis session key 恢复 Cookie。"""
        if not self.cookie_store or not self.session_key:
            return
        payload = self.cookie_store.get_json(self.session_key)
        if isinstance(payload, dict):
            self.session.cookies.update(payload)

    def _save_cookies(self) -> None:
        """将当前 Cookie 以 TTL 保存到显式 Redis session key。"""
        if not self.cookie_store or not self.session_key:
            return
        cookies = requests.utils.dict_from_cookiejar(self.session.cookies)
        self.cookie_store.set_json(self.session_key, cookies, self.cookie_ttl_seconds)

    @staticmethod
    def extract_en_token(html: str) -> str:
        """从登录表单提取隐藏的 enToken。"""
        soup = BeautifulSoup(html or "", "html.parser")
        form = soup.select_one("form#loginForm") or soup
        field = form.select_one("input[name='enToken']")
        return str(field.get("value") or "").strip() if field else ""

    @staticmethod
    def extract_nickname(html: str) -> str:
        """从登录后的页面提取用户昵称。"""
        soup = BeautifulSoup(html or "", "html.parser")
        node = soup.select_one("p.user-name, li.user h3")
        return re.sub(r"\s+", " ", node.get_text(" ")).strip() if node else ""


class ChaoxingAdapter:
    """超星适配器；验证码和学习地址均要求显式配置。"""

    name = "chaoxing"

    def __init__(self, config: dict[str, object] | None = None, client_factory=None):
        self.config = config or {}
        self._client_factory = client_factory or (lambda url, timeout: ChaoxingClient(url, timeout=timeout))
        self._clients: dict[str, ChaoxingClient] = {}

    def login(self, context: AdapterContext) -> AdapterResult:
        """提交显式验证码并返回登录结果，错误信息不包含账号密码。"""
        username = context.account.strip()
        password = context.password.strip()
        verify_code = str(context.extra.get("verifyCode") or "").strip()
        base_url = str(context.extra.get("schoolUrl") or self.config.get("base_url") or os.getenv("EDUCATION_CHAOXING_BASE_URL") or "").strip()
        if not username or not password:
            return AdapterResult(False, "credentials_empty", "超星账号或密码为空")
        if not base_url:
            return AdapterResult(False, "adapter_config_missing", "超星适配器未配置平台地址")
        stage = "prepare"
        try:
            client = self._client_factory(base_url, int(self.config.get("timeout", 15)))
            captcha_id = str(context.extra.get("captchaId") or self.config.get("captcha_id") or os.getenv("EDUCATION_CHAOXING_CAPTCHA_ID") or "").strip()
            if not verify_code and not captcha_id:
                stage = "resolve_captcha_id"
                captcha_id = client.resolve_captcha_id()
            if not verify_code and captcha_id:
                stage = "fetch_captcha"
                captcha_type = str(context.extra.get("captchaType") or self.config.get("captcha_type") or os.getenv("EDUCATION_CHAOXING_CAPTCHA_TYPE") or "slide")
                captcha_version = str(context.extra.get("captchaVersion") or self.config.get("captcha_version") or os.getenv("EDUCATION_CHAOXING_CAPTCHA_VERSION") or "1.1.20")
                captcha = client.fetch_captcha(captcha_id, captcha_type, captcha_version)
                if context.extra.get("captchaX") is not None:
                    x = int(context.extra["captchaX"])
                else:
                    stage = "solve_captcha"
                    x = client.solve_captcha_x(
                        captcha["token"], captcha["shadeImage"], captcha["cutoutImage"],
                        str(context.extra.get("captchaApiUrl") or self.config.get("captcha_api_url") or os.getenv("EDUCATION_CHAOXING_CAPTCHA_API_URL") or ""),
                        str(context.extra.get("captchaApiToken") or self.config.get("captcha_api_token") or os.getenv("EDUCATION_CHAOXING_CAPTCHA_API_TOKEN") or ""),
                        str(context.extra.get("captchaApiType") or self.config.get("captcha_api_type") or os.getenv("EDUCATION_CHAOXING_CAPTCHA_API_TYPE") or "10110"),
                    )
                stage = "verify_captcha"
                verify_code = client.verify_captcha(captcha_id, captcha_type, captcha_version, captcha["token"], x, captcha["iv"])
            if not verify_code:
                return AdapterResult(False, "captcha_required", "超星登录需要验证码")
            stage = "login_submit"
            response = client.login(username, password, verify_code, str(self.config.get("elserolestustatus", "0")))
            self._clients[context.student_id] = client
            location = str(response.headers.get("Location") or "")
            nickname = client.extract_nickname(response.text)
            if 300 <= response.status_code < 400 or location or nickname:
                data: dict[str, Any] = {"studentName": nickname} if nickname else {}
                if context.extra.get("refreshSnapshots"):
                    try:
                        learning = ChaoxingLearningClient(client.base_url, client.session, int(self.config.get("timeout", 15)))
                        courses = learning.fetch_courses()
                        items = [
                            {
                                "courseName": str(course.get("title") or "未命名课程"),
                                "courseType": str(course.get("desc") or "") or None,
                                "requiredFlag": 1,
                                "term": None,
                                "learningStatus": 0,
                                "learningPercent": None,
                                "learningText": "平台已获取课程信息",
                                "workStatus": 0,
                            }
                            for course in courses
                            if str(course.get("title") or "").strip()
                        ]
                        data["course_progress_items"] = {"items": items}
                        data["course_progress"] = {
                            "courseName": items[0]["courseName"] if len(items) == 1 else (f"{len(items)} 门课程" if items else None),
                            "videoStatus": 0,
                            "workStatus": 0,
                            "examStatus": 0,
                        }
                    except (ValueError, TypeError, KeyError, requests.RequestException):
                        # 登录已成功时，快照失败不应覆盖登录结果；页面仍可保留已有明细。
                        data["snapshotWarning"] = "课程信息暂未获取"
                return AdapterResult(True, "login_ok", "超星登录成功", data)
            return AdapterResult(False, "login_failed", "超星登录失败")
        except (ValueError, requests.RequestException, TypeError, KeyError) as exc:
            logger.warning(
                "chaoxing login failed: stage=%s exception=%s status=%s",
                stage,
                type(exc).__name__,
                getattr(getattr(exc, "response", None), "status_code", None),
            )
            return AdapterResult(False, "login_failed", "超星登录请求失败")

    def execute(self, task: AdapterTask, context: AdapterContext) -> AdapterResult:
        """自动发现课程和章节，执行平台确认的学习任务。"""
        client = self._clients.get(context.student_id)
        if client is None:
            return AdapterResult(False, "login_required", "超星任务执行前必须先登录", {"taskId": task.task_id})
        payload = task.payload if isinstance(task.payload, dict) else {}
        operation = str(payload.get("operation") or payload.get("action") or "study").strip().lower()
        try:
            learning_url = str(payload.get("learningBaseUrl") or self.config.get("learning_base_url") or os.getenv("EDUCATION_CHAOXING_LEARNING_URL") or client.base_url).strip()
            learning = ChaoxingLearningClient(learning_url, client.session, int(self.config.get("timeout", 15)))
            if operation in {"list_courses", "discover_courses"}:
                courses = learning.fetch_courses()
                return AdapterResult(True, "courses_fetched", "超星课程列表获取成功", {"courses": courses})
            if operation in {"study", "run", "execute", ""} and not isinstance(payload.get("course"), dict):
                return self._execute_discovered_study(task, learning, payload)
            course = payload.get("course") if isinstance(payload.get("course"), dict) else payload
            if operation in {"list_chapters", "discover_chapters"}:
                course_url = str(course.get("courseUrl") or course.get("enterUrl") or "").strip()
                if not course_url:
                    return AdapterResult(False, "course_url_missing", "超星课程入口地址为空")
                chapters = learning.fetch_chapters(course_url)
                return AdapterResult(True, "chapters_fetched", "超星章节列表获取成功", {"chapters": [chapter.__dict__ for chapter in chapters]})
            chapter_id = str(payload.get("chapterId") or "").strip()
            if not chapter_id or not all(str(course.get(key) or "").strip() for key in ("courseId", "clazzId", "cpi")):
                return AdapterResult(False, "course_context_missing", "超星课程参数或章节标识为空")
            jobs, job_info = learning.fetch_jobs(course, chapter_id)
            if operation in {"list_jobs", "discover_jobs"}:
                return AdapterResult(True, "jobs_fetched", "超星章节任务获取成功", {"jobs": jobs, "jobInfo": job_info})
            if not jobs:
                return AdapterResult(False, "no_pending_jobs", "超星章节没有待执行任务", {"course_progress": {"orderId": task.order_id, "tenantId": task.tenant_id, "videoStatus": 1, "workStatus": 1}})
            failed: list[str] = []
            unsupported_work = False
            tiku_config = payload.get("tiku") if isinstance(payload.get("tiku"), dict) else None
            tiku_client = TikuClient(tiku_config) if tiku_config else None
            font_map_path = str(payload.get("fontMapPath") or "").strip() or None
            video_total = video_done = 0
            work_total = work_done = 0
            for job in jobs:
                kind = str(job.get("type") or "")
                if kind == "video":
                    video_total += 1
                elif kind in {"workid"}:
                    work_total += 1
                ok, code = learning.execute_job(course, job, job_info, tiku_client, font_map_path)
                if kind == "video" and ok:
                    video_done += 1
                if kind == "workid" and ok:
                    work_done += 1
                if code.startswith("work_"):
                    unsupported_work = True
                if not ok:
                    failed.append(code)
            data = {"course_progress": {"orderId": task.order_id, "tenantId": task.tenant_id,
                                         "courseName": payload.get("courseName"), "videoStatus": 1 if video_done == video_total else 0,
                                         "videoNote": "超星视频任务已由平台确认" if video_total and not any(code.startswith("video_") for code in failed) else None,
                                         "workStatus": 1 if work_total and work_done == work_total else (1 if not work_total else 0),
                                         "workNote": "超星作业题库流程尚未迁移" if unsupported_work else None}}
            if failed:
                return AdapterResult(False, "work_not_migrated" if unsupported_work else "study_failed", "超星任务未全部完成", data)
            return AdapterResult(True, "study_completed", "超星学习任务完成", data)
        except (ValueError, KeyError, TypeError, requests.RequestException):
            return AdapterResult(False, "study_failed", "超星学习请求失败", {"taskId": task.task_id})

    def _execute_discovered_study(self, task: AdapterTask, learning: ChaoxingLearningClient, payload: dict[str, Any]) -> AdapterResult:
        """按订单配置自动筛选课程、遍历待完成章节并执行所有已支持任务。"""
        courses = learning.fetch_courses()
        include = self._course_names(payload.get("includeCourses"))
        exclude = self._course_names(payload.get("excludeCourses"))
        course_name = str(payload.get("courseName") or "").strip()
        if course_name:
            include.add(course_name)
        selected = [course for course in courses if (not include or str(course.get("title") or "").strip() in include) and str(course.get("title") or "").strip() not in exclude]
        if not selected:
            return AdapterResult(False, "course_not_found", "超星未找到符合订单配置的课程", {"course_progress": {"orderId": task.order_id, "tenantId": task.tenant_id, "courseName": course_name, "videoStatus": 0, "workStatus": 0, "examStatus": 0}})
        tiku_config = payload.get("tiku") if isinstance(payload.get("tiku"), dict) else None
        tiku_client = TikuClient(tiku_config) if tiku_config else None
        allow_work = str(payload.get("cxWorkSw", "1")) not in {"0", "false", "False"}
        exam_mode = task.kind is TaskKind.EXAM
        items: list[dict[str, Any]] = []
        failures: list[str] = []
        video_total = video_done = work_total = work_done = 0
        for course in selected:
            course_url = str(course.get("courseUrl") or course.get("enterUrl") or "").strip()
            if not course_url:
                course_url = learning._url("mycourse/studentcourse") + "?" + urlencode({"courseId": course.get("courseId", ""), "clazzid": course.get("clazzId", ""), "cpi": course.get("cpi", "")})
            chapters = learning.fetch_chapters(course_url)
            course_failed = False
            for chapter in chapters:
                jobs, info = learning.fetch_jobs(course, chapter.chapter_id)
                for job in jobs:
                    kind = str(job.get("type") or "")
                    if exam_mode and kind != "workid":
                        continue
                    if kind == "video":
                        video_total += 1
                    if kind == "workid":
                        work_total += 1
                        if not allow_work:
                            continue
                    ok, code = learning.execute_job(course, job, info, tiku_client, str(payload.get("fontMapPath") or "") or None)
                    video_done += int(kind == "video" and ok)
                    work_done += int(kind == "workid" and ok)
                    if not ok:
                        failures.append(code)
                        course_failed = True
            items.append({"courseName": str(course.get("title") or "未命名课程"), "courseType": str(course.get("desc") or ""), "requiredFlag": 1, "term": payload.get("term"), "learningStatus": 2 if course_failed else 1, "learningPercent": 0 if course_failed else 100, "learningText": "执行失败" if course_failed else "已完成", "workStatus": 1 if not course_failed else 2})
        data = {
            "course_progress": {"orderId": task.order_id, "tenantId": task.tenant_id, "courseName": course_name or (selected[0].get("title") if len(selected) == 1 else f"{len(selected)} 门课程"), "term": payload.get("term"), "videoStatus": 0 if exam_mode else (1 if video_done == video_total else 2), "videoNote": None if exam_mode else f"平台确认 {video_done}/{video_total}", "workStatus": 1 if (not allow_work or work_done == work_total) else 2, "workNote": "已关闭作业执行" if not allow_work else f"平台确认 {work_done}/{work_total}", "examStatus": 1 if exam_mode and work_total > 0 and work_done == work_total else (2 if exam_mode else 0)},
            "course_progress_items": {"orderId": task.order_id, "tenantId": task.tenant_id, "items": items},
        }
        if exam_mode:
            data["exam_progress"] = {"orderId": task.order_id, "tenantId": task.tenant_id, "status": 1 if work_total > 0 and work_done == work_total else 2, "note": f"平台确认 {work_done}/{work_total}"}
            if work_total == 0:
                return AdapterResult(False, "exam_not_found", "超星未发现待执行考试", data)
        if failures:
            return AdapterResult(False, "exam_failed" if exam_mode else "study_failed", "超星考试任务未全部完成" if exam_mode else "超星学习任务未全部完成", data)
        return AdapterResult(True, "exam_completed" if exam_mode else "study_completed", "超星考试任务完成" if exam_mode else "超星学习任务完成", data)

    @staticmethod
    def _course_names(value: Any) -> set[str]:
        """归一化任务配置中的课程名称列表。"""
        if isinstance(value, list):
            return {str(item).strip() for item in value if str(item).strip()}
        return {item.strip() for item in re.split(r"[,，;；\n]", str(value or "")) if item.strip()}
