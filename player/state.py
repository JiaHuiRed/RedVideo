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
    """读取状态文件；不存在/损坏/结构异常都返回空 dict，不阻断启动。

    损坏时在状态文件旁留一行诊断（用户目录，不写资源文件夹）。
    """
    if not STATE_PATH.exists() and _LEGACY_PATH.exists():
        try:
            STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(_LEGACY_PATH, STATE_PATH)
        except Exception:
            pass
    try:
        with open(STATE_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return {}
    except Exception as e:
        _diagnose(f"state.json 读取失败，使用默认状态：{e!r}")
        return {}
    if not isinstance(data, dict):
        _diagnose(f"state.json 顶层不是对象（{type(data).__name__}），使用默认状态")
        return {}
    return data


def save(data: dict) -> None:
    """原子写入：同目录临时文件 + flush/fsync + os.replace。

    中断只留孤儿临时文件，已保存的上一个有效配置不会被截断成半个 JSON。
    """
    tmp = STATE_PATH.parent / (STATE_PATH.name + ".tmp")
    try:
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, STATE_PATH)
    except Exception as e:
        _diagnose(f"state.json 写入失败：{e!r}")
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass


def _diagnose(message: str) -> None:
    """往状态文件同目录追加一行诊断，便于定位配置问题。"""
    try:
        from datetime import datetime
        line = f"{datetime.now():%Y-%m-%d %H:%M:%S} {message}\n"
        with open(STATE_PATH.parent / "state.error.log", "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass  # 诊断失败不影响主流程


def _num(value) -> float | None:
    """int/float 且非 bool，否则 None（JSON 的 true/false 不是数值）。"""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def sanitize(data: dict) -> dict:
    """把状态文件当不可信输入：逐字段校验，非法字段丢弃回退默认（RV-006）。

    调用方（window.py）拿到的字段类型已保证，恢复时不会再被畸形配置打断；
    有效取值范围不偷偷收窄播放器本身允许的控制范围。
    """
    out: dict = {}
    if not isinstance(data, dict):
        return out

    geo = data.get("geometry")
    if isinstance(geo, str):
        try:
            bytes.fromhex(geo)
        except ValueError:
            pass
        else:
            out["geometry"] = geo

    vol = _num(data.get("volume"))
    if vol is not None:
        out["volume"] = max(0, min(100, int(vol)))

    speed = _num(data.get("speed"))
    if speed is not None and 0.1 <= speed <= 100.0:
        out["speed"] = speed

    for key in ("theme", "loop_mode", "last_dir"):
        v = data.get(key)
        if isinstance(v, str) and v:
            out[key] = v

    last_file = data.get("last_file")
    if isinstance(last_file, str) and last_file:
        out["last_file"] = last_file

    pos = _num(data.get("last_position"))
    if pos is not None and pos >= 0:
        out["last_position"] = pos
    dur = _num(data.get("last_duration"))
    if dur is not None and dur >= 0:
        out["last_duration"] = dur

    files = data.get("playlist_files")
    if isinstance(files, list):
        out["playlist_files"] = [p for p in files if isinstance(p, str) and p]

    sizes = data.get("splitter_sizes")
    if isinstance(sizes, list) and len(sizes) == 2:
        nums = [_num(v) for v in sizes]
        if all(n is not None and n >= 1 for n in nums):
            out["splitter_sizes"] = [int(n) for n in nums]

    idx = _num(data.get("playlist_index"))
    if idx is not None:
        out["playlist_index"] = max(-1, int(idx))

    return out
