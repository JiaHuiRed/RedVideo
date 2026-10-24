# -*- coding: utf-8 -*-
"""EOF 后进度条/时间标签钉终点（真机截图发现：播完进度条差一截不到头）。"""

import pytest

from player.controls import ControlsBar


@pytest.fixture
def bar(qapp):
    b = ControlsBar()
    yield b
    b.deleteLater()


def test_set_finished_pins_slider_and_label(bar):
    bar.update_time(1.0, 2.0)
    bar._flush_time()
    bar.set_finished(2.816)
    assert bar.slider.value() == bar.slider.maximum()
    assert bar.lbl_time.text() == "0:02 / 0:02 · 1.0x"


def test_zero_tick_after_finish_ignored(bar):
    bar.set_finished(2.816)
    bar.update_time(0.0, 0.0)  # EOF 后 mpv 的归零 tick
    assert bar._finished is True
    bar._flush_time()
    assert bar.slider.value() == bar.slider.maximum()
    assert bar.lbl_time.text() == "0:02 / 0:02 · 1.0x"


def test_new_file_restores_live_updates(bar):
    bar.set_finished(2.816)
    bar.update_time(0.5, 3.0)  # 新文件加载：duration 正值，恢复实时刷新
    assert bar._finished is False
    bar._flush_time()
    assert bar.lbl_time.text() == "0:00 / 0:03 · 1.0x"
    assert bar.slider.value() == int(0.5 / 3.0 * 10000)


def test_seek_after_finish_restores_live_updates(bar):
    bar.set_finished(2.816)
    bar.update_time(1.0, 2.816)  # EOF 后 seek 回中间重看
    assert bar._finished is False
    bar._flush_time()
    assert bar.slider.value() == int(1.0 / 2.816 * 10000)


def test_duration_cache_ignores_eof_zero(qapp):
    """EOF 时 mpv 先归零 duration：缓存不能被刷掉，否则 set_finished 拿到 0。"""
    from player.window import MainWindow

    class FakeControls:
        def __init__(self):
            self.calls = []

        def update_time(self, pos, dur):
            self.calls.append((pos, dur))

    class FakeMPV:
        time_pos = 0.0

    w = MainWindow.__new__(MainWindow)
    w._duration = 0.0
    w.mpv = FakeMPV()
    fc = FakeControls()
    w.controls = fc

    w._on_duration_changed(2.666)
    w._on_duration_changed(0.0)  # EOF 归零 tick
    assert w._duration == 2.666  # 缓存保留最后有效时长
    assert fc.calls == [(0.0, 2.666), (0.0, 0.0)]  # 归零 tick 仍下发给控件防护


# ── 0.6.0：进度条悬停提示 / 倍速菜单 / 音量回环 ──

from player.controls import SeekSlider, _fmt_speed, SPEED_PRESETS


def test_speed_label_format():
    assert _fmt_speed(0.5) == "0.5x"
    assert _fmt_speed(0.75) == "0.75x"
    assert _fmt_speed(1.0) == "1.0x"
    assert _fmt_speed(1.25) == "1.25x"
    assert _fmt_speed(2.0) == "2.0x"


def test_set_speed_clamps_to_unified_range(bar):
    got = []
    bar.speed_changed.connect(got.append)
    bar.set_speed(5.0)
    assert bar._speed == 2.0
    bar.set_speed(0.1)
    assert bar._speed == 0.5
    assert got == [2.0, 0.5]
    assert bar.btn_speed.text() == "0.5x"


def test_slider_total_ignores_nonpositive(bar):
    bar.slider.set_total(120.0)
    bar.slider.set_total(0.0)  # EOF 归零 tick 不清掉悬停换算的总时长
    assert bar.slider._total == 120.0


def test_programmatic_volume_no_signal_echo(bar):
    """程序化设音量不得回发 volume_changed（回环会反向再写一次 mpv）。"""
    got = []
    bar.volume_changed.connect(got.append)
    bar.set_volume(42)
    assert got == []
    bar.vol_slider.setValue(80)  # 用户拖动路径照常发信号
    assert got == [80]


def test_speed_menu_builds_presets_and_triggers(bar):
    menu = bar._build_speed_menu()
    acts = menu.actions()
    assert [a.text() for a in acts] == [_fmt_speed(s) for s in SPEED_PRESETS]
    assert acts[2].isChecked()  # 默认 1.0x 勾选

    got = []
    bar.speed_changed.connect(got.append)
    acts[1].trigger()  # 0.75x
    assert bar._speed == 0.75
    assert got == [0.75]
    assert bar.btn_speed.text() == "0.75x"


def test_seekslider_value_at_maps_groove(qapp):
    from PyQt6.QtCore import Qt
    s = SeekSlider(Qt.Orientation.Horizontal)
    s.setRange(0, 10000)
    s.resize(200, 20)
    mid = s._value_at(100)
    assert 0 <= mid <= 10000  # 无凹槽几何（未布局）时回退当前值不崩溃
