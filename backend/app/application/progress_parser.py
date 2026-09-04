"""课程、考试和学生档案页面快照解析器。"""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup


def _text(value: Any) -> str:
    """折叠 HTML 文本中的空白并去除首尾空格。"""
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _status(value: str, *, exam: bool = False) -> int:
    """把平台状态文案统一为 0 未开始、1 成功、2 失败、3 进行中。"""
    text = _text(value)
    if any(word in text for word in ("已完成", "已结束", "已提交", "已交", "完成")):
        return 1
    if any(word in text for word in ("失败", "未通过", "不及格")):
        return 2
    if any(word in text for word in ("进行中", "学习中", "处理中")):
        return 3
    return 0


class ProgressDetailParser:
    """解析平台快照为仓储写回所需的结构化字典。"""

    def parse_student_profile(self, snapshot: str | None) -> dict[str, str]:
        """解析姓名、学籍年级和培养专业。"""
        soup = BeautifulSoup(snapshot or "", "html.parser")
        result: dict[str, str] = {}
        name = soup.select_one("p.user-name, li.user h3")
        if name:
            result["studentName"] = _text(name.get_text(" "))
        for row in soup.select("tr"):
            cells = [_text(cell.get_text(" ")) for cell in row.select("th,td")]
            if len(cells) < 2:
                continue
            self._profile_pair(result, cells[0], cells[1])
        lines = [_text(line) for line in soup.get_text("\n").splitlines() if _text(line)]
        for index, line in enumerate(lines):
            if not any(key in line for key in ("姓名", "学籍年级", "年级", "培养专业", "专业")):
                continue
            if ":" in line or "：" in line:
                self._profile_pair(result, line, "")
            elif index + 1 < len(lines):
                self._profile_pair(result, line, lines[index + 1])
        return result

    def parse_course_items(self, snapshot: str | None) -> list[dict[str, Any]]:
        """解析课程卡片或表格，提取课程名称、类型和学习进度。"""
        soup = BeautifulSoup(snapshot or "", "html.parser")
        rows: list[dict[str, Any]] = []
        seen: set[str] = set()
        candidates = soup.select("tr, div.course, div[class*='course'], dl.w_cour_row")
        for node in candidates:
            text = _text(node.get_text(" "))
            if not text:
                continue
            name_node = node.select_one(".course-name, .coursename, .kcname, .w_cour_txtH a, h3 a")
            name = _text(name_node.get_text(" ") if name_node else "")
            if not name:
                cells = [_text(cell.get_text(" ")) for cell in node.select("th,td")]
                name = cells[0] if cells else ""
            if not name or name in seen or name in {"课程", "我的课程", "学习进度"}:
                continue
            seen.add(name)
            percent_match = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
            course_type = _text((node.select_one(".w_coulogo") or {}).get_text(" ") if node.select_one(".w_coulogo") else "")
            rows.append({
                "courseName": name,
                "courseType": course_type or None,
                "requiredFlag": 1 if "必修" in course_type else 0,
                "learningStatus": _status(text),
                "learningPercent": float(percent_match.group(1)) if percent_match else None,
                "learningText": text[:64],
            })
        return rows

    def parse_exam_items(self, snapshot: str | None) -> list[dict[str, Any]]:
        """解析考试表格，提取名称、状态、成绩和备注。"""
        soup = BeautifulSoup(snapshot or "", "html.parser")
        tables = soup.select("table")
        rows: list[dict[str, Any]] = []
        for table in tables:
            table_rows = table.select("tr")
            if len(table_rows) < 2:
                continue
            headers = [_text(cell.get_text(" ")) for cell in table_rows[0].select("th,td")]
            name_index = self._header_index(headers, "试卷名称", "考试科目", "考试名称")
            status_index = self._header_index(headers, "考试状态")
            score_index = self._header_index(headers, "考试成绩", "成绩")
            submit_index = self._header_index(headers, "提交状态")
            for row in table_rows[1:]:
                cells = [_text(cell.get_text(" ")) for cell in row.select("th,td")]
                if not cells:
                    continue
                name = cells[name_index] if name_index >= 0 and name_index < len(cells) else cells[0]
                if not name or name in {"考试名称", "试卷名称"}:
                    continue
                status_text = self._cell(cells, status_index)
                submit_text = self._cell(cells, submit_index)
                score_text = self._cell(cells, score_index)
                score_match = re.search(r"\d+(?:\.\d+)?", score_text)
                rows.append({
                    "examName": name,
                    "examStatus": _status(f"{status_text} {submit_text}", exam=True),
                    "score": float(score_match.group(0)) if score_match else None,
                    "remark": _text(f"{status_text} {submit_text}")[:255] or None,
                })
        return rows

    @staticmethod
    def _profile_pair(result: dict[str, str], label: str, value: str) -> None:
        """按字段标签写入档案结果。"""
        if ":" in label or "：" in label:
            label, inline_value = re.split(r"[:：]", label, maxsplit=1)
            value = inline_value
        value = _text(value)
        if not value:
            return
        if "姓名" in label:
            result.setdefault("studentName", value)
        elif "学籍年级" in label or "年级" in label:
            result.setdefault("studyGrade", value)
        elif "培养专业" in label or "专业" in label:
            result.setdefault("major", value)

    @staticmethod
    def _header_index(headers: list[str], *names: str) -> int:
        """查找第一个匹配的表头下标。"""
        for index, header in enumerate(headers):
            if any(name in header for name in names):
                return index
        return -1

    @staticmethod
    def _cell(cells: list[str], index: int) -> str:
        """安全读取表格单元格。"""
        return cells[index] if 0 <= index < len(cells) else ""
