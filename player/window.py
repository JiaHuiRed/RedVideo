"""RedVideo 主窗口 — 无框 + 缩放 + 毛玻璃 + 主题切换"""

import sys
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout,
    QFileDialog, QSplitter, QMenu, QToolButton, QApplication,
    QStyle,
)
from PyQt6.QtCore import Qt, QTimer, QRect, QPoint
from PyQt6.QtGui import (
    QDragEnterEvent, QDropEvent, QAction, QActionGroup, QMouseEvent, QCursor,
)

from player.mpv_widget import MpvWidget
from player.controls import ControlsBar
from player.playlist import PlaylistPanel
from player.shortcuts import Shortcuts
from player.titlebar import Titlebar, TITLEBAR_HEIGHT
from player.windows_effects import enable_acrylic

RESIZE_MARGIN = 6


def _base() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


THEMES_DIR = _base() / "resources" / "themes"
THEME_NAMES = {"night": "夜间", "day": "日间", "deepblue": "深蓝"}
THEME_LIST = list(THEME_NAMES)


def apply_theme(name: str) -> None:
    """加载主题 QSS 并应用到全局。"""
    path = THEMES_DIR / f"{name}.qss"
    if not path.exists():
        return
    app = QApplication.instance()
    if app is None:
        return
    with open(path, encoding="utf-8") as f:
        app.setStyleSheet(f.read())


