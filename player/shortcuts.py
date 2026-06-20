"""键盘快捷键定义"""

from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import QWidget


class Shortcuts:
    """给窗口绑定一组快捷键，每个快捷键映射到窗口的一个方法。"""

    _BINDINGS: list[tuple[str, str]] = [
        ("Space",           "toggle_play"),
        ("Left",            "seek_backward"),
        ("Right",           "seek_forward"),
        ("Up",              "volume_up"),
        ("Down",            "volume_down"),
        ("Ctrl+Right",      "seek_big_forward"),
        ("Ctrl+Left",       "seek_big_backward"),
        ("Esc",             "exit_fullscreen"),
        ("F11",             "toggle_fullscreen"),
        ("F",               "toggle_fullscreen"),
        ("M",               "toggle_mute"),
        ("Ctrl+O",          "open_file"),
        ("Delete",          "remove_playlist_item"),
        ("Ctrl+I",          "toggle_playlist"),
        ("Ctrl+Q",          "close"),
    ]

    def __init__(self, parent: QWidget) -> None:
        self._parent = parent
        self._shortcuts: list[QShortcut] = []
        for key, method_name in self._BINDINGS:
            method = getattr(parent, method_name, None)
            if method:
                sc = QShortcut(QKeySequence(key), parent)
                sc.activated.connect(method)
                self._shortcuts.append(sc)
