"""讲解词对齐机检（页面 ↔ 讲解同源）测试——用户验收教训：讲解有、页面无 = 不合格。

D18 FR7.8 追加：备注/讲解词输入从"页面文字"改为 storyline 推演链
（sowhat/framing/bridge_from/part）——本文件锁定推演链各环真的进了产出、且签名向后兼容。
"""

from __future__ import annotations

import pytest

from engine.narration import narrate_pptx
from engine.speaker_notes import (
    _spoken,
    check_narration_aligned,
    narration_for_line,
    narration_for_storyline,
    narration_list_for_pptx,
    notes_for_line,
)


def test_aligned_ok():
    # 页面有 −20% / 18% / 11%，讲解念的也是这几个 → 对齐
    page = "净利 −20% 净利率 18%→11%"
    nar = "净利负20%、净利率18%降到11%"
    assert check_narration_aligned(page, nar) == []


def test_misaligned_warns():
    # 页面只有 −20%，讲解却念了 18% / 11% → 逮住
    out = check_narration_aligned("净利 −20%", "净利负20%、净利率18%降到11%")
    assert any(i["rule"] == "narration_page_misaligned" for i in out)


# ── B2-9 回归（2026-07-02 saopan扫盘）：TTS 旧版把 "→" 一律念"降到"（30%→45% 明明是升·讲反事实）、
#    "-" 一律念"负"（2023-2025 被念成"2023负2025"）——"→"改方向中立的"到"，"-"分语境 ──
def test_spoken_arrow_is_direction_neutral():
    assert _spoken("30%→45%") == "30%到45%"        # 上升场景不再被念成"降到"
    assert _spoken("45%→30%") == "45%到30%"        # 下降场景同样成立（"到"两头都对）


def test_spoken_dash_between_digits_is_range():
    assert _spoken("2023-2025") == "2023到2025"     # 年份区间不再是"2023负2025"
    assert _spoken("30%-45%") == "30%到45%"         # 百分数区间（% 后接数字也算范围）


def test_spoken_leading_dash_is_negative():
    assert _spoken("-5%") == "负5%"                  # 行首负号
    assert _spoken("增速-3%") == "增速负3%"          # 中文后的负号
    assert _spoken("−20%") == "负20%"                # U+2212 数学负号先归一再判


def test_spoken_hyphen_in_words_kept():
    assert _spoken("T-shirt") == "T-shirt"           # 后面不是数字的连字符保留·不乱念"负"


def test_narration_for_line_uses_neutral_arrow():
    line = {"n": 3, "page_type": "数据论断", "claim": "盈利能力在改善",
            "evidence": [{"dim": "毛利率", "data": "30%→45%"}]}
    nar = narration_for_line(line, seed=3)
    assert "30%到45%" in nar and "降到" not in nar


# ── D18 FR7.8：备注/讲解词吃 storyline 推演链（sowhat/framing/bridge_from/part）──────────


def test_notes_reads_stage_not_stale_scr():
    # 2026-07-01 storyline 字段 scr→stage 改名后，notes 旧版还在读 scr → 新数据"段"位恒空；
    # 修复后：读 stage、旧落盘数据的 scr 键兜底。
    assert "C 段" in notes_for_line({"n": 5, "stage": "C", "claim": "x", "page_type": "数据论断"})
    assert "S 段" in notes_for_line({"n": 1, "scr": "S", "claim": "x", "page_type": "封面"})


def test_notes_carry_part_and_bridge():
    line = {"n": 7, "stage": "C", "claim": "本章看渠道", "page_type": "转场",
            "part": "渠道诊断", "bridge_from": "人群画像已锁定 Z 世代"}
    notes = notes_for_line(line)
    assert "Part·渠道诊断" in notes                      # 章节位置进备注头
    assert "承接上章：人群画像已锁定 Z 世代" in notes     # 承接上章结论进备注


def test_narration_transition_uses_bridge_from():
    line = {"n": 7, "page_type": "转场", "claim": "接下来看渠道",
            "bridge_from": "人群画像已锁定 Z 世代"}
    nar = narration_for_line(line, seed=7)
    assert "人群画像已锁定 Z 世代" in nar                 # 转场念的是承接链，不是光念本页 claim


def test_narration_transition_falls_back_to_prev_line():
    # 旧数据没填 bridge_from：退回上一行 claim（同样来自推演链·不是模板编造）
    nar = narration_for_line({"n": 7, "page_type": "转场", "claim": "接下来看渠道"},
                             seed=7, prev_line={"n": 6, "claim": "成本失控在人力"})
    assert "成本失控在人力" in nar


