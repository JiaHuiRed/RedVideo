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
