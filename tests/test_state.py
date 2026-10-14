# -*- coding: utf-8 -*-
"""RV-005/006: 状态持久化 — 原子写入 + 把状态文件当不可信输入逐字段校验。"""

import json

import pytest

import player.state as state_mod
from player.state import load, sanitize, save


@pytest.fixture
def state_file(tmp_path, monkeypatch):
    path = tmp_path / "state.json"
    monkeypatch.setattr(state_mod, "STATE_PATH", path)
    return path


class TestLoad:
    def test_missing_returns_empty(self, state_file):
        assert load() == {}

    def test_corrupted_returns_empty(self, state_file):
        state_file.write_text("{not json", encoding="utf-8")
        assert load() == {}

    def test_non_dict_returns_empty(self, state_file):
        state_file.write_text("[1, 2]", encoding="utf-8")
        assert load() == {}

    def test_roundtrip(self, state_file):
        save({"volume": 42, "theme": "day"})
        assert load() == {"volume": 42, "theme": "day"}


class TestAtomicSave:
    def test_interrupted_write_keeps_previous_content(self, state_file, monkeypatch):
        """写入中断不能把上一个有效配置截断成半个 JSON。"""
        save({"volume": 30})
        original = state_file.read_text(encoding="utf-8")

        def _boom(*a, **k):
            raise OSError("disk full")

        monkeypatch.setattr(json, "dump", _boom)
        save({"volume": 99})  # 必须静默失败
        assert state_file.read_text(encoding="utf-8") == original
        assert json.loads(original)["volume"] == 30

    def test_no_tmp_residue(self, state_file):
        save({"volume": 1})
        assert list(state_file.parent.glob("*.tmp")) == []

    def test_unwritable_dir_degrades_silently(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            state_mod, "STATE_PATH", tmp_path / "no" / "such" / "dir" / "state.json")
        save({"volume": 1})  # 不抛异常


class TestSanitize:
    def test_geometry_hex_validated(self):
        assert sanitize({"geometry": "deadbeef"})["geometry"] == "deadbeef"
        assert "geometry" not in sanitize({"geometry": "zzzz"})
        assert "geometry" not in sanitize({"geometry": 123})

    def test_volume_clamped_and_typed(self):
        assert sanitize({"volume": 150})["volume"] == 100
        assert sanitize({"volume": -5})["volume"] == 0
        assert sanitize({"volume": 42.7})["volume"] == 42
        assert "volume" not in sanitize({"volume": "loud"})
        assert "volume" not in sanitize({"volume": True})

    def test_speed_range(self):
        assert sanitize({"speed": 2.0})["speed"] == 2.0
        assert sanitize({"speed": 0.1})["speed"] == 0.1
        assert "speed" not in sanitize({"speed": 0.0})
        assert "speed" not in sanitize({"speed": 1000})
        assert "speed" not in sanitize({"speed": "fast"})

    def test_playlist_files_filtered(self):
        out = sanitize({"playlist_files": ["/v/A.mp4", 5, "", None, "/v/B.mp4"]})
        assert out["playlist_files"] == ["/v/A.mp4", "/v/B.mp4"]
        assert "playlist_files" not in sanitize({"playlist_files": "nope"})

    def test_playlist_index_floored(self):
        assert sanitize({"playlist_index": 2})["playlist_index"] == 2
        assert sanitize({"playlist_index": -9})["playlist_index"] == -1
        assert "playlist_index" not in sanitize({"playlist_index": "x"})

    def test_positions(self):
        out = sanitize({"last_position": 12.5, "last_duration": 600.0})
        assert out["last_position"] == 12.5
        assert out["last_duration"] == 600.0
        assert "last_position" not in sanitize({"last_position": -1})
        assert "last_position" not in sanitize({"last_position": None})

    def test_string_fields(self):
        out = sanitize({"theme": "day", "loop_mode": "one",
                        "last_dir": "/v", "last_file": "/v/A.mp4"})
        assert out["theme"] == "day"
        assert out["loop_mode"] == "one"
        assert out["last_dir"] == "/v"
        assert out["last_file"] == "/v/A.mp4"
        assert "theme" not in sanitize({"theme": 7})
        assert "last_file" not in sanitize({"last_file": ""})

    def test_non_dict_input(self):
        assert sanitize([1, 2]) == {}
        assert sanitize(None) == {}
