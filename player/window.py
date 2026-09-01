"""RedVideo 主窗口 — 无框 + 缩放 + 毛玻璃 + 主题切换"""

import sys
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout,
    QFileDialog, QSplitter, QMenu, QToolButton, QApplication,
)
from PyQt6.QtCore import Qt, QRect, QPoint, QTimer
from PyQt6.QtGui import (
    QDragEnterEvent, QDropEvent, QAction, QActionGroup, QMouseEvent, QCursor,
    QIcon,
)

from player.mpv_widget import MpvWidget
from player.controls import ControlsBar
from player.playlist import PlaylistPanel, SUB_EXTS
from player.shortcuts import Shortcuts
from player.titlebar import Titlebar, TITLEBAR_HEIGHT
from player.windows_effects import enable_acrylic
from player.state import load as load_state, save as save_state

RESIZE_MARGIN = 6


def _base() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


VERSION = "0.4.0"

THEMES_DIR = _base() / "resources" / "themes"
THEME_NAMES = {"night": "夜间", "day": "日间", "deepblue": "深蓝"}
THEME_LIST = list(THEME_NAMES)

MEDIA_EXTS = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm",
              ".mp3", ".flac", ".wav", ".m4a", ".aac", ".ogg", ".opus"}
MEDIA_FILTER = (
    "媒体文件 (*.mp4 *.mkv *.avi *.mov *.wmv *.flv *.webm"
    " *.mp3 *.flac *.wav *.m4a *.aac *.ogg *.opus);;所有文件 (*)"
)
SUB_FILTER = "字幕文件 (*.srt *.ass *.ssa *.vtt *.sub);;所有文件 (*)"
LOOP_MODES = {"off": "播完停止", "one": "单曲循环", "all": "列表循环"}


_theme_cache: dict[str, str] = {}


def apply_theme(name: str) -> None:
    """加载主题 QSS 并应用到全局。"""
    path = THEMES_DIR / f"{name}.qss"
    if not path.exists():
        return
    app = QApplication.instance()
    if app is None:
        return
    if name in _theme_cache:
        app.setStyleSheet(_theme_cache[name])
        return
    with open(path, encoding="utf-8") as f:
        qss = f.read()
    _theme_cache[name] = qss
    app.setStyleSheet(qss)


