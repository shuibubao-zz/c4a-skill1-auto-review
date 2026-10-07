#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""终端截图取证脚本（C4A v5）——可复现，Windows 专用。

干的活：起一个真控制台跑命令 → 截屏 → 用三条机器指标自证"这图不是假的"。

  核验 1  像素构成：黑底占比 / 前景占比 / 颜色数 —— 排除空窗口、被遮挡
  核验 2  屏幕缓冲区字符回读（AttachConsole + CONOUT$ + ReadConsoleOutputCharacterW）
          —— 读回截屏那一刻屏幕上真实存在的字符，这是最硬的一条
  核验 3  ASCII 结构图（降采样 150x46）—— 粗看版面，排除只拍到标题栏

依赖：Pillow（只用于截屏）；其余为 ctypes / subprocess 标准库。
用法：python 终端截图脚本.py [输出.png]    默认 ./terminal_shot.png
"""
import ctypes
import os
import subprocess
import sys
import time
from ctypes import wintypes

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
user32.SetProcessDPIAware()

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../C4A
SKILL_DIR = os.path.join(REPO, "c4-skill-evaluator")
OUT = sys.argv[1] if len(sys.argv) > 1 else "terminal_shot.png"
TITLE = "C4A_DEMO"

CMD = (
    "title {t}&& mode con: cols=112 lines=36 && "
    "cd /d {d} && chcp 65001 >nul && "
    r"echo [命令] python scripts\c4_evaluator.py selftest && "
    r"python scripts\c4_evaluator.py selftest && echo [exit=0] && echo. && "
    r"echo [命令] python scripts\build_skill_pkg.py --check && "
    r"python scripts\build_skill_pkg.py --check && echo [exit=0] && "
    "echo [截图就绪]"
).format(t=TITLE, d=SKILL_DIR)


def find_window():
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    found = []

    def _enum(hwnd, _lp):
        if user32.IsWindowVisible(hwnd):
            n = user32.GetWindowTextLengthW(hwnd)
            if n:
                b = ctypes.create_unicode_buffer(n + 1)
                user32.GetWindowTextW(hwnd, b, n + 1)
                if b.value.strip().startswith(TITLE):
                    found.append(hwnd)
        return True

    user32.EnumWindows(EnumWindowsProc(_enum), 0)
    return found


def grab(hwnd):
    """按 DWM 扩展边界截屏（去掉窗口阴影）。"""
    from PIL import ImageGrab

    class RECT(ctypes.Structure):
        _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                    ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

    rect = RECT()
    r = ctypes.windll.dwmapi.DwmGetWindowAttribute(
        hwnd, 9, ctypes.byref(rect), ctypes.sizeof(rect))  # DWMWA_EXTENDED_FRAME_BOUNDS
    if r != 0:
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
    return ImageGrab.grab(bbox=(rect.left, rect.top, rect.right, rect.bottom))


def read_console(pid):
    """回读控制台屏幕缓冲区里的真实字符。返回 (行数信息 dict, 文本行 list)。"""
    class COORD(ctypes.Structure):
        _fields_ = [("X", ctypes.c_short), ("Y", ctypes.c_short)]

    class SMALL_RECT(ctypes.Structure):
        _fields_ = [("Left", ctypes.c_short), ("Top", ctypes.c_short),
                    ("Right", ctypes.c_short), ("Bottom", ctypes.c_short)]

    class CSBI(ctypes.Structure):
        _fields_ = [("dwSize", COORD), ("dwCursorPosition", COORD),
                    ("wAttributes", ctypes.c_ushort), ("srWindow", SMALL_RECT),
                    ("dwMaximumWindowSize", COORD)]

    info = {}
    rows = []
    try:
        kernel32.FreeConsole()
        if not kernel32.AttachConsole(pid):
            info["error"] = "AttachConsole 失败(%d)" % ctypes.GetLastError()
            return info, rows
        # 注意：AttachConsole 之后不能直接用 GetStdHandle(-11)，
        # 必须用 CreateFile("CONOUT$") 打开控制台缓冲区句柄，否则 CSBI 拿不到。
        h = kernel32.CreateFileW("CONOUT$", 0x80000000 | 0x40000000,
                                 0x00000001 | 0x00000002, None, 3, 0, None)
        csbi = CSBI()
        if h != -1 and kernel32.GetConsoleScreenBufferInfo(h, ctypes.byref(csbi)):
            W, H = csbi.dwSize.X, min(csbi.dwSize.Y, 300)
            buf = ctypes.create_unicode_buffer(W * H)
            written = ctypes.c_ulong(0)
            kernel32.ReadConsoleOutputCharacterW(
                h, buf, W * H, COORD(0, 0), ctypes.byref(written))
            raw = buf.value
            # 中文是双宽字符，按 W 切分会错位；这里只做"内容是否存在"的统计，不做精确分行
            rows = [raw[y * W:(y + 1) * W].rstrip() for y in range(H)]
            info["size"] = (W, H)
            info["chars"] = written.value
        else:
            info["error"] = "GetConsoleScreenBufferInfo 失败"
        kernel32.FreeConsole()
    except Exception as e:  # 回读失败不阻断截屏
        info["error"] = repr(e)
    return info, rows


def ascii_art(im, w=150, h=46):
    g = im.convert("L").resize((w, h))
    gp = g.load()
    ramp = " .:-=+*#%@"
    return "\n".join("".join(ramp[min(9, gp[x, y] * 10 // 256)] for x in range(w))
                     for y in range(h))


def main():
    proc = subprocess.Popen(["cmd", "/k", CMD], creationflags=0x00000010)
    time.sleep(6.0)
    try:
        wins = find_window()
        if not wins:
            print("FAIL: 未找到窗口 %s" % TITLE)
            return 1
        hwnd = wins[0]
        user32.ShowWindow(hwnd, 9)
        user32.SetForegroundWindow(hwnd)
        time.sleep(1.5)

        img = grab(hwnd)
        img.save(OUT)
        print("截图 %s | %s | %d 字节" % (OUT, img.size, os.path.getsize(OUT)))
        import hashlib
        print("sha256", hashlib.sha256(open(OUT, "rb").read()).hexdigest())

        # 核验 1：像素构成
        import collections
        im = img.convert("RGB")
        w, h = im.size
        px = im.load()
        cnt = collections.Counter()
        for y in range(0, h, 2):
            for x in range(0, w, 2):
                cnt[px[x, y]] += 1
        tot = sum(cnt.values())
        bg, bgn = cnt.most_common(1)[0]
        print("核验1 背景%s %.2f%% | 前景 %.2f%% | 颜色数 %d"
              % (bg, 100.0 * bgn / tot, 100.0 * (tot - bgn) / tot, len(cnt)))

        # 核验 2：屏幕缓冲区字符回读
        info, rows = read_console(proc.pid)
        ne = [r for r in rows if r.strip()]
        joined = "".join(ne)
        print("核验2 缓冲区 %s | 非空行 %d | PASS %d | FAIL %d | 含17/17 %s | 中文字 %d"
              % (info.get("size", info.get("error")), len(ne),
                 joined.count("PASS"), joined.count("FAIL"),
                 "17/17" in joined,
                 sum(1 for c in joined if "一" <= c <= "鿿")))

        # 核验 3：ASCII 结构图
        print("核验3 --- ASCII 结构图 ---")
        print(ascii_art(img))
    finally:
        proc.kill()
    return 0


if __name__ == "__main__":
    sys.exit(main())
