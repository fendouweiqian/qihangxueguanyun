"""扫描目标 Python 锁定依赖的安装版本和许可证元数据。"""

from __future__ import annotations

import re
from importlib import metadata
from pathlib import Path


def _requirements(path: Path) -> list[str]:
    """读取锁定文件中的发行包名称。"""
    names: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        names.append(re.split(r"[=<>!~\[]", line, maxsplit=1)[0].strip())
    return names


def _license_name(dist: metadata.Distribution) -> str:
    """从元数据许可证字段或官方分类器解析可审计的许可证名称。"""
    declared = (dist.metadata.get("License") or "").strip()
    if declared:
        return declared
    classifiers = dist.metadata.get_all("Classifier") or []
    for classifier in classifiers:
        prefix = "License :: OSI Approved :: "
        if classifier.startswith(prefix):
            name = classifier.removeprefix(prefix)
            return {
                "MIT License": "MIT",
                "BSD License": "BSD-3-Clause",
                "Apache Software License": "Apache-2.0",
            }.get(name, name)
    return "UNKNOWN"


def main() -> int:
    """输出许可证摘要，缺少锁定包时返回失败。"""
    lock = Path(__file__).resolve().parents[1] / "backend" / "requirements.lock"
    missing: list[str] = []
    for name in _requirements(lock):
        try:
            dist = metadata.distribution(name)
        except metadata.PackageNotFoundError:
            missing.append(name)
            continue
        license_name = _license_name(dist)
        print(f"{dist.metadata.get('Name', name)}=={dist.version}; license={license_name}")
    if missing:
        print("missing=" + ",".join(missing))
        return 1
    print("license_scan=passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
