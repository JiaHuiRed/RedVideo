"""macOS 风格自定义标题栏 — 交通灯按钮 + 拖拽移动"""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel
from PyQt6.QtCore import Qt, QPoint, pyqtSignal
from PyQt6.QtGui import QPainter, QColor

TRAFFIC_SIZE = 12
TRAFFIC_MARGIN = 8
TITLEBAR_HEIGHT = 34

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

    def __init__(self, title: str = "RedVideo", version: str = "", parent=None):
        super().__init__(parent)
        self.setFixedHeight(TITLEBAR_HEIGHT)
        self.setObjectName("Titlebar")

        self._drag_pos = QPoint()
        self._dragging = False

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

        # 版本标签
        if version:
            self.version_label = QLabel(f"v{version}")
            self.version_label.setObjectName("VersionLabel")
            layout.addSpacing(6)
            layout.addWidget(self.version_label)

        # 标题
        self.title_label = QLabel(title)
        self.title_label.setObjectName("TitleLabel")
        layout.addSpacing(12)
        layout.addWidget(self.title_label, 1, Qt.AlignmentFlag.AlignLeft)

    def set_title(self, text: str):
        self.title_label.setText(text)

    # ── 窗口拖拽 ──

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint()
            self._dragging = True
            event.accept()

    def mouseMoveEvent(self, event):
        if self._dragging and event.buttons() == Qt.MouseButton.LeftButton:
            win = self.window()
            if win.isMaximized() or win.isFullScreen():
                return
            delta = event.globalPosition().toPoint() - self._drag_pos
            win.move(win.x() + delta.x(), win.y() + delta.y())
            self._drag_pos = event.globalPosition().toPoint()
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.maximize_clicked.emit()
            event.accept()
