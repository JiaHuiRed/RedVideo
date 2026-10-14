# -*- coding: utf-8 -*-
"""pytest 共享配置：offscreen Qt + libmpv PATH（与 main.py 启动时一致）。"""

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
# python-mpv 用 find_library 扫 PATH 找 libmpv-2.dll，测试环境也要指到 bin/
os.environ["PATH"] = str(_ROOT / "bin") + os.pathsep + os.environ.get("PATH", "")

import pytest
from PyQt6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app
