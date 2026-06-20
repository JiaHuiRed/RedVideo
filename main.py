"""RedVideo — Windows 桌面视频播放器"""

import sys
import os

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
os.environ["PATH"] = os.path.join(BASE, "bin") + os.pathsep + os.environ.get("PATH", "")

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from player.window import MainWindow


def main():
    if hasattr(Qt, "HighDpiScaleFactorRoundingPolicy"):
        app = QApplication(sys.argv)
        app.setStyle("Fusion")
    else:
        app = QApplication(sys.argv)

    app.setApplicationName("RedVideo")
    app.setOrganizationName("RedStudio")

    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
