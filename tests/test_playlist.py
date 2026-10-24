# -*- coding: utf-8 -*-
"""RV-003: 播放真值统一 — 选中行/正在播/恢复索引不再分裂。"""

import pytest

from player.playlist import PlaylistPanel


@pytest.fixture
def panel(qapp):
    p = PlaylistPanel()
    p.add_files(["/v/A.mp4", "/v/B.mp4", "/v/C.mp4"])
    yield p
    p.deleteLater()


class TestMarkPlaying:
    def test_sets_truth_selection_and_dot(self, panel):
        panel.mark_playing("/v/B.mp4")
        assert panel.current_index() == 1
        assert panel.list.currentRow() == 1
        assert not panel.list.item(1).icon().isNull()  # 红点
        assert panel.list.item(0).icon().isNull()

    def test_unknown_path_clears_truth(self, panel):
        panel.mark_playing("/v/B.mp4")
        panel.mark_playing("/v/D.mp4")  # 播放的文件不在列表里
        assert panel.current_index() == -1
        assert panel.list.item(1).icon().isNull()  # 旧红点被清掉

    def test_duplicate_path_marks_first_occurrence(self, panel):
        panel.add_files(["/v/A.mp4"])
        panel.mark_playing("/v/A.mp4")
        assert panel.current_index() == 0


class TestPrevNext:
    def test_follow_playing_row_not_selection(self, panel):
        panel.mark_playing("/v/B.mp4")
        panel.list.setCurrentRow(2)  # 用户点选 C，不应影响上/下一曲基准
        assert panel.prev_file() == "/v/A.mp4"
        assert panel.next_file() == "/v/C.mp4"

    def test_wrap(self, panel):
        panel.mark_playing("/v/C.mp4")
        assert panel.next_file() is None
        assert panel.next_file(wrap=True) == "/v/A.mp4"


class TestRemoveSelected:
    def test_remove_before_playing_shifts_row(self, panel):
        panel.mark_playing("/v/B.mp4")
        panel.list.clearSelection()  # 模拟真实单击：单击 A 会独占选中
        panel.list.item(0).setSelected(True)
        panel.remove_selected()
        assert panel.list.count() == 2
        assert panel.current_index() == 0  # B 现在第 0 行
        assert not panel.list.item(0).icon().isNull()  # 红点跟着 B
        assert panel.next_file() == "/v/C.mp4"

    def test_remove_playing_row_leaves_queue(self, panel):
        """删除正在播放项：文件继续播但退出队列导航，prev/next 无目标。"""
        panel.mark_playing("/v/B.mp4")
        panel.list.item(1).setSelected(True)
        panel.remove_selected()
        assert panel.current_index() == -1
        assert panel.list.count() == 2
        assert panel.prev_file() is None
        assert panel.next_file() is None

    def test_remove_playing_with_earlier_rows(self, panel):
        """多选删 [A,B] 且 B 正在播：不能把播放真值错指向 A。"""
        panel.mark_playing("/v/B.mp4")
        panel.list.item(0).setSelected(True)
        panel.list.item(1).setSelected(True)
        panel.remove_selected()
        assert panel.current_index() == -1
        assert panel.list.count() == 1

    def test_clear_resets_truth(self, panel):
        panel.mark_playing("/v/B.mp4")
        panel._clear()
        assert panel.current_index() == -1
        assert panel.prev_file() is None


class TestReorderTracking:
    """拖拽重排：行号从播放真值（路径）重建，不靠手工偏移。"""

    def test_move_before_playing_row_follows(self, panel):
        panel.mark_playing("/v/B.mp4")
        item = panel.list.takeItem(0)      # A 拖到末尾，模型信号与真实拖拽一致
        panel.list.insertItem(2, item)
        assert panel.current_index() == 0  # B 从第 1 行移到第 0 行
        assert panel.next_file() == "/v/C.mp4"

    def test_playing_item_moved_keeps_dot(self, panel):
        panel.mark_playing("/v/B.mp4")
        item = panel.list.takeItem(1)
        panel.list.insertItem(0, item)
        assert panel.current_index() == 0
        assert not panel.list.item(0).icon().isNull()  # 红点跟着条目对象

    def test_normkey_lookup_ignores_case_and_separators(self, panel):
        panel.add_files(["D:\\V\\B.mp4"])
        panel.mark_playing("d:/v/b.mp4")  # 大小写/分隔符不同，同一文件
        assert panel.current_index() == 3


class TestFilter:
    def test_keyword_hides_non_matching(self, panel):
        panel.filter_edit.setText("b")
        assert panel.list.item(0).isHidden()
        assert not panel.list.item(1).isHidden()
        assert panel.list.item(2).isHidden()

    def test_clearing_filter_restores(self, panel):
        panel.filter_edit.setText("b")
        panel.filter_edit.setText("")
        assert not any(panel.list.item(i).isHidden() for i in range(3))

    def test_count_label_shows_visible_over_total(self, panel):
        panel.filter_edit.setText("b")
        assert panel.lbl_count.text() == "1/3"
        panel.filter_edit.setText("")
        assert panel.lbl_count.text() == "3"

    def test_new_files_respect_active_filter(self, panel):
        panel.filter_edit.setText("b")
        panel.add_files(["/v/other.mp4"])
        assert panel.list.item(3).isHidden()


class TestExternalDropRouting:
    def test_subtitles_and_media_split(self, qapp):
        from player.playlist import PlaylistPanel
        p = PlaylistPanel()  # external_drop → _handle_dropped 已在构造时接好
        subs = []
        p.subtitle_files_dropped.connect(subs.extend)
        p.list.external_drop.emit(["/v/ep1.srt", "/v/ep1.mp4", "/v/ep2.mkv"])
        assert subs == ["/v/ep1.srt"]
        assert p.list.count() == 2  # media 走 add_files
        p.deleteLater()
