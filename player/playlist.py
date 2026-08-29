"""播放列表侧栏"""

import os

from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QListWidgetItem,
    QLabel, QPushButton, QHBoxLayout, QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent


class PlaylistPanel(QWidget):
    """可拖拽添加文件的播放列表。"""

    item_activated = pyqtSignal(str)   # 双击播放某文件

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

        lbl = QLabel("播放列表")
        lbl.setObjectName("PlaylistTitle")
        hl.addWidget(lbl, 1)

        self.btn_clear = QPushButton("清空")
        self.btn_clear.setObjectName("BtnClear")
        hl.addWidget(self.btn_clear)

        layout.addWidget(header)

        self.list = QListWidget()
        self.list.setObjectName("PlaylistList")
        self.list.setAlternatingRowColors(True)
        self.list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.list.itemDoubleClicked.connect(self._on_item_activated)
        layout.addWidget(self.list, 1)

        self.btn_clear.clicked.connect(self._clear)

        # 正在播放的行：上一曲/下一曲以它为基准，而不是用户当前点选的行
        self._playing_row = -1

    # ── API ──

    def add_files(self, paths: list[str]) -> None:
        for p in paths:
            name = Path(p).name
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, p)
            item.setToolTip(p)
            self.list.addItem(item)

    def mark_playing(self, path: str) -> None:
        """标记正在播放的文件：选中高亮该行并作为上/下一曲的基准。"""
        row = self._row_for_path(path)
        self._playing_row = row
        if row >= 0:
            self.list.setCurrentRow(row)

    def current_index(self) -> int:
        return self._playing_row

    def set_current_index(self, index: int) -> None:
        self.list.setCurrentRow(index)

    def prev_file(self) -> str | None:
        if self._playing_row > 0:
            return self._path_at(self._playing_row - 1)
        return None

    def next_file(self) -> str | None:
        if 0 <= self._playing_row < self.list.count() - 1:
            return self._path_at(self._playing_row + 1)
        return None

    def remove_selected(self) -> None:
        for item in self.list.selectedItems():
            row = self.list.row(item)
            self.list.takeItem(row)
            if row < self._playing_row:
                self._playing_row -= 1
            elif row == self._playing_row:
                self._playing_row = -1

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
            self.add_files(urls)

    # ── 内部 ──

    def _path_at(self, row: int) -> str | None:
        item = self.list.item(row)
        return str(item.data(Qt.ItemDataRole.UserRole)) if item else None

    def _row_for_path(self, path: str) -> int:
        target = os.path.normcase(os.path.normpath(path))
        for i in range(self.list.count()):
            p = self.list.item(i).data(Qt.ItemDataRole.UserRole)
            if p and os.path.normcase(os.path.normpath(p)) == target:
                return i
        return -1

    def _clear(self) -> None:
        self.list.clear()
        self._playing_row = -1

    def _on_item_activated(self, item: QListWidgetItem) -> None:
        path = item.data(Qt.ItemDataRole.UserRole)
        if path:
            self.item_activated.emit(path)
