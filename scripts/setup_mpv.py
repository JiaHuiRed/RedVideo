"""下载 mpv Windows 开发包（libmpv-2.dll + 依赖）到 bin/ 目录。

用法:
    python scripts/setup_mpv.py

libmpv 版本固定在下方常量（含 SHA-256），不再跟踪 releases/latest：
同版本构建取到同一预期依赖，下载后先校验再解压，哈希不符拒绝使用。

升级流程：到 github.com/shinchiro/mpv-winbuild-cmake 的 release 资产页
取新 tag 与 mpv-dev-x86_64-*.7z 的 sha256，改下面三个常量，本地跑一遍
本脚本 + 启动播放验证通过后再提交。
"""

import hashlib
import io
import os
import shutil
import subprocess
import sys
import urllib.request

BIN_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bin")
SZ_EXE = os.path.join(BIN_DIR, "7zr.exe")
SZ_URL = "https://www.7-zip.org/a/7zr.exe"

# 已测试的 libmpv 构建（2026-10-14）：版本 + 资产名 + 哈希三者固定
MPV_TAG = "20261014"
MPV_ASSET = "mpv-dev-x86_64-20261014-git-ec38361c56.7z"
MPV_SHA256 = "325555b4e0b1d87fb7c92c96010776581599c64e4988052cb9d05e130b52f939"
MPV_URL = (f"https://github.com/shinchiro/mpv-winbuild-cmake/"
           f"releases/download/{MPV_TAG}/{MPV_ASSET}")


def _progress(cur: int, total: int) -> None:
    pct = cur * 100 // total if total else 0
    bar = "#" * (pct // 5) + "-" * (20 - pct // 5)
    print(f"\r  [{bar}] {pct}%", end="", flush=True)


def _download(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "RedVideo/0.5.3"})
    with urllib.request.urlopen(req, timeout=60) as r:
        total = int(r.headers.get("Content-Length", 0))
        data = io.BytesIO()
        chunk = r.read(8192)
        while chunk:
            data.write(chunk)
            _progress(data.tell(), total)
            chunk = r.read(8192)
        _progress(total, total)
        print()
        return data.getvalue()


def ensure_7zr() -> None:
    """如果 7zr.exe 不存在则从 7-zip.org 下载。"""
    if os.path.exists(SZ_EXE):
        return
    print(">> 下载 7zr.exe...")
    os.makedirs(BIN_DIR, exist_ok=True)
    try:
        data = _download(SZ_URL)
    except Exception as e:
        print(f"!! 下载 7zr.exe 失败：{e}")
        sys.exit(1)
    with open(SZ_EXE, "wb") as f:
        f.write(data)
    print(f"   已保存到 {SZ_EXE}")


def download_mpv() -> None:
    ensure_7zr()
    print(f">> 下载 libmpv {MPV_TAG}（{MPV_ASSET}）...")
    try:
        data = _download(MPV_URL)
    except Exception as e:
        print(f"!! 下载失败：{e}")
        sys.exit(1)

    # 先校验再解压：哈希不符（掉包/截断/版本漂移）一律拒绝使用
    digest = hashlib.sha256(data).hexdigest()
    if digest != MPV_SHA256:
        print("!! SHA-256 校验失败，拒绝使用：")
        print(f"   实际 {digest}")
        print(f"   期望 {MPV_SHA256}")
        sys.exit(1)
    print("   SHA-256 校验通过")

    # 保存 7z 到临时文件，用 7zr 解压
    print(f"-> 解压到 {BIN_DIR}")
    os.makedirs(BIN_DIR, exist_ok=True)
    sz_path = os.path.join(BIN_DIR, "mpv.7z")
    with open(sz_path, "wb") as f:
        f.write(data)
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
