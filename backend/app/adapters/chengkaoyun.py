"""成考云平台适配器；所有外部地址必须通过配置显式提供。"""

from __future__ import annotations

import base64
import os
import re
from collections.abc import Callable
from typing import Any

import requests
from bs4 import BeautifulSoup

from app.adapters.base import AdapterContext, AdapterResult, AdapterTask, TaskKind


class ChengKaoYunClient:
    """成考云 HTTP 客户端，集中处理超时、授权头和响应解析。"""

    def __init__(self, base_url: str, session: requests.Session | None = None, timeout: int = 20):
        if not base_url.startswith(("http://", "https://")):
            raise ValueError("chengkaoyun base_url must be an explicit http(s) URL")
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()
        self.timeout = max(1, timeout)

    def login(self, phone: str, open_id: str, password: str) -> tuple[str, dict[str, Any]]:
        """提交账号密码并返回授权令牌与原始业务响应。"""
        response = self.session.post(
            f"{self.base_url}/api/v1/user/password/check",
            json={"phone": phone, "openId": open_id, "password": password},
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        data = payload.get("data") or {}
        token = str(data.get("token") or data.get("my_token") or "")
        return token, payload

    def student_management(self, token: str) -> dict[str, Any]:
        """读取登录后的学生档案响应。"""
        response = self.session.get(
            f"{self.base_url}/api/v1/student/mobile/management",
            headers={"Authorization": token},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def sign(self, token: str, payload: dict[str, Any]) -> dict[str, Any]:
        """提交考试签到信息。"""
        response = self.session.post(
            f"{self.base_url}/api/v1/examination/sign",
            json=payload,
            headers={"Authorization": token},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def get_vcode_image(self, phone: str) -> bytes:
        """获取考试签到验证码图片字节，不落盘。"""
        response = self.session.get(
            f"{self.base_url}/api/v1/examination/makecode",
            params={"phone": phone},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return bytes(response.content)

    def solve_vcode(self, image: bytes, api_url: str, api_token: str, api_type: str = "10110") -> str:
        """调用显式验证码识别服务并返回验证码文本。"""
        if not api_url.startswith(("http://", "https://")) or not api_token:
            raise ValueError("captcha solver URL and token are required")
        response = self.session.post(
            api_url,
            json={"image": base64.b64encode(image).decode("ascii"), "token": api_token, "type": api_type},
            headers={"Content-Type": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        value = payload.get("data") if isinstance(payload, dict) else None
        if payload.get("code") != 10000 or not isinstance(value, dict) or not str(value.get("data") or "").strip():
            raise ValueError("captcha solver rejected request")
        return str(value["data"]).strip()

    def program_exams(self, token: str, semester_id: str) -> dict[str, Any]:
        """读取指定学期的课程考试列表。"""
        response = self.session.get(
            f"{self.base_url}/api/v1/examination/programexam",
            params={"semester_id": semester_id},
            headers={"Authorization": token},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def management(self, token: str, payload: dict[str, Any]) -> dict[str, Any]:
        """读取考试题目和考试会话数据。"""
        response = self.session.post(
            f"{self.base_url}/api/v1/examination/mobile/management",
            json=payload,
            headers={"Authorization": token},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def save_answer(self, token: str, payload: dict[str, Any]) -> dict[str, Any]:
        """保存考试过程中的答案。"""
        response = self.session.post(
            f"{self.base_url}/api/v1/answer/mobile/save",
            json=payload,
            headers={"Authorization": token},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def submit_exam(self, token: str, payload: dict[str, Any]) -> dict[str, Any]:
        """提交最终考试答案并返回平台结果。"""
        response = self.session.put(
            f"{self.base_url}/api/v1/examination/mobile/management",
            json=payload,
            headers={"Authorization": token},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()


class ChengKaoYunAdapter:
    """成考云适配器；考试链路要求显式验证码和题库配置。"""

    name = "chengkaoyun"

    def __init__(
        self,
        config: dict[str, Any] | None = None,
        client_factory: Callable[[str, int], ChengKaoYunClient] | None = None,
    ):
        self.config = config or {}
        self._client_factory = client_factory or (lambda url, timeout: ChengKaoYunClient(url, timeout=timeout))
        self._sessions: dict[str, tuple[ChengKaoYunClient, str]] = {}

    def login(self, context: AdapterContext) -> AdapterResult:
        """验证账号、授权令牌和学生档案，不在错误中回显凭证。"""
        account = context.account.strip()
        password = context.password.strip()
        open_id = str(context.extra.get("studentOpenId") or "").strip()
        base_url = str(context.extra.get("schoolUrl") or self.config.get("base_url") or os.getenv("EDUCATION_CHENGKAOYUN_BASE_URL") or "").strip()
        if not account or not password or not open_id:
            return AdapterResult(False, "credentials_empty", "成考云账号、密码或开放标识为空")
        if not base_url:
            return AdapterResult(False, "adapter_config_missing", "成考云适配器未配置平台地址")
        try:
            client = self._client_factory(base_url, int(self.config.get("timeout", 20)))
            token, payload = client.login(account, open_id, password)
            if int(payload.get("code", 0)) != 200 or not token:
                return AdapterResult(False, "login_failed", "成考云登录失败")
            profile = client.student_management(token)
            name = self._student_name(profile)
            if not name:
                return AdapterResult(False, "profile_missing", "成考云学生档案缺少姓名")
            self._sessions[context.student_id] = (client, token)
            return AdapterResult(True, "login_ok", "成考云登录成功", {"studentName": name})
        except (ValueError, requests.RequestException, TypeError, KeyError):
            return AdapterResult(False, "login_failed", "成考云登录请求失败")

    def execute(self, task: AdapterTask, context: AdapterContext) -> AdapterResult:
        """执行显式配置的成考云考试，并拒绝平台未定义的学习任务。"""
        payload = task.payload
        is_exam = task.kind is TaskKind.EXAM
        if is_exam:
            return self._execute_exam(task, context)
        note = "成考云平台未提供独立学习任务接口"
        return AdapterResult(
            False,
            "task_type_not_supported",
            note,
            {
                "course_progress": {
                    "orderId": task.order_id,
                    "tenantId": task.tenant_id,
                    "courseName": payload.get("courseName"),
                    "term": payload.get("term"),
                    "videoStatus": 0,
                    "videoNote": note,
                    "workStatus": 0,
                    "workNote": note,
                    "examStatus": 1 if is_exam else 0,
                    "examNote": note,
                },
                "exam_progress": {
                    "orderId": task.order_id,
                    "tenantId": task.tenant_id,
                    "status": 1 if is_exam else 0,
                    "note": note,
                },
            },
        )

    def _execute_exam(self, task: AdapterTask, context: AdapterContext) -> AdapterResult:
        """编排考试列表、签到、题库答题、保存和最终提交。"""
        session = self._sessions.get(context.student_id)
        if session is None:
            return AdapterResult(False, "login_required", "成考云考试执行前必须先登录")
        client, token = session
        payload = task.payload if isinstance(task.payload, dict) else {}
        semester_id = str(payload.get("semesterId") or payload.get("semester_id") or "").strip()
        if not semester_id:
            return AdapterResult(False, "exam_context_missing", "成考云考试缺少学期标识")
        sign_code = str(payload.get("signCode") or payload.get("sign_code") or "").strip()
        if not sign_code:
            captcha_url = str(payload.get("captchaApiUrl") or self.config.get("captcha_api_url") or os.getenv("EDUCATION_CHENGKAOYUN_CAPTCHA_API_URL") or "").strip()
            captcha_token = str(payload.get("captchaApiToken") or self.config.get("captcha_api_token") or os.getenv("EDUCATION_CHENGKAOYUN_CAPTCHA_API_TOKEN") or "").strip()
            if not captcha_url or not captcha_token:
                return AdapterResult(False, "exam_captcha_required", "成考云考试签到需要显式验证码或识别服务")
            try:
                sign_code = client.solve_vcode(
                    client.get_vcode_image(context.account), captcha_url, captcha_token,
                    str(payload.get("captchaApiType") or self.config.get("captcha_api_type") or os.getenv("EDUCATION_CHENGKAOYUN_CAPTCHA_API_TYPE") or "10110"),
                )
            except (ValueError, TypeError, requests.RequestException):
                return AdapterResult(False, "exam_captcha_failed", "成考云考试验证码识别失败")
        tiku_config = payload.get("tiku") if isinstance(payload.get("tiku"), dict) else None
        if not tiku_config:
            return AdapterResult(False, "exam_tiku_missing", "成考云考试需要显式题库配置")
        from app.adapters.tiku import TikuClient

        tiku = TikuClient(tiku_config, client.session)
        try:
            program = client.program_exams(token, semester_id)
            items = program.get("data") if isinstance(program.get("data"), list) else []
            selected = self._select_exam(items, payload.get("examId"), payload.get("crsId"))
            if selected is None:
                return AdapterResult(False, "exam_not_found", "成考云未找到目标考试")
            if int(selected.get("is_sign") or 0) != 1:
                sign_result = client.sign(token, {
                    "stu_id": payload.get("stuId") or payload.get("stu_id"),
                    "phone": context.account, "code": sign_code, "semester_id": semester_id,
                    "crs_id": selected.get("crs_id"),
                })
                if int(sign_result.get("code") or 0) not in {200, 1000005}:
                    return AdapterResult(False, "exam_sign_failed", "成考云考试签到失败")
            management_payload = {
                "semester_id": semester_id, "ques_id": selected.get("ques_id"),
                "stu_exam": selected.get("stu_exam") or {}, "crs_id": selected.get("crs_id"),
            }
            management = client.management(token, management_payload)
            questions = management.get("ques_list") if isinstance(management.get("ques_list"), list) else []
            if int(management.get("code") or 0) != 200 or not questions:
                return AdapterResult(False, "exam_questions_missing", "成考云考试题目获取失败")
            missing = 0
            for question in questions:
                if not self._apply_exam_answer(question, tiku):
                    missing += 1
            if missing:
                return AdapterResult(False, "exam_answer_missing", "成考云考试题库未覆盖全部题目", {"exam_progress": {"orderId": task.order_id, "tenantId": task.tenant_id, "status": 0, "note": "题库覆盖不足"}})
            answer_payload = {
                "ques_id": management_payload["ques_id"], "question_list": questions,
                "semester_id": semester_id, "type": management.get("type", 1), "crs_id": management_payload["crs_id"],
            }
            saved = client.save_answer(token, answer_payload)
            if int(saved.get("code") or 0) != 200:
                return AdapterResult(False, "exam_save_failed", "成考云考试答案保存失败")
            if bool(payload.get("submitExam", payload.get("submit_exam", False))):
                submitted = client.submit_exam(token, {"exam_id": management.get("exam_id") or (management_payload.get("stu_exam") or {}).get("exam_id"), "question_list": questions, "semester_id": semester_id})
                if int(submitted.get("code") or 0) != 200:
                    return AdapterResult(False, "exam_submit_failed", "成考云考试提交失败")
            return AdapterResult(True, "exam_completed", "成考云考试完成", {"exam_progress": {"orderId": task.order_id, "tenantId": task.tenant_id, "status": 1, "note": "平台已确认答案"}})
        except (ValueError, TypeError, KeyError, requests.RequestException):
            return AdapterResult(False, "exam_failed", "成考云考试请求失败")

    @staticmethod
    def _select_exam(items: list[dict[str, Any]], exam_id: Any, crs_id: Any) -> dict[str, Any] | None:
        """按考试或课程标识选择考试，缺少匹配时使用第一项。"""
        if exam_id is not None:
            for item in items:
                if str((item.get("stu_exam") or {}).get("exam_id")) == str(exam_id):
                    return item
        if crs_id is not None:
            for item in items:
                if str(item.get("crs_id")) == str(crs_id):
                    return item
        return items[0] if items else None

    @staticmethod
    def _apply_exam_answer(question: dict[str, Any], tiku: Any) -> bool:
        """查询题库并把答案写入成考云题目结构。"""
        kind = str(question.get("type") or "")
        title = BeautifulSoup(str(question.get("html") or question.get("title") or ""), "html.parser").get_text(" ", strip=True)
        options = question.get("options") if isinstance(question.get("options"), list) else []
        option_texts = [BeautifulSoup(str(item.get("title") or ""), "html.parser").get_text(" ", strip=True) for item in options if isinstance(item, dict)]
        type_name = {"radio": "single", "checkbox": "multiple", "boolean": "judgement"}.get(kind, "shortanswer")
        answer = tiku.query(title, "\n".join(option_texts), type_name)
        if not answer:
            return False
        if kind in {"radio", "checkbox"}:
            letters = set(re.findall(r"[A-Z]", answer.upper()))
            if not letters:
                letters = {str(item.get("option_num") or "").upper() for item in options if isinstance(item, dict) and str(item.get("title") or "") in answer}
            selected = {letter for letter in letters if letter}
            for item in options:
                if isinstance(item, dict):
                    item["is_selected"] = str(item.get("option_num") or "").upper() in selected
            if not selected:
                return False
            if kind == "checkbox":
                question["text_answer"] = "".join(sorted(selected))
                question["answer_num"] = len(selected)
            else:
                question["text_answer"] = ""
                question["answer_num"] = 0
            question["has_answer"] = True
            return True
        if kind == "boolean":
            text = answer.strip().lower()
            if text in {"true", "1", "是", "正确", "对"}:
                question["boolean_answer"] = True
            elif text in {"false", "0", "否", "错误", "错"}:
                question["boolean_answer"] = False
            else:
                return False
            question["text_answer"] = ""
        else:
            question["text_answer"] = answer.strip()
            if not question["text_answer"]:
                return False
        question["has_answer"] = True
        return True

    @staticmethod
    def _student_name(payload: dict[str, Any]) -> str:
        """从平台档案响应中提取第一个非空姓名。"""
        data = payload.get("data")
        values = data if isinstance(data, list) else [data]
        for item in values:
            if isinstance(item, dict) and str(item.get("name") or "").strip():
                return str(item["name"]).strip()
        return ""
