"""统一单色图标 — 内置 SVG，替代字符/emoji 图标。

字符图标（⏮ ▶ ⛶）和 emoji（🔊 📌）在 Windows 上会被 Segoe UI Emoji
接管渲染成彩色块，与深色主题和红色强调色冲突；这里内置一套 24×24
线型 SVG（统一 2px 圆角笔画，play/pause 实心保证视觉重量），运行时
按颜色渲染成位图。

QSS 无法给 QIcon 换色，悬停/激活的换色由 IconButton 自己处理：
默认灰 → 悬停亮 → 激活（如图钉置顶）用主题强调色。
"""

from PyQt6.QtCore import QByteArray, QSize, Qt
from PyQt6.QtGui import QIcon, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QPushButton

_TPL = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
    '<g fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" '
    'stroke-linejoin="round">{body}</g></svg>'
)

# 实心三角形描同色边让尖角圆润，和 2px 线型的视觉粗细一致
_ICONS: dict[str, str] = {
    "prev": (
        '<path d="M18 6.7v10.6c0 .84-.93 1.34-1.63.88l-8.2-5.3a1.05 1.05 0 0 1 0-1.76'
        'l8.2-5.3c.7-.46 1.63.04 1.63.88z" fill="{c}" stroke="{c}" stroke-width="1.5"/>'
        '<path d="M5.5 5.5v13"/>'
    ),
    "next": (
        '<path d="M6 6.7v10.6c0 .84.93 1.34 1.63.88l8.2-5.3a1.05 1.05 0 0 0 0-1.76'
        'l-8.2-5.3C6.93 5.36 6 5.86 6 6.7z" fill="{c}" stroke="{c}" stroke-width="1.5"/>'
        '<path d="M18.5 5.5v13"/>'
    ),
    "play": (
        '<path d="M8.5 5.9v12.2c0 .9.98 1.45 1.75.98l10.2-6.1a1.15 1.15 0 0 0 0-1.96'
        'L10.25 4.92A1.15 1.15 0 0 0 8.5 5.9z" fill="{c}" stroke="{c}" stroke-width="2"/>'
    ),
    "pause": (
        '<rect x="6.2" y="5" width="4" height="14" rx="1.5" fill="{c}" stroke="none"/>'
        '<rect x="13.8" y="5" width="4" height="14" rx="1.5" fill="{c}" stroke="none"/>'
    ),
    "volume": (
        '<path d="M11.4 4.9 7.6 8H5.2A1.2 1.2 0 0 0 4 9.2v5.6A1.2 1.2 0 0 0 5.2 16h2.4'
        'l3.8 3.1a.85.85 0 0 0 1.4-.66V5.56a.85.85 0 0 0-1.4-.66z" fill="{c}" stroke="none"/>'
        '<path d="M15.8 9.3a4.2 4.2 0 0 1 0 5.4"/>'
        '<path d="M18.4 6.9a7.6 7.6 0 0 1 0 10.2"/>'
    ),
    "volume_muted": (
        '<path d="M11.4 4.9 7.6 8H5.2A1.2 1.2 0 0 0 4 9.2v5.6A1.2 1.2 0 0 0 5.2 16h2.4'
        'l3.8 3.1a.85.85 0 0 0 1.4-.66V5.56a.85.85 0 0 0-1.4-.66z" fill="{c}" stroke="none"/>'
        '<path d="m16 9.7 4.6 4.6M20.6 9.7 16 14.3"/>'
    ),
    "pin": (
        '<path d="M12 17v5"/>'
        '<path d="M9 10.8a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.27V16a1 1 0 0 0 1 1'
        'h12a1 1 0 0 0 1-1v-.73a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.8V7a1 1 0 0 1 1-1'
        ' 2 2 0 0 0 0-4H8a2 2 0 0 0 0 4 1 1 0 0 1 1 1z"/>'
    ),
    "fullscreen": (
        '<path d="M4 9V6a2 2 0 0 1 2-2h3M15 4h3a2 2 0 0 1 2 2v3'
        'M20 15v3a2 2 0 0 1-2 2h-3M9 20H6a2 2 0 0 1-2-2v-3"/>'
    ),
}

# 各主题的图标配色（accent 与该主题 QSS 的滑杆/选中色保持一致）
ICON_THEMES: dict[str, dict[str, str]] = {
    "night": {"base": "#c9c9c9", "hover": "#ffffff", "accent": "#e53935"},
    "day": {"base": "#6b6b6b", "hover": "#1a1a1a", "accent": "#e53935"},
    "deepblue": {"base": "#b9cade", "hover": "#ffffff", "accent": "#3a7bd5"},
}

_pixmap_cache: dict[tuple[str, str, int, float], QPixmap] = {}


def icon(name: str, color: str, px: int, dpr: float = 1.0) -> QIcon:
    """把图标按颜色渲染为指定逻辑尺寸的 QIcon（带缓存）。"""
    pm = _pixmap(name, color, px, dpr)
    ic = QIcon()
    ic.addPixmap(pm)
    return ic


def _pixmap(name: str, color: str, px: int, dpr: float) -> QPixmap:
    key = (name, color, px, dpr)
    if key not in _pixmap_cache:
        # 先插 body 再统一替换颜色：format() 不会处理作为值插入的字符串里的占位符
        svg = _TPL.replace("{body}", _ICONS[name]).replace("{c}", color)
        renderer = QSvgRenderer(QByteArray(svg.encode()))
        pm = QPixmap(int(px * dpr), int(px * dpr))
        pm.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pm)
        renderer.render(painter)
        painter.end()
        pm.setDevicePixelRatio(dpr)
        _pixmap_cache[key] = pm
    return _pixmap_cache[key]


def palette_for(theme: str) -> dict[str, str]:
    return ICON_THEMES.get(theme, ICON_THEMES["night"])


class IconButton(QPushButton):
    """以 SVG 图标为内容的按钮，随 悬停/激活 状态换色。

    active（如置顶生效）优先级最高且用主题强调色；悬停次之。
    """

    def __init__(self, name: str, px: int = 18, parent=None):
        super().__init__(parent)
        self._icon_name = name
        self._px = px
        self._base, self._hover, self._accent = "#c9c9c9", "#ffffff", "#e53935"
        self._active = False
        self._refresh()

    @property
    def icon_name(self) -> str:
        return self._icon_name

    def set_colors(self, base: str, hover: str, accent: str) -> None:
        self._base, self._hover, self._accent = base, hover, accent
        self._refresh()

    def set_icon_name(self, name: str) -> None:
        if name != self._icon_name:
            self._icon_name = name
            self._refresh()

    def set_active(self, on: bool) -> None:
        if on != self._active:
            self._active = on
            self._refresh()

    def enterEvent(self, event) -> None:
        self._refresh()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._refresh()
        super().leaveEvent(event)

    def _refresh(self) -> None:
        color = self._accent if self._active else (self._hover if self.underMouse() else self._base)
        self.setIcon(icon(self._icon_name, color, self._px, self.devicePixelRatioF()))
        self.setIconSize(QSize(self._px, self._px))
