"""播放列表侧栏 — 拖拽添加/内部重排/过滤/右键菜单"""

import os

from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QListWidgetItem,
    QLabel, QPushButton, QHBoxLayout, QSizePolicy, QLineEdit,
    QMenu, QAbstractItemView,
)
from PyQt6.QtCore import Qt, pyqtSignal, QEvent, QSize, QUrl
from PyQt6.QtGui import (
    QDragEnterEvent, QDropEvent, QIcon, QDesktopServices, QAction,
)

from .icons import icon as svg_icon, palette_for
from .media_files import expand_media

SUB_EXTS = {".srt", ".ass", ".ssa", ".vtt", ".sub"}

_PATH_ROLE = Qt.ItemDataRole.UserRole          # 原始路径：播放/持久化用
_KEY_ROLE = Qt.ItemDataRole.UserRole + 1       # 规范化路径：大小写/分隔符无关比较


def _norm_key(path: str) -> str:
    return os.path.normcase(os.path.normpath(path))


class _PlaylistList(QListWidget):
    """列表本体：内部拖拽重排 + 把外部文件拖放转交面板。"""

    external_drop = pyqtSignal(list)  # 外部来源拖入的本地路径

    def dragEnterEvent(self, event) -> None:
        if event.source() is self:
            super().dragEnterEvent(event)  # 内部重排走 QAbstractItemView 流程
        elif event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event) -> None:
        if event.source() is self:
            super().dragMoveEvent(event)  # 让基类算出 dropIndicatorPosition
        elif event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:
        if event.source() is self:
            self._reorder_drop(event)
            return
        if event.mimeData().hasUrls():
            paths = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
            if paths:
                self.external_drop.emit(paths)
                event.acceptProposedAction()

    def _reorder_drop(self, event) -> None:
        """手动完成内部重排。QListWidget 默认 InternalMove 经 MIME 序列化
        重建条目，红点图标/自定义数据是否保留随 Qt 版本行为浮动；直接搬移
        条目对象零丢失，播放真值由 model 信号自动跟随。"""
        selected = sorted((self.row(it), it) for it in self.selectedItems())
        if not selected:
            event.ignore()
            return
        idx = self.indexAt(event.position().toPoint())
        row = idx.row() if idx.isValid() else self.count()
        if idx.isValid() and (self.dropIndicatorPosition()
                              == QAbstractItemView.DropIndicatorPosition.BelowItem):
            row += 1
        insert = row
        for src_row, _ in selected:
            if src_row < row:
                insert -= 1
        items = [it for _, it in selected]
        for src_row, _ in reversed(selected):
            self.takeItem(src_row)
        for offset, it in enumerate(items):
            self.insertItem(insert + offset, it)
        for it in items:
            it.setSelected(True)
        event.setDropAction(Qt.DropAction.MoveAction)
        event.accept()


