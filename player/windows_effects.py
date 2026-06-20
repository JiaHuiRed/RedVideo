"""Windows Acrylic / Mica 毛玻璃效果。

提供两个等级的毛玻璃：
- Acrylic（深色半透明模糊，Win10+）
- Mica（着色模糊，Win11 22H2+）

自动探测系统版本，优先用更高版本。
"""

import ctypes
from ctypes import wintypes
import sys

# ── DWM API (Windows 11 22H2+) ──

_DWMA_SYSTEMBACKDROP_TYPE = 38
_DWMA_SBT_DISABLE = 1
_DWMA_SBT_MAINWINDOW = 2  # Mica
_DWMA_SBT_TABBEDWINDOW = 3
_DWMA_SBT_ARGBSCROLL = 4  # Acrylic

_dwmapi = None
_DwmSetWindowAttribute = None


def _init_dwm():
    global _dwmapi, _DwmSetWindowAttribute
    try:
        _dwmapi = ctypes.windll.dwmapi
        _DwmSetWindowAttribute = _dwmapi.DwmSetWindowAttribute
        _DwmSetWindowAttribute.argtypes = [
            wintypes.HWND, ctypes.c_int,
            ctypes.c_void_p, ctypes.c_int,
        ]
        _DwmSetWindowAttribute.restype = ctypes.c_long
        return True
    except Exception:
        return False


def _dwm_set_backdrop(hwnd: int, backdrop_type: int) -> bool:
    if not _DwmSetWindowAttribute:
        if not _init_dwm():
            return False
    try:
        _DwmSetWindowAttribute(hwnd, _DWMA_SYSTEMBACKDROP_TYPE,
                                ctypes.byref(ctypes.c_int(backdrop_type)),
                                ctypes.sizeof(ctypes.c_int))
        return True
    except Exception:
        return False


# ── SetWindowCompositionAttribute (Win10 Acrylic) ──

_ACCENT_ENABLE_ACRYLICBLUR = 4
_WCA_ACCENT_POLICY = 19


class _ACCENT_POLICY(ctypes.Structure):
    _fields_ = [
        ("AccentState", ctypes.c_uint),
        ("AccentFlags", ctypes.c_uint),
        ("GradientColor", ctypes.c_uint),
        ("AnimationId", ctypes.c_uint),
    ]


class _WINCOMPATTRDATA(ctypes.Structure):
    _fields_ = [
        ("Attribute", ctypes.c_int),
        ("Data", ctypes.POINTER(_ACCENT_POLICY)),
        ("SizeOfData", ctypes.c_size_t),
    ]


_user32 = None
_SetWindowCompositionAttribute = None


def _init_swca():
    global _user32, _SetWindowCompositionAttribute
    try:
        _user32 = ctypes.windll.user32
        _SetWindowCompositionAttribute = _user32.SetWindowCompositionAttribute
        _SetWindowCompositionAttribute.argtypes = [
            wintypes.HWND, ctypes.POINTER(_WINCOMPATTRDATA),
        ]
        _SetWindowCompositionAttribute.restype = ctypes.c_bool
        return True
    except Exception:
        return False


def _swca_acrylic(hwnd: int, dark_tint: bool = True) -> bool:
    """通过 SetWindowCompositionAttribute 设置亚克力毛玻璃。"""
    if not _SetWindowCompositionAttribute:
        if not _init_swca():
            return False
    # GradientColor = 0x00BBGGRR (前两位 alpha, BE 排列)
    # 深色遮罩: alpha=0x99, 黑底
    tint = 0x00440000 if dark_tint else 0x00993300  # 暗色或亮色
    accent = _ACCENT_POLICY(
        AccentState=_ACCENT_ENABLE_ACRYLICBLUR,
        AccentFlags=0x20 | 0x40,  # 允许绘制 + 模糊后绘制
        GradientColor=tint,
        AnimationId=0,
    )
    data = _WINCOMPATTRDATA(
        Attribute=_WCA_ACCENT_POLICY,
        Data=ctypes.pointer(accent),
        SizeOfData=ctypes.sizeof(accent),
    )
    return _SetWindowCompositionAttribute(hwnd, data)


def enable_acrylic(hwnd: int, dark_tint: bool = True) -> bool:
    """尝试启用亚克力毛玻璃效果。

    优先级: DWM Acrylic (Win11 22H2+) → SWCA Acrylic (Win10+)

    Args:
        hwnd: 窗口句柄 (winId())
        dark_tint: 深色遮罩

    Returns:
        True if any method succeeded
    """
    # Win11 22H2+: DWM Acrylic
    if _dwm_set_backdrop(hwnd, _DWMA_SBT_ARGBSCROLL):
        return True

    # Win10: SWCA Acrylic
    return _swca_acrylic(hwnd, dark_tint)


def enable_mica(hwnd: int) -> bool:
    """启用 Mica（Win11 22H2+ 着色模糊）。"""
    return _dwm_set_backdrop(hwnd, _DWMA_SBT_MAINWINDOW)


def is_windows_11_or_later() -> bool:
    try:
        ver = sys.getwindowsversion()
        return ver.build >= 22000
    except Exception:
        return False


def is_windows_10_or_later() -> bool:
    try:
        ver = sys.getwindowsversion()
        return ver.major >= 10
    except Exception:
        return False
