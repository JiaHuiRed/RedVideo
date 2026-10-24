"""播放控制栏 — 进度条/时间/音量/全屏/倍速/置顶"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QSlider, QLabel,
    QPushButton, QStyle, QStyleOptionSlider, QMenu, QToolTip,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPoint
from PyQt6.QtGui import QAction, QActionGroup

from .icons import IconButton, palette_for

# 倍速菜单档位（键盘 [/] 仍可 0.1 微调，边界同 set_speed 钳制 0.5–2.0）
SPEED_PRESETS = (0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0)


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


def _fmt_speed(v: float) -> str:
    """倍速显示统一格式：0.5 → '0.5x'，0.75 → '0.75x'，1.0 → '1.0x'。"""
    s = f"{v:.2f}".rstrip("0")
    if s.endswith("."):
        s += "0"
    return s + "x"


class SeekSlider(QSlider):
    """支持单击跳转与悬停时间提示的进度条 — 点击凹槽直接跳到该位置，随后可继续拖拽。

    原生 QSlider 点击凹槽只走一个 page step 且不触发 sliderPressed/Released，
    导致单击进度条无法 seek；这里在按下时把值设到点击处，把手会落到光标下，
    之后的按下/拖拽/释放全部走原生流程。
    """

    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self._total = 0.0  # 悬停提示换算用总时长（仅正值更新）
        self.setMouseTracking(True)

    def set_total(self, seconds: float) -> None:
        if seconds > 0:
            self._total = seconds

    def _value_at(self, x: int) -> int:
        """光标横坐标 → 滑块值（按凹槽几何换算，跳过手柄宽度更贴合点击处）。"""
        opt = QStyleOptionSlider()
        self.initStyleOption(opt)
        st = self.style()
        groove = st.subControlRect(QStyle.ComplexControl.CC_Slider, opt,
                                   QStyle.SubControl.SC_SliderGroove, self)
        handle = st.subControlRect(QStyle.ComplexControl.CC_Slider, opt,
                                   QStyle.SubControl.SC_SliderHandle, self)
        if groove.isValid() and groove.width() > handle.width():
            return QStyle.sliderValueFromPosition(
                self.minimum(), self.maximum(),
                x - groove.x() - handle.width() // 2,
                groove.width() - handle.width())
        return self.value()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.setValue(self._value_at(int(event.position().x())))
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._total > 0:
            ratio = self._value_at(int(event.position().x())) / self.maximum()
            pos = max(0.0, min(1.0, ratio)) * self._total
            QToolTip.showText(event.globalPosition().toPoint(), _fmt(pos), self)
        super().mouseMoveEvent(event)


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
    always_on_top_toggled = pyqtSignal(bool)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("ControlsBar")

        self._slider_dragging = False
        self._duration: float = 0.0
        self._pending_time = (0.0, 0.0)
        self._speed: float = 1.0
        self._preview_mode = False
        self._finished = False  # EOF 后钉住终点显示，忽略 mpv 归零 tick
        self._ui_timer = QTimer(self)
        self._ui_timer.setSingleShot(True)
        self._ui_timer.timeout.connect(self._flush_time)

        self._build_ui()

    def _build_ui(self):
        self.setFixedHeight(56)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 8)
        # 组内 6px、组间再叠加 10px：传输 | 进度 | 时间 | 音量 | 附加 五组
        layout.setSpacing(6)

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
        layout.addSpacing(10)  # ── 传输 | 进度 ──

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
        layout.addSpacing(10)  # ── 进度 | 音量 ──

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
        layout.addSpacing(10)  # ── 音量 | 附加 ──

        # ── 倍速 ──
        self.btn_speed = QPushButton(_fmt_speed(1.0))
        self.btn_speed.setObjectName("BtnSpeed")
        self.btn_speed.setFixedSize(42, 28)
        self.btn_speed.clicked.connect(self._show_speed_menu)
        layout.addWidget(self.btn_speed)

        # ── 置顶（激活时图标转主题强调色，QSS 加底色）──
        self.btn_pin = IconButton("pin", px=16)
        self.btn_pin.setObjectName("BtnPin")
        self.btn_pin.setFixedSize(28, 28)
        self.btn_pin.setCheckable(True)
        self.btn_pin.toggled.connect(self.always_on_top_toggled.emit)
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
        self.slider.set_total(duration)
        if self._preview_mode:
            return
        if self._finished and duration <= 0:
            return  # EOF 后 mpv 的归零 tick 不把显示刷回起点
        self._finished = False
        self._pending_time = (pos, duration)
        # 单次定时器活跃时不重置：高频率 tick 不会把节流饿死，且最多 100ms 刷一次
        if not self._ui_timer.isActive():
            self._ui_timer.start(100)

    def _flush_time(self) -> None:
        pos, duration = self._pending_time
        self.lbl_time.setText(f"{_fmt(pos)} / {_fmt(duration)} · {_fmt_speed(self._speed)}")
        # 进度条也并入 100ms 节流，避免短视频下每帧重绘
        if duration > 0 and not self._slider_dragging:
            self.slider.setValue(int(min(1.0, pos / duration) * 10000))

    def set_paused(self, paused: bool) -> None:
        self.btn_play.set_icon_name("play" if paused else "pause")

    def set_finished(self, duration: float) -> None:
        """EOF 后把进度条与时间标签钉在终点。

        keep_open 下 mpv 停在最后一帧，time-pos 略小于 duration，
        直接按比例算滑块会差一截到头；这里显式补满。
        """
        if duration <= 0:
            return
        self._duration = duration
        self._pending_time = (duration, duration)
        self._finished = True
        self.slider.set_total(duration)
        self.slider.setValue(self.slider.maximum())
        self.lbl_time.setText(
            f"{_fmt(duration)} / {_fmt(duration)} · {_fmt_speed(self._speed)}")

    def set_volume(self, vol: int) -> None:
        # 程序化设值不回发 volume_changed：回环会经窗口连接反向再写一次 mpv
        self.vol_slider.blockSignals(True)
        self.vol_slider.setValue(vol)
        self.vol_slider.blockSignals(False)

    def set_muted(self, muted: bool) -> None:
        self.btn_mute.set_icon_name("volume_muted" if muted else "volume")

    def set_speed(self, speed: float) -> None:
        self._speed = max(0.5, min(2.0, speed))
        self.btn_speed.setText(_fmt_speed(self._speed))
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

    def _build_speed_menu(self) -> QMenu:
        menu = QMenu(self)
        group = QActionGroup(menu)
        group.setExclusive(True)
        for s in SPEED_PRESETS:
            act = QAction(_fmt_speed(s), menu)
            act.setCheckable(True)
            act.setChecked(abs(s - self._speed) < 1e-6)
            act.triggered.connect(lambda checked, v=s: self.set_speed(v))
            group.addAction(act)
            menu.addAction(act)
        return menu

    def _show_speed_menu(self):
        """倍速菜单在按钮上方弹出（控制栏贴窗口底，向下会出屏）。"""
        menu = self._build_speed_menu()
        pos = self.btn_speed.mapToGlobal(QPoint(0, -menu.sizeHint().height() - 4))
        menu.exec(pos)

    # ── 内部 ──

    def _on_slider_moved(self, value: int) -> None:
        if not self._slider_dragging or not self._duration:
            return
        self._preview_mode = True
        preview = (value / 10000.0) * self._duration
        self.lbl_time.setText(
            f"{_fmt(preview)} / {_fmt(self._duration)} · {_fmt_speed(self._speed)}")

    def _on_slider_released(self):
        self._slider_dragging = False
        self._preview_mode = False
        ratio = self.slider.value() / 10000.0
        self.seeked.emit(ratio * self._duration)
