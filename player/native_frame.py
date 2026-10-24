"""Windows 原生无边框 — WS_THICKFRAME + WM_NCCALCSIZE / WM_NCHITTEST。

接管命中测试后，缩放/移动走 DWM 原生路径：
- Aero Snap 可用（拖到屏幕边缘分屏 / Win+方向键）
- 原生窗口阴影、系统尺寸光标免费获得
- 尺寸移动循环（WM_ENTERSIZEMOVE/EXITSIZEMOVE）期间临时关闭毛玻璃，
  消除合成器实时重算造成的拖动/缩放卡顿
- 顶边缩放不再被子控件（标题栏）拦截

方案：给 FramelessWindowHint 窗口补上 WS_THICKFRAME|WS_CAPTION 样式，
在 WM_NCCALCSIZE 返回 0 让客户区占满整窗（不绘制系统边框），在
WM_NCHITTEST 里按边缘热区返回 HTLEFT/…/HTCAPTION。

Win32 结构与纯函数（可离屏单测）在此模块；Qt 接驳（nativeEvent、
childAt 判按钮）由调用方通过 handle(win, msg_addr) 注入。
"""

import ctypes
import sys
from ctypes import wintypes

from .windows_effects import disable_acrylic, enable_acrylic

# ── Win32 常量 ──
GWL_STYLE = -16
WS_MAXIMIZEBOX = 0x0001_0000
WS_MINIMIZEBOX = 0x0002_0000
WS_THICKFRAME = 0x0004_0000
WS_CAPTION = 0x00C0_0000

WM_NCCALCSIZE = 0x0083
WM_NCHITTEST = 0x0084
WM_ENTERSIZEMOVE = 0x0231
WM_EXITSIZEMOVE = 0x0232

HTCLIENT = 1
HTCAPTION = 2
HTLEFT = 10
HTRIGHT = 11
HTTOP = 12
HTTOPLEFT = 13
HTTOPRIGHT = 14
HTBOTTOM = 15
HTBOTTOMLEFT = 16
HTBOTTOMRIGHT = 17

SM_CXSIZEFRAME = 32
SM_CXPADDEDBORDER = 92

# SetWindowPos: NOSIZE|NOMOVE|NOZORDER|NOACTIVATE|FRAMECHANGED
_SWP_FLAGS = 0x0001 | 0x0002 | 0x0004 | 0x0010 | 0x0020


def apply(hwnd: int) -> bool:
    """给无边框窗口补 WS_THICKFRAME|WS_CAPTION 并触发非客户区重算。

    失败（非 Win32 / API 缺失）返回 False，调用方继续走手动缩放回退路径。
    """
    if sys.platform != "win32" or not hwnd:
        return False
    try:
        user32 = ctypes.windll.user32
        if ctypes.sizeof(ctypes.c_void_p) == 8:
            get_style, set_style = user32.GetWindowLongPtrW, user32.SetWindowLongPtrW
        else:
            get_style, set_style = user32.GetWindowLongW, user32.SetWindowLongW
        get_style.restype = ctypes.c_ssize_t
        get_style.argtypes = [wintypes.HWND, ctypes.c_int]
        set_style.restype = ctypes.c_ssize_t
        set_style.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
        style = get_style(hwnd, GWL_STYLE)
        set_style(hwnd, GWL_STYLE, style | WS_THICKFRAME | WS_CAPTION
                  | WS_MAXIMIZEBOX | WS_MINIMIZEBOX)
        user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, _SWP_FLAGS)
        return True
    except Exception:
        return False


def parse_lparam_point(lparam: int) -> tuple[int, int]:
    """WM 消息 lParam 低/高字 → 有符号屏幕坐标（多显示器会有负值）。"""
    x = ctypes.c_short(lparam & 0xFFFF).value
    y = ctypes.c_short((lparam >> 16) & 0xFFFF).value
    return x, y


