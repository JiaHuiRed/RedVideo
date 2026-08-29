# RedVideo 更新日志

## 0.4.0（2026-08-29）

> 播放体验大版本：连播/循环、画面鼠标操作、OSD 反馈、外挂字幕、截图，以及一批 Bug 修复与性能优化。

### ✨ 新增

- **播完自动连播 + 循环模式** — mpv 观察 `eof-reached`，播完自动播下一曲；菜单或 `L` 键切换 播完停止/单曲循环/列表循环，模式持久化；单曲循环回到起点续播，列表循环回卷到第一条
- **画面鼠标交互** — 双击画面切换全屏（全屏时隐藏播放列表侧栏，退出恢复）；单击画面暂停/恢复（延迟一个双击间隔判定，与双击互不误触）；滚轮在画面上以 5% 步进调音量
- **OSD 屏显反馈** — 快进/快退、音量、静音、倍速、循环模式切换时画面短暂显示文字（mpv show-text，渲染在视频层上，全屏也可见）
- **外挂字幕** — `sub-auto=fuzzy` 自动加载同名/近似命名字幕；拖入 .srt/.ass/.ssa/.vtt/.sub 直接挂载到当前播放（媒体文件照常进列表）；菜单新增"加载字幕..."
- **截图** — `S` 键或菜单"截图"，保存到视频同目录 `<片名> <时分秒>.png`，含字幕画面
- **单击进度条跳转** — 进度条子类化，单击凹槽直接跳到点击位置并可继续拖拽（原生 QSlider 单击只走一个 page step 且不触发 seek）
- **多文件打开** — 资源管理器多选"打开方式"时全部文件进播放列表（原来只取第一个）
- **缺 libmpv 友好提示** — 找不到 libmpv-2.dll 时弹错误对话框并提示运行 setup_mpv.py，`import main` 不再裸崩

### 🐛 修复

- **倍速按钮不生效** — `ControlsBar.speed_changed` 信号从未连接，点按钮只改标签文字不动播放速度
- **上一曲/下一曲走错行** — 导航基准从"用户点选的行"改为"正在播放的行"（`mark_playing`），删除条目/清空列表时同步维护
- **播放新文件强制展开播放列表** — 0.3.1 声称已修但代码残留，现在尊重 Ctrl+I 的显隐状态
- **`last_dir` 只存不读** — 启动时恢复上次打开目录，文件对话框不再从空白开始
- **全屏留 1px 边框** — `changeEvent` 只判 `isMaximized()`，补上 `isFullScreen()`
- **播放记忆在 Program Files 下静默失效** — `state.json` 写到安装目录会因权限失败，迁移到 `%APPDATA%/RedVideo/`，旧文件首次启动自动拷贝
- **断点续播竞态** — 固定 200ms 定时器赶不上慢盘/网络加载，改为挂一次性 `file_loaded` 信号后再 seek
- **空格双触发** — 控制栏/交通灯/菜单按钮设 `NoFocus`，点过按钮后按空格不再快捷键+按钮各触发一次
- **Win10 毛玻璃兜底失效** — `DwmSetWindowAttribute` 失败通过 HRESULT 返回而非异常，原代码误判成功导致 SWCA Acrylic 永远不生效；同时修正 SWCA tint 值（原值 alpha=0 与注释不符）并按主题区分深浅遮罩
- **倍速下限不一致** — 连接 `speed_changed` 后 UI 的 0.5x 下限成为真实下限，`[` 键再按也不会出现"实际 0.4x 显示 0.5x"

### ⚡ 性能

- **duration 缓存** — 时间标签不再每个 time-pos tick（约 60Hz）跨线程读一次 mpv duration
- **进度条节流** — 滑块更新并入 100ms 节流定时器，短视频不再每帧重绘；单次定时器活跃时不再被重置，消除节流饿死隐患
- **播放列表批量添加** — `setUpdatesEnabled(False)` 包裹插入过程，2000 条约 20ms
- **mpv 参数** — `hwdec` auto→auto-safe 避开兼容性差的硬解路径；删除与默认值相同的 `demuxer-max-bytes`

## 0.3.2（2026-07-29）

> 新增播放记忆、打开即播上次、倍速 0.1x 步进。

### ✨ 新增

- **播放记忆持久化** — 新增 `player/state.py`，自动保存/恢复窗口几何、音量、倍速、主题、上次文件和断点位置，重启后自动还原
- **打开即播上次** — 启动时自动恢复上次播放文件和断点位置（命令行传参优先）
- **倍速控制 0.1x 步进** — 底部栏新增倍速按钮，支持 0.5x/1.0x/1.5x/2.0x 循环切换；快捷键 `[` / `]` 以 0.1x 步进增减

### ♛ 优化

- **进度标签显示倍速** — `ControlsBar.update_time()` 时间显示末尾追加当前倍速，一目了然

## 0.3.1（2026-07-29）

> 稳定性修复：单实例通信异常保护、mpv 下载超时、代码清理。

### 🐛 修复

- **单实例通信 socket 泄漏** — `main.py` 的 `_send_to_existing` 和 `_on_new_instance` 在异常路径下未调用 `disconnectFromServer()`，现在都包上 `try/finally`，确保连接总是被清理
- **mpv 下载无限等待** — `scripts/setup_mpv.py` 的 `urlopen` 缺少 timeout，GFW/慢网下会卡死整个安装流程，现在加 `timeout=30` 并打印错误后退出

### ♻️ 重构 / 优化

- **清理 `player/playlist.py` 空行噪音** — 删除重复空行和重复注释块，182 行压缩到 110 行，结构更清晰
- **修复 `_play_file` 状态冲突** — `player/window.py` 的 `_play_file` 不再每次强设 `setVisible(True)`，改从 `isVisible()` 判断，避免和 `toggle_playlist` 的显隐状态冲突
- **删除冗余初始化** — `main.py` 的 `_root_layout = None` 被 `_build_ui()` 立刻覆盖，属于死代码，直接删除
- **删除未使用的导入** — `scripts/gen_icon.py` 的 `ImageFilter` 和 `ImageFont` 从未使用，清理冗余导入
- **删除未使用的 QStyle 导入** — `player/window.py` 中导入 `QStyle` 但从未使用，删除冗余导入

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
