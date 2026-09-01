"""播放控制栏 — 进度条/时间/音量/全屏/倍速/置顶"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QSlider, QLabel,
    QPushButton, QStyle, QStyleOptionSlider,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer

from .icons import IconButton, palette_for


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


class SeekSlider(QSlider):
    """支持单击跳转的进度条 — 点击凹槽直接跳到该位置，随后可继续拖拽。

    原生 QSlider 点击凹槽只走一个 page step 且不触发 sliderPressed/Released，
    导致单击进度条无法 seek；这里在按下时把值设到点击处，把手会落到光标下，
    之后的按下/拖拽/释放全部走原生流程。
    """

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            opt = QStyleOptionSlider()
            self.initStyleOption(opt)
            st = self.style()
            groove = st.subControlRect(QStyle.ComplexControl.CC_Slider, opt,
                                       QStyle.SubControl.SC_SliderGroove, self)
            handle = st.subControlRect(QStyle.ComplexControl.CC_Slider, opt,
                                       QStyle.SubControl.SC_SliderHandle, self)
            if groove.isValid() and groove.width() > handle.width():
                self.setValue(QStyle.sliderValueFromPosition(
                    self.minimum(), self.maximum(),
                    int(event.position().x()) - groove.x() - handle.width() // 2,
                    groove.width() - handle.width()))
        super().mousePressEvent(event)


class ControlsBar(QWidget):
    """底部控制栏：播放/暂停 → 进度条 → 时间 → 音量 → 倍速 → 置顶 → 全屏"""

    play_toggled = pyqtSignal()
    seeked = pyqtSignal(float)
    prev_clicked = pyqtSignal()
    next_clicked = pyqtSignal()
    volume_changed = pyqtSignal(int)
    mute_toggled = pyqtSignal()
    fullscreen_toggled = pyqtSignal()
    speed_changed = pyqtSignal(float)
    always_on_top_toggled = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("ControlsBar")

        self._slider_dragging = False
        self._duration: float = 0.0
        self._pending_time = (0.0, 0.0)
        self._speed: float = 1.0
        self._preview_mode = False
        self._ui_timer = QTimer(self)
        self._ui_timer.setSingleShot(True)
        self._ui_timer.timeout.connect(self._flush_time)

        self._build_ui()

    def _build_ui(self):
        self.setFixedHeight(56)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 8)
        layout.setSpacing(8)

        # ── 播放控制（播放键是主角：40px 圆形，其余 32px 幽灵）──
        self.btn_prev = IconButton("prev", px=18)
        self.btn_prev.setObjectName("BtnPrev")
        self.btn_prev.setFixedSize(32, 32)
        self.btn_prev.clicked.connect(self.prev_clicked)
        layout.addWidget(self.btn_prev)

        self.btn_play = IconButton("play", px=20)
        self.btn_play.setObjectName("BtnPlay")
        self.btn_play.setFixedSize(40, 40)
        self.btn_play.clicked.connect(self.play_toggled)
        layout.addWidget(self.btn_play)

        self.btn_next = IconButton("next", px=18)
        self.btn_next.setObjectName("BtnNext")
        self.btn_next.setFixedSize(32, 32)
        self.btn_next.clicked.connect(self.next_clicked)
        layout.addWidget(self.btn_next)

        # ── 进度条 ──
        self.slider = SeekSlider(Qt.Orientation.Horizontal)
        self.slider.setObjectName("SeekSlider")
        self.slider.setRange(0, 10000)
        self.slider.setValue(0)
        self.slider.sliderPressed.connect(lambda: setattr(self, "_slider_dragging", True))
        self.slider.sliderReleased.connect(self._on_slider_released)
        self.slider.valueChanged.connect(self._on_slider_moved)
        layout.addWidget(self.slider, 1)

        # ── 时间标签 ──
        self.lbl_time = QLabel("0:00 / 0:00")
        self.lbl_time.setObjectName("TimeLabel")
        self.lbl_time.setFixedWidth(120)
        self.lbl_time.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_time)

        # ── 音量 ──
        self.btn_mute = IconButton("volume", px=16)
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

        # ── 倍速 ──
        self.btn_speed = QPushButton("1.0x")
        self.btn_speed.setObjectName("BtnSpeed")
        self.btn_speed.setFixedSize(42, 28)
        self.btn_speed.clicked.connect(self._cycle_speed)
        layout.addWidget(self.btn_speed)

        # ── 置顶（激活时图标转主题强调色，QSS 加底色）──
        self.btn_pin = IconButton("pin", px=16)
        self.btn_pin.setObjectName("BtnPin")
        self.btn_pin.setFixedSize(28, 28)
        self.btn_pin.setCheckable(True)
        self.btn_pin.clicked.connect(self.always_on_top_toggled.emit)
        layout.addWidget(self.btn_pin)

        # ── 全屏 ──
        self.btn_fs = IconButton("fullscreen", px=16)
        self.btn_fs.setObjectName("BtnFullscreen")
        self.btn_fs.setFixedSize(28, 28)
        self.btn_fs.clicked.connect(self.fullscreen_toggled)
        layout.addWidget(self.btn_fs)

        # 按钮不抢焦点：避免点过按钮后空格同时触发快捷键和按钮（双触发）
        for btn in (self.btn_prev, self.btn_play, self.btn_next, self.btn_mute,
                    self.btn_speed, self.btn_pin, self.btn_fs):
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.apply_icon_theme("night")  # 主窗口创建后会按实际主题再调一次

    # ── API ──

    def update_time(self, pos: float, duration: float) -> None:
        self._duration = duration
        if self._preview_mode:
            return
        self._pending_time = (pos, duration)
        # 单次定时器活跃时不重置：高频率 tick 不会把节流饿死，且最多 100ms 刷一次
        if not self._ui_timer.isActive():
            self._ui_timer.start(100)

    def _flush_time(self) -> None:
        pos, duration = self._pending_time
        self.lbl_time.setText(f"{_fmt(pos)} / {_fmt(duration)} · {self._speed:.1f}x")
        # 进度条也并入 100ms 节流，避免短视频下每帧重绘
        if duration > 0 and not self._slider_dragging:
            self.slider.setValue(int(min(1.0, pos / duration) * 10000))

    def set_paused(self, paused: bool) -> None:
        self.btn_play.set_icon_name("play" if paused else "pause")

    def set_volume(self, vol: int) -> None:
        self.vol_slider.setValue(vol)

    def set_muted(self, muted: bool) -> None:
        self.btn_mute.set_icon_name("volume_muted" if muted else "volume")

    def set_speed(self, speed: float) -> None:
        self._speed = max(0.5, min(2.0, speed))
        self.btn_speed.setText(f"{self._speed:.1f}x")
        self.speed_changed.emit(self._speed)

    def set_always_on_top(self, checked: bool) -> None:
        self.btn_pin.setChecked(checked)
        self.btn_pin.set_active(checked)

    def apply_icon_theme(self, theme: str) -> None:
        """主题切换时同步图标配色（accent 与该主题 QSS 强调色一致）。"""
        pal = palette_for(theme)
        for btn in (self.btn_prev, self.btn_play, self.btn_next, self.btn_mute,
                    self.btn_pin, self.btn_fs):
            btn.set_colors(pal["base"], pal["hover"], pal["accent"])

    def _cycle_speed(self):
        nxt = round(self._speed + 0.1, 1)
        if nxt > 2.0:
            nxt = 0.5
        self.set_speed(nxt)

    # ── 内部 ──

    def _on_slider_moved(self, value: int) -> None:
        if not self._slider_dragging or not self._duration:
            return
        self._preview_mode = True
        preview = (value / 10000.0) * self._duration
        self.lbl_time.setText(f"{_fmt(preview)} / {_fmt(self._duration)} · {self._speed:.1f}x")

    def _on_slider_released(self):
        self._slider_dragging = False
        self._preview_mode = False
        ratio = self.slider.value() / 10000.0
        self.seeked.emit(ratio * self._duration)
