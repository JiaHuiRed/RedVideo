# 🎬 RedVideo

> **Windows 桌面视频播放器。** mpv 引擎、macOS 风格界面、零损耗。
> _A Windows desktop video player — libmpv-powered, macOS‑inspired, zero quality loss._

[![版本](https://badgen.net/badge/版本/0.1.0/red)](CHANGELOG.md)
[![平台](https://badgen.net/badge/平台/Windows%2010%2F11/blue)](https://python.org)
[![Python](https://badgen.net/badge/Python/3.11/3776ab)](https://python.org)
[![PyQt6](https://badgen.net/badge/PyQt6/6.11/green)](https://pypi.org/project/PyQt6/)
[![许可证](https://badgen.net/badge/许可证/MIT/grey)](LICENSE)

---

## ✨ 功能

- **mpv 硬解** — 全格式支持，零画质损耗
- **macOS 风格** — 红黄绿交通灯、无框窗口
- **Windows 毛玻璃** — DWM Acrylic 亚克力效果
- **三主题** — 夜间 / 日间 / 深蓝一键切换
- **自由缩放** — 四边四角拖拽调整窗口
- **全快捷键** — 键盘控制一切
- **播放列表** — 拖拽添加，侧栏管理

---

## 🚀 快速开始

```bash
pip install -r requirements.txt
python scripts/setup_mpv.py
python main.py
```

或直接双击 `main.py`。

---

## ⌨️ 快捷键

| 按键 | 功能 |
|------|------|
| `Space` | 播放 / 暂停 |
| `←` `→` | 5s 跳转 |
| `Ctrl+←` `→` | 30s 跳转 |
| `↑` `↓` | 音量 |
| `F` / `F11` | 全屏 |
| `Esc` | 退出全屏 |
| `M` | 静音 |
| `Ctrl+O` | 打开文件 |
| `Ctrl+I` | 切换播放列表 |
| `Delete` | 删除选中列表项 |
| `Ctrl+Q` | 退出 |

---

## 📋 更新日志

见 [CHANGELOG.md](CHANGELOG.md)。

---

## 💙 致谢

- 播放引擎：[mpv](https://mpv.io) / [libmpv](https://github.com/shinchiro/mpv-winbuild-cmake)
- Python 绑定：[python-mpv](https://github.com/jaseg/python-mpv)
- 界面框架：[PyQt6](https://pypi.org/project/PyQt6/)
- 构建者：敏敏
