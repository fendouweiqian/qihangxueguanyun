"""题库查询适配器；服务地址、参数和令牌全部来自运行时配置。"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

import requests


def _as_list(value: Any) -> list[str]:
    """将配置或题目选项统一为非空字符串列表。"""
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def _question_type(value: str) -> int:
    """转换题型名称为历史题库协议使用的整数。"""
    return {"single": 0, "multiple": 1, "completion": 2, "judgement": 3}.get(value, 4)


def _answer_text(answer: Mapping[str, Any], question_type: str) -> str:
    """按题型优先级归一化题库响应中的答案字段。"""
    best = answer.get("bestAnswer") or []
    answer_text = str(answer.get("answerText") or "").replace("#", "\n").strip()
    all_answer = answer.get("allAnswer") or []
    key_text = str(answer.get("answerKeyText") or "").strip()
    if best:
        return "\n".join(str(item).strip() for item in best if str(item).strip())
    if answer_text:
        return answer_text
    if isinstance(all_answer, list):
        flattened = all_answer[0] if all_answer and isinstance(all_answer[0], list) else all_answer
        value = "\n".join(str(item).strip() for item in flattened if str(item).strip())
    else:
        value = str(all_answer).strip()
    return value or key_text


class TikuClient:
    """调用结构化题库服务并返回脱敏之外的答案文本。"""

    def __init__(self, config: Mapping[str, Any], session: requests.Session | None = None):
        self.provider = str(config.get("provider") or "").strip().lower()
        self.url = str(config.get("url") or "").strip()
        self.params = config.get("params") or None
        self.timeout = max(1, int(config.get("timeout", 15)))
        self.session = session or requests.Session()

    def query(self, question: str, options: str = "", question_type: str = "") -> str | None:
        """查询一道题；未配置服务或返回无答案时返回 None。"""
        if self.provider not in {"adapter", "tikuadapter"} or not self.url or not question.strip():
            return None
        cleaned = []
        for option in options.splitlines():
            option = option.strip()
            if option:
                cleaned.append(re.sub(r"^[A-Za-z][\.!、]?\s*", "", option) or option)
        response = self.session.post(
            self.url,
            params=self.params,
            json={"question": question, "options": cleaned, "type": _question_type(question_type)},
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        answer = payload.get("answer") if isinstance(payload, dict) else None
        if not isinstance(answer, Mapping):
            return None
        value = _answer_text(answer, question_type).strip()
        return value or None
