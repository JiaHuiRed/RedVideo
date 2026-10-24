# -*- coding: utf-8 -*-
"""RV-001: 零音量是合法值，不能被 `or 100` 回退成 100。"""

from player.mpv_widget import MpvWidget


class FakeMPV:
    """只实现 MpvWidget 属性/控制用到的 mpv 接口，不碰真 libmpv。"""

    def __init__(self, volume=None, speed=1.0, pause=False, mute=False,
                 time_pos=0.0, duration=0.0, path=None):
        self.volume = volume
        self.speed = speed
        self.pause = pause
        self.mute = mute
        self.time_pos = time_pos
        self.duration = duration
        self.path = path


def _widget(**kwargs) -> MpvWidget:
    w = MpvWidget.__new__(MpvWidget)  # 绕过 __init__（真 MPV 需要窗口），只测属性逻辑
    w._mpv = FakeMPV(**kwargs)
    return w


class TestVolumeProperty:
    def test_zero_stays_zero(self):
        assert _widget(volume=0).volume == 0

    def test_zero_float_stays_zero(self):
        assert _widget(volume=0.0).volume == 0

    def test_none_falls_back_to_100(self):
        assert _widget(volume=None).volume == 100

    def test_normal_values_pass_through(self):
        assert _widget(volume=1).volume == 1
        assert _widget(volume=50).volume == 50
        assert _widget(volume=100).volume == 100

    def test_out_of_range_clamped(self):
        assert _widget(volume=150).volume == 100
        assert _widget(volume=-5).volume == 0


class TestVolumeControl:
    def test_set_volume_clamps(self):
        w = _widget()
        w.set_volume(150)
        assert w._mpv.volume == 100
        w.set_volume(-5)
        assert w._mpv.volume == 0

    def test_volume_up_from_zero(self):
        w = _widget(volume=0)
        w.volume_up()
        assert w.volume == 5

    def test_volume_down_floor(self):
        w = _widget(volume=3)
        w.volume_down()
        assert w.volume == 0


# ── 0.6.0：time-pos 跨线程信号节流 ──

from player.mpv_widget import _POS_MIN_INTERVAL, _POS_JUMP


def _throttle_widget() -> MpvWidget:
    w = MpvWidget.__new__(MpvWidget)
    w._last_pos = 0.0
    w._last_pos_emit = 0.0
    return w


class TestPosThrottle:
    def test_first_tick_immediate(self):
        w = _throttle_widget()
        assert w._should_emit_pos(5.0, now=0.01) is True  # 跳变（首帧）立即投递

    def test_frame_within_window_dropped(self):
        w = _throttle_widget()
        w._last_pos, w._last_pos_emit = 10.0, 100.0
        assert w._should_emit_pos(10.05, now=100.0 + _POS_MIN_INTERVAL / 2) is False

    def test_frame_after_window_passes(self):
        w = _throttle_widget()
        w._last_pos, w._last_pos_emit = 10.0, 100.0
        assert w._should_emit_pos(10.16, now=100.0 + _POS_MIN_INTERVAL * 2) is True

    def test_seek_jump_bypasses_window(self):
        w = _throttle_widget()
        w._last_pos, w._last_pos_emit = 10.0, 100.0
        assert (w._should_emit_pos(10.0 + _POS_JUMP + 1, now=100.0 + 0.01)
                is True)  # seek 落点不等窗口

    def test_jump_threshold_is_exact(self):
        w = _throttle_widget()
        w._last_pos, w._last_pos_emit = 10.0, 100.0
        assert w._should_emit_pos(10.0 + _POS_JUMP, now=100.0 + 0.01) is False


class TestSpeedClamp:
    def test_unified_range(self):
        w = _widget()
        w.set_speed(5.0)
        assert w._mpv.speed == 2.0
        w.set_speed(0.1)
        assert w._mpv.speed == 0.5
