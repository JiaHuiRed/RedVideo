"""RedVideo — Windows 桌面视频播放器"""

import sys
import os


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

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtNetwork import QLocalServer, QLocalSocket

from player.window import MainWindow

_INSTANCE_NAME = "redvideo-single-instance"


def _send_to_existing(path: str) -> bool:
    socket = QLocalSocket()
    socket.connectToServer(_INSTANCE_NAME)
    if socket.waitForConnected(500):
        if path:
            socket.write(path.encode("utf-8"))
            socket.flush()
            socket.waitForBytesWritten(500)
        socket.disconnectFromServer()
        return True
    return False


def main():
    file_path = None
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if args:
        file_path = os.path.abspath(args[0])

    # 单实例：若已有实例在运行，把文件路径发过去后退出
    if file_path and _send_to_existing(file_path):
        sys.exit(0)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    app.setApplicationName("RedVideo")
    app.setOrganizationName("RedStudio")

    win = MainWindow(file_path=file_path)
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
    if socket.waitForReadyRead(500):
        data = socket.readAll().data().decode("utf-8", errors="replace")
        if data:
            win.playlist.add_files([data])
            if not win.mpv.filename:
                win._play_file(data)
            win.show()
            win.raise_()
            win.activateWindow()
    socket.disconnectFromServer()


if __name__ == "__main__":
    main()
