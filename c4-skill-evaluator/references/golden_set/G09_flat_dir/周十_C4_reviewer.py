#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""班级提交评审助手：扫描文件夹，按槽位检查完整性与四条件质量。

运行方式:
    python reviewer.py 待评文件夹 --out ./reports
"""

import argparse
import json
import re
import sys
from pathlib import Path

SLOTS = {
    "skill_doc": ["skill说明", "教学说明"],
    "teaching_doc": ["教学说明"],
    "ai_log": ["AI日志"],
    "demo": [],
    "executable": [],
}


def scan(folder: Path) -> dict:
    """输入一个文件夹路径，返回 {作者: {文件名: 字节数}} 的分组结果。"""
    if not folder.is_dir():
        raise SystemExit("输入必须是存在的文件夹：%s" % folder)
    groups = {}
    for p in sorted(folder.rglob("*")):
        if not p.is_file() or p.stat().st_size == 0:
            continue  # 0 字节文件视为未提交
        m = re.match(r"^(?P<author>[^_]+)_C4_", p.name)
        author = m.group("author") if m else (p.parent.name or "未知")
        groups.setdefault(author, {})[p.name] = p.stat().st_size
    return groups


def check_slots(files: dict) -> dict:
    """对一位作者的文件清单逐槽位判定是否齐全。"""
    low = {n.lower() for n in files}
    return {
        "skill_doc": any("skill说明" in n for n in low),
        "teaching_doc": any("教学说明" in n for n in low),
        "ai_log": any("ai日志" in n or "ai_log" in n for n in low),
        "demo": any(n.endswith((".png", ".jpg", ".mp4")) for n in low),
        "executable": any(n.endswith((".py", ".skill", ".zip")) for n in low),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="输入文件夹，输出评审报告")
    ap.add_argument("folder", help="待评文件夹路径")
    ap.add_argument("--out", default="./reports", help="报告输出目录")
    args = ap.parse_args()

    groups = scan(Path(args.folder))
    lines = ["# 评审报告", ""]
    for author, files in sorted(groups.items()):
        slots = check_slots(files)
        missing = [k for k, v in slots.items() if not v]
        score = round(100 * (len(slots) - len(missing)) / len(slots))
        grade = "✅" if score >= 75 else ("⚠️" if score >= 40 else "❌")
        lines.append("## %s（%d 分 %s）" % (author, score, grade))
        for k, ok in slots.items():
            lines.append("- %s：%s" % (k, "有" if ok else "缺"))
        lines.append("")
    report = "\n".join(lines)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.md").write_text(report, encoding="utf-8")
    print(report)
    print("已写入 %s" % (out / "report.md"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
