# -*- coding: utf-8 -*-
"""全屏沉浸态：进入/退出条件与可见性推导（不触达 C++ 层，替身注入）。"""

from PyQt6.QtCore import Qt

from player.window import MainWindow


class FakeTimer:
    def __init__(self):
        self.started = 0

    def start(self, *_args):
        self.started += 1


def _make_window():
    vis = {}

    class FakeTitlebar:
        def setVisible(self, v):
            vis["titlebar"] = v

    class FakeControls:
        def setVisible(self, v):
            vis["controls"] = v

        def set_paused(self, p):
            vis["paused"] = p

    class FakeMpv:
        filename = "a.mp4"
        is_paused = False

        def setCursor(self, c):
            vis["cursor"] = c

    w = MainWindow.__new__(MainWindow)
    w.titlebar = FakeTitlebar()
    w.controls = FakeControls()
    w.mpv = FakeMpv()
    w._immersive = False
    w._immersive_timer = FakeTimer()
    return w, vis


def _playing_fullscreen(w):
    w.isFullScreen = lambda: True
    w.isMinimized = lambda: False


class TestEligibility:
    def test_playing_fullscreen_eligible(self):
        w, _ = _make_window()
        _playing_fullscreen(w)
        assert w._immersive_eligible() is True

    def test_windowed_not_eligible(self):
        w, _ = _make_window()
        w.isFullScreen = lambda: False
        w.isMinimized = lambda: False
        assert w._immersive_eligible() is False

    def test_paused_not_eligible(self):
        w, _ = _make_window()
        _playing_fullscreen(w)
        w.mpv.is_paused = True
        assert w._immersive_eligible() is False

    def test_no_file_not_eligible(self):
        w, _ = _make_window()
        _playing_fullscreen(w)
        w.mpv.filename = None
        assert w._immersive_eligible() is False


class TestEnterExit:
    def test_enter_hides_chrome_and_blanks_cursor(self):
        w, vis = _make_window()
        _playing_fullscreen(w)
        w._enter_immersive()
        assert w._immersive is True
        assert vis["titlebar"] is False
        assert vis["controls"] is False
        assert vis["cursor"] == Qt.CursorShape.BlankCursor

    def test_windowed_enter_is_noop(self):
        w, vis = _make_window()
        w.isFullScreen = lambda: False
        w.isMinimized = lambda: False
        w._enter_immersive()
        assert w._immersive is False
        assert "controls" not in vis  # 可见性未被扰动

    def test_enter_twice_idempotent(self):
        w, _ = _make_window()
        _playing_fullscreen(w)
        w._enter_immersive()
        w._enter_immersive()
        assert w._immersive is True

    def test_poke_exits_and_restarts_timer(self):
        w, vis = _make_window()
        _playing_fullscreen(w)
        w._immersive = True
        w._poke_immersive()
        assert w._immersive is False
        assert vis["controls"] is True
        assert vis["cursor"] == Qt.CursorShape.ArrowCursor
        assert w._immersive_timer.started == 1

    def test_paused_changed_pokes(self):
        w, vis = _make_window()
        _playing_fullscreen(w)
        w._immersive = True
        w._on_paused_changed(True)
        assert vis["paused"] is True
        assert w._immersive is False  # 暂停唤出控制栏
        assert w._immersive_timer.started == 1


class TestUpdateChrome:
    def test_windowed_shows_all(self):
        w, vis = _make_window()
        w.isFullScreen = lambda: False
        w._update_chrome()
        assert vis["titlebar"] is True
        assert vis["controls"] is True

    def test_fullscreen_hides_titlebar_keeps_controls(self):
        w, vis = _make_window()
        _playing_fullscreen(w)
        w._update_chrome()
        assert vis["titlebar"] is False
        assert vis["controls"] is True

    def test_immersive_hides_both(self):
        w, vis = _make_window()
        _playing_fullscreen(w)
        w._immersive = True
        w._update_chrome()
        assert vis["titlebar"] is False
        assert vis["controls"] is False