def test_narration_data_page_lands_on_sowhat():
    line = {"n": 5, "page_type": "数据论断", "claim": "失控在人力", "sowhat": "定位病灶",
            "evidence": [{"dim": "人力占比", "data": "42%→58%"}],
            "framing": {"stance": "效率失控", "counter_read": "战略储备", "basis": "人均产出降"}}
    nar = narration_for_line(line, seed=5)
    assert "定位病灶" in nar                              # sowhat 落点收尾（推演链最后一环）
    assert "战略储备" in nar and "人均产出降" in nar      # 反方处理链保留


def test_narration_part_opened_announces_chapter():
    sl = {"lines": [
        {"n": 2, "page_type": "数据论断", "claim": "市场在涨", "part": "市场诊断",
         "evidence": [{"dim": "规模", "data": "+12%"}]},
        {"n": 3, "page_type": "数据论断", "claim": "但份额在跌", "part": "市场诊断",
         "evidence": [{"dim": "份额", "data": "-3%"}]},
    ]}
    nar = narration_for_storyline(sl)
    assert "进入市场诊断这一部分" in nar[2]               # Part 首页报站（pritzker"第七站"式）
    assert "进入市场诊断这一部分" not in nar[3]           # 同 Part 后续页不重复报站


def test_narration_list_for_pptx_orders_and_fills_gaps():
    sl = {"lines": [
        {"n": 3, "page_type": "数据论断", "claim": "B", "evidence": [{"dim": "x", "data": "1"}]},
        {"n": 1, "page_type": "封面", "claim": "A"},
    ]}
    lst = narration_list_for_pptx(sl)
    assert len(lst) == 3 and lst[0] == "A。" and lst[1] == ""   # 页 2 无 storyline 行=不配音
    assert narration_list_for_pptx(sl, total_pages=5)[4] == ""  # 指定总页数补尾部空串


def test_narration_list_for_pptx_explicit_zero_total_pages_is_empty():
    """2026-07-03 二轮扫盘批D：显式 total_pages=0 此前被 `or` 当"未传"回退到最大页号——
    0 页就该如实返回空列表（判 None 而非 falsy）。"""
    sl = {"lines": [{"n": 1, "page_type": "封面", "claim": "A"}]}
    assert narration_list_for_pptx(sl, total_pages=0) == []
    assert narration_list_for_pptx({"lines": []}, total_pages=0) == []
    assert len(narration_list_for_pptx(sl)) == 1  # 不传（None）仍取最大页号·不误伤


def test_narrate_pptx_requires_exactly_one_source():
    # fail-closed：讲稿来源必须唯一——都不传 / 都传 都在碰文件系统之前被拒
    with pytest.raises(ValueError):
        narrate_pptx("whatever.pptx")
    with pytest.raises(ValueError):
        narrate_pptx("whatever.pptx", ["a"], storyline={"lines": []})


def test_tts_say_cleans_aiff_when_afconvert_fails(tmp_path, monkeypatch):
    """2026-07-03 二轮扫盘批D：afconvert 失败此前直接抛、.aiff 中间文件泄漏——try/finally 必清。"""
    import subprocess as sp
    from pathlib import Path as P

    from engine import narration as N

    calls = []

    def fake_run(cmd, check=True):
        calls.append(cmd[0])
        if cmd[0] == "say":
            P(cmd[cmd.index("-o") + 1]).write_bytes(b"AIFF")  # say 真的落了 aiff
            return
        raise sp.CalledProcessError(1, cmd)  # afconvert 崩

    monkeypatch.setattr(N.subprocess, "run", fake_run)
    with pytest.raises(sp.CalledProcessError):
        N.tts("你好", tmp_path / "p1", engine="say")
    assert calls == ["say", "afconvert"]
    assert not (tmp_path / "p1.aiff").exists()  # 中间产物不泄漏


def test_tts_say_success_returns_m4a_and_cleans_aiff(tmp_path, monkeypatch):
    """成功路径不被 finally 误伤：返回 .m4a、.aiff 照旧清掉。"""
    from pathlib import Path as P

    from engine import narration as N

    def fake_run(cmd, check=True):
        if cmd[0] == "say":
            P(cmd[cmd.index("-o") + 1]).write_bytes(b"AIFF")
        else:  # afconvert 成功产出 m4a
            P(cmd[2]).write_bytes(b"M4A")

    monkeypatch.setattr(N.subprocess, "run", fake_run)
    out = N.tts("你好", tmp_path / "p1", engine="say")
    assert out == tmp_path / "p1.m4a" and out.exists()
    assert not (tmp_path / "p1.aiff").exists()
