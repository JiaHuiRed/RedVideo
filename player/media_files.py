"""媒体文件识别与路径展开 — 打开文件/文件夹/拖拽入口的共用过滤。"""

from pathlib import Path

MEDIA_EXTS = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm",
              ".mp3", ".flac", ".wav", ".m4a", ".aac", ".ogg", ".opus"}
MEDIA_FILTER = (
    "媒体文件 (*.mp4 *.mkv *.avi *.mov *.wmv *.flv *.webm"
    " *.mp3 *.flac *.wav *.m4a *.aac *.ogg *.opus);;所有文件 (*)"
)


def expand_media(paths: list[str]) -> list[str]:
    """把输入路径展开为媒体文件列表。

    目录递归收集（排序保证顺序稳定），文件按扩展名过滤；
    字幕等非媒体文件不在此处理（由播放列表的拖入分流负责）。
    """
    out: list[str] = []
    for p in paths:
        pp = Path(p)
        if pp.is_dir():
            out.extend(sorted(str(f) for f in pp.rglob("*")
                              if f.suffix.lower() in MEDIA_EXTS))
        elif pp.suffix.lower() in MEDIA_EXTS:
            out.append(p)
    return out
