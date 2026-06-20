# RedVideo 更新日志

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
