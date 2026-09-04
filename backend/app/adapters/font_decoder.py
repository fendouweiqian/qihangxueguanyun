"""页面内嵌字体解码边界；映射表必须由部署配置显式提供。"""

from __future__ import annotations

import base64
import hashlib
import json
import re
from io import BytesIO
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup
from fontTools.ttLib import TTFont


_FONT_BASE64_PATTERN = re.compile(r"base64,([A-Za-z0-9+/=]+)")
_FONT_STYLE_ID = "cxSecretStyle"


def _extract_font_base64(html_text: str) -> str | None:
    """提取页面秘密样式中的字体 Base64 内容。"""
    style = BeautifulSoup(html_text or "", "html.parser").find("style", id=_FONT_STYLE_ID)
    if not style or not style.text:
        return None
    match = _FONT_BASE64_PATTERN.search(style.text)
    return match.group(1) if match else None


def _glyph_hash(glyph: Any) -> str:
    """按字形轮廓坐标生成与历史实现一致的 MD5。"""
    if glyph.numberOfContours <= 0:
        return ""
    values: list[str] = []
    start = 0
    for end in glyph.endPtsOfContours:
        for index in range(start, end + 1):
            x, y = glyph.coordinates[index]
            values.append(f"{x}{y}{glyph.flags[index] & 0x01}")
        start = end + 1
    return hashlib.md5("".join(values).encode("utf-8")).hexdigest()


def _font_hashes(font_data: bytes) -> dict[str, str]:
    """解析字体 glyf 表并返回 glyph 名称到哈希的映射。"""
    result: dict[str, str] = {}
    with TTFont(BytesIO(font_data), lazy=False) as font:
        table = font["glyf"]
        for name in table.glyphOrder:
            if name.startswith("uni"):
                digest = _glyph_hash(table.glyphs[name])
                if digest:
                    result[name] = digest
    return result


class FontDecoder:
    """根据部署提供的字形哈希表还原页面中的替换字符。"""

    def __init__(self, font_map_path: str | Path):
        self.font_map_path = Path(font_map_path)
        self._hash_to_char: dict[str, str] = {}
        self._font_to_hash: dict[str, str] = {}

    def set_html_content(self, html_text: str) -> bool:
        """解析页面字体并载入映射表；缺任一资源时返回 False。"""
        encoded = _extract_font_base64(html_text)
        if not encoded or not self.font_map_path.is_file():
            self._font_to_hash = {}
            return False
        try:
            self._font_to_hash = _font_hashes(base64.b64decode(encoded))
            mapping = json.loads(self.font_map_path.read_text(encoding="utf-8"))
            self._hash_to_char = {str(value): str(key) for key, value in mapping.items()}
        except (OSError, ValueError, TypeError, KeyError):
            self._font_to_hash = {}
            self._hash_to_char = {}
            return False
        return bool(self._font_to_hash and self._hash_to_char)

    def decode(self, target: str) -> str:
        """将可识别的私有字形转换为原始 Unicode 字符。"""
        if not target or not self._font_to_hash or not self._hash_to_char:
            return target
        result: list[str] = []
        for char in target:
            digest = self._font_to_hash.get(f"uni{ord(char):X}")
            original = self._hash_to_char.get(digest or "")
            if original and original.startswith("uni"):
                try:
                    result.append(chr(int(original[3:], 16)))
                    continue
                except (ValueError, IndexError):
                    pass
            result.append(char)
        return "".join(result)