class MainWindow(QMainWindow):
    """RedVideo 主窗口 — 无框窗口 + macOS 风格标题栏 + 毛玻璃 + 四边缩放。"""

    def __init__(self, theme: str = "night", file_paths: list[str] | None = None):
        super().__init__()
        self._theme = theme
        self._startup_files = file_paths

        # ── 窗口图标 ──
        icon_path = _base() / "resources" / "icon.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        # ── 无框窗口 ──
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setMinimumSize(800, 500)
        self.resize(1280, 720)
        self.setAcceptDrops(True)
        self.setMouseTracking(True)

        self._playlist_visible = True
        self._acrylic_applied = False
        self._last_dir = ""
        self._duration = 0.0  # duration_changed 时缓存，position tick 不必跨线程读 mpv
        self._loop_mode = "off"

        # 缩放状态
        self._resizing = False
        self._resize_dir: set[str] = set()
        self._drag_pos: QPoint | None = None
        self._start_geo: QRect | None = None

        # 双击标题栏最大化
        self._maximized_before_full = self.isMaximized()

        # 单击画面延迟判定：双击全屏时取消单击的暂停/恢复
        self._click_timer = QTimer(self)
        self._click_timer.setSingleShot(True)
        self._click_timer.timeout.connect(self.toggle_play)

        apply_theme(self._theme)

        self._build_titlebar()
        self._build_ui()
        self._connect_signals()

        Shortcuts(self)

        # 恢复播放记忆
        state = load_state()
        self._last_dir = state.get("last_dir", "")
        if state.get("geometry"):
            self.restoreGeometry(bytes.fromhex(state["geometry"]))
        if state.get("volume") is not None:
            vol = int(state["volume"])  # mpv.volume 是 float，QSlider 只收 int
            self.mpv.set_volume(vol)
            self.controls.set_volume(vol)
        if state.get("speed") is not None:
            self.mpv.set_speed(state["speed"])
            self.controls.set_speed(state["speed"])
        if state.get("theme") and state["theme"] != self._theme:
            self.switch_theme(state["theme"])
        if state.get("loop_mode") in LOOP_MODES:
            self._loop_mode = state["loop_mode"]
            for name, act in self._loop_actions.items():
                act.setChecked(name == self._loop_mode)
        # 打开即播上次
        if self._startup_files is None and state.get("last_file"):
            self._startup_files = [state["last_file"]]
        if self._startup_files:
            if state.get("playlist_files"):
                self.playlist.add_files(state["playlist_files"])
            else:
                self.playlist.add_files(self._startup_files)
            self._play_file(self._startup_files[0])
            if state.get("last_position"):
                self._restore_position(state["last_position"])
            if state.get("playlist_index") is not None:
                self.playlist.set_current_index(state["playlist_index"])

    def _restore_position(self, pos: float) -> None:
        """file_loaded 后一次性恢复断点（固定延时对慢盘/网络文件不可靠）。"""

        def _seek(_path: str) -> None:
            self.mpv.seek(pos)
            try:
                self.mpv.file_loaded.disconnect(_seek)
            except TypeError:
                pass

        self.mpv.file_loaded.connect(_seek)

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
        self.controls.apply_icon_theme(name)

    # ── 构建 UI ──

    def _build_titlebar(self):
        self.titlebar = Titlebar("RedVideo", version=VERSION)
        self.titlebar.close_clicked.connect(self.close)
        self.titlebar.minimize_clicked.connect(self.showMinimized)
        self.titlebar.maximize_clicked.connect(self._toggle_maximize)

        menu_btn = QToolButton()
        menu_btn.setObjectName("MenuButton")
        menu_btn.setArrowType(Qt.ArrowType.DownArrow)
        menu_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu_btn.setCursor(Qt.CursorShape.ArrowCursor)
        menu_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        menu = QMenu(menu_btn)

        # 文件
        act_open = QAction("打开文件...", self)
        act_open.setShortcut("Ctrl+O")
        act_open.triggered.connect(self.open_file)
        menu.addAction(act_open)

        act_open_dir = QAction("打开文件夹...", self)
        act_open_dir.triggered.connect(self._open_directory)
        menu.addAction(act_open_dir)

        act_sub = QAction("加载字幕...", self)
        act_sub.triggered.connect(self.load_subtitle_dialog)
        menu.addAction(act_sub)

        act_shot = QAction("截图", self)
        act_shot.triggered.connect(self.screenshot)
        menu.addAction(act_shot)

        menu.addSeparator()

        # 播放列表开关
        act_toggle_pl = QAction("播放列表", self)
        act_toggle_pl.setShortcut("Ctrl+I")
        act_toggle_pl.setCheckable(True)
        act_toggle_pl.setChecked(True)
        act_toggle_pl.triggered.connect(self.toggle_playlist)
        menu.addAction(act_toggle_pl)

        menu.addSeparator()

        # 循环模式
        loop_menu = menu.addMenu("循环模式")
        loop_group = QActionGroup(self)
        loop_group.setExclusive(True)
        self._loop_actions: dict[str, QAction] = {}
        for name, label in LOOP_MODES.items():
            act = QAction(label, self)
            act.setCheckable(True)
            act.setChecked(name == self._loop_mode)
            act.triggered.connect(lambda checked, m=name: self.set_loop_mode(m))
            loop_group.addAction(act)
            loop_menu.addAction(act)
            self._loop_actions[name] = act

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

        splitter.addWidget(self.video_container)

        self.playlist = PlaylistPanel()
        splitter.addWidget(self.playlist)
        splitter.setSizes([1020, 260])
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, True)

        root.addWidget(splitter, 1)

        self.controls = ControlsBar()
        self.controls.apply_icon_theme(self._theme)
        root.addWidget(self.controls)

    def _connect_signals(self):
        c = self.controls
        c.play_toggled.connect(self.toggle_play)
        c.seeked.connect(lambda pos: self.mpv.seek(pos))
        c.prev_clicked.connect(self.prev_file)
        c.next_clicked.connect(self.next_file)
        c.volume_changed.connect(self.mpv.set_volume)
        c.speed_changed.connect(self.mpv.set_speed)
        c.mute_toggled.connect(self.toggle_mute)
        c.fullscreen_toggled.connect(self.toggle_fullscreen)
        c.always_on_top_toggled.connect(self.toggle_always_on_top)

        m = self.mpv
        m.file_loaded.connect(self._on_file_loaded)
        m.paused_changed.connect(c.set_paused)
        m.position_changed.connect(lambda pos: c.update_time(pos, self._duration))
        m.duration_changed.connect(self._on_duration_changed)
        m.finished.connect(self._on_playback_finished)
        m.video_clicked.connect(self._on_video_clicked)
        m.video_double_clicked.connect(self._on_video_double_clicked)
        m.wheel_scrolled.connect(self._wheel_volume)

        p = self.playlist
        p.item_activated.connect(self._play_file)
        p.subtitle_files_dropped.connect(self._load_subtitles)

    # ── 窗口状态 ──

    def showEvent(self, event):
        super().showEvent(event)
        if not self._acrylic_applied:
            enable_acrylic(int(self.winId()), dark_tint=self._theme != "day")
            self._acrylic_applied = True

    def _toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event and event.type() == event.Type.WindowStateChange:
            m = 0 if (self.isMaximized() or self.isFullScreen()) else 1
            self._root_layout.setContentsMargins(m, 0, m, m)
            self._update_cursor(self.mapFromGlobal(QCursor.pos()))

    # ── 播放控制 ──

    def open_file(self):
        opts = QFileDialog.Option.DontUseNativeDialog
        start = self._last_dir or ""
        paths, _ = QFileDialog.getOpenFileNames(
            self, "打开媒体文件", start, MEDIA_FILTER, options=opts,
        )
        if paths:
            self._last_dir = str(Path(paths[0]).parent)
            self.playlist.add_files(paths)
            self._play_file(paths[0])

    def _open_directory(self):
        opts = QFileDialog.Option.DontUseNativeDialog
        start = self._last_dir or ""
        d = QFileDialog.getExistingDirectory(self, "选择文件夹", start, options=opts)
        if not d:
            return
        self._last_dir = d
        files = sorted([str(p) for p in Path(d).iterdir() if p.suffix.lower() in MEDIA_EXTS])
        if files:
            self.playlist.add_files(files)
            self._play_file(files[0])

    def open_paths(self, paths: list[str]) -> None:
        """单实例/多文件入口：追加到播放列表，空闲则开播第一个。"""
        self.playlist.add_files(paths)
        if not self.mpv.filename:
            self._play_file(paths[0])
        self.show()
        self.raise_()
        self.activateWindow()

    def _play_file(self, path: str):
        self.playlist.mark_playing(path)
        self.mpv.open(path)
        if not self.isVisible():
            self.show()

    def _on_file_loaded(self, path: str):
        self.titlebar.set_title(f"RedVideo — {Path(path).name}")

    def _on_duration_changed(self, dur: float):
        self._duration = dur
        self.controls.update_time(self.mpv.time_pos, dur)

    def prev_file(self):
        path = self.playlist.prev_file()
        if path:
            self._play_file(path)

    def next_file(self):
        path = self.playlist.next_file()
        if path:
            self._play_file(path)

    def _on_playback_finished(self):
        if self._loop_mode == "one":
            self.mpv.replay()
            return
        # 播完自动连播下一曲；off 到列表末尾停在末帧，all 循环整个列表
        path = self.playlist.next_file(wrap=(self._loop_mode == "all"))
        if path:
            self._play_file(path)

    def set_loop_mode(self, mode: str) -> None:
        if mode not in LOOP_MODES:
            return
        self._loop_mode = mode
        for name, act in self._loop_actions.items():
            act.setChecked(name == mode)
        self._osd(LOOP_MODES[mode])

    def cycle_loop_mode(self) -> None:
        order = list(LOOP_MODES)
        nxt = order[(order.index(self._loop_mode) + 1) % len(order)]
        self.set_loop_mode(nxt)

    # ── 字幕 / 截图 ──

    def load_subtitle_dialog(self):
        if not self.mpv.filename:
            return
        opts = QFileDialog.Option.DontUseNativeDialog
        paths, _ = QFileDialog.getOpenFileNames(
            self, "加载字幕", self._last_dir or "", SUB_FILTER, options=opts,
        )
        if paths:
            self._load_subtitles(paths)

    def _load_subtitles(self, paths: list[str]) -> None:
        if not self.mpv.filename:
            return
        ok = sum(1 for p in paths if self.mpv.load_subtitle(p))
        if ok:
            self._osd("字幕已加载" if ok == 1 else f"已加载 {ok} 条字幕")

    def screenshot(self) -> None:
        src = self.mpv.filename
        if not src:
            return
        dest = Path(src).with_name(f"{Path(src).stem} {datetime.now():%H%M%S}.png")
        if self.mpv.screenshot(str(dest)):
            self._osd("已保存截图")

    def toggle_play(self):
        self.mpv.toggle_play()

    def seek_forward(self):
        self.mpv.seek_rel(5)
        self._osd("+5s")

    def seek_backward(self):
        self.mpv.seek_rel(-5)
        self._osd("-5s")

    def seek_big_forward(self):
        self.mpv.seek_rel(30)
        self._osd("+30s")

    def seek_big_backward(self):
        self.mpv.seek_rel(-30)
        self._osd("-30s")

    def volume_up(self):
        self.mpv.volume_up()
        self.controls.set_volume(self.mpv.volume)
        self._osd(f"音量 {self.mpv.volume}%")

    def volume_down(self):
        self.mpv.volume_down()
        self.controls.set_volume(self.mpv.volume)
        self._osd(f"音量 {self.mpv.volume}%")

    def toggle_mute(self):
        self.mpv.toggle_mute()
        self.controls.set_muted(self.mpv.is_muted)
        self._osd("静音" if self.mpv.is_muted else "取消静音")

    def speed_up(self):
        self.mpv.speed_up()
        self.controls.set_speed(self.mpv.speed)
        self._osd(f"倍速 {self.mpv.speed:.1f}x")

    def speed_down(self):
        self.mpv.speed_down()
        self.controls.set_speed(self.mpv.speed)
        self._osd(f"倍速 {self.mpv.speed:.1f}x")

    # ── 画面鼠标交互 ──

    def _on_video_clicked(self):
        # 延迟一个双击间隔，双击全屏时取消单击的暂停/恢复
        self._click_timer.start(QApplication.doubleClickInterval())

    def _on_video_double_clicked(self):
        self._click_timer.stop()
        self.toggle_fullscreen()

    def _wheel_volume(self, steps: int):
        if steps > 0:
            self.mpv.volume_up(steps * 5)
        elif steps < 0:
            self.mpv.volume_down(-steps * 5)
        else:
            return
        self.controls.set_volume(self.mpv.volume)
        self._osd(f"音量 {self.mpv.volume}%")

    def _osd(self, text: str, ms: int = 800) -> None:
        self.mpv.show_osd(text, ms)

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self._exit_fullscreen()
        else:
            self._enter_fullscreen()

    def exit_fullscreen(self):
        self._exit_fullscreen()

    def _enter_fullscreen(self):
        self.showFullScreen()
        self.titlebar.setVisible(False)
        self.playlist.setVisible(False)  # 全屏沉浸；退出时按原状态恢复

    def _exit_fullscreen(self):
        if not self.isFullScreen():
            return
        self.showNormal()
        self.titlebar.setVisible(True)
        self.playlist.setVisible(self._playlist_visible)

    def toggle_playlist(self):
        self._playlist_visible = not self._playlist_visible
        self.playlist.setVisible(self._playlist_visible)

    def toggle_always_on_top(self, checked: bool) -> None:
        flags = self.windowFlags()
        if checked:
            self.setWindowFlags(flags | Qt.WindowType.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(flags & ~Qt.WindowType.WindowStaysOnTopHint)
        self.show()

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

    # ── 关闭 ──

    def closeEvent(self, event):
        # 保存播放记忆
        geo = self.saveGeometry().data().hex()
        pos = self.mpv.time_pos if self.mpv.filename else None
        save_state({
            "geometry": geo,
            "volume": int(self.mpv.volume),
            "speed": self.mpv.speed,
            "theme": self._theme,
            "last_file": self.mpv.filename,
            "last_position": pos,
            "playlist_files": [self.playlist.list.item(i).data(Qt.ItemDataRole.UserRole)
                               for i in range(self.playlist.list.count())
                               if self.playlist.list.item(i)],
            "playlist_index": self.playlist.current_index(),
            "last_dir": self._last_dir,
            "loop_mode": self._loop_mode,
        })
        self.mpv.cleanup()
        super().closeEvent(event)