class PlaylistPanel(QWidget):
    """可拖拽添加文件的播放列表。"""

    item_activated = pyqtSignal(str)   # 双击播放某文件
    subtitle_files_dropped = pyqtSignal(list)  # 拖入字幕文件

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("PlaylistPanel")
        self.setAcceptDrops(True)
        self.setMinimumWidth(160)
        self.setMaximumWidth(480)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QWidget()
        header.setObjectName("PlaylistHeader")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(12, 8, 8, 8)
        hl.setSpacing(8)

        lbl = QLabel("播放列表")
        lbl.setObjectName("PlaylistTitle")
        hl.addWidget(lbl, 1)

        self.lbl_count = QLabel()
        self.lbl_count.setObjectName("PlaylistCount")
        hl.addWidget(self.lbl_count)

        self.btn_clear = QPushButton("清空")
        self.btn_clear.setObjectName("BtnClear")
        hl.addWidget(self.btn_clear)

        layout.addWidget(header)

        # 过滤行：列表为空时整个隐藏
        self._filter_row = QWidget()
        fl = QHBoxLayout(self._filter_row)
        fl.setContentsMargins(12, 0, 12, 6)
        self.filter_edit = QLineEdit()
        self.filter_edit.setObjectName("PlaylistFilter")
        self.filter_edit.setPlaceholderText("过滤…")
        self.filter_edit.setClearButtonEnabled(True)
        fl.addWidget(self.filter_edit)
        layout.addWidget(self._filter_row)
        self.filter_edit.textChanged.connect(self._apply_filter)

        self.list = _PlaylistList()
        self.list.setObjectName("PlaylistList")
        self.list.setAlternatingRowColors(True)
        self.list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.list.setUniformItemSizes(True)  # 行高一致：大列表布局计算 O(1) 化
        self.list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.list.setIconSize(QSize(10, 10))  # 播放行红点
        self.list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self._show_context_menu)
        self.list.itemDoubleClicked.connect(self._on_item_activated)
        self.list.external_drop.connect(self._handle_dropped)
        layout.addWidget(self.list, 1)

        # 播放真值是路径本身，行号只是缓存：增删/重排/清空后从路径重建
        model = self.list.model()
        model.rowsRemoved.connect(self._sync_playing_row)
        model.rowsInserted.connect(self._sync_playing_row)
        model.modelReset.connect(self._sync_playing_row)

        self.btn_clear.clicked.connect(self._clear)

        # 空态覆盖层：图标 + 拖入提示；清空按钮在空列表时置灰
        self._build_empty_overlay()
        self._update_empty_state()

        # 正在播放的行：上一曲/下一曲以它为基准，而不是用户当前点选的行
        self._playing_row = -1
        self._playing_path: str | None = None
        self._accent = "#e53935"  # apply_icon_theme 按主题覆盖

    def _build_empty_overlay(self):
        self._empty_overlay = QWidget(self.list)
        box = QVBoxLayout(self._empty_overlay)
        box.setContentsMargins(16, 0, 16, 32)
        box.addStretch(1)
        self._empty_icon = QLabel()
        self._empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        box.addWidget(self._empty_icon)
        text = QLabel("把视频拖到这里\n或按 Ctrl+O 打开文件")
        text.setObjectName("PlaylistEmptyText")
        text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        box.addWidget(text)
        box.addStretch(2)
        self._empty_overlay.setGeometry(self.list.rect())
        self.list.installEventFilter(self)  # 覆盖层跟随列表尺寸

    # ── API ──

    def add_files(self, paths: list[str]) -> None:
        if not paths:
            return
        # 大文件夹批量添加时暂停重绘
        self.list.setUpdatesEnabled(False)
        try:
            for p in paths:
                item = QListWidgetItem(Path(p).name)
                item.setData(_PATH_ROLE, p)
                item.setData(_KEY_ROLE, _norm_key(p))
                item.setToolTip(p)
                self.list.addItem(item)
        finally:
            self.list.setUpdatesEnabled(True)
        self._update_empty_state()
        if self.filter_edit.text():
            self._apply_filter(self.filter_edit.text())  # 新增条目同样受过滤约束

    def mark_playing(self, path: str) -> None:
        """标记正在播放的文件：选中高亮该行并作为上/下一曲的基准。

        列表允许重复路径（用户可能想重播）；此时标记第一条匹配行。
        文件不在列表中时 _playing_row = -1：继续播放但不参与列表导航。
        """
        self._clear_playing_icon()
        self._playing_path = path
        self._sync_playing_row()
        if self._playing_row >= 0:
            item = self.list.item(self._playing_row)
            self.list.setCurrentRow(self._playing_row)
            self.list.scrollToItem(item, QAbstractItemView.ScrollHint.EnsureVisible)
            item.setIcon(QIcon(svg_icon("dot", self._accent, 10).pixmap(10, 10)))

    def _clear_playing_icon(self) -> None:
        if 0 <= self._playing_row < self.list.count():
            self.list.item(self._playing_row).setIcon(QIcon())

    def _sync_playing_row(self, *_args) -> None:
        """结构性变化（增删/重排/清空）后从 _playing_path 重建行号。

        takeItem/insertItem/clear 各自发出 model 信号触发本回调，
        删除与拖拽重排不再需要手工偏移行号。
        """
        self._playing_row = -1
        if self._playing_path:
            self._playing_row = self._row_for_path(self._playing_path)

    def current_index(self) -> int:
        return self._playing_row

    def prev_file(self) -> str | None:
        if self._playing_row > 0:
            return self._path_at(self._playing_row - 1)
        return None

    def next_file(self, wrap: bool = False) -> str | None:
        row = self._playing_row
        count = self.list.count()
        if 0 <= row < count - 1:
            return self._path_at(row + 1)
        if wrap and 0 <= row < count:
            return self._path_at((row + 1) % count)
        return None

    def remove_selected(self) -> None:
        """删除选中行。

        播放真值（路径）经由 model 信号自动重建：删掉的行在播放行之前
        行号自动前移；正在播放的行被删则 _playing_row = -1（文件继续播，
        但退出列表导航，prev/next 无目标）。
        """
        for item in list(self.list.selectedItems()):
            self.list.takeItem(self.list.row(item))
        self._sync_playing_row()
        self._update_empty_state()

    # ── 主题 ──

    def apply_icon_theme(self, theme: str) -> None:
        """空态图标与播放行红点随主题换色（文字颜色走 QSS）。"""
        pal = palette_for(theme)
        self._accent = pal["accent"]
        pm = svg_icon("video", pal["base"], 44).pixmap(44, 44)
        self._empty_icon.setPixmap(pm)
        if 0 <= self._playing_row < self.list.count():
            self.list.item(self._playing_row).setIcon(
                QIcon(svg_icon("dot", self._accent, 10).pixmap(10, 10)))

    # ── 右键菜单 ──

    def _show_context_menu(self, pos) -> None:
        item = self.list.itemAt(pos)
        menu = QMenu(self)
        act_play: QAction | None = None
        act_folder: QAction | None = None
        if item is not None:
            act_play = menu.addAction("播放")
            act_folder = menu.addAction("打开所在文件夹")
            menu.addSeparator()
        act_remove = menu.addAction("从列表移除")
        act_remove.setEnabled(bool(self.list.selectedItems()))
        act_clear = menu.addAction("清空")
        act_clear.setEnabled(self.list.count() > 0)
        chosen = menu.exec(self.list.viewport().mapToGlobal(pos))
        if chosen is None:
            return
        if chosen is act_play and item is not None:
            path = item.data(_PATH_ROLE)
            if path:
                self.item_activated.emit(str(path))
        elif chosen is act_folder and item is not None:
            path = str(item.data(_PATH_ROLE) or "")
            if path:
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(path).parent)))
        elif chosen is act_remove:
            self.remove_selected()
        elif chosen is act_clear:
            self._clear()

    # ── 过滤 ──

    def _apply_filter(self, text: str) -> None:
        kw = text.strip().lower()
        for i in range(self.list.count()):
            item = self.list.item(i)
            item.setHidden(bool(kw) and kw not in item.text().lower())
        self._update_count()

    # ── 拖拽 ──

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        urls = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
        if urls:
            self._handle_dropped(urls)

    def _handle_dropped(self, paths: list[str]) -> None:
        """文件/字幕混拖的统一入口（面板空白区与列表区共用）。"""
        subs = [p for p in paths if Path(p).suffix.lower() in SUB_EXTS]
        media = expand_media([p for p in paths if p not in subs])
        if subs:
            self.subtitle_files_dropped.emit(subs)
        if media:
            self.add_files(media)

    # ── 内部 ──

    def _path_at(self, row: int) -> str | None:
        item = self.list.item(row)
        return str(item.data(_PATH_ROLE)) if item else None

    def _row_for_path(self, path: str) -> int:
        target = _norm_key(path)
        for i in range(self.list.count()):
            if self.list.item(i).data(_KEY_ROLE) == target:
                return i
        return -1

    def _clear(self) -> None:
        self.list.clear()
        self._sync_playing_row()
        self._update_empty_state()

    def _update_empty_state(self) -> None:
        empty = self.list.count() == 0
        self._empty_overlay.setVisible(empty)
        self.btn_clear.setEnabled(not empty)
        self._filter_row.setVisible(not empty)
        self._update_count()

    def _update_count(self) -> None:
        total = self.list.count()
        kw = self.filter_edit.text().strip()
        if total == 0:
            self.lbl_count.setText("")
        elif kw:
            visible = sum(1 for i in range(total) if not self.list.item(i).isHidden())
            self.lbl_count.setText(f"{visible}/{total}")
        else:
            self.lbl_count.setText(str(total))

    def eventFilter(self, obj, event):
        if obj is self.list and event.type() == QEvent.Type.Resize:
            self._empty_overlay.setGeometry(self.list.rect())
        return super().eventFilter(obj, event)

    def _on_item_activated(self, item: QListWidgetItem) -> None:
        path = item.data(_PATH_ROLE)
        if path:
            self.item_activated.emit(str(path))
