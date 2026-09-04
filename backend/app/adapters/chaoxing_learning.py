"""超星课程、章节和学习任务协议。

该模块只处理已观察到的 HTTP 协议和 HTML/JSON 解析，不保存账号密码或输出
Cookie。外部请求必须由适配器在显式登录成功后触发。
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from hashlib import md5
from html.parser import HTMLParser
from typing import Any
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from app.adapters.font_decoder import FontDecoder


_VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
}


@dataclass(frozen=True)
class Chapter:
    """课程章节及其平台链接。"""

    chapter_id: str
    title: str
    href: str
    job_count: str = ""


def _text(value: Any) -> str:
    """把 HTML 节点文本折叠为空白。"""
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _attrs(tag: Any) -> dict[str, str]:
    """将 HTMLParser 属性列表转换为字符串字典。"""
    return {str(key): str(value or "") for key, value in tag}


class _CourseParser(HTMLParser):
    """解析超星课程卡片，保留历史查询使用的字段名。"""

    def __init__(self) -> None:
        super().__init__()
        self.courses: list[dict[str, str]] = []
        self._depth = 0
        self._current: dict[str, str] | None = None
        self._skip = False
        self._capture: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = _attrs(attrs)
        classes = set(values.get("class", "").split())
        if self._current is None and tag == "div" and "course" in classes:
            self._current = {
                "id": values.get("id", ""), "info": values.get("info", ""),
                "roleid": values.get("roleid", ""), "clazzId": "", "courseId": "",
                "cpi": "", "title": "", "desc": "", "teacher": "",
            }
            self._depth = 1
            self._skip = False
        elif self._current is not None and tag not in _VOID_TAGS:
            self._depth += 1
        if self._current is None:
            return
        if "not-open-tip" in classes:
            self._skip = True
        if tag == "input":
            if "clazzId" in classes:
                self._current["clazzId"] = values.get("value", "")
            elif "courseId" in classes:
                self._current["courseId"] = values.get("value", "")
        if tag == "a" and not self._current["cpi"]:
            match = re.search(r"(?:^|[?&])cpi=([^&]+)", values.get("href", ""))
            if match:
                self._current["cpi"] = match.group(1)
        if tag in {"span", "p"}:
            if "course-name" in classes:
                self._capture = "title"
                self._current["title"] = values.get("title", self._current["title"])
            elif tag == "p" and "margint10" in classes:
                self._capture = "desc"
                self._current["desc"] = values.get("title", self._current["desc"])
            elif tag == "p" and "color3" in classes:
                self._capture = "teacher"
                self._current["teacher"] = values.get("title", self._current["teacher"])

    def handle_endtag(self, tag: str) -> None:
        if self._current is None:
            return
        if self._capture and ((self._capture == "title" and tag == "span") or tag == "p"):
            self._capture = None
        if tag not in _VOID_TAGS:
            self._depth -= 1
        if self._depth <= 0:
            if not self._skip:
                self.courses.append(self._current)
            self._current = None
            self._capture = None

    def handle_data(self, data: str) -> None:
        if self._current is not None and self._capture:
            value = _text(data)
            if value and not self._current[self._capture]:
                self._current[self._capture] = value


def decode_course_list(html_text: str) -> list[dict[str, str]]:
    """解析课程列表 HTML，并过滤尚未开放的课程。"""
    parser = _CourseParser()
    parser.feed(html_text or "")
    return parser.courses


def decode_course_folders(html_text: str) -> list[dict[str, str]]:
    """解析课程文件夹列表。"""
    result: list[dict[str, str]] = []
    for match in re.finditer(
        r"<li\b[^>]*\bfileid=[\"']([^\"']+)[\"'][^>]*>(.*?)</li>",
        html_text or "", re.I | re.S,
    ):
        input_match = re.search(
            r"<input\b[^>]*class=[\"'][^\"']*rename-input[^\"']*[\"'][^>]*value=[\"']([^\"']*)",
            match.group(2), re.I | re.S,
        )
        result.append({"id": match.group(1), "rename": input_match.group(1) if input_match else ""})
    return result


def parse_course_meta(final_url: str) -> dict[str, str]:
    """从课程入口 URL 提取课程、班级和 CPI 参数。"""
    params = parse_qs(urlparse(final_url).query)
    return {
        "courseId": (params.get("courseId") or [""])[0],
        "clazzId": (params.get("clazzid") or params.get("clazzId") or [""])[0],
        "cpi": (params.get("cpi") or [""])[0],
    }


def normalize_chapter_host(href: str) -> str:
    """将历史 jxjy 章节地址统一到超星学习主机。"""
    parsed = urlparse(href)
    if parsed.netloc.endswith(".jxjy.chaoxing.com"):
        return parsed._replace(scheme="https", netloc="mooc1.chaoxing.com").geturl()
    return href


def parse_chapters(html_text: str, base_url: str) -> list[Chapter]:
    """解析课程页面中的章节链接和未完成任务数量。"""
    result: list[Chapter] = []
    pattern = re.compile(r"<a\b([^>]*studentstudy\?chapterId=[^>]+)>(.*?)</a>", re.I | re.S)
    for match in pattern.finditer(html_text or ""):
        attrs = dict(re.findall(r"([\w:-]+)=[\"']([^\"']*)", match.group(1)))
        href = attrs.get("href", "")
        params = parse_qs(urlparse(href).query)
        chapter_id = (params.get("chapterId") or [""])[0]
        body = match.group(2)
        aria = _text(attrs.get("aria-label", ""))
        number = _text(re.sub(r"<[^>]+>", " ", re.search(r"class=[\"'][^\"']*chapterNumber[^\"']*[\"'][^>]*>(.*?)</", body, re.I | re.S).group(1)) if re.search(r"class=[\"'][^\"']*chapterNumber[^\"']*[\"'][^>]*>(.*?)</", body, re.I | re.S) else "")
        name_match = re.search(r"class=[\"'][^\"']*articlename[^\"']*[\"'][^>]*>(.*?)</", body, re.I | re.S)
        name = _text(re.sub(r"<[^>]+>", " ", name_match.group(1))) if name_match else ""
        count_match = re.search(r"class=[\"'][^\"']*knowledgeJobCount[^\"']*[\"'][^>]*value=[\"']([^\"']*)", body, re.I | re.S)
        title = aria or _text(f"{number} {name}")
        absolute = normalize_chapter_host(urljoin(base_url, href))
        if chapter_id:
            result.append(Chapter(chapter_id, title, absolute, count_match.group(1) if count_match else ""))
    return result


def _extract_json_object(text: str, marker: str) -> dict[str, Any] | None:
    """从页面脚本中读取 marker 后的 JSON 对象。"""
    start = (text or "").find(marker)
    if start < 0:
        return None
    start += len(marker)
    try:
        value, _ = json.JSONDecoder().raw_decode(text[start:].lstrip())
    except (TypeError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def decode_course_cards(html_text: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """解析章节任务卡片，返回未完成任务和公共令牌。"""
    if "章节未开放" in (html_text or ""):
        return [], {"notOpen": True}
    payload = _extract_json_object(html_text or "", "mArg=")
    if not payload:
        return [], {}
    defaults = payload.get("defaults") if isinstance(payload.get("defaults"), dict) else {}
    info = {key: defaults.get(key, "") for key in ("ktoken", "mtEnc", "defenc", "cardid", "cpi", "qnenc", "knowledgeid")}
    info["reportTimeInterval"] = defaults.get("reportTimeInterval", 60)
    jobs: list[dict[str, Any]] = []
    for card in payload.get("attachments", []):
        if not isinstance(card, dict) or card.get("isPassed") or card.get("job") is None:
            continue
        item = {
            "jobid": card.get("jobid", ""), "otherinfo": str(card.get("otherInfo", "")).split("&", 1)[0],
        }
        kind = str(card.get("type", "")).lower()
        if kind == "video":
            prop = card.get("property") if isinstance(card.get("property"), dict) else {}
            item.update({"type": "video", "name": prop.get("name", ""), "mid": card.get("mid", ""),
                         "objectid": card.get("objectId", ""), "aid": card.get("aid", ""),
                         "playTime": card.get("playTime", 0), "rt": prop.get("rt", ""),
                         "attDuration": card.get("attDuration", ""), "attDurationEnc": card.get("attDurationEnc", ""),
                         "videoFaceCaptureEnc": card.get("videoFaceCaptureEnc", "")})
        elif kind in {"document", "read"}:
            item.update({"type": kind, "jtoken": card.get("jtoken", "")})
        elif kind == "workid":
            item.update({"type": "workid", "mid": card.get("mid", ""), "enc": card.get("enc", ""), "aid": card.get("aid", "")})
        else:
            continue
        jobs.append(item)
    return jobs, info


def get_video_enc(clazz_id: str, job_id: str, object_id: str, playing_time: int, duration: int, user_id: str) -> str:
    """生成超星视频进度接口使用的摘要。"""
    value = f"[{clazz_id}][{user_id}][{job_id}][{object_id}][{playing_time * 1000}]" \
            f"[d_yHJ!$pdA~5][{duration * 1000}][0_{duration}]"
    return md5(value.encode()).hexdigest()


def _work_type_name(type_code: str) -> str:
    """将超星作业题型编码转换为题库类型。"""
    return {"0": "single", "1": "multiple", "2": "completion", "3": "judgement", "4": "shortanswer"}.get(type_code, "unknown")


def _normalize_text(value: Any) -> str:
    """归一化全角标点和不可见空格，便于比较题库答案。"""
    text = str(value or "").replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    text = text.replace("。", ".").replace("&nbsp;", " ").replace("\xa0", " ")
    return "".join(chr(ord(char) - 65248) if 65281 <= ord(char) <= 65374 else (" " if ord(char) == 12288 else char) for char in text)


def _normalize_option(value: str) -> str:
    """去掉选项序号并压缩空白。"""
    text = re.sub(r"^[A-Za-z]\s*[\.、]?\s*", "", _normalize_text(value))
    text = re.sub(r"(选择|选项)\s*$", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _resolve_choice_answer(answer: str, options: list[str], multiple: bool) -> str | None:
    """将题库返回的字母或选项文本解析成平台答案。"""
    letters = re.findall(r"[A-D]", str(answer or "").upper())
    if letters:
        unique = sorted(set(letters))
        return "".join(unique) if multiple else unique[0]
    option_map = {}
    for option in options:
        match = re.match(r"\s*([A-Za-z])", option)
        if match:
            option_map[match.group(1).upper()] = _normalize_option(option)
    parts = [part.strip() for part in re.split(r"[\n,，、;；|/#]+", str(answer or "")) if part.strip()]
    selected = []
    for part in parts or [_normalize_option(str(answer or ""))]:
        needle = _normalize_option(part)
        found = next((letter for letter, text in option_map.items() if text and (needle in text or text in needle)), None)
        if not found:
            selected = []
            break
        selected.append(found)
    if selected:
        unique = sorted(set(selected))
        return "".join(unique) if multiple else unique[0]
    return None


def _resolve_judgement(answer: str, true_list: list[str], false_list: list[str]) -> str | None:
    """将判断题答案归一化为 true 或 false。"""
    text = _normalize_text(answer).strip().lower()
    if text in {"true", "false"}:
        return text
    if text in {_normalize_text(item).strip().lower() for item in true_list}:
        return "true"
    if text in {_normalize_text(item).strip().lower() for item in false_list}:
        return "false"
    return None


def parse_work_questions(html_text: str, font_map_path: str | None = None) -> tuple[dict[str, str], list[dict[str, Any]]]:
    """解析作业表单、题干和选项；字体映射缺失时保留原始文本。"""
    decoder = None
    if font_map_path:
        candidate = FontDecoder(font_map_path)
        if candidate.set_html_content(html_text):
            decoder = candidate
    decode = decoder.decode if decoder else (lambda value: value)
    soup = BeautifulSoup(html_text or "", "html.parser")
    form = soup.find("form")
    if form is None:
        return {}, []
    form_data: dict[str, str] = {}
    for field in form.find_all("input"):
        name = str(field.get("name") or "")
        if name and not name.startswith(("answer", "answertype")):
            form_data[name] = str(field.get("value") or "")
    questions: list[dict[str, Any]] = []
    for node in form.find_all("div", class_="singleQuesId"):
        question_id = str(node.get("data") or "").strip()
        title_node = node.find("div", class_="Zy_TItle")
        type_node = node.find("div", class_="TiMu")
        type_code = str(type_node.get("data") or "").strip() if type_node else ""
        if not question_id or not type_code:
            continue
        title = decode(_text(title_node.get_text(" ") if title_node else ""))
        options = [decode(_text(item.get("aria-label") or item.get_text(" "))) for item in node.find_all("li")]
        questions.append({"id": question_id, "type_code": type_code, "type": _work_type_name(type_code), "title": title, "options": options})
    return form_data, questions


class ChaoxingLearningClient:
    """执行超星课程发现及视频、文档、阅读任务请求。"""

    def __init__(self, base_url: str, session: requests.Session, timeout: int = 15):
        if not base_url.startswith(("http://", "https://")):
            raise ValueError("chaoxing learning base_url must be an explicit http(s) URL")
        self.base_url = base_url.rstrip("/")
        self.session = session
        self.timeout = max(1, int(timeout))

    def _url(self, path: str) -> str:
        """在显式学习站点地址下构造相对路径。"""
        return urljoin(self.base_url + "/", path.lstrip("/"))

    def fetch_courses(self) -> list[dict[str, str]]:
        """读取课程文件夹和课程卡片。"""
        headers = {"Referer": self._url("mooc2-ans/visit/interaction")}
        interaction = self.session.get(self._url("mooc2-ans/visit/interaction"), headers=headers, timeout=self.timeout)
        interaction.raise_for_status()
        data = {"courseType": 1, "courseFolderId": 0, "query": "", "superstarClass": 0}
        response = self.session.post(self._url("mooc2-ans/visit/courselistdata"), headers=headers, data=data, timeout=self.timeout)
        response.raise_for_status()
        courses = decode_course_list(response.text)
        for folder in decode_course_folders(interaction.text):
            folder_data = dict(data)
            folder_data["courseFolderId"] = folder["id"]
            response = self.session.post(self._url("mooc2-ans/visit/courselistdata"), headers=headers, data=folder_data, timeout=self.timeout)
            response.raise_for_status()
            courses.extend(decode_course_list(response.text))
        return courses

    def fetch_chapters(self, course_url: str) -> list[Chapter]:
        """读取课程入口页面中的章节。"""
        response = self.session.get(course_url, headers={"Referer": self.base_url + "/"}, timeout=self.timeout)
        response.raise_for_status()
        return parse_chapters(response.text, self.base_url)

    def fetch_jobs(self, course: dict[str, Any], chapter_id: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """读取章节任务卡片并合并分页片段。"""
        params: dict[str, Any] = {
            "clazzid": course.get("clazzId", ""), "courseid": course.get("courseId", ""),
            "knowledgeid": chapter_id, "ut": "s", "cpi": course.get("cpi", ""), "v": "2025-0424-1038-3", "mooc2": 1,
        }
        jobs: list[dict[str, Any]] = []
        info: dict[str, Any] = {}
        for number in "0123456":
            params["num"] = number
            response = self.session.get(self._url("mooc-ans/knowledge/cards"), params=params, timeout=self.timeout)
            response.raise_for_status()
            chunk, chunk_info = decode_course_cards(response.text)
            if chunk_info.get("notOpen"):
                return [], chunk_info
            jobs.extend(chunk)
            info.update(chunk_info)
        return jobs, info

    def execute_job(self, course: dict[str, Any], job: dict[str, Any], info: dict[str, Any], tiku_client: Any | None = None, font_map_path: str | None = None) -> tuple[bool, str]:
        """执行一个视频、文档或阅读任务，并返回平台状态。"""
        kind = str(job.get("type") or "")
        if kind == "video":
            return self._complete_video(course, job)
        if kind == "document":
            node = re.search(r"nodeId_(.*?)-", str(job.get("otherinfo", "")))
            if not node:
                return False, "document_node_missing"
            response = self.session.get(self._url("mooc-ans/ananas/job/document"), params={
                "jobid": job.get("jobid"), "knowledgeid": node.group(1), "courseid": course.get("courseId"),
                "clazzid": course.get("clazzId"), "jtoken": job.get("jtoken"), "_dc": str(int(time.time() * 1000)),
            }, timeout=self.timeout)
            return response.status_code == 200, "document_completed" if response.status_code == 200 else "document_failed"
        if kind == "read":
            response = self.session.get(self._url("mooc-ans/ananas/job/readv2"), params={
                "jobid": job.get("jobid"), "knowledgeid": info.get("knowledgeid", ""), "jtoken": job.get("jtoken"),
                "courseid": course.get("courseId"), "clazzid": course.get("clazzId"),
            }, timeout=self.timeout)
            return response.status_code == 200, "read_completed" if response.status_code == 200 else "read_failed"
        if kind == "workid":
            return self._complete_work(course, job, info, tiku_client, font_map_path)
        return False, "unsupported_job_type"

    def _complete_work(self, course: dict[str, Any], job: dict[str, Any], info: dict[str, Any], tiku_client: Any | None, font_map_path: str | None) -> tuple[bool, str]:
        """读取作业、查询显式题库并提交完整答案。"""
        if tiku_client is None:
            return False, "work_tiku_missing"
        job_id = str(job.get("jobid") or "")
        if not job_id or not info.get("ktoken") or not info.get("knowledgeid"):
            return False, "work_context_missing"
        response = self.session.get(self._url("mooc-ans/api/work"), params={
            "api": "1", "workId": job_id.replace("work-", ""), "jobid": job_id, "originJobId": job_id,
            "needRedirect": "true", "skipHeader": "true", "knowledgeid": info.get("knowledgeid"),
            "ktoken": info.get("ktoken"), "cpi": info.get("cpi", ""), "ut": "s", "clazzId": course.get("clazzId", ""),
            "enc": job.get("enc", ""), "mooc2": "1", "courseid": course.get("courseId", ""),
        }, timeout=self.timeout)
        if response.status_code != 200:
            return False, "work_fetch_failed"
        form_data, questions = parse_work_questions(response.text, font_map_path)
        if not questions:
            return False, "work_questions_missing"
        answers: dict[str, str] = {}
        true_list = list(getattr(tiku_client, "true_list", []))
        false_list = list(getattr(tiku_client, "false_list", []))
        for question in questions:
            answer = tiku_client.query(question["title"], "\n".join(question["options"]), question["type"])
            if not answer:
                continue
            kind = question["type"]
            if kind == "single":
                resolved = _resolve_choice_answer(answer, question["options"], False)
            elif kind == "multiple":
                resolved = _resolve_choice_answer(answer, question["options"], True)
            elif kind == "judgement":
                resolved = _resolve_judgement(answer, true_list, false_list)
            else:
                resolved = str(answer).strip()
            if resolved:
                answers[question["id"]] = resolved
        coverage = len(answers) / len(questions)
        cover_rate = float(getattr(tiku_client, "cover_rate", 1.0))
        if coverage < cover_rate:
            return False, "work_coverage_insufficient"
        payload = dict(form_data)
        payload["answerwqbid"] = ",".join(question["id"] for question in questions) + ","
        payload["pyFlag"] = "" if bool(getattr(tiku_client, "submit", True)) else "1"
        for question in questions:
            payload[f"answer{question['id']}"] = answers[question["id"]]
            payload[f"answertype{question['id']}"] = question["type_code"]
        submitted = self.session.post(self._url("mooc-ans/work/addStudentWorkNew"), data=payload, headers={"X-Requested-With": "XMLHttpRequest", "Referer": getattr(response, "url", self.base_url), "Origin": self.base_url}, timeout=self.timeout)
        if submitted.status_code != 200:
            return False, "work_submit_failed"
        try:
            passed = bool(submitted.json().get("status"))
        except (TypeError, ValueError):
            passed = False
        return passed, "work_completed" if passed else "work_not_passed"

    def _complete_video(self, course: dict[str, Any], job: dict[str, Any]) -> tuple[bool, str]:
        """提交一次到视频末尾的进度记录，平台未确认时返回失败。"""
        object_id = str(job.get("objectid") or "")
        user_id = str(self.session.cookies.get("_uid") or self.session.cookies.get("UID") or "")
        if not object_id or not user_id:
            return False, "video_context_missing"
        response = self.session.get(self._url(f"ananas/status/{object_id}"), params={"k": self.session.cookies.get("fid", ""), "flag": "normal"}, timeout=self.timeout)
        response.raise_for_status()
        info = response.json()
        if info.get("status") != "success" or not info.get("dtoken"):
            return False, "video_status_failed"
        duration = max(0, int(info.get("duration") or 0))
        params = {
            "clazzId": course.get("clazzId", ""), "playingTime": duration, "duration": duration, "clipTime": f"0_{duration}",
            "objectId": object_id, "otherInfo": job.get("otherinfo", ""), "courseId": course.get("courseId", ""),
            "jobid": job.get("jobid", ""), "userid": user_id, "isdrag": "4", "view": "pc",
            "enc": get_video_enc(str(course.get("clazzId", "")), str(job.get("jobid", "")), object_id, duration, duration, user_id),
            "dtype": "Video", "rt": str(job.get("rt") or "1.0"), "_t": str(int(time.time() * 1000)),
        }
        for key in ("videoFaceCaptureEnc", "attDuration", "attDurationEnc"):
            if job.get(key):
                params[key] = job[key]
        logged = self.session.get(self._url(f"mooc-ans/multimedia/log/a/{course.get('cpi', '')}/{info['dtoken']}"), params=params, timeout=self.timeout)
        if logged.status_code != 200:
            return False, "video_progress_failed"
        try:
            passed = bool(logged.json().get("isPassed"))
        except (TypeError, ValueError):
            passed = False
        return passed, "video_completed" if passed else "video_not_passed"