class MainWindow(QMainWindow):
    """RedVideo 主窗口 — 无框窗口 + macOS 风格标题栏 + 毛玻璃 + 四边缩放。"""

    def __init__(self, theme: str = "night", file_path: str | None = None):
        super().__init__()
        self._theme = theme
        self._startup_file = file_path

        # ── 无框窗口 ──
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setMinimumSize(800, 500)
        self.resize(1280, 720)
        self.setAcceptDrops(True)
        self.setMouseTracking(True)

        self._playlist_visible = True
        self._acrylic_applied = False
        self._root_layout = None

        # 缩放状态
        self._resizing = False
        self._resize_dir: set[str] = set()
        self._drag_pos: QPoint | None = None
        self._start_geo: QRect | None = None

        # 双击标题栏最大化
        self._maximized_before_full = self.isMaximized()

        apply_theme(self._theme)

        self._build_titlebar()
        self._build_ui()
        self._connect_signals()

        self._position_timer = QTimer(self)
        self._position_timer.setInterval(250)
        self._position_timer.timeout.connect(self._poll_position)
        self._position_timer.start()

        Shortcuts(self)

        # 从命令行传入的视频路径（Windows 打开方式）
        if self._startup_file:
            self.playlist.add_files([self._startup_file])
            self._play_file(self._startup_file)

    # ── 缩放 ──

    def _get_resize_dir(self, pos: QPoint) -> set[str]:
        """返回鼠标位置 pos 对应的缩放方向集合。"""
        if self.isMaximized() or self.isFullScreen():
            return set()
        r: set[str] = set()
        if pos.x() <= RESIZE_MARGIN:
            r.add("left")
        if pos.x() >= self.width() - RESIZE_MARGIN:
            r.add("right")
        if pos.y() <= RESIZE_MARGIN:
            r.add("top")
        if pos.y() >= self.height() - RESIZE_MARGIN:
            r.add("bottom")
        return r

    def _update_cursor(self, pos: QPoint) -> None:
        dir = self._get_resize_dir(pos)
        if not dir:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        elif dir in ({"top", "left"}, {"bottom", "right"}):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif dir in ({"top", "right"}, {"bottom", "left"}):
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        elif "top" in dir or "bottom" in dir:
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        else:
            self.setCursor(Qt.CursorShape.SizeHorCursor)

    def mousePressEvent(self, event: QMouseEvent | None) -> None:
        if event is None:
            return
        if event.button() == Qt.MouseButton.LeftButton:
            dir = self._get_resize_dir(event.pos())
            if dir:
                self._resizing = True
                self._resize_dir = dir
                self._drag_pos = event.globalPosition().toPoint()
                self._start_geo = QRect(self.geometry())
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent | None) -> None:
        if event is None:
            return
        if self._resizing and self._resize_dir and self._drag_pos and self._start_geo:
            delta = event.globalPosition().toPoint() - self._drag_pos
            geo = QRect(self._start_geo)
            if "left" in self._resize_dir:
                geo.setLeft(geo.left() + delta.x())
            if "right" in self._resize_dir:
                geo.setRight(geo.right() + delta.x())
            if "top" in self._resize_dir:
                geo.setTop(geo.top() + delta.y())
            if "bottom" in self._resize_dir:
                geo.setBottom(geo.bottom() + delta.y())
            if geo.width() >= self.minimumWidth() and geo.height() >= self.minimumHeight():
                self.setGeometry(geo)
            event.accept()
            return
        self._update_cursor(event.pos())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent | None) -> None:
        if event is None:
            return
        if self._resizing:
            self._resizing = False
            self._resize_dir = set()
            self._drag_pos = None
            self._start_geo = None
            event.accept()
            return
        super().mouseReleaseEvent(event)

    # ── 主题 ──

    def switch_theme(self, name: str) -> None:
        if name not in THEME_NAMES:
            return
        self._theme = name
        apply_theme(name)

    # ── 构建 UI ──

    def _build_titlebar(self):
        self.titlebar = Titlebar("RedVideo")
        self.titlebar.close_clicked.connect(self.close)
        self.titlebar.minimize_clicked.connect(self.showMinimized)
        self.titlebar.maximize_clicked.connect(self._toggle_maximize)

        menu_btn = QToolButton()
        menu_btn.setObjectName("MenuButton")
        menu_btn.setArrowType(Qt.ArrowType.DownArrow)
        menu_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu_btn.setCursor(Qt.CursorShape.ArrowCursor)

        menu = QMenu(menu_btn)

        # 文件
        act_open = QAction("打开文件...", self)
        act_open.setShortcut("Ctrl+O")
        act_open.triggered.connect(self.open_file)
        menu.addAction(act_open)

        act_open_dir = QAction("打开文件夹...", self)
        act_open_dir.triggered.connect(self._open_directory)
        menu.addAction(act_open_dir)

        menu.addSeparator()

        # 播放列表开关
        act_toggle_pl = QAction("播放列表", self)
        act_toggle_pl.setShortcut("Ctrl+I")
        act_toggle_pl.setCheckable(True)
        act_toggle_pl.setChecked(True)
        act_toggle_pl.triggered.connect(self.toggle_playlist)
        menu.addAction(act_toggle_pl)

        menu.addSeparator()

        # 主题切换
        theme_menu = menu.addMenu("主题")
        theme_group = QActionGroup(self)
        theme_group.setExclusive(True)
        self._theme_actions: dict[str, QAction] = {}
        for name in THEME_LIST:
            act = QAction(THEME_NAMES[name], self)
            act.setCheckable(True)
            act.setChecked(name == self._theme)
            act.triggered.connect(lambda checked, n=name: self.switch_theme(n))
            theme_group.addAction(act)
            theme_menu.addAction(act)
            self._theme_actions[name] = act

        menu.addSeparator()

        act_close = QAction("退出", self)
        act_close.setShortcut("Ctrl+Q")
        act_close.triggered.connect(self.close)
        menu.addAction(act_close)

        menu_btn.setMenu(menu)
        self.titlebar.layout().addWidget(menu_btn)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        self._root_layout = QVBoxLayout(central)
        self._root_layout.setContentsMargins(1, 0, 1, 1)
        self._root_layout.setSpacing(0)
        root = self._root_layout

        root.addWidget(self.titlebar)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("MainSplitter")
        splitter.setHandleWidth(1)

        self.video_container = QWidget()
        self.video_container.setObjectName("VideoContainer")
        vl = QVBoxLayout(self.video_container)
        vl.setContentsMargins(0, 0, 0, 0)

        self.mpv = MpvWidget()
        vl.addWidget(self.mpv, 1)

        self.placeholder = QWidget()
        self.placeholder.setObjectName("Placeholder")
        vl.addWidget(self.placeholder)

        splitter.addWidget(self.video_container)

        self.playlist = PlaylistPanel()
        splitter.addWidget(self.playlist)
        splitter.setSizes([1, 0])
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, True)

        root.addWidget(splitter, 1)

        self.controls = ControlsBar()
        root.addWidget(self.controls)

    def _connect_signals(self):
        c = self.controls
        c.play_toggled.connect(self.toggle_play)
        c.seeked.connect(lambda pos: self.mpv.seek(pos))
        c.volume_changed.connect(self.mpv.set_volume)
        c.fullscreen_toggled.connect(self.toggle_fullscreen)

        m = self.mpv
        m.file_loaded.connect(self._on_file_loaded)
        m.paused_changed.connect(c.set_paused)

        p = self.playlist
        p.item_activated.connect(self._play_file)

    # ── 窗口状态 ──

    def showEvent(self, event):
        super().showEvent(event)
        if not self._acrylic_applied:
            enable_acrylic(int(self.winId()))
            self._acrylic_applied = True

    def _toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event and event.type() == event.Type.WindowStateChange:
            is_max = self.isMaximized()
            m = 0 if is_max else 1
            self._root_layout.setContentsMargins(m, 0, m, m)
            self._update_cursor(self.mapFromGlobal(QCursor.pos()))

    # ── 播放控制 ──

    def open_file(self):
        opts = QFileDialog.Option.DontUseNativeDialog
        paths, _ = QFileDialog.getOpenFileNames(
            self, "打开媒体文件", "",
            "媒体文件 (*.mp4 *.mkv *.avi *.mov *.wmv *.flv *.webm *.mp3 *.flac *.wav *.m4a *.aac);;所有文件 (*)",
            options=opts,
        )
        if paths:
            self.playlist.add_files(paths)
            self._play_file(paths[0])

    def _open_directory(self):
        opts = QFileDialog.Option.DontUseNativeDialog
        d = QFileDialog.getExistingDirectory(self, "选择文件夹", options=opts)
        if not d:
            return
        exts = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm",
                ".mp3", ".flac", ".wav", ".m4a", ".aac", ".ogg", ".opus"}
        files = sorted([str(p) for p in Path(d).iterdir() if p.suffix.lower() in exts])
        if files:
            self.playlist.add_files(files)
            self._play_file(files[0])

    def _play_file(self, path: str):
        self.mpv.open(path)
        self._playlist_visible = True
        self.playlist.setVisible(True)
        if not self.isFullScreen():
            self._show_placeholder(False)

    def _on_file_loaded(self, path: str):
        self.titlebar.set_title(f"RedVideo — {Path(path).name}")

    def toggle_play(self):
        self.mpv.toggle_play()

    def seek_forward(self):
        self.mpv.seek_rel(5)

    def seek_backward(self):
        self.mpv.seek_rel(-5)

    def seek_big_forward(self):
        self.mpv.seek_rel(30)

    def seek_big_backward(self):
        self.mpv.seek_rel(-30)

    def volume_up(self):
        self.mpv.volume_up()
        self.controls.set_volume(self.mpv.volume)

    def volume_down(self):
        self.mpv.volume_down()
        self.controls.set_volume(self.mpv.volume)

    def toggle_mute(self):
        self.mpv.toggle_mute()
        self.controls.set_muted(self.mpv.is_muted)

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()
        self.titlebar.setVisible(not self.isFullScreen())

    def exit_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
            self.titlebar.setVisible(True)

    def toggle_playlist(self):
        self._playlist_visible = not self._playlist_visible
        self.playlist.setVisible(self._playlist_visible)

    def remove_playlist_item(self):
        self.playlist.remove_selected()

    # ── 拖拽 ──

    def dragEnterEvent(self, event: QDragEnterEvent | None):
        if event and event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event and event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent | None):
        if event is None:
            return
        urls = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
        if urls:
            self.playlist.add_files(urls)
            if not self.mpv.filename:
                self._play_file(urls[0])

    # ── 位置轮询 ──

    def _poll_position(self):
        try:
            if self.mpv.filename:
                self.controls.update_time(self.mpv.time_pos, self.mpv.duration)
        except Exception:
            pass

    # ── 占位显示 ──

    def _show_placeholder(self, show: bool):
        self.placeholder.setVisible(show)

    # ── 关闭 ──

    def closeEvent(self, event):
        self._position_timer.stop()
        self.mpv.cleanup()
        super().closeEvent(event)
