# -*- coding: utf-8 -*-
"""RV-004: 单实例交接 — 所有启动（含空参数）走同一入口，文件完整交付。"""

import uuid

import pytest

import main as main_mod
from PyQt6.QtCore import QEventLoop, QThread, QTimer
from PyQt6.QtNetwork import QLocalServer


class FakeWin:
    """记录 open_paths / 激活调用，不建真窗口。"""

    def __init__(self):
        self.paths: list[str] = []
        self.activated = False

    def open_paths(self, paths):
        self.paths.extend(paths)

    def show(self):
        self.activated = True

    def raise_(self):
        pass

    def activateWindow(self):
        self.activated = True


class Sender(QThread):
    """在子线程里跑发送端：waitForReadyRead 阻塞不会卡死测试主线程。"""

    def __init__(self, payload: str):
        super().__init__()
        self.payload = payload
        self.ok = False

    def run(self):
        self.ok = main_mod._send_to_existing(self.payload)


@pytest.fixture
def instance_name(monkeypatch):
    name = f"redvideo-test-{uuid.uuid4().hex}"
    monkeypatch.setattr(main_mod, "_INSTANCE_NAME", name)
    return name


def _pump(ms: int = 2000):
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def _serve(win, server) -> None:
    server.newConnection.connect(lambda: main_mod._on_new_instance(win, server))


def test_no_instance_returns_false(instance_name):
    assert main_mod._send_to_existing("") is False


def test_handoff_delivers_paths(qapp, instance_name):
    win = FakeWin()
    server = QLocalServer()
    assert server.listen(instance_name)
    _serve(win, server)

    t = Sender("/v/A.mp4\n/v/B.mp4")
    t.start()
    _pump()
    t.wait(3000)
    assert t.ok is True
    assert win.paths == ["/v/A.mp4", "/v/B.mp4"]


def test_empty_payload_activates_window(qapp, instance_name):
    win = FakeWin()
    server = QLocalServer()
    assert server.listen(instance_name)
    _serve(win, server)

    t = Sender("")
    t.start()
    _pump()
    t.wait(3000)
    assert t.ok is True
    assert win.paths == []
    assert win.activated is True


def test_large_payload_not_truncated(qapp, instance_name):
    """多选大量文件：readyRead 分片累积，不能只收到第一批。"""
    win = FakeWin()
    server = QLocalServer()
    assert server.listen(instance_name)
    _serve(win, server)

    paths = [f"/v/movie{i:03d}.mkv" for i in range(300)]
    t = Sender("\n".join(paths))
    t.start()
    _pump(3000)
    t.wait(5000)
    assert t.ok is True
    assert win.paths == paths


def test_second_launch_never_steals_active_listener(qapp, instance_name):
    """Windows 语义：同名 listen 对后到者也返回 True，但连接只归首个管道。

    单实例所有权靠 connect-first 交接保证：第二个启动进程交接后即退出，
    不该（也不会）removeServer 抢掉活跃实例的监听。
    """
    win = FakeWin()
    first = QLocalServer()
    assert first.listen(instance_name)
    first.newConnection.connect(lambda: main_mod._on_new_instance(win, first))

    # 第二个进程的启动序列：connect-first 交接 → 确认已交付
    t = Sender("/v/A.mp4")
    t.start()
    _pump()
    t.wait(3000)
    assert t.ok is True
    assert win.paths == ["/v/A.mp4"]

    # 首个实例仍是唯一交付目标：后续连接仍进 first
    t2 = Sender("/v/B.mp4")
    t2.start()
    _pump()
    t2.wait(3000)
    assert win.paths == ["/v/A.mp4", "/v/B.mp4"]
