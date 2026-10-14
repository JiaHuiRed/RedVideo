"""RedVideo — Windows 桌面视频播放器"""

from __future__ import annotations

import os
import sys
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
from PyQt6.QtCore import QTimer
from PyQt6.QtNetwork import QLocalServer, QLocalSocket

_INSTANCE_NAME = "redvideo-single-instance"
_ACK = b"REDVIDEO-OK"
_QUIET_MS = 300  # 本地管道消息无帧界：静默期即消息结束（分片间隔远小于此）


def _send_to_existing(payload: str) -> bool:
    """把 payload 交给已在运行的实例；空 payload = 激活已有窗口。

    返回 True 表示调用方应退出：要么收到服务端确认，要么字节已写给一个
    仍在对端的连接（不双开窗口）；只有「没有实例 / 对端已断开」才返回
    False，让调用方自建窗口，避免静默丢文件。
    """
    socket = QLocalSocket()
    try:
        socket.connectToServer(_INSTANCE_NAME)
        if not socket.waitForConnected(500):
            return False
        if payload:
            socket.write(payload.encode("utf-8"))
            socket.flush()
            socket.waitForBytesWritten(500)
        # 等服务端处理完再退出：否则旧实例还没读完，连接就断了
        if socket.waitForReadyRead(2000) and bytes(socket.readAll().data()).strip() == _ACK:
            return True
        # 无确认时看对端是否还活着：活着当已交付（可能正忙），断开才是交付失败
        return socket.state() == QLocalSocket.LocalSocketState.ConnectedState
    finally:
        socket.disconnectFromServer()


def main():
    paths = [os.path.abspath(a) for a in sys.argv[1:] if not a.startswith("-")]

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    app.setApplicationName("RedVideo")
    app.setOrganizationName("RedStudio")

    # 单实例：无论是否带文件，先尝试交接给已有实例（空参数=激活原窗口）。
    # 必须在 QApplication 之后——QLocalSocket 的等待/信号依赖事件循环。
    if _send_to_existing("\n".join(paths)):
        sys.exit(0)

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

    # 本地服务器接收后续打开的文件。Windows 上连接总是到达首个同名管道，
    # listen 成功不代表独占（与另一实例同时启动时可能成为收不到连接的
    # 僵尸名）——单实例所有权由上面的 connect-first 交接保证；这里绝不
    # removeServer，避免抢掉活跃实例的监听。
    server = QLocalServer()
    server.listen(_INSTANCE_NAME)
    server.newConnection.connect(lambda: _on_new_instance(win, server))

    win = MainWindow(file_paths=paths)
    win.show()

    sys.exit(app.exec())


def _on_new_instance(win: MainWindow, server: QLocalServer) -> None:
    socket = server.nextPendingConnection()
    if not socket:
        return
    chunks = bytearray()
    # 消息无帧界：readyRead 持续累积，静默 300ms 视为发送方写完
    timer = QTimer(socket)
    timer.setSingleShot(True)
    timer.setInterval(_QUIET_MS)

    def _drain() -> None:
        chunks.extend(socket.readAll().data())
        timer.start()  # 每来一片就重新计静默期，大列表分片也不会截断

    def _finish() -> None:
        for sig, slot in ((socket.readyRead, _drain), (timer.timeout, _finish),
                          (socket.disconnected, _finish)):
            try:
                sig.disconnect(slot)
            except TypeError:
                pass
        data = bytes(chunks).decode("utf-8", errors="replace")
        # 多选打开时资源管理器会传多个路径，换行分隔
        paths = [p for p in data.split("\n") if p]
        if paths:
            win.open_paths(paths)
        else:
            # 空参数启动：激活原窗口
            win.show()
            win.raise_()
            win.activateWindow()
        socket.write(_ACK)
        socket.flush()
        socket.disconnectFromServer()

    socket.readyRead.connect(_drain)
    timer.timeout.connect(_finish)
    socket.disconnected.connect(_finish)
    timer.start()


if __name__ == "__main__":
    main()
