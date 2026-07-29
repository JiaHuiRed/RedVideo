# 项目记忆

> 该项目特有的备忘与教训。通用教训请写入全局 `~/.redcode/MEMORY.md`。

## 项目概况

- 技术栈：Python + PyQt6 + MPV 播放器
- 结构：`main.py` 入口 + `player/` 包（window/widget/controls/playlist/shortcuts/titlebar/windows_effects）+ `scripts/`
- 代码规模：10 个文件，136 个符号，0 死代码，0 依赖环

## 当前进度（2026-07-29）

- 版本：0.3.2
- 已完成 7 项优化（commit `956d60d` + `6a038f3`）
- 全仓 0 死代码，0 未使用导入，代码质量健康

## 已知优化点（已完成）

1. ~~`scripts/setup_mpv.py` 下载函数无 timeout~~ → 已加 `timeout=30`（`956d60d`）
2. ~~`main.py` socket 未在 finally 中关闭~~ → `_send_to_existing` / `_on_new_instance` 已包 `try/finally`（`956d60d`）
3. ~~`main.py` `_root_layout = None` 冗余~~ → 已删除（`956d60d`）
4. ~~`player/window.py` `_play_file` 每次 `setVisible(True)` 状态冲突~~ → 改从 `isVisible()` 判断（`956d60d`）
5. ~~`player/playlist.py` 空行噪音~~ → 182 行压到 110 行（`956d60d`）
6. ~~`player/window.py` 未使用的 `QStyle` 导入~~ → 已删除（`6a038f3`）
7. ~~`scripts/gen_icon.py` 未使用的 `ImageFilter` / `ImageFont` 导入~~ → 已删除（`6a038f3`）

## 关键路径

- 主窗口：`player/window.py`
- 播放控件：`player/controls.py`
- 播放列表：`player/playlist.py`
- MPV 安装脚本：`scripts/setup_mpv.py`

## jcodemunch 索引

- repo id：`JiaHuiRed/RedVideo`
- 索引状态：已建立，健康度 A（90.2）
