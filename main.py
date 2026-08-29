"""RedVideo — Windows 桌面视频播放器"""

from __future__ import annotations

import sys
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from player.window import MainWindow


def _base() -> str:
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


BASE = _base()
sys.path.insert(0, BASE)

# 编译后 DLL 在 exe 同级 bin/，未打包进 _MEIPASS
if getattr(sys, "frozen", False):
    exe_dir = os.path.dirname(sys.executable)
    dll_dir = os.path.join(exe_dir, "bin")
else:
    dll_dir = os.path.join(BASE, "bin")
os.environ["PATH"] = dll_dir + os.pathsep + os.environ.get("PATH", "")

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt
from PyQt6.QtNetwork import QLocalServer, QLocalSocket

_INSTANCE_NAME = "redvideo-single-instance"


def _send_to_existing(payload: str) -> bool:
    socket = QLocalSocket()
    try:
        socket.connectToServer(_INSTANCE_NAME)
        if not socket.waitForConnected(500):
            return False
        if payload:
            socket.write(payload.encode("utf-8"))
            socket.flush()
            socket.waitForBytesWritten(500)
        return True
    finally:
        socket.disconnectFromServer()


def main():
    paths = [os.path.abspath(a) for a in sys.argv[1:] if not a.startswith("-")]

    # 单实例：若已有实例在运行，把文件路径发过去后退出
    if paths and _send_to_existing("\n".join(paths)):
        sys.exit(0)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    app.setApplicationName("RedVideo")
    app.setOrganizationName("RedStudio")

    # 缺 libmpv 时给友好提示，而不是裸 traceback
    try:
        from player.window import MainWindow
    except (ImportError, OSError) as e:
        QMessageBox.critical(
            None, "RedVideo",
            "无法加载 mpv 解码库（libmpv-2.dll）。\n\n"
            f"{e}\n\n"
            "请先运行 python scripts/setup_mpv.py 下载解码器，"
            "或重新执行 pip install -r requirements.txt。",
        )
        sys.exit(1)

    win = MainWindow(file_paths=paths)
    win.show()

    # 启动本地服务器，监听后续打开的 files
    _server = QLocalServer()
    _server.removeServer(_INSTANCE_NAME)
    _server.listen(_INSTANCE_NAME)
    _server.newConnection.connect(lambda: _on_new_instance(win, _server))

    sys.exit(app.exec())


def _on_new_instance(win: MainWindow, server: QLocalServer) -> None:
    socket = server.nextPendingConnection()
    if not socket:
        return
    try:
        if socket.waitForReadyRead(500):
            data = socket.readAll().data().decode("utf-8", errors="replace")
            # 多选打开时资源管理器会传多个路径，换行分隔
            paths = [p for p in data.split("\n") if p]
            if paths:
                win.open_paths(paths)
    finally:
        socket.disconnectFromServer()


if __name__ == "__main__":
    main()
