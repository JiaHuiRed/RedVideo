"""RedVideo — Windows 桌面视频播放器"""

import sys
import os


def _base() -> str:
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


BASE = _base()
sys.path.insert(0, BASE)

# 编译后 DLL 在 exe 同级 bin/，未打包进 _MEIPASS
if getattr(sys, "frozen", False):
    exe_dir = os.path.dirname(sys.executable)
    dll_dir = os.path.join(exe_dir, "bin")
else:
    dll_dir = os.path.join(BASE, "bin")
os.environ["PATH"] = dll_dir + os.pathsep + os.environ.get("PATH", "")

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from player.window import MainWindow


def main():
    # 提取命令行传入的文件路径（Windows 打开方式传参）
    file_path = None
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if args:
        file_path = os.path.abspath(args[0])

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    app.setApplicationName("RedVideo")
    app.setOrganizationName("RedStudio")

    win = MainWindow(file_path=file_path)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
