# -*- coding: utf-8 -*-
"""原生无边框：命中测试纯函数与消息路由（离屏，不依赖真实窗口）。"""

import ctypes
from ctypes import wintypes

from player import native_frame as nf


class TestHitTest:
    W, H, PAD, CAP = 1280, 720, 8, 34

    def _ht(self, px, py, maximized=False, fullscreen=False, over_button=False):
        return nf.hit_test(px, py, self.W, self.H, self.PAD, self.CAP,
                           maximized, fullscreen, over_button)

    def test_corners(self):
        assert self._ht(2, 2) == nf.HTTOPLEFT
        assert self._ht(self.W - 2, 2) == nf.HTTOPRIGHT
        assert self._ht(2, self.H - 2) == nf.HTBOTTOMLEFT
        assert self._ht(self.W - 2, self.H - 2) == nf.HTBOTTOMRIGHT

    def test_edges(self):
        assert self._ht(2, self.H // 2) == nf.HTLEFT
        assert self._ht(self.W - 2, self.H // 2) == nf.HTRIGHT
        assert self._ht(self.W // 2, 2) == nf.HTTOP
        assert self._ht(self.W // 2, self.H - 2) == nf.HTBOTTOM

    def test_caption_and_client(self):
        assert self._ht(self.W // 2, 17) == nf.HTCAPTION
        assert self._ht(self.W // 2, 17, over_button=True) == nf.HTCLIENT
        assert self._ht(self.W // 2, self.CAP + 10) == nf.HTCLIENT

    def test_top_resize_band_beats_caption(self):
        # 标题栏顶部 pad 像素是缩放热区（Windows 惯例：边角优先）
        assert self._ht(self.W // 2, 3) == nf.HTTOP

    def test_maximized_no_resize_but_caption(self):
        assert self._ht(2, 2, maximized=True) == nf.HTCAPTION  # 客户区内缩后顶带是标题栏（可拖动还原）
        assert self._ht(self.W // 2, self.H - 2, maximized=True) == nf.HTCLIENT
        assert self._ht(self.W // 2, 17, maximized=True) == nf.HTCAPTION

    def test_fullscreen_all_client(self):
        assert self._ht(2, 2, fullscreen=True) == nf.HTCLIENT
        assert self._ht(self.W // 2, 17, fullscreen=True) == nf.HTCLIENT


class TestParseLparamPoint:
    def test_positive(self):
        assert nf.parse_lparam_point((500 << 16) | 1200) == (1200, 500)

    def test_negative_multi_monitor(self):
        lparam = (-1920 & 0xFFFF) | ((500 & 0xFFFF) << 16)
        assert nf.parse_lparam_point(lparam) == (-1920, 500)


class TestInsetForMaximized:
    def test_insets_all_sides(self):
        rc = wintypes.RECT(0, 0, 1280, 720)
        nf.inset_for_maximized(rc, 8)
        assert (rc.left, rc.top, rc.right, rc.bottom) == (8, 8, 1272, 712)


class _FakeWin:
    _acrylic_applied = False
    _sizemove_acrylic_off = False
    _native_caption_height = 34

    def __init__(self, hwnd=0x1234):
        self._hwnd = hwnd

    def winId(self):
        return self._hwnd

    def isFullScreen(self):
        return False

    def childAt(self, _pos):
        return None


def _msg(message, wparam=0, lparam=0, hwnd=0x1234) -> wintypes.MSG:
    m = wintypes.MSG()
    m.message = message
    m.wParam = wparam
    m.lParam = lparam
    m.hWnd = hwnd
    return m


class TestHandleRouting:
    def test_nccalcsize_consumed_with_zero(self):
        assert nf.handle(_FakeWin(), ctypes.addressof(
            _msg(nf.WM_NCCALCSIZE, wparam=1))) == 0

    def test_nccalcsize_wparam_false_passes_through(self):
        assert nf.handle(_FakeWin(), ctypes.addressof(
            _msg(nf.WM_NCCALCSIZE, wparam=0))) is None

    def test_hittest_invalid_hwnd_degrades(self):
        # GetWindowRect 失败（伪句柄）→ 放行，不接管不崩溃
        assert nf.handle(_FakeWin(), ctypes.addressof(
            _msg(nf.WM_NCHITTEST, lparam=(500 << 16) | 1200))) is None

    def test_foreign_hwnd_passes_through(self):
        m = _msg(nf.WM_NCHITTEST, hwnd=0x999)
        assert nf.handle(_FakeWin(), ctypes.addressof(m)) is None

    def test_unrelated_message_passes_through(self):
        assert nf.handle(_FakeWin(), ctypes.addressof(
            _msg(0x0200))) is None  # WM_MOUSEMOVE

    def test_sizemove_without_acrylic_passes_through(self):
        w = _FakeWin()
        assert nf.handle(w, ctypes.addressof(_msg(nf.WM_ENTERSIZEMOVE))) is None
        assert w._sizemove_acrylic_off is False
