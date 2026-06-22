"""播放列表侧栏"""

from pathlib import Path

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QLabel, QPushButton, QHBoxLayout, QSizePolicy
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

        self.btn_clear.clicked.connect(self.list.clear)

    # ── API ──

    def add_files(self, paths: list[str]) -> None:
        for p in paths:
            name = Path(p).name
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, p)
            item.setToolTip(p)
            self.list.addItem(item)

    def get_items(self) -> list[str]:
        return [
            self.list.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self.list.count())
        ]

    def current_file(self) -> str | None:
        item = self.list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def remove_selected(self) -> None:
        for item in self.list.selectedItems():
            self.list.takeItem(self.list.row(item))

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

    def _on_item_activated(self, item: QListWidgetItem) -> None:
        path = item.data(Qt.ItemDataRole.UserRole)
        if path:
            self.item_activated.emit(path)
