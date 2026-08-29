# 📺 RedVideo

> **Windows 桌面视频播放器** · 基于 mpv 驱动 · macOS 风格界面 · 零质量损失
> _A Windows desktop video player — libmpv-powered, macOS-inspired, zero quality loss._

[![版本](https://badgen.net/badge/版本/0.4.0/red)](CHANGELOG.md)
[![平台](https://badgen.net/badge/平台/Windows%2010%2F11/blue)](https://python.org)
[![Python](https://badgen.net/badge/Python/3.11/3776ab)](https://python.org)
[![PyQt6](https://badgen.net/badge/PyQt6/6.11/green)](https://pypi.org/project/PyQt6/)
[![协议](https://badgen.net/badge/协议/MIT/grey)](LICENSE)

---

## ✨ 功能

- **mpv 驱动** — 全格式支持，硬件解码，零质量损失
- **macOS 风格** — 简洁优雅，无边框设计，Windows Acrylic 毛玻璃
- **智能连播** — 播完自动下一曲，支持单曲循环 / 列表循环
- **外挂字幕** — 自动加载同名字幕，拖入 .srt / .ass 即挂载
- **画面操作** — 双击全屏、单击暂停、滚轮调音量，操作有 OSD 反馈
- **播放记忆** — 断点续播，记住音量 / 倍速 / 主题 / 播放列表
- **截图** — 一键保存当前画面到视频同目录

## ⌨️ 快捷键

| 按键 | 功能 |
| --- | --- |
| Space | 播放 / 暂停 |
| ← / → | 快退 / 快进 5s |
| Ctrl+← / Ctrl+→ | 快退 / 快进 30s |
| ↑ / ↓ | 音量 ±5% |
| [ / ] | 减速 / 加速 0.1x |
| L | 切换循环模式 |
| S | 截图 |
| F / F11 | 全屏 |
| M | 静音 |
| Ctrl+O | 打开文件 |
| Ctrl+I | 播放列表 |
| Delete | 移除选中项 |
| Esc | 退出全屏 |
| Ctrl+Q | 退出 |

## 📦 安装

```bash
pip install -r requirements.txt
```

## 🚀 运行

```bash
python main.py
```

## 📝 更新日志

详见 [CHANGELOG.md](CHANGELOG.md)

## 📄 协议

MIT