def hit_test(px: int, py: int, width: int, height: int, pad: int, caption_h: int,
             maximized: bool, fullscreen: bool, over_button: bool) -> int:
    """窗口本地坐标 → HT* 命中结果（纯函数）。

    边角优先于标题栏：标题栏顶部 pad 像素是缩放热区（Windows 惯例）；
    最大化/全屏不返回缩放命中。
    """
    if fullscreen:
        return HTCLIENT
    edge_l, edge_r = px < pad, px >= width - pad
    edge_t, edge_b = py < pad, py >= height - pad
    if not maximized:
        if edge_t and edge_l:
            return HTTOPLEFT
        if edge_t and edge_r:
            return HTTOPRIGHT
        if edge_b and edge_l:
            return HTBOTTOMLEFT
        if edge_b and edge_r:
            return HTBOTTOMRIGHT
        if edge_l:
            return HTLEFT
        if edge_r:
            return HTRIGHT
        if edge_t:
            return HTTOP
        if edge_b:
            return HTBOTTOM
    if py < caption_h and not over_button:
        return HTCAPTION
    return HTCLIENT


def _pad_for(hwnd: int) -> int:
    """缩放热区宽度：当前 DPI 的系统可调边框 + 内边距。"""
    user32 = ctypes.windll.user32
    try:
        dpi = user32.GetDpiForWindow(hwnd)
        if dpi:
            frame = user32.GetSystemMetricsForDpi(SM_CXSIZEFRAME, dpi)
            extra = user32.GetSystemMetricsForDpi(SM_CXPADDEDBORDER, dpi)
            if frame + extra > 0:
                return frame + extra
    except Exception:
        pass  # 旧系统没有按 DPI 查询的 API，退回系统 DPI 的值
    return max(4, user32.GetSystemMetrics(SM_CXSIZEFRAME)
               + user32.GetSystemMetrics(SM_CXPADDEDBORDER))


def inset_for_maximized(rect: wintypes.RECT, pad: int) -> None:
    """最大化时窗口矩形越出屏幕一个边框：就地内缩，客户区内容不出屏。"""
    rect.left += pad
    rect.top += pad
    rect.right -= pad
    rect.bottom -= pad


def _over_button(win, px: int, py: int) -> bool:
    """标题栏区域内是否悬停在交互按钮上（按钮必须保持 HTCLIENT 可点）。"""
    if py >= getattr(win, "_native_caption_height", 34):
        return False
    from PyQt6.QtCore import QPoint
    from PyQt6.QtWidgets import QAbstractButton
    child = win.childAt(QPoint(px, py))
    return isinstance(child, QAbstractButton)


def handle(win, msg_addr: int) -> int | None:
    """Qt nativeEvent 接驳：返回结果值表示接管该消息，None 表示放行。

    win 需提供：winId()/isFullScreen()/childAt()（Qt 接口）、
    _native_caption_height、_acrylic_applied/_sizemove_acrylic_off（毛玻璃联动）。
    """
    msg = wintypes.MSG.from_address(msg_addr)
    hwnd = int(msg.hWnd) if msg.hWnd else 0
    if not hwnd or hwnd != int(win.winId()):
        return None  # 子原生窗口（如 mpv 画面）的消息不走这里

    if msg.message == WM_NCHITTEST:
        x, y = parse_lparam_point(msg.lParam & 0xFFFFFFFF)
        rc = wintypes.RECT()
        if not ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rc)):
            return None
        px, py = x - rc.left, y - rc.top
        width, height = rc.right - rc.left, rc.bottom - rc.top
        maximized = bool(ctypes.windll.user32.IsZoomed(hwnd))
        return hit_test(
            px, py, width, height, _pad_for(hwnd),
            getattr(win, "_native_caption_height", 34),
            maximized, bool(win.isFullScreen()),
            _over_button(win, px, py),
        )

    if msg.message == WM_NCCALCSIZE and msg.wParam:
        if ctypes.windll.user32.IsZoomed(hwnd):
            inset_for_maximized(
                ctypes.cast(ctypes.c_void_p(msg.lParam),
                            ctypes.POINTER(wintypes.RECT)).contents,
                _pad_for(hwnd),
            )
        return 0  # 客户区占满整窗：去掉系统边框/标题栏绘制

    if msg.message == WM_ENTERSIZEMOVE:
        if getattr(win, "_acrylic_applied", False):
            win._sizemove_acrylic_off = disable_acrylic(hwnd)
        return None

    if msg.message == WM_EXITSIZEMOVE:
        if getattr(win, "_sizemove_acrylic_off", False):
            enable_acrylic(hwnd, dark_tint=getattr(win, "_theme", "night") != "day")
            win._sizemove_acrylic_off = False
        return None

    return None
