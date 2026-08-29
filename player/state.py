"""播放状态持久化 — 窗口几何/音量/倍速/主题/上次播放"""

import json
import os
import shutil
import sys
from pathlib import Path


def _base() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


# 状态写到用户目录：打包后程序目录（如 Program Files）通常不可写
def _state_path() -> Path:
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "RedVideo" / "state.json"
    return Path.home() / ".redvideo" / "state.json"


STATE_PATH = _state_path()
_LEGACY_PATH = _base() / "state.json"  # 旧版写到程序安装目录，启动时迁移一次


def load() -> dict:
    if not STATE_PATH.exists() and _LEGACY_PATH.exists():
        try:
            STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(_LEGACY_PATH, STATE_PATH)
        except Exception:
            pass
    if not STATE_PATH.exists():
        return {}
    try:
        with open(STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save(data: dict) -> None:
    try:
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
