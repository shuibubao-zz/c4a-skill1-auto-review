#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_skill_pkg.py — 打包 c4-skill-evaluator.skill 并防漂移。

铁律（P0 事故教训，不可删）：
    **改过 rubric / 代码之后必须重新打包，打包后必须重跑自检与黄金集。**
    否则仓库内与 .skill 内是两份会各自漂移的 rubric——
    v4 的 P0（rubric 加行内注释 → 无 PyYAML 环境崩溃）正是"改了库内、没同步包内"造成的。

行尾不变式（P1 事故教训，2026-10-07 外部复核发现，不可删）：
    **包内文本文件一律 LF；--check 对文本文件做行尾归一后比对。**
    v5 的 P1：--check 逐字节 sha256，而 Windows 默认 Git 配置（core.autocrlf=true）
    克隆出的工作区是 CRLF、包内是 LF → 误报 39 条"内容漂移"（归一后 48/48 一致，真漂移 0 条）。
    误报会摧毁护栏的可信度——它正是"测试看着通过，其实没测到"的镜像：
    测试看着失败，其实没有失败。修法（本文件已落实）：
      1) 仓库加 .gitattributes（* -text，git 从此不碰行尾，克隆即 LF）；
      2) 打包时文本统一写 LF（与工作区行尾无关）；
      3) --check 对文本行尾归一后比对，纯行尾差异单独警告、不计入漂移。

用法:
    python build_skill_pkg.py            # 重新打包（覆盖 C4A 根目录的 .skill）
    python build_skill_pkg.py --check    # 只校验：包内文件与仓库当前文件是否一致
"""

import argparse
import hashlib
import sys
import time
import zipfile
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
PKG_PATH = SKILL_DIR.parent / "c4-skill-evaluator.skill"
EXCLUDE = {".DS_Store", "Thumbs.db", "__pycache__"}

# 这些扩展名按二进制处理：打包与比对都不做行尾归一（归一会破坏文件）
BINARY_EXT = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".bmp",
    ".zip", ".skill", ".gz", ".tar", ".pdf", ".docx", ".xlsx", ".pptx",
    ".mp4", ".mov", ".webm", ".mp3", ".wav",
    ".woff", ".woff2", ".ttf", ".otf", ".eot",
}


def collect_files(root: Path = SKILL_DIR) -> list[Path]:
    files = sorted(p for p in root.rglob("*")
                   if p.is_file() and not (set(p.parts) & EXCLUDE)
                   and p.name not in EXCLUDE and "__pycache__" not in p.parts)
    return files


def _is_text(name: str) -> bool:
    return Path(name).suffix.lower() not in BINARY_EXT


def _norm_lf(data: bytes, name: str) -> bytes:
    """文本文件行尾归一为 LF（CRLF/CR → LF）；二进制原样返回。"""
    if not _is_text(name):
        return data
    return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def build(root: Path = SKILL_DIR, pkg_path: Path | None = None) -> int:
    pkg_path = pkg_path or PKG_PATH
    files = collect_files(root)
    with zipfile.ZipFile(pkg_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            rel = f.relative_to(root).as_posix()
            info = zipfile.ZipInfo(rel, date_time=time.localtime(f.stat().st_mtime)[:6])
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (f.stat().st_mode & 0xFFFF) << 16
            # 行尾不变式：包内文本一律 LF，与工作区当前行尾无关
            z.writestr(info, _norm_lf(f.read_bytes(), rel))
    print("已打包 %d 个文件 → %s（%d 字节，文本行尾统一 LF）"
          % (len(files), pkg_path, pkg_path.stat().st_size))
    print("\n⚠️ 别忘了验收三连：")
    print("  1) python scripts/c4_evaluator.py selftest        # 17/17")
    print("  2) python scripts/golden_test.py                  # 与 evidence/ 留档一致")
    print("  3) 解包到另一目录再跑一遍（见 evidence/skill安装验证.txt）")
    return 0


def compare(pkg_path: Path, root: Path = SKILL_DIR) -> tuple[list[str], list[str], int]:
    """比较包内与 root 目录。

    返回 (drift, eol_only, n_total)：
      drift    — 结构缺失/多余 + 归一后仍不一致的文件（真漂移）
      eol_only — 仅行尾不同、归一后一致的文件（不算漂移，调用方自行决定是否提示）
    """
    with zipfile.ZipFile(pkg_path) as z:
        zipped = {n: z.read(n) for n in z.namelist()}
    local = {f.relative_to(root).as_posix(): f.read_bytes() for f in collect_files(root)}
    drift, eol_only = [], []
    for n in sorted(set(local) | set(zipped)):
        if n not in zipped:
            drift.append("仓库新增/包内缺失: %s" % n)
        elif n not in local:
            drift.append("包内多余/仓库已删: %s" % n)
        elif _norm_lf(local[n], n) != _norm_lf(zipped[n], n):
            drift.append("内容漂移: %s" % n)
        elif local[n] != zipped[n]:
            eol_only.append(n)          # 内容一致，仅行尾不同
    return drift, eol_only, len(set(local) | set(zipped))


def check(pkg_path: Path | None = None, root: Path = SKILL_DIR) -> int:
    pkg_path = pkg_path or PKG_PATH
    if not pkg_path.exists():
        print("ERROR: 找不到 %s，先打包" % pkg_path, file=sys.stderr)
        return 1
    drift, eol_only, n_total = compare(pkg_path, root)
    if drift:
        print("检测到 %d 处漂移（改完 rubric/代码后没重新打包？）：" % len(drift))
        for d in drift:
            print("  -", d)
        print("→ 运行 python scripts/build_skill_pkg.py 重新打包")
        return 1
    if eol_only:
        # P1 教训：行尾差异不是内容漂移。单列警告，不失败、不计入漂移。
        print("注意：%d 个文件仅行尾不同（工作区/包内 CRLF/LF 混用），内容归一后一致：" % len(eol_only))
        for n in eol_only[:5]:
            print("  ~", n)
        if len(eol_only) > 5:
            print("  … 共 %d 个" % len(eol_only))
    print("OK：包内 %d 个文件与仓库内容一致（文本行尾归一后比对）" % (n_total - len(drift)))
    return 0


def main():
    ap = argparse.ArgumentParser(description="打包/校验 c4-skill-evaluator.skill")
    ap.add_argument("--check", action="store_true", help="只校验不打包")
    args = ap.parse_args()
    sys.exit(check() if args.check else build())


if __name__ == "__main__":
    main()
