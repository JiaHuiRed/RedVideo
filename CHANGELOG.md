# RedVideo 更新日志

## 0.3.0（2026-06-25）

### ✨ 新功能

- **单实例锁** — `main.py` 用 `QLocalServer` 监听二次打开的文件，不再弹出新窗口，文件追加到已有实例的播放列表
- **上一曲 / 下一曲** — 底部栏新增 `⏮` `⏭` 按钮，`playlist.py` 提供 `prev_file()` / `next_file()` 导航，双击播放列表项自动切歌
- **窗口图标** — `resources/icon.ico` 设为窗口和任务栏图标

### 🐛 修复

- **底部栏按钮不显示自定义图标** — 夜间/深蓝主题下 `QStyle.StandardPixmap` 位图与暗背景融为一体，改回 Unicode 文本（⏮ ▶ ⏭ 🔊, ⛶），受 QSS `color` 控制

### ♻️ 重构 / 优化

- **进度标签节流** — `ControlsBar.update_time()` 改为 100ms 单次定时器，播放时不再每帧重建时间字符串
- **主题缓存** — `apply_theme()` 首次读文件后缓存 QSS，切主题不再重复 I/O
- **死代码清理** — 删除 `player/__init__.py`（空文件）、`playlist.get_items()` / `current_file()`、`windows_effects.enable_mica()` / `is_windows_11_or_later()` / `is_windows_10_or_later()`，全仓零引用

## 0.2.0（2026-06-22）

### ✨ 新功能

- **标题栏版本标签** — 交通灯右侧显示 `v0.2.0`，版本号由 `window.py` 中 `VERSION` 常量统一管理，升级时只需改一处

### ♻️ 重构 / 优化

- **进度更新改为信号驱动** — 删除 250ms 定时器轮询，改用 mpv `time-pos` / `duration` 事件信号直接驱动控制栏，响应更即时，CPU 占用降低
- **静音状态管理** — `ControlsBar` 新增 `mute_toggled` 信号，删除原来靠按钮 emoji 文字反推状态的脆弱逻辑，由 `MainWindow.toggle_mute` 统一处理
- **删除 `resizeEvent` 中多余的 wid 重设** — mpv 嵌入后窗口句柄不变，resize 由系统通知渲染器，手动重设无效且可能引起闪烁
- **集中管理媒体扩展名** — 提取 `MEDIA_EXTS` / `MEDIA_FILTER` 模块级常量，消除 `open_file` 与 `_open_directory` 两处重复且不一致的列表（补齐 `.ogg` / `.opus`）
- **播放列表宽度可调** — 将 `setFixedWidth(260)` 改为 `setMinimumWidth(160)` + `setMaximumWidth(480)`，Splitter 拖拽手柄现在生效
- **删除 placeholder 死代码** — `placeholder` widget 从未可见，连同 4 个 QSS 文件中的 `#Placeholder` 规则一并移除
- **简化 HighDPI 分支** — 两分支代码完全相同，合并为一行；`app.setStyle("Fusion")` 始终生效
- **删除 `import math`** — `controls.py` 中从未使用

## 0.1.1（2026-06-20）

> Unity 图标不再依赖系统主题，三个主题按钮都清晰了。

### 🐛 修复

- **Windows 按钮不显示** — `QIcon.fromTheme()` 在 Windows 返回空图标，改用 Unicode 符号（▶ ⏸ 🔊 ⛶），字号加大、颜色提亮
- **主题菜单 ✅ 标记残留** — 加 `QActionGroup.setExclusive(True)` 互斥，切换只勾一个
- **点击文件后闪退** — `QFileDialog` 加 `DontUseNativeDialog` 选项
- **启动时找不到 libmpv** — 添加 `sys._MEIPASS` 和 `exe_dir/bin` 到 PATH
- **src/resources 找不到** — 移除 `--specpath` 让 spec 生成在项目根，路径自然解析
- **默认打开方式传参未处理** — `main.py` 提取 `sys.argv[1]` 传给 `MainWindow` 自动加载

## 0.1.0（2026-06-20）

### ✨ 新功能

- **macOS 风格界面** — 交通灯标题栏、无框窗口、亚克力毛玻璃
- **窗口自由缩放** — 四边四角拖拽调整大小
- **三主题系统** — 日间/夜间/深蓝，菜单即时切换
- **mpv 硬解播放** — libmpv 嵌入式渲染，全格式支持
- **播放控制** — 播放/暂停、进度拖拽、音量、全屏
- **播放列表** — 侧栏管理，文件拖拽添加
- **键盘快捷键** — Space/方向键/F11 等完整映射
- **mpv 自动下载** — `scripts/setup_mpv.py` 一键获取引擎

### 技术细节

- PyQt6 + python-mpv，mpv 异步事件驱动
- DWM Acrylic + SetWindowCompositionAttribute 双保险毛玻璃
- ctypes 调用 dwmapi.dll / user32.dll 无额外依赖
- 四套 QSS 主题，选择器与对象名严格对应

## 0.0.1（2026-06-20）

### ✨ 新功能

- **mpv 播放引擎** — libmpv 嵌入式渲染，GPU 硬解自动启用
- **播放控制** — 播放/暂停、进度条拖拽、音量滑块、全屏切换
- **文件拖拽** — 从资源管理器直接拖入文件/文件夹
- **播放列表** — 侧栏管理，双击切换，清空/删除选中
- **键盘快捷键** — Space/方向键/F11/Ctrl+O 等完整映射
- **暗色主题（夜间）** — 三套主题 QSS（日间/夜间/深蓝），菜单即时切换
- **mpv 自动下载** — `scripts/setup_mpv.py` 一键获取 Windows 版 mpv 引擎
- **macOS 风格标题栏** — 交通灯按钮（红 #ff5f56 / 黄 #ffbd2e / 绿 #27c93f），hover 显示图标，可拖拽
- **Windows 亚克力毛玻璃** — DWM Acrylic（Win11 22H2+）/ SetWindowCompositionAttribute（Win10）双保险
- **无框窗口** — FramelessWindowHint + WA_TranslucentBackground，内容层透明透出毛玻璃
- **四边四角缩放** — 鼠标移至边缘/顶点自动变形缩放光标，按住拖拽自由调节窗口
- **三主题切换** — 日间（浅色）/ 夜间（深色）/ 深蓝，菜单栏「主题」子菜单即时切换

### 技术细节

- 架构：PyQt6 + python-mpv，主进程单线程 + mpv 异步事件
- 进度轮询 250ms 间隔，滑块拖拽不冲突
- 视频窗口内嵌到 QWidget HWND
- 窗口效果用 ctypes 调用 dwmapi.dll / user32.dll，无额外依赖
