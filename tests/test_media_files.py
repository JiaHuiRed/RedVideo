# -*- coding: utf-8 -*-
"""expand_media：目录递归展开与非媒体文件过滤。"""

from player.media_files import expand_media


def test_single_media_file_passes_through(tmp_path):
    f = tmp_path / "a.mp4"
    f.write_bytes(b"x")
    assert expand_media([str(f)]) == [str(f)]


def test_folder_expanded_recursively_and_sorted(tmp_path):
    (tmp_path / "b.mp4").write_bytes(b"x")
    sub = tmp_path / "season2"
    sub.mkdir()
    (sub / "a.mkv").write_bytes(b"x")
    (tmp_path / "cover.jpg").write_bytes(b"x")  # 非媒体不入列
    got = expand_media([str(tmp_path)])
    assert len(got) == 2
    assert got == sorted(got)  # 顺序稳定
    assert any(f.endswith("a.mkv") for f in got)


def test_non_media_and_subtitles_filtered_out(tmp_path):
    srt = tmp_path / "a.srt"
    srt.write_text("1", encoding="utf-8")
    txt = tmp_path / "a.txt"
    txt.write_text("x", encoding="utf-8")
    assert expand_media([str(srt), str(txt)]) == []


def test_nonexistent_file_passes_through(tmp_path):
    """文件不校验存在性：不存在的路径交给 mpv 报错（与拖拽直加行为一致）。"""
    got = expand_media([str(tmp_path / "nope.mp4")])
    assert got == [str(tmp_path / "nope.mp4")]


def test_missing_and_mixed_input(tmp_path):
    f = tmp_path / "a.mp4"
    f.write_bytes(b"x")
    txt = tmp_path / "n.txt"
    txt.write_text("x", encoding="utf-8")
    got = expand_media([str(txt), str(f)])
    assert got == [str(f)]


def test_audio_extensions_recognized(tmp_path):
    f = tmp_path / "t.flac"
    f.write_bytes(b"x")
    assert expand_media([str(f)]) == [str(f)]
