"""MPV 视频渲染控件 — 把 libmpv 嵌入 PyQt6 窗口"""

import os
import ctypes

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, pyqtSignal

# 优先加载 bundled bin/ 下的 libmpv
_bin_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bin")
_libmpv_path = os.path.join(_bin_dir, "libmpv-2.dll")
if os.path.exists(_libmpv_path):
    try:
        ctypes.CDLL(_libmpv_path)
    except OSError:
        pass  # 会在 import mpv 时失败，由调用方处理

import mpv


class MpvWidget(QWidget):
    """内嵌 mpv 视频画面的 QWidget。"""

    position_changed = pyqtSignal(float)  # 当前播放位置（秒）
    duration_changed = pyqtSignal(float)  # 总时长（秒）
    paused_changed = pyqtSignal(bool)
    file_loaded = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_NativeWindow)
        self.setAttribute(Qt.WidgetAttribute.WA_DontCreateNativeAncestors)
        self.setStyleSheet("background-color: #000;")

        self._mpv = mpv.MPV(
            wid=str(int(self.winId())),
            config=False,
            keep_open=True,
            idle=True,
            osc=False,
            input_default_bindings=False,
            input_vo_keyboard=True,
            vo="gpu",
            hwdec="auto",
            cache=True,
            demuxer_max_bytes=150 * 1024 * 1024,
        )

        self._mpv.observe_property("time-pos", lambda _n, v: v is not None and self.position_changed.emit(float(v)))
        self._mpv.observe_property("duration", lambda _n, v: v is not None and self.duration_changed.emit(float(v)))
        self._mpv.observe_property("pause", lambda _n, v: self.paused_changed.emit(bool(v)))
        self._mpv.observe_property("path", lambda _n, v: v is not None and self.file_loaded.emit(str(v)))

    # ── 播放控制 ──

    def open(self, path: str) -> None:
        self._mpv.play(path)

    def play(self) -> None:
        self._mpv.pause = False

    def pause(self) -> None:
        self._mpv.pause = True

    def toggle_play(self) -> None:
        self._mpv.pause = not self._mpv.pause

    def seek(self, pos: float) -> None:
        self._mpv.time_pos = max(0, pos)

    def seek_rel(self, offset: float) -> None:
        self._mpv.time_pos = (self._mpv.time_pos or 0) + offset

    def set_volume(self, vol: int) -> None:
        self._mpv.volume = max(0, min(100, vol))

    def volume_up(self, step: int = 5) -> None:
        self.set_volume(self._mpv.volume + step)

    def volume_down(self, step: int = 5) -> None:
        self.set_volume(self._mpv.volume - step)

    def toggle_mute(self) -> None:
        self._mpv.mute = not self._mpv.mute

    # ── 属性 ──

    @property
    def time_pos(self) -> float:
        return self._mpv.time_pos or 0.0

    @property
    def duration(self) -> float:
        return self._mpv.duration or 0.0

    @property
    def is_paused(self) -> bool:
        return bool(self._mpv.pause)

    @property
    def volume(self) -> int:
        return self._mpv.volume or 100

    @property
    def is_muted(self) -> bool:
        return bool(self._mpv.mute)

    @property
    def filename(self) -> str | None:
        """当前播放的文件路径，未播放时返回 None。"""
        path = self._mpv.path
        return str(path) if path else None

    # ── 清理 ──

    def cleanup(self) -> None:
        try:
            del self._mpv
        except Exception:
            pass

