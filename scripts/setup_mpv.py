"""下载 mpv Windows 开发包（libmpv-2.dll + 依赖）到 bin/ 目录。

用法:
    python scripts/setup_mpv.py

从 shinchiro 的 mpv-winbuild 自动下载最新 64-bit 版本。
"""

import io
import json
import os
import subprocess
import sys
import urllib.request
import shutil

BIN_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bin")
SZ_EXE = os.path.join(BIN_DIR, "7zr.exe")
MPV_API = "https://api.github.com/repos/shinchiro/mpv-winbuild-cmake/releases/latest"


def _progress(cur: int, total: int) -> None:
    pct = cur * 100 // total if total else 0
    bar = "#" * (pct // 5) + "-" * (20 - pct // 5)
    print(f"\r  [{bar}] {pct}%", end="", flush=True)


def download_mpv() -> None:
    print(">> 获取最新 mpv 版本信息...")
    req = urllib.request.Request(MPV_API, headers={"User-Agent": "RedVideo/0.0.1"})
    with urllib.request.urlopen(req) as r:
        release = json.loads(r.read())

    version = release["tag_name"]
    print(f"   最新版本: {version}")

    # 找 mpv-dev-x86_64-*.7z
    assets = release.get("assets", [])
    target = None
    for a in assets:
        name = a["name"]
        if "mpv-dev" in name and "x86_64" in name and name.endswith(".7z"):
            target = a
            break

    if not target:
        print("!! 没找到 mpv-dev x86_64 7z，可用的文件：")
        for a in assets:
            print(f"   - {a['name']}")
        sys.exit(1)

    url = target["browser_download_url"]
    print(f"-> 下载 {target['name']}...")

    req = urllib.request.Request(url, headers={"User-Agent": "RedVideo/0.0.1"})
    with urllib.request.urlopen(req) as r:
        total = int(r.headers.get("Content-Length", 0))
        data = io.BytesIO()
        chunk = r.read(8192)
        while chunk:
            data.write(chunk)
            _progress(data.tell(), total)
            chunk = r.read(8192)
        _progress(total, total)
        print()

    # 保存 7z 到临时文件，用 7zr 解压
    print(f"-> 解压到 {BIN_DIR}")
    os.makedirs(BIN_DIR, exist_ok=True)
    sz_path = os.path.join(BIN_DIR, "mpv.7z")
    data.seek(0)
    with open(sz_path, "wb") as f:
        f.write(data.read())
    tmp = os.path.join(BIN_DIR, ".tmp_extract")
    if os.path.exists(tmp):
        shutil.rmtree(tmp)
    # 7zr x -y -otmp file.7z
    subprocess.run([SZ_EXE, "x", "-y", f"-o{tmp}", sz_path], check=True, capture_output=True)
    os.remove(sz_path)
    # 7z 里是 mpv-dev-x86_64-xxx/...，把内层文件移上来
    items = os.listdir(tmp)
    if len(items) == 1 and os.path.isdir(os.path.join(tmp, items[0])):
        inner = os.path.join(tmp, items[0])
        for name in os.listdir(inner):
            shutil.move(os.path.join(inner, name), os.path.join(BIN_DIR, name))
        shutil.rmtree(tmp)
    else:
        for name in items:
            shutil.move(os.path.join(tmp, name), os.path.join(BIN_DIR, name))
        shutil.rmtree(tmp)

    print(f"OK 完成！libmpv-2.dll 位于 {BIN_DIR}")


if __name__ == "__main__":
    download_mpv()
