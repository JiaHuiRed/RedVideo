"""macOS 风格自定义标题栏 — 交通灯按钮 + 拖拽移动"""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel, QApplication
from PyQt6.QtCore import Qt, QPoint, QTimer, pyqtSignal
from PyQt6.QtGui import QPainter, QColor
from player.windows_effects import disable_acrylic, enable_acrylic

TRAFFIC_SIZE = 12
TRAFFIC_MARGIN = 8
TITLEBAR_HEIGHT = 34
DRAG_INTERVAL_MS = 8

# macOS 交通灯颜色
COLOR_CLOSE = "#ff5f56"
COLOR_MINIMIZE = "#ffbd2e"
COLOR_MAXIMIZE = "#27c93f"


class TrafficButton(QPushButton):
    """单个交通灯按钮（纯色圆点，无 hover 图标）。"""

    def __init__(self, color: str):
        super().__init__()
        self._color = color
        self.setFixedSize(TRAFFIC_SIZE, TRAFFIC_SIZE)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setObjectName("TrafficButton")

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor(self._color))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(self.rect())
        p.end()


class Titlebar(QWidget):
    """自定义标题栏，左侧交通灯按钮，可拖拽移动。"""

    close_clicked = pyqtSignal()
    minimize_clicked = pyqtSignal()
    maximize_clicked = pyqtSignal()

    def __init__(self, title: str = "RedVideo", parent=None):
        super().__init__(parent)
        self.setFixedHeight(TITLEBAR_HEIGHT)
        self.setObjectName("Titlebar")

        self._dragging = False
        self._drag_offset: QPoint | None = None
        self._pending_global_pos: QPoint | None = None
        self._acrylic_was_applied = False
        self._drag_timer = QTimer(self)
        self._drag_timer.setInterval(DRAG_INTERVAL_MS)
        self._drag_timer.timeout.connect(self._flush_drag)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(TRAFFIC_MARGIN, 0, TRAFFIC_MARGIN, 0)
        layout.setSpacing(TRAFFIC_MARGIN)
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        # 交通灯（纯色圆，无图标）
        self.btn_close = TrafficButton(COLOR_CLOSE)
        self.btn_minimize = TrafficButton(COLOR_MINIMIZE)
        self.btn_maximize = TrafficButton(COLOR_MAXIMIZE)

        self.btn_close.clicked.connect(self.close_clicked.emit)
        self.btn_minimize.clicked.connect(self.minimize_clicked.emit)
        self.btn_maximize.clicked.connect(self.maximize_clicked.emit)

        layout.addWidget(self.btn_close)
        layout.addWidget(self.btn_minimize)
        layout.addWidget(self.btn_maximize)

        # 标题
        self.title_label = QLabel(title)
        self.title_label.setObjectName("TitleLabel")
        layout.addSpacing(12)
        layout.addWidget(self.title_label, 1, Qt.AlignmentFlag.AlignLeft)

    def set_title(self, text: str):
        self.title_label.setText(text)

    # ── 窗口拖拽 ──

    def _move_to_pending(self) -> None:
        if self._drag_offset is None or self._pending_global_pos is None:
            return
        self.window().move(self._pending_global_pos - self._drag_offset)

    def _flush_drag(self) -> None:
        if not self._dragging or self._drag_offset is None or self._pending_global_pos is None:
            return
        if not (QApplication.mouseButtons() & Qt.MouseButton.LeftButton):
            self._stop_drag()
            return
        self._move_to_pending()

    def _stop_drag(self, flush: bool = False) -> None:
        if not self._dragging:
            return
        if flush:
            self._move_to_pending()
        restore_acrylic = self._acrylic_was_applied
        self._dragging = False
        self._drag_offset = None
        self._pending_global_pos = None
        self._acrylic_was_applied = False
        self._drag_timer.stop()
        self.releaseMouse()
        if restore_acrylic:
            win = self.window()
            enable_acrylic(int(win.winId()), dark_tint=getattr(win, "_theme", "night") != "day")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            win = self.window()
            if win.isMaximized() or win.isFullScreen():
                return
            global_pos = event.globalPosition().toPoint()
            if getattr(win, "_acrylic_applied", False):
                self._acrylic_was_applied = disable_acrylic(int(win.winId()))
            self._drag_offset = global_pos - win.frameGeometry().topLeft()
            self._pending_global_pos = global_pos
            self._dragging = True
            self.grabMouse()
            self._drag_timer.start()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._dragging and not (QApplication.mouseButtons() & Qt.MouseButton.LeftButton):
            self._stop_drag()
            event.accept()
            return
        if self._dragging and event.buttons() & Qt.MouseButton.LeftButton:
            self._pending_global_pos = event.globalPosition().toPoint()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._dragging:
            self._stop_drag()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._stop_drag()
            self.maximize_clicked.emit()
            event.accept()
