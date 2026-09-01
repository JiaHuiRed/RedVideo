# 项目记忆

> 该项目特有的备忘与教训。通用教训请写入全局 `~/.redcode/MEMORY.md`。

## 项目概况

- 技术栈：Python + PyQt6 + MPV 播放器
- 结构：`main.py` 入口 + `player/` 包（window/widget/controls/playlist/shortcuts/titlebar/windows_effects/state）+ `scripts/`
- 代码规模：11 个文件（新增 `player/state.py`），0 死代码，0 依赖环

## 当前进度（2026-08-29）

- 版本：0.4.0（2026-08-29 发布，`d3b7180`..`1dda2b7` 共 7 个 commit + 文档）
- 2026-08-29 完成一轮全面检查与修复：10 项 Bug 全部清零（倍速信号未连接、单击进度条不跳转、导航基准、state 目录迁移 %APPDATA%、Win10 Acrylic HRESULT 误判等），性能优化（duration 缓存、进度条节流、列表批量加载）
- 新功能：EOF 连播 + 循环模式（L）、画面鼠标交互（双击全屏/单击暂停/滚轮音量）、OSD 反馈（mpv show-text）、外挂字幕（fuzzy + 拖挂载）、截图（S）、进度条单击跳转（SeekSlider）、多文件单实例传参、缺 libmpv 友好报错
- 播放导航以 `_playing_row` 为基准（`PlaylistPanel.mark_playing`），`current_index()` 返回播放行
- 全仓 0 死代码，0 未使用导入，代码质量健康

## 已知优化点（已完成）

1. ~~`scripts/setup_mpv.py` 下载函数无 timeout~~ → 已加 `timeout=30`（`956d60d`）
2. ~~`main.py` socket 未在 finally 中关闭~~ → `_send_to_existing` / `_on_new_instance` 已包 `try/finally`（`956d60d`）
3. ~~`main.py` `_root_layout = None` 冗余~~ → 已删除（`956d60d`）
4. ~~`player/window.py` `_play_file` 每次 `setVisible(True)` 状态冲突~~ → 改从 `isVisible()` 判断（`956d60d`）
5. ~~`player/playlist.py` 空行噪音~~ → 182 行压到 110 行（`956d60d`）
6. ~~`player/window.py` 未使用的 `QStyle` 导入~~ → 已删除（`6a038f3`）
7. ~~`scripts/gen_icon.py` 未使用的 `ImageFilter` / `ImageFont` 导入~~ → 已删除（`6a038f3`）
8. ~~倍速按钮 `speed_changed` 信号未连接~~ → 已连接（`d3b7180`）
9. ~~原生 QSlider 单击凹槽不 seek~~ → `SeekSlider` 子类单击跳转（`d3b7180`）
10. ~~prev/next 被点选行带偏~~ → 以播放行为基准（`328991b`）
11. ~~state.json 写安装目录~~ → %APPDATA% + 旧文件迁移（`27ddead`）
12. ~~Win10 SWCA Acrylic 永不生效~~ → HRESULT 判断修正 + tint 修正（`27ddead`）

## 关键路径

- 主窗口：`player/window.py`
- 播放状态持久化：`player/state.py`（新增于 2508f9b）
- 播放控件：`player/controls.py`
- 播放列表：`player/playlist.py`
- 单实例入口：`main.py`
- 资源主题：`resources/themes/*.qss`

## jcodemunch 索引

- repo id：`JiaHuiRed/RedVideo`
- 索引状态：已建立，健康度 A（90.2）
