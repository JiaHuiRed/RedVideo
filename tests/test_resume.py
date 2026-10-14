# -*- coding: utf-8 -*-
"""RV-002: 续播点隔离 — 显式打开不得继承旧媒体进度，seek 回调绑定预期文件。"""

import player.window as win_mod
from player.window import _resume_position, _same_path


class TestSamePath:
    def test_normalized_comparison(self):
        assert _same_path(r"C:\V\A.mp4", r"c:/v/a.mp4")
        assert _same_path("/v/A.mp4", "/v/./A.mp4")

    def test_different_files(self):
        assert not _same_path(r"C:\V\A.mp4", r"C:\V\B.mp4")


class TestResumeDecision:
    def test_resume_when_restoring_same_file(self):
        state = {"last_file": r"C:\V\A.mp4", "last_position": 300.0, "last_duration": 600.0}
        assert _resume_position(state, r"c:\v\a.mp4") == 300.0

    def test_no_resume_for_explicitly_opened_other_file(self):
        state = {"last_file": r"C:\V\A.mp4", "last_position": 300.0}
        assert _resume_position(state, r"C:\V\B.mp4") is None

    def test_no_resume_without_position(self):
        assert _resume_position({"last_file": "/v/A.mp4"}, "/v/A.mp4") is None
        assert _resume_position({"last_file": "/v/A.mp4", "last_position": 0},
                                "/v/A.mp4") is None

    def test_no_resume_near_eof(self):
        state = {"last_file": "/v/A.mp4", "last_position": 599.0, "last_duration": 600.0}
        assert _resume_position(state, "/v/A.mp4") is None  # 接近看完 → 从头播

    def test_resume_without_duration_info(self):
        # 旧版本 state.json 没有 last_duration 字段，也应正常恢复
        state = {"last_file": "/v/A.mp4", "last_position": 300.0}
        assert _resume_position(state, "/v/A.mp4") == 300.0

    def test_tolerates_bad_types(self):
        assert _resume_position({"last_file": 123, "last_position": "300"},
                                "/v/A.mp4") is None
        assert _resume_position({"last_file": "/v/A.mp4", "last_position": True},
                                "/v/A.mp4") is None


class TestRestorePositionCallback:
    """_restore_position 绑定预期路径：file_loaded 来路不明就不跳转。"""

    def test_seeks_only_matching_path(self, qapp):
        from PyQt6.QtCore import QObject, pyqtSignal

        class FakeMPV(QObject):
            file_loaded = pyqtSignal(str)

            def __init__(self):
                super().__init__()
                self.seeked = None

            def seek(self, pos):
                self.seeked = pos

        w = win_mod.MainWindow.__new__(win_mod.MainWindow)
        fake = FakeMPV()
        w.mpv = fake
        w._restore_position("/v/A.mp4", 300.0)

        fake.file_loaded.emit("/v/B.mp4")  # 快速切文件：不得套 A 的进度
        assert fake.seeked is None

        # 一次性回调已被消费：之后 A 再加载也不补跳（恢复时机已过）
        fake.file_loaded.emit("/v/A.mp4")
        assert fake.seeked is None

    def test_seeks_matching_path(self, qapp):
        from PyQt6.QtCore import QObject, pyqtSignal

        class FakeMPV(QObject):
            file_loaded = pyqtSignal(str)

            def __init__(self):
                super().__init__()
                self.seeked = None

            def seek(self, pos):
                self.seeked = pos

        w = win_mod.MainWindow.__new__(win_mod.MainWindow)
        fake = FakeMPV()
        w.mpv = fake
        w._restore_position("/v/A.mp4", 300.0)

        fake.file_loaded.emit("/v/A.mp4")
        assert fake.seeked == 300.0

        fake.file_loaded.emit("/v/A.mp4")  # 重复事件不二次跳转
        assert fake.seeked == 300.0
