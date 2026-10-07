#!/usr/bin/env python
# -*- coding: utf-8 -*-
""".skill 解包复验脚本（C4A v5）——可复现。

把 .skill 解包到纯 ASCII 路径（模拟换台机器），跑验收五连：
  [1] selftest（有 PyYAML）
  [2] selftest（sys.modules['yaml']=None 模拟无 PyYAML）
  [3] golden_test，输出与 evidence/golden_test_v3.txt 逐字节比对
  [4] evaluate 一个 fixture
  [5] build_skill_pkg.py --check

注意 [3][4] 的输出必须写到**解包目录之外**，否则会在解包目录里留下包内没有的文件，
让 [5] 报出"仓库新增"——那是护栏的正确行为，不是 bug。

用法：python 解包复验脚本.py
依赖：仅标准库。
"""
import hashlib
import os
import shutil
import subprocess
import sys
import zipfile

PY = sys.executable
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)                      # .../C4A
PKG = os.path.join(REPO, "c4-skill-evaluator.skill")
GOLDEN_REF = os.path.join(HERE, "golden_test_v3.txt")
DST = r"C:\Users\Public\c4a_install_test"
OUT = r"C:\Users\Public\c4a_verify_out"           # 产物放这里，别污染解包目录


def run(args, block=False, cwd=DST):
    if block:
        p0 = os.path.join(cwd, args[0])
        code = ("import sys; sys.modules['yaml']=None; sys.argv=%r; "
                "exec(compile(open(%r,encoding='utf-8').read(), %r, 'exec'), "
                "{'__name__':'__main__','__file__':%r})"
                % ([args[0]] + args[1:], p0, p0, p0))
        cmd = [PY, "-c", code]
    else:
        cmd = [PY] + args
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def main():
    for d in (DST, OUT):
        if os.path.isdir(d):
            shutil.rmtree(d)
        os.makedirs(d)
    with zipfile.ZipFile(PKG) as z:
        z.extractall(DST)
    print("解包 %s → %s" % (PKG, DST))
    print("包 sha256:", hashlib.sha256(open(PKG, "rb").read()).hexdigest())

    rc, out = run(["scripts/c4_evaluator.py", "selftest"])
    print("[1] selftest(有PyYAML) exit=%d %s" % (rc, out.strip().splitlines()[-1]))
    rc, out = run(["scripts/c4_evaluator.py", "selftest"], block=True)
    print("[2] selftest(无PyYAML) exit=%d %s" % (rc, out.strip().splitlines()[-1]))

    g = os.path.join(OUT, "g.txt")
    rc, _ = run(["scripts/golden_test.py", "--out", g])
    got = open(g, "rb").read()
    ref = open(GOLDEN_REF, "rb").read()
    print("[3] golden_test exit=%d | %d 字节 | 与留档逐字节一致：%s"
          % (rc, len(got), got == ref))

    rc, out = run(["scripts/c4_evaluator.py", "evaluate",
                   os.path.join("references", "golden_set", "G09_flat_dir"), "--out", OUT])
    tail = [l for l in out.splitlines() if "作者" in l]
    print("[4] evaluate G09 exit=%d | %s" % (rc, tail[-1] if tail else ""))

    up = os.path.dirname(DST)
    cp = os.path.join(up, "c4-skill-evaluator.skill")
    shutil.copy(PKG, cp)
    try:
        rc, out = run(["scripts/build_skill_pkg.py", "--check"])
        print("[5] --check exit=%d | %s" % (rc, out.strip()))
    finally:
        os.remove(cp)


if __name__ == "__main__":
    main()
