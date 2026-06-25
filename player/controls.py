"""播放控制栏 — 进度条/时间/音量/全屏"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QSlider, QLabel,
    QPushButton, QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer


def _fmt(seconds: float) -> str:
    """秒 → hh:mm:ss"""
    if seconds <= 0:
        return "0:00"
    total = int(seconds)
    h, m = divmod(total, 3600)
    m, s = divmod(m, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


class ControlsBar(QWidget):
    """底部控制栏：播放/暂停 → 进度条 → 时间 → 音量 → 全屏"""

    play_toggled = pyqtSignal()
    seeked = pyqtSignal(float)
    prev_clicked = pyqtSignal()
    next_clicked = pyqtSignal()
    volume_changed = pyqtSignal(int)
    mute_toggled = pyqtSignal()
    fullscreen_toggled = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("ControlsBar")

        self._slider_dragging = False
        self._duration: float = 0.0
        self._pending_time = (0.0, 0.0)
        self._ui_timer = QTimer(self)
        self._ui_timer.setSingleShot(True)
        self._ui_timer.timeout.connect(self._flush_time)

        self._build_ui()

    def _build_ui(self):
        self.setFixedHeight(56)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 8)
        layout.setSpacing(8)

        # ── 播放控制 ──
        self.btn_prev = QPushButton("⏮")
        self.btn_prev.setObjectName("BtnPrev")
        self.btn_prev.setFixedSize(36, 36)
        self.btn_prev.clicked.connect(self.prev_clicked)
        layout.addWidget(self.btn_prev)

        self.btn_play = QPushButton("▶")
        self.btn_play.setObjectName("BtnPlay")
        self.btn_play.setFixedSize(36, 36)
        self.btn_play.clicked.connect(self.play_toggled)
        layout.addWidget(self.btn_play)

        self.btn_next = QPushButton("⏭")
        self.btn_next.setObjectName("BtnNext")
        self.btn_next.setFixedSize(36, 36)
        self.btn_next.clicked.connect(self.next_clicked)
        layout.addWidget(self.btn_next)

        # ── 进度条 ──
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setObjectName("SeekSlider")
        self.slider.setRange(0, 10000)
        self.slider.setValue(0)
        self.slider.sliderPressed.connect(lambda: setattr(self, "_slider_dragging", True))
        self.slider.sliderReleased.connect(self._on_slider_released)
        layout.addWidget(self.slider, 1)

        # ── 时间标签 ──
        self.lbl_time = QLabel("0:00 / 0:00")
        self.lbl_time.setObjectName("TimeLabel")
        self.lbl_time.setFixedWidth(120)
        self.lbl_time.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_time)

        # ── 音量 ──
        self.btn_mute = QPushButton("🔊")
        self.btn_mute.setObjectName("BtnMute")
        self.btn_mute.setFixedSize(28, 28)
        self.btn_mute.clicked.connect(self.mute_toggled)
        layout.addWidget(self.btn_mute)

        self.vol_slider = QSlider(Qt.Orientation.Horizontal)
        self.vol_slider.setObjectName("VolSlider")
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(100)
        self.vol_slider.setFixedWidth(80)
        self.vol_slider.valueChanged.connect(lambda v: self.volume_changed.emit(v))
        layout.addWidget(self.vol_slider)

        # ── 全屏 ──
        self.btn_fs = QPushButton("⛶")
        self.btn_fs.setObjectName("BtnFullscreen")
        self.btn_fs.setFixedSize(28, 28)
        self.btn_fs.clicked.connect(self.fullscreen_toggled)
        layout.addWidget(self.btn_fs)

    # ── API ──

    def update_time(self, pos: float, duration: float) -> None:
        self._duration = duration
        if not self._slider_dragging and duration > 0:
            ratio = min(1.0, pos / duration) if duration else 0
            self.slider.setValue(int(ratio * 10000))
        self._pending_time = (pos, duration)
        self._ui_timer.start(100)

    def _flush_time(self) -> None:
        pos, duration = self._pending_time
        self.lbl_time.setText(f"{_fmt(pos)} / {_fmt(duration)}")

    def set_paused(self, paused: bool) -> None:
        self.btn_play.setText("▶" if paused else "⏸")

    def set_volume(self, vol: int) -> None:
        self.vol_slider.setValue(vol)

    def set_muted(self, muted: bool) -> None:
        self.btn_mute.setText("🔇" if muted else "🔊")

    # ── 内部 ──

    def _on_slider_released(self):
        self._slider_dragging = False
        ratio = self.slider.value() / 10000.0
        self.seeked.emit(ratio * self._duration)
