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
