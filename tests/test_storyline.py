"""策略层 storyline schema + 机检硬门测试。

覆盖：目的卡/假设树/SCR 弧校验、降解成合法 deck_outline、storyline 硬门(决策结尾 error / 主题式·含糊 warn)。
"""

from __future__ import annotations

import pytest

from reinforce.deck_rules import storyline as SG
from reinforce.deck_state import validate_outline
from reinforce.storyline_state import (FRAMEWORK_MODE_AFFINITY, FRAMEWORK_PICK_WHEN, FRAMEWORK_STAGES,
                                       add_line, new_storyline, set_hypothesis_tree, to_outline,
                                       validate_storyline)


def _full_storyline() -> dict:
    sl = new_storyline("brief 文本", purpose="董事会批成本管控专项", intent="说服决策",
                       audience=["董事会"], decision_ask="今日批准专项", domain="财务")
    set_hypothesis_tree(sl, "收入增25%是虚假繁荣，需立即批专项管控否则明年转亏",
                        [{"id": "H1", "claim": "成本增速>收入增速", "test": "成本同比 vs 收入同比"},
                         {"id": "H2", "claim": "失控集中在人力", "test": "成本结构+人均产出"},
                         {"id": "H3", "claim": "明年由盈转亏", "test": "净利率外推+敏感性"}])
    add_line(sl, 1, "S", "收入增25%却净利降20%，建议批专项", "metric_callout", "执行摘要", "全deck浓缩")
    add_line(sl, 2, "S", "收入增25%、ARR创新高是好年景", "bar_callout", "共识", "先给点头事实")
    add_line(sl, 3, "C", "但净利反降20%，增长没换来盈利", "line_compare", "冲突", "打破共识")
    add_line(sl, 4, "C", "成本增速50%是收入25%的整2倍", "waterfall", "归因", "钱去哪了")
    add_line(sl, 5, "R", "失控在人力，占比42%升至58%", "stacked_over_time", "定位", "病灶")
    add_line(sl, 6, "R", "请董事会今日批准专项，CFO牵头", "decision_box", "决策", "owner+日期")
    return sl


# ── schema 校验 ──
def test_full_storyline_valid():
    assert validate_storyline(_full_storyline())["valid"]


def test_missing_purpose_invalid():
    sl = _full_storyline(); sl["purpose"] = ""
    assert not validate_storyline(sl)["valid"]


def test_hypothesis_needs_falsifiable_test():
    sl = _full_storyline(); sl["sub_hypotheses"][0].pop("test")
    assert not validate_storyline(sl)["valid"]


def test_scr_missing_segment_invalid():
    sl = new_storyline("b", "p", "说服决策", ["董事会"], "批")
    set_hypothesis_tree(sl, "gt", [{"id": "H1", "claim": "c", "test": "t"},
                                   {"id": "H2", "claim": "c", "test": "t"}])
    add_line(sl, 1, "S", "收入增25%", "metric_callout")
    add_line(sl, 2, "C", "净利降20%", "waterfall")  # 缺 R 段
    assert not validate_storyline(sl)["valid"]


def test_scr_out_of_order_invalid():
    sl = new_storyline("b", "p", "说服决策", ["董事会"], "批")
    set_hypothesis_tree(sl, "gt", [{"id": "H1", "claim": "c", "test": "t"},
                                   {"id": "H2", "claim": "c", "test": "t"}])
    add_line(sl, 1, "S", "收入增25%", "metric_callout")
    add_line(sl, 2, "R", "批专项", "decision_box")
    add_line(sl, 3, "C", "净利降20%", "waterfall")  # R 后又 C = 乱序
    assert not validate_storyline(sl)["valid"]


# ── 故事框架（2026-07-01·gist_AI-Presentation-Coach 启发·D6 决策记录🟢采纳）──
def test_default_framework_is_scr():
    sl = new_storyline("b", "p", "说服决策", ["受众"], "批")
    assert sl["framework"] == "SCR"  # 不传 framework 向后兼容·跟改动前行为一致


def test_all_14_frameworks_have_pick_when():
    # 14 = SCR(项目默认) + coach 13 个·每个都要有引导对齐用的"何时选"依据，不能有声明了没配文案的死条目
    assert set(FRAMEWORK_STAGES) == set(FRAMEWORK_PICK_WHEN)
    assert len(FRAMEWORK_STAGES) == 14


# ── mode×framework 软契合提示（2026-07-01·修复"接了这么多GitHub项目会不会互相冲突"的第二处缺口）──
def _bca_storyline(mode):
    sl = new_storyline("b", "案例pitch", "说服决策", ["客户"], "签约",
                       mode=mode, framework="before_change_after")
    set_hypothesis_tree(sl, "gt", [{"id": "H1", "claim": "c", "test": "t"}])
    add_line(sl, 1, "Before", "转化率仅2%", "metric_callout")
    add_line(sl, 2, "Change", "接入推荐引擎", "bar_callout")
    add_line(sl, 3, "After", "转化率提升至8%，请续约", "decision_box")
    return sl


def test_mismatched_mode_framework_warns_not_errors():
    # before_change_after 常配 narrative/showcase(D6记录·出处coach「Best suited for」)，配pyramid是罕见搭配
    sl = _bca_storyline("pyramid")
    r = validate_storyline(sl)
    assert r["valid"]  # warn 不阻断，不是 error
    assert any("不是常见搭配" in i["msg"] for i in r["issues"] if i["sev"] == "warn")


def test_matched_mode_framework_no_warning():
    sl = _bca_storyline("narrative")  # before_change_after 的推荐 mode 之一
    r = validate_storyline(sl)
    assert not any("不是常见搭配" in i["msg"] for i in r["issues"])


def test_scr_default_framework_never_warns_regardless_of_mode():
    # SCR 是项目默认骨架·CFO(pyramid)/Descente(narrative)两个真实demo都验证过任意mode能配·不在检查范围内
    for mode in ("pyramid", "narrative", "briefing", "showcase"):
        sl = new_storyline("b", "p", "说服决策", ["受众"], "批", mode=mode)  # framework 缺省=SCR
        set_hypothesis_tree(sl, "gt", [{"id": "H1", "claim": "c", "test": "t"}])
        add_line(sl, 1, "S", "s", "cover")
        add_line(sl, 2, "C", "c", "waterfall")
        add_line(sl, 3, "R", "r", "decision")
        assert not any("不是常见搭配" in i["msg"] for i in validate_storyline(sl)["issues"])


def test_all_non_scr_frameworks_have_affinity_entry():
    # 13个coach框架都该有软提示依据·不能有声明了stages却没配affinity的死条目(同chart_assign死字段教训)
    assert set(FRAMEWORK_STAGES) - {"SCR"} == set(FRAMEWORK_MODE_AFFINITY)


def test_non_default_framework_valid_when_arc_complete():
    sl = new_storyline("b", "案例pitch", "说服决策", ["客户"], "签约", framework="before_change_after")
    set_hypothesis_tree(sl, "gt", [{"id": "H1", "claim": "c", "test": "t"}])
    add_line(sl, 1, "Before", "客户上线前转化率仅2%", "metric_callout")
    add_line(sl, 2, "Change", "接入我们的推荐引擎", "bar_callout")
    add_line(sl, 3, "After", "转化率提升至8%，请批准续约", "decision_box")
    assert validate_storyline(sl)["valid"]


def test_non_default_framework_missing_stage_invalid():
    sl = new_storyline("b", "p", "说服决策", ["客户"], "签约", framework="abt")
    set_hypothesis_tree(sl, "gt", [{"id": "H1", "claim": "c", "test": "t"}])
    add_line(sl, 1, "And", "现状", "metric_callout")
    add_line(sl, 2, "But", "冲突", "waterfall")  # 缺 Therefore
    assert not validate_storyline(sl)["valid"]


def test_non_default_framework_out_of_order_invalid():
    sl = new_storyline("b", "p", "说服决策", ["客户"], "签约", framework="abt")
    set_hypothesis_tree(sl, "gt", [{"id": "H1", "claim": "c", "test": "t"}])
    add_line(sl, 1, "And", "现状", "metric_callout")
    add_line(sl, 2, "Therefore", "结论", "decision_box")
    add_line(sl, 3, "But", "冲突", "waterfall")  # Therefore 后又 But = 乱序
    assert not validate_storyline(sl)["valid"]


def test_stage_not_in_declared_framework_rejected():
    # 声明 framework=golden_circle(Why/How/What)，行却用了 SCR 的 S/C/R 标签——不该被当合法
    sl = new_storyline("b", "p", "说服决策", ["受众"], "批", framework="golden_circle")
    set_hypothesis_tree(sl, "gt", [{"id": "H1", "claim": "c", "test": "t"}])
    add_line(sl, 1, "S", "误用了 SCR 的标签", "metric_callout")
    assert not validate_storyline(sl)["valid"]


def test_invalid_framework_name_rejected():
    sl = _full_storyline(); sl["framework"] = "乱填的框架"
    assert not validate_storyline(sl)["valid"]


def test_freytag_five_stage_arc():
    # Freytag 五段是 14 个框架里段数最多的(5段)·确认通用弧校验不是只对3段写死的
    sl = new_storyline("b", "深度案例复盘", "复盘总结", ["内部团队"], "汲取经验", framework="freytag")
    set_hypothesis_tree(sl, "gt", [{"id": "H1", "claim": "c", "test": "t"}])
    add_line(sl, 1, "铺垫", "项目背景", "metric_callout")
    add_line(sl, 2, "上升", "风险逐步累积", "waterfall")
    add_line(sl, 3, "高潮", "系统崩溃当天", "line_compare")
    add_line(sl, 4, "下降", "应急响应与止损", "stacked_over_time")
    add_line(sl, 5, "结局", "复盘结论与改进项", "decision_box")
    assert validate_storyline(sl)["valid"]


def test_stage_facet_survives_to_outline_for_non_default_framework():
    sl = new_storyline("b", "p", "说服决策", ["客户"], "签约", framework="before_change_after")
    set_hypothesis_tree(sl, "gt", [{"id": "H1", "claim": "c", "test": "t"}])
    add_line(sl, 1, "Before", "转化率仅2%", "metric_callout")
    add_line(sl, 2, "Change", "接入推荐引擎", "bar_callout")
    add_line(sl, 3, "After", "转化率提升至8%，请续约", "decision_box")
    o = to_outline(sl)
    assert o["pages"][0]["facets"]["stage"] == "Before"


# ── 降解 to_outline（page_function 优先级：显式指定 > page_type 兜底 > chart 技术名垫底）──
def test_to_outline_produces_valid_deck():
    o = to_outline(_full_storyline())
    assert validate_outline(o)["valid"]
    assert len(o["pages"]) == 6
    # p4 (chart="waterfall") 未显式传 page_function，兜底到 page_type 默认值"数据论断"——
    # 不再是旧bug"page_function='waterfall'"(英文技术名冒充中文页型卡词汇、检索必然落空)
    assert o["pages"][3]["page_function"] == "数据论断"
    assert o["pages"][3]["facets"]["chart"] == "waterfall"  # chart 技术词汇独立保留，未丢
    assert o["pages"][0]["facets"]["stage"] == "S"         # 框架 stage 随大纲下传


def test_to_outline_prefers_explicit_page_function():
    sl = new_storyline("b", "p", "说服决策", ["受众"], "批")
    set_hypothesis_tree(sl, "gt", [{"id": "H1", "claim": "c", "test": "t"}])
    add_line(sl, 1, "S", "封面", "cover", page_type="封面")
    add_line(sl, 2, "C", "成本增速50%是收入的2倍", "waterfall",
             page_function="案例效果against行业中位数柱状对标")  # 阶段4查过范本库·有贴切真实卡就传
    add_line(sl, 3, "R", "请批准", "decision", page_type="决策")
    o = to_outline(sl)
    assert o["pages"][1]["page_function"] == "案例效果against行业中位数柱状对标"


def test_to_outline_falls_back_to_chart_when_no_page_type():
    # page_type 传空字符串(极端情况)才会真正落到 chart 技术名垫底
    sl = new_storyline("b", "p", "说服决策", ["受众"], "批")
    set_hypothesis_tree(sl, "gt", [{"id": "H1", "claim": "c", "test": "t"}])
    add_line(sl, 1, "S", "封面", "cover", page_type="封面")
    add_line(sl, 2, "C", "瀑布图页", "waterfall", page_type="")
    add_line(sl, 3, "R", "请批准", "decision", page_type="决策")
    o = to_outline(sl)
    assert o["pages"][1]["page_function"] == "waterfall"


def test_to_outline_refuses_invalid():
    sl = _full_storyline(); sl["governing_thought"] = ""
    with pytest.raises(ValueError, match="拒降解"):
        to_outline(sl)


# ── 机检硬门 ──
def test_gate_passes_full():
    assert SG.run_storyline_gate(_full_storyline())["passed"]


def test_gate_no_decision_ending_errors():
    sl = _full_storyline()
    sl["lines"][-1]["claim"] = "成本结构分析"; sl["lines"][-1]["role"] = ""
    r = SG.run_storyline_gate(sl)
    assert not r["passed"]
    assert any(i["rule"] == "no_decision_ending" for i in r["issues"])


def test_gate_topic_title_warns():
    lines = [{"n": 1, "claim": "成本结构", "sowhat": "s"}]  # 无数字无方向词
    assert any(i["rule"] == "topic_title" for i in SG.check_claim_titles(lines))


def test_gate_vague_word_warns():
    lines = [{"n": 1, "claim": "人力成本表现良好", "sowhat": "s"}]
    assert any(i["rule"] == "vague" for i in SG.check_vague_words(lines))


# ── 近似重复标题检测（2026-07-01 yanjiu研究驱动评估🟢采纳·Instrumenta Levenshtein≤2）──
def test_duplicate_titles_exact_match_warns():
    lines = [{"n": 1, "claim": "成本结构人力占比升至58%"}, {"n": 2, "claim": "成本结构人力占比升至58%"}]
    out = SG.check_duplicate_titles(lines)
    assert out and out[0]["rule"] == "duplicate_title" and out[0]["sev"] == "warn" and out[0]["n"] == 2


def test_duplicate_titles_near_match_warns():
    lines = [{"n": 1, "claim": "成本结构人力占比升至58%"}, {"n": 2, "claim": "成本结构人力占比升至59%"}]
    out = SG.check_duplicate_titles(lines)  # 编辑距离1(58→59)
    assert any(i["rule"] == "duplicate_title" for i in out)


def test_duplicate_titles_distinct_claims_pass():
    lines = [{"n": 1, "claim": "成本结构人力占比升至58%"}, {"n": 2, "claim": "收入增速三年首次转负"}]
    assert SG.check_duplicate_titles(lines) == []


def test_duplicate_titles_skips_non_argument_page_types():
    # 情绪/封面类标题本就该短促接近·不比
    lines = [{"n": 1, "claim": "谢谢", "page_type": "落幕"}, {"n": 2, "claim": "谢谢", "page_type": "落幕"}]
    assert SG.check_duplicate_titles(lines) == []


def test_duplicate_titles_wired_into_gate():
    sl = _full_storyline()
    sl["lines"][0]["claim"] = sl["lines"][1]["claim"]  # 强制前两行标题完全相同
    out = SG.run_storyline_gate(sl)["issues"]
    assert any(i["rule"] == "duplicate_title" for i in out)


# ── 相邻页版式去重检测（2026-07-01 yanjiu研究驱动评估🟢采纳·02号页型手法"相邻页不得同版式"）──
def test_adjacent_layout_repeat_same_chart_warns():
    lines = [{"n": 1, "claim": "a", "chart": "bar_callout"}, {"n": 2, "claim": "b", "chart": "bar_callout"}]
    out = SG.check_adjacent_layout_repeat(lines)
    assert out and out[0]["rule"] == "adjacent_layout_repeat" and out[0]["sev"] == "warn" and out[0]["n"] == 2


def test_adjacent_layout_repeat_different_chart_passes():
    lines = [{"n": 1, "claim": "a", "chart": "bar_callout"}, {"n": 2, "claim": "b", "chart": "waterfall"}]
    assert SG.check_adjacent_layout_repeat(lines) == []


def test_adjacent_layout_repeat_skips_non_argument_charts():
    # decision_box 允许连续出现·不是论证节奏的一部分
    lines = [{"n": 1, "claim": "a", "chart": "decision_box"}, {"n": 2, "claim": "b", "chart": "decision_box"}]
    assert SG.check_adjacent_layout_repeat(lines) == []


def test_adjacent_layout_repeat_skips_non_argument_page_types():
    lines = [{"n": 1, "claim": "谢谢", "chart": "hero_text", "page_type": "落幕"},
             {"n": 2, "claim": "谢谢", "chart": "hero_text", "page_type": "落幕"}]
    assert SG.check_adjacent_layout_repeat(lines) == []


def test_adjacent_layout_repeat_non_adjacent_same_chart_not_flagged():
    # 隔了一页(waterfall)的两个bar_callout不算"相邻"
    lines = [{"n": 1, "claim": "a", "chart": "bar_callout"}, {"n": 2, "claim": "b", "chart": "waterfall"},
             {"n": 3, "claim": "c", "chart": "bar_callout"}]
    assert SG.check_adjacent_layout_repeat(lines) == []


def test_adjacent_layout_repeat_wired_into_gate():
    sl = _full_storyline()
    # lines[1]="bar_callout"(n=2)/lines[2]="line_compare"(n=3)均不在NON_ARGUMENT_CHARTS·强制相邻相同
    sl["lines"][2]["chart"] = sl["lines"][1]["chart"]
    out = SG.run_storyline_gate(sl)["issues"]
    assert any(i["rule"] == "adjacent_layout_repeat" for i in out)


# ── 证据组深度 + 数据解读（用户洞察：一组数据论证 + 数据靠论点赋义）──
def test_gate_flags_thin_evidence():
    lines = [{"n": 5, "chart": "stacked_over_time", "evidence": [{"dim": "结构"}]}]  # 仅 1 证据
    assert any(i["rule"] == "thin_evidence" for i in SG.check_evidence_depth(lines))


def test_gate_evidence_satisfied_when_multi():
    lines = [{"n": 5, "chart": "stacked_over_time",
              "evidence": [{"dim": "结构"}, {"dim": "效率"}, {"dim": "基准"}]}]
    assert SG.check_evidence_depth(lines) == []


def test_gate_skips_evidence_for_cover_and_decision():
    lines = [{"n": 1, "chart": "metric_callout", "evidence": []},
             {"n": 9, "chart": "decision_box", "evidence": []}]
    assert SG.check_evidence_depth(lines) == []  # 封面/决策非论证页·豁免


def test_gate_flags_no_framing():
    lines = [{"n": 5, "chart": "waterfall", "evidence": [{"dim": "a"}, {"dim": "b"}], "framing": {}}]
    assert any(i["rule"] == "no_framing" for i in SG.check_framing(lines))


def test_gate_framing_satisfied_with_stance():
    lines = [{"n": 5, "chart": "waterfall", "framing": {"stance": "失控"}}]
    assert SG.check_framing(lines) == []


# ── 双模式（07 演讲版 vs 阅读版·visual_style 轴）──
def test_invalid_visual_style_rejected():
    sl = _full_storyline(); sl["visual_style"] = "乱填"
    assert not validate_storyline(sl)["valid"]


def test_speech_mode_flags_no_rhythm():
    # D18 FR7.1：密度轴改用 delivery_purpose（visual_style 已是美学轴·手改旧字段不再表达密度意图）
    sl = _full_storyline(); sl["delivery_purpose"] = "演讲版"  # 全数据论断页·无情绪/转场
    rules = {i["rule"] for i in SG.run_storyline_gate(sl)["issues"]}
    assert "no_emotion_page" in rules and "no_transition" in rules


def test_speech_mode_satisfied_with_rhythm():
    sl = _full_storyline(); sl["visual_style"] = "演讲版"
    sl["lines"][1]["page_type"] = "转场"
    sl["lines"][2]["page_type"] = "情绪slogan"
    assert SG.check_rhythm(sl) == []


def test_reading_mode_flags_missing_subtitle():
    sl = _full_storyline()  # 阅读版·论证页无 subtitle
    assert any(i["rule"] == "no_reading_subtitle" for i in SG.run_storyline_gate(sl)["issues"])


def test_reading_subtitle_satisfied():
    sl = _full_storyline()
    for ln in sl["lines"]:
        ln["subtitle"] = "本页作用说明"
    assert SG.check_reading_subtitle(sl) == []


# ── 数字溯源（阶段3·01 雷区7）──
def test_evidence_no_source_warns():
    lines = [{"n": 3, "chart": "waterfall", "page_type": "数据论断",
              "evidence": [{"dim": "净利", "data": "-20%"}]}]
    assert any(i["rule"] == "evidence_no_source" for i in SG.check_evidence_source(lines))


def test_evidence_source_ok():
    lines = [{"n": 3, "chart": "waterfall", "page_type": "数据论断",
              "evidence": [{"dim": "净利", "data": "-20%", "source": "财报2024"}]}]
    assert SG.check_evidence_source(lines) == []


def test_evidence_client_provided_exempt_from_source_warn():
    """2026-07-03 二轮扫盘批D：client_provided（客户自己的资料·D18 FR5.1 页面不标源）此前
    在这里没豁免——对齐 rules.check_source 口径后不再报警；external/未标注仍照查不误伤。"""
    lines = [{"n": 3, "chart": "waterfall", "page_type": "数据论断",
              "evidence": [{"dim": "净利", "data": "-20%", "source_type": "client_provided"},
                           {"dim": "市场规模", "data": "300亿", "source_type": "external"}]}]
    issues = SG.check_evidence_source(lines)
    assert len(issues) == 1                      # 只报 external 那条
    assert "市场规模" in issues[0]["note"]


# ── narrative/showcase mode 适配（mode 轴·真实 Descente pitch 实战暴露）──
def test_invalid_mode_rejected():
    sl = _full_storyline(); sl["mode"] = "乱填"
    assert not validate_storyline(sl)["valid"]


def test_narrative_mode_relaxes_gate():
    sl = new_storyline("b", "赢pitch", "说服决策", ["品牌方"], "选我们",
                       visual_style="演讲版", mode="narrative")
    set_hypothesis_tree(sl, "一切始于滑雪 big idea",
                        [{"id": "B1", "claim": "c", "test": "t"}, {"id": "B2", "claim": "c", "test": "t"}])
    add_line(sl, 1, "S", "封面", "cover", page_type="封面")
    add_line(sl, 2, "C", "传统套路化", "transition", page_type="转场")
    add_line(sl, 3, "C", "智性人群没被打动", "emotion", page_type="情绪slogan")
    add_line(sl, 4, "R", "big idea 溯源之旅", "climax", page_type="高潮")
    add_line(sl, 5, "R", "THE SHOW 把雪变画布", "idea", page_type="创意展示")  # 创意页无 evidence·豁免
    add_line(sl, 6, "R", "请选择我们进下一轮", "decision", page_type="决策", role="ask", sowhat="ask")
    g = SG.run_storyline_gate(sl)
    rules = {i["rule"] for i in g["issues"]}
    assert g["passed"]
    assert "evidence_no_source" not in rules   # narrative：方案数字不溯源
    assert "lead_no_decision" not in rules     # 塔顶 = big idea·不查决策指向


def test_pitch_decision_words_accepted():
    assert SG.check_decision_ending([{"n": 1, "claim": "请选择我们进下一轮", "role": "ask"}]) == []


# ── mode × visual_style 正交（08 方法论核心断言：两轴独立锁定，任意组合合法）──
@pytest.mark.parametrize("mode", ["pyramid", "narrative", "briefing", "showcase"])
@pytest.mark.parametrize("visual_style", ["演讲版", "阅读版"])
def test_mode_visual_style_any_combo_valid(mode, visual_style):
    sl = new_storyline("b", "p", "说服决策", ["受众"], "批",
                       visual_style=visual_style, mode=mode)
    set_hypothesis_tree(sl, "gt", [{"id": "H1", "claim": "c", "test": "t"}])
    add_line(sl, 1, "S", "封面", "cover", page_type="封面")
    add_line(sl, 2, "C", "转场", "transition", page_type="转场")
    add_line(sl, 3, "R", "请批准本方案", "decision", page_type="决策")
    assert validate_storyline(sl)["valid"]  # schema 合法不代表机检全过·这里只验 4×2=8 种组合不会被 schema 拒


# ── 时间锚定（真实踩过的坑：2026年了还写"2025年预计"）──
def test_temporal_freshness_no_current_year_skips():
    lines = [{"n": 1, "evidence": [{"dim": "规模", "data": "2025年预计破万亿"}]}]
    assert SG.check_temporal_freshness(lines) == []  # 不传 current_year 不查


def test_temporal_freshness_catches_stale_forecast():
    lines = [{"n": 1, "evidence": [{"dim": "规模", "data": "2025年预计破万亿"}]}]
    out = SG.check_temporal_freshness(lines, current_year=2026)
    assert any(i["rule"] == "stale_forecast" for i in out)


def test_temporal_freshness_future_year_ok():
    lines = [{"n": 1, "evidence": [{"dim": "规模", "data": "2027年预计破1.5万亿"}]}]
    assert SG.check_temporal_freshness(lines, current_year=2026) == []  # 2027 还没过·不算过期


def test_run_storyline_gate_wires_current_year():
    sl = _full_storyline()
    sl["lines"][0]["evidence"] = [{"dim": "x", "data": "2025年预计达标"}]
    g = SG.run_storyline_gate(sl, current_year=2026)
    assert any(i["rule"] == "stale_forecast" for i in g["issues"])


# ── 策略→制作 交接卡（待办①）──
def test_handoff_to_production():
    from reinforce.storyline_state import handoff_to_production
    h = handoff_to_production(_full_storyline())
    assert h["kind"] == "strategy_to_production_handoff"
    assert h["status"] == "策略定稿·待制作"
    assert len(h["outline"]["pages"]) == len(_full_storyline()["lines"])
    assert h["mode"] and h["delivery_purpose"]  # D18 FR7.1：交接卡两轴分开·密度轴看 delivery_purpose


def test_handoff_refuses_invalid():
    import pytest as _pt
    from reinforce.storyline_state import handoff_to_production
    sl = _full_storyline(); sl["purpose"] = ""
    with _pt.raises(ValueError, match="拒交接"):
        handoff_to_production(sl)


def test_handoff_refuses_quality_gate_failure():
    """schema 合法但质量机检有 error（无决策收尾）→ 同样拒交接（本轮新接入的门）。"""
    from reinforce.storyline_state import handoff_to_production
    sl = _full_storyline()
    sl["lines"][-2]["role"], sl["lines"][-2]["claim"] = "归因", "问题已定位清楚"
    sl["lines"][-1]["role"], sl["lines"][-1]["claim"] = "收尾", "专项已充分论证，供参考"
    with pytest.raises(ValueError, match="质量机检未过"):
        handoff_to_production(sl)


def test_handoff_threads_current_year_into_quality_warnings():
    """current_year 透传给 run_storyline_gate；warn 级问题不拦但挂进 quality_warnings 喂人审。"""
    from reinforce.storyline_state import handoff_to_production
    sl = _full_storyline()
    sl["lines"][1]["evidence"] = [{"dim": "规模", "data": "2025年预计达标"}]
    h = handoff_to_production(sl, current_year=2026)
    assert any(w["rule"] == "stale_forecast" for w in h["quality_warnings"])


# ── deck 反向索引防前后冲突（2026-07-01·A1，原误记在 retrieval/_说明.md）──
def test_cross_page_consistency_flags_conflicting_numbers():
    lines = [{"n": 1, "evidence": [{"dim": "成本增速", "data": "50%"}]},
             {"n": 4, "evidence": [{"dim": "成本增速", "data": "45%"}]}]
    out = SG.check_cross_page_consistency(lines)
    assert any(i["rule"] == "cross_page_conflict" and i["dim"] == "成本增速" for i in out)


def test_cross_page_consistency_ignores_repeated_same_value():
    lines = [{"n": 1, "evidence": [{"dim": "成本增速", "data": "50%"}]},
             {"n": 4, "evidence": [{"dim": "成本增速", "data": "50%"}]}]
    assert SG.check_cross_page_consistency(lines) == []


def test_run_storyline_gate_includes_cross_page_conflict():
    sl = _full_storyline()
    sl["lines"][0]["evidence"] = [{"dim": "成本增速", "data": "50%"}]
    sl["lines"][3]["evidence"] = [{"dim": "成本增速", "data": "45%"}]
    g = SG.run_storyline_gate(sl)
    assert any(i["rule"] == "cross_page_conflict" for i in g["issues"])


# ── 目录↔章节标题逐字匹配（2026-07-01·A3）──
def test_toc_matches_chapters_when_items_match():
    lines = [{"n": 1, "page_type": "目录", "toc_items": ["市场概览", "竞争格局"]},
             {"n": 2, "page_type": "转场", "claim": "市场概览"},
             {"n": 3, "page_type": "转场", "claim": "竞争格局"}]
    assert SG.check_toc_matches_chapters(lines) == []


def test_toc_matches_chapters_flags_mismatch():
    lines = [{"n": 1, "page_type": "目录", "toc_items": ["市场概览", "竞争格局"]},
             {"n": 2, "page_type": "转场", "claim": "市场概览"}]  # 缺"竞争格局"对应转场页
    out = SG.check_toc_matches_chapters(lines)
    assert any(i["rule"] == "toc_chapter_mismatch" for i in out)


def test_toc_matches_chapters_flags_missing_toc_items():
    lines = [{"n": 1, "page_type": "目录"}]  # 目录页但没填 toc_items
    out = SG.check_toc_matches_chapters(lines)
    assert any(i["rule"] == "toc_items_missing" for i in out)


def test_add_line_stores_toc_items():
    sl = new_storyline("b", "p", "说服决策", ["董事会"], "批")
    add_line(sl, 1, "S", "目录", "none", page_type="目录", toc_items=["第一章", "第二章"])
    assert sl["lines"][0]["toc_items"] == ["第一章", "第二章"]


def test_to_outline_carries_toc_items_into_facets():
    sl = _full_storyline()
    sl["lines"][0]["page_type"] = "目录"
    sl["lines"][0]["toc_items"] = ["执行摘要", "详细分析"]
    o = to_outline(sl)
    assert o["pages"][0]["facets"]["toc_items"] == ["执行摘要", "详细分析"]


# ── 证据"要堵的反驳"承诺-兑现（2026-07-01·问题收口 R-B）──
def test_counter_addressed_flags_missing_data():
    lines = [{"n": 1, "evidence": [{"dim": "x", "data": "", "counter": "这只是行业周期性波动"}]}]
    out = SG.check_counter_addressed(lines)
    assert any(i["rule"] == "counter_not_backed" for i in out)


def test_counter_addressed_flags_data_explicitly_none():
    """2026-07-01 saopan扫盘揪出：str(None)="None"是非空字符串，此前会被误判成"有数据"放行。"""
    lines = [{"n": 1, "evidence": [{"dim": "x", "data": None, "counter": "这只是行业周期性波动"}]}]
    out = SG.check_counter_addressed(lines)
    assert any(i["rule"] == "counter_not_backed" for i in out)


def test_counter_addressed_passes_data_zero():
    """data=0 是合法的数字零值(比如"流失率降到0")，不该被误判成"没填"。"""
    lines = [{"n": 1, "evidence": [{"dim": "x", "data": 0, "counter": "流失率降到0"}]}]
    assert SG.check_counter_addressed(lines) == []


def test_counter_addressed_passes_when_data_present():
    lines = [{"n": 1, "evidence": [{"dim": "x", "data": "人均产出-12%", "counter": "行业周期性波动"}]}]
    assert SG.check_counter_addressed(lines) == []


def test_counter_read_unaddressed_when_no_evidence_counters():
    lines = [{"n": 1, "evidence": [{"dim": "x", "data": "50%"}],
              "framing": {"counter_read": "对方会说这只是短期波动"}}]
    out = SG.check_counter_addressed(lines)
    assert any(i["rule"] == "counter_read_unaddressed" for i in out)


def test_counter_read_addressed_when_some_evidence_has_counter():
    lines = [{"n": 1, "evidence": [{"dim": "x", "data": "50%", "counter": "堵住短期波动说"}],
              "framing": {"counter_read": "对方会说这只是短期波动"}}]
    assert SG.check_counter_addressed(lines) == []


# ── 假设树 test 承诺-兑现（2026-07-01·问题收口 R-B）──
def test_hypothesis_tested_flags_unverified():
    sl = {"sub_hypotheses": [{"id": "H1", "claim": "成本增速>收入增速", "test": "拉报表核实"}]}
    out = SG.check_hypothesis_tested(sl)
    assert any(i["rule"] == "hypothesis_test_unverified" and i["id"] == "H1" for i in out)


def test_hypothesis_tested_passes_when_verified():
    sl = {"sub_hypotheses": [{"id": "H1", "claim": "c", "test": "t",
                              "verified": {"answer": "成立", "source": "报表"}}]}
    assert SG.check_hypothesis_tested(sl) == []


def test_hypothesis_tested_skips_hypothesis_without_test():
    sl = {"sub_hypotheses": [{"id": "H1", "claim": "c"}]}  # 没声明 test 的不查
    assert SG.check_hypothesis_tested(sl) == []


def test_new_storyline_expected_pages_defaults_none():
    sl = new_storyline("b", "p", "说服决策", ["董事会"], "批")
    assert sl["expected_pages"] is None


def test_new_storyline_expected_pages_stored():
    sl = new_storyline("b", "p", "说服决策", ["董事会"], "批", expected_pages=(4, 6))
    assert sl["expected_pages"] == (4, 6)


# ── 实际页数 vs 阶段2规划一致性（2026-07-01·问题收口D）──
def test_page_count_consistency_skips_when_not_declared():
    sl = _full_storyline()  # expected_pages 默认 None
    assert SG.check_page_count_consistency(sl) == []


def test_page_count_consistency_passes_within_range():
    sl = _full_storyline()
    sl["expected_pages"] = (4, 8)  # 实际6页(_full_storyline)落在区间内
    assert SG.check_page_count_consistency(sl) == []


def test_page_count_consistency_flags_drift_over():
    sl = _full_storyline()  # 实际6页
    sl["expected_pages"] = (2, 3)
    out = SG.check_page_count_consistency(sl)
    assert any(i["rule"] == "page_count_drift" and "多" in i["note"] for i in out)


def test_page_count_consistency_flags_drift_under():
    sl = _full_storyline()  # 实际6页
    sl["expected_pages"] = (10, 12)
    out = SG.check_page_count_consistency(sl)
    assert any(i["rule"] == "page_count_drift" and "少" in i["note"] for i in out)


# ── 防御性输入（2026-07-01·saopan扫盘揪出的崩溃点）──
def test_page_count_consistency_rejects_non_pair_gracefully():
    """expected_pages 传成裸 int（正常API误用，不是直接改字典）不该 TypeError 崩溃。"""
    sl = {"lines": [{"n": 1}], "expected_pages": 5}
    out = SG.check_page_count_consistency(sl)
    assert any(i["rule"] == "expected_pages_malformed" for i in out)


def test_page_count_consistency_rejects_wrong_length_tuple():
    sl = {"lines": [{"n": 1}], "expected_pages": (1, 2, 3)}
    out = SG.check_page_count_consistency(sl)
    assert any(i["rule"] == "expected_pages_malformed" for i in out)


def test_page_count_consistency_auto_corrects_reversed_range():
    """min/max 写反((6,4)而非(4,6))不该报自相矛盾的错，sorted()自动纠正。"""
    sl = {"lines": [{"n": i} for i in range(5)], "expected_pages": (6, 4)}
    assert SG.check_page_count_consistency(sl) == []  # 5落在纠正后的[4,6]区间内


def test_run_storyline_gate_survives_lines_explicitly_none():
    """sl['lines']=None(手改坏的JSON、非缺字段)此前会让 run_storyline_gate 自己崩溃。"""
    sl = {"lines": None, "purpose": "x"}
    r = SG.run_storyline_gate(sl)
    assert r["passed"] is False  # 走到 check_decision_ending 的 no_lines error 分支


def test_check_hypothesis_tested_survives_sub_hypotheses_none():
    """set_hypothesis_tree(sl, gt, None) 是合法调用签名，不该让检查函数崩溃。"""
    assert SG.check_hypothesis_tested({"sub_hypotheses": None}) == []


# ── 内容密度/注水检查（2026-07-01·问题收口"太碎/注水"）──
def _thin_line(n):
    return {"n": n, "page_type": "数据论断", "chart": "bar_callout", "claim": f"论点{n}",
            "evidence": [], "sowhat": ""}


def _rich_line(n):
    return {"n": n, "page_type": "数据论断", "chart": "bar_callout", "claim": f"论点{n}",
            "evidence": [{"dim": "a", "data": "1"}, {"dim": "b", "data": "2"}], "sowhat": "有解读"}


def test_content_density_flags_high_thin_ratio():
    sl = {"lines": [_thin_line(1), _thin_line(2), _thin_line(3), _rich_line(4)]}  # 3/4=75%单薄
    out = SG.check_content_density(sl)
    assert any(i["rule"] == "content_thin_ratio_high" for i in out)


def test_content_density_passes_when_mostly_rich():
    sl = {"lines": [_rich_line(1), _rich_line(2), _rich_line(3), _thin_line(4)]}  # 1/4=25%单薄
    assert SG.check_content_density(sl) == []


def test_content_density_skips_when_too_few_argument_pages():
    sl = {"lines": [_thin_line(1), _thin_line(2)]}  # 只2页·统计没意义
    assert SG.check_content_density(sl) == []


def test_run_storyline_gate_includes_counter_and_hypothesis_checks():
    sl = _full_storyline()
    sl["sub_hypotheses"] = [{"id": "H1", "claim": "c", "test": "t"}]  # 未回填 verified
    sl["lines"][0]["evidence"] = [{"dim": "x", "data": "", "counter": "反驳未堵"}]
    g = SG.run_storyline_gate(sl)
    rules = {i["rule"] for i in g["issues"]}
    assert {"counter_not_backed", "hypothesis_test_unverified"} <= rules


# ── 2026-07-02 saopan扫盘修复回归（接线+误报修正）───────────────────────
def test_gate_wires_facts_grounded_and_directions():
    """孤岛A2/A3摘帽：两层防假阳真进 run_storyline_gate（此前文档喊自动·零调用点）。"""
    sl = {"lines": [
        {"n": 1, "stage": "S", "claim": "收入涨了", "chart": "waterfall", "sowhat": "s",
         "evidence": [{"dim": "收入", "data": "42%", "source": "财报", "source_quote": "原文里是 45%"},
                      {"dim": "毛利", "data": "从58%提升到42%", "source": "财报"}]},
    ]}
    issues = SG.run_storyline_gate(sl)["issues"]
    rules = {i["rule"] for i in issues if "rule" in i}
    assert "number_not_in_source_quote" in rules       # A2：数字↔原文核验在跑
    assert "evidence_direction_mismatch" in rules      # A3：方向词校验在跑


def test_duplicate_title_exempts_parallel_numbers():
    """③🟢校准：平行结构论点（数字不同）不再误报近似重复；无数字的近似仍报。"""
    assert SG.check_duplicate_titles([
        {"n": 1, "claim": "Q1亏损2亿"}, {"n": 2, "claim": "Q2亏损5亿"}]) == []
    assert SG.check_duplicate_titles([
        {"n": 1, "claim": "华东区营收增长强劲"}, {"n": 2, "claim": "华西区营收增长强劲"}])


def test_sowhat_skips_non_argument_charts():
    """③🟢对齐：decision_box/metric_callout 不再要求 sowhat（与姊妹检查同口径）。"""
    assert SG.check_sowhat([{"n": 1, "claim": "批准专项", "chart": "decision_box"}]) == []
    assert SG.check_sowhat([{"n": 2, "claim": "成本翻倍", "chart": "waterfall"}])


def test_toc_match_strips_whitespace():
    """③🟢：目录项/转场标题带首尾空格不再误报 mismatch。"""
    lines = [{"n": 2, "page_type": "目录", "toc_items": ["第一章 现状 "]},
             {"n": 3, "page_type": "转场", "claim": " 第一章 现状"}]
    assert not any(i["rule"] == "toc_chapter_mismatch"
                   for i in SG.check_toc_matches_chapters(lines))


def test_validate_storyline_none_shapes_no_crash():
    """🟡：sub_hypotheses/lines 显式 None、行缺 n——第一道结构门如实报 error 不崩。"""
    sl = new_storyline("b", purpose="p", intent="说服决策", audience=["a"],
                       decision_ask="d", domain="x")
    set_hypothesis_tree(sl, "gt", None)                 # deck_rules/storyline.py:384 自举的例子
    r = validate_storyline(sl)
    assert not r["valid"]                               # 无行 error·但没崩
    sl2 = {"lines": [{"claim": "c", "stage": "S", "chart": "x"}]}   # 行缺 n
    r2 = validate_storyline(sl2)
    assert any("缺页号 n" in i["msg"] for i in r2["issues"])


def test_handoff_carries_open_questions_check(tmp_path):
    """孤岛A4摘帽：handoff_to_production(team=...) 自动跑遗留问题收口。"""
    from reinforce.storyline_state import handoff_to_production
    sl = _full_storyline()
    team = {"order": ["行业专家", "财务尽调"],
            "roles": {"行业专家": {"status": "done", "handoff": {
                          "open_questions": ["渠道库存周转天数到底多少"],
                          "key_findings": ["市场增速8%"], "decisions": []}},
                      "财务尽调": {"status": "done", "handoff": {
                          "open_questions": [], "key_findings": ["毛利率42%"], "decisions": []}}}}
    h = handoff_to_production(sl, team=team)
    assert any("渠道库存周转天数" in str(w) for w in h["quality_warnings"])


# ── D18 FR7.1 两轴迁移 + FR2.1 part 字段 ──────────────────────────────
def test_delivery_purpose_migration_old_calls_unbroken():
    from reinforce.storyline_state import delivery_purpose_of
    sl = new_storyline("b", purpose="p", intent="说服决策", audience=["a"],
                       decision_ask="d", domain="x", visual_style="演讲版")   # 旧语义调用
    assert sl["delivery_purpose"] == "演讲版"      # 旧值自动挪到密度轴
    assert sl["visual_style"] is None              # 不污染美学轴
    assert delivery_purpose_of(sl) == "演讲版"
    assert delivery_purpose_of({"visual_style": "阅读版"}) == "阅读版"   # 旧落盘数据兼容读


def test_new_aesthetic_axis_validated():
    sl = new_storyline("b", purpose="p", intent="说服决策", audience=["a"],
                       decision_ask="d", domain="x", visual_style="memphis",
                       delivery_purpose="阅读版")
    assert sl["visual_style"] == "memphis" and sl["delivery_purpose"] == "阅读版"
    set_hypothesis_tree(sl, "gt", [{"id": "h1", "test": "t"}])
    add_line(sl, 1, "S", "论断1", "waterfall", sowhat="s", subtitle="导读")
    add_line(sl, 2, "C", "冲突", "line_compare", sowhat="s", subtitle="导读")
    add_line(sl, 3, "R", "批准专项», owner定", "decision_box", sowhat="s", subtitle="导读")
    assert validate_storyline(sl)["valid"]
    bad = dict(sl, visual_style="乱写的风格")
    assert not validate_storyline(bad)["valid"]


def test_rhythm_check_uses_delivery_purpose():
    # 新字段驱动演讲版检查；旧落盘形态（visual_style=演讲版）同样触发（兼容读）
    for shape in ({"delivery_purpose": "演讲版"}, {"visual_style": "演讲版"}):
        sl = {**shape, "lines": [{"n": 1, "page_type": "数据论断"}]}
        rules = {i["rule"] for i in SG.check_rhythm(sl)}
        assert "no_emotion_page" in rules and "no_transition" in rules


def test_add_line_part_and_bridge_from():
    sl = new_storyline("b", purpose="p", intent="i", audience=["a"], decision_ask="d", domain="x")
    add_line(sl, 5, "C", "第二章：人群断层", "section", page_type="转场",
             part="人群洞察", bridge_from="上一章确认了市场增速见顶")
    ln = sl["lines"][0]
    assert ln["part"] == "人群洞察" and "市场增速见顶" in ln["bridge_from"]


# ── D18 FR2.2 结构件硬门（error 级·拦交棒）──────────────────────────────
def _part_storyline() -> dict:
    """12 页·目录+双 Part（各有转场+章小结）的合规夹具——FR2.2 四条判定的绿基线。"""
    sl = new_storyline("brief 文本", purpose="赢比稿", intent="说服决策",
                       audience=["客户评审团"], decision_ask="选定我方", domain="快消")
    set_hypothesis_tree(sl, "建议做减法差异化突围",
                        [{"id": "H1", "claim": "同质化触达失效", "test": "对比近3年声量数据"}])
    add_line(sl, 1, "S", "2027 CNY 提案", "cover", page_type="封面")
    add_line(sl, 2, "S", "目录", "toc", page_type="目录", toc_items=["市场诊断", "策略方案"])
    add_line(sl, 3, "S", "市场诊断", "chapter_cover", page_type="转场", part="市场诊断")
    add_line(sl, 4, "S", "声量降40%说明触达失效", "line_compare", sowhat="s", part="市场诊断")
    add_line(sl, 5, "C", "竞品同质化率超80%", "bar_callout", sowhat="s", part="市场诊断")
    add_line(sl, 6, "C", "诊断小结：不变则被淹没", "metric_callout", role="章小结", part="市场诊断")
    add_line(sl, 7, "C", "策略方案", "chapter_cover", page_type="转场", part="策略方案",
             bridge_from="同质化触达已失效，所以我们换打法")
    add_line(sl, 8, "R", "做减法：一笔水墨替代堆砌", "creative_concept", sowhat="s", part="策略方案")
    add_line(sl, 9, "R", "KOC共创占预算70%", "kol_pyramid", sowhat="s", part="策略方案")
    add_line(sl, 10, "R", "3波节奏引爆CNY档期", "wave_timeline", sowhat="s", part="策略方案")
    add_line(sl, 11, "R", "方案小结：减法赢注意力", "metric_callout", role="章小结", part="策略方案")
    add_line(sl, 12, "R", "请选定我方进入下一轮", "decision_box", part="策略方案")
    return sl


def test_part_structure_complete_parts_pass():
    """合规夹具（目录+每 Part 转场[次章带bridge_from]+章小结）零 error 零 warn。"""
    assert SG.check_part_structure(_part_storyline()) == []


def test_part_structure_short_deck_without_parts_exempt():
    """条款③豁免：<12 页短 deck 允许无章节（硬纪律4：简单需求不加仪式锁）。"""
    assert SG.check_part_structure(_full_storyline()) == []  # 6 页·零 part·零目录


def test_part_structure_long_flat_deck_errors_on_toc_and_parts():
    """条款①+③：≥12 页无目录、零 part → 两条 error（第一轮实测 24 页平铺的抽象形态）。"""
    sl = {"lines": [{"n": i, "page_type": "数据论断", "claim": f"论断{i}"} for i in range(1, 13)]}
    rules = {i["rule"] for i in SG.check_part_structure(sl) if i["sev"] == "error"}
    assert {"no_toc_page", "no_parts"} <= rules


def test_part_structure_toc_present_but_items_empty_errors():
    """条款①后半：有目录页但 toc_items 全空 → error（没数据没法核对目录↔转场一致性）。"""
    sl = _part_storyline()
    for ln in sl["lines"]:
        if ln["page_type"] == "目录":
            ln["toc_items"] = []
    rules = {i["rule"] for i in SG.check_part_structure(sl) if i["sev"] == "error"}
    assert "toc_items_empty" in rules


def test_part_structure_first_part_bridge_exempt_second_required():
    """条款②豁免边界：首 Part 转场无 bridge_from 不报（前面没有章可承接）；
    次 Part 转场删掉 bridge_from 必报 transition_no_bridge。"""
    sl = _part_storyline()   # 首 Part 转场本就无 bridge_from → 合规夹具已证不报
    for ln in sl["lines"]:
        if ln.get("part") == "策略方案" and ln["page_type"] == "转场":
            ln["bridge_from"] = "  "   # 空白串同样算空——strip 后判定
    out = SG.check_part_structure(sl)
    assert any(i["rule"] == "transition_no_bridge" and i["part"] == "策略方案" for i in out)
    assert not any(i.get("part") == "市场诊断" and i["rule"] == "transition_no_bridge" for i in out)


def test_part_structure_missing_transition_errors():
    """条款②：某 Part 整章没有转场页 → part_no_transition。"""
    sl = _part_storyline()
    sl["lines"] = [ln for ln in sl["lines"]
                   if not (ln.get("part") == "市场诊断" and ln["page_type"] == "转场")]
    out = SG.check_part_structure(sl)
    assert any(i["rule"] == "part_no_transition" and i["part"] == "市场诊断" for i in out)


def test_part_structure_missing_summary_errors():
    """条款②：某 Part 没有章小结行 → part_no_summary。"""
    sl = _part_storyline()
    for ln in sl["lines"]:
        if ln.get("part") == "策略方案" and ln.get("role") == "章小结":
            ln["role"] = ""
    out = SG.check_part_structure(sl)
    assert any(i["rule"] == "part_no_summary" and i["part"] == "策略方案" for i in out)


def test_part_structure_summary_via_page_function_also_counts():
    """章小结判定第二通道：page_function 含"小结"（如库内"阶段总览小结"卡）同样算数。"""
    sl = _part_storyline()
    for ln in sl["lines"]:
        if ln.get("part") == "策略方案" and ln.get("role") == "章小结":
            ln["role"] = ""
            ln["page_function"] = "阶段总览小结"
    assert not any(i["rule"] == "part_no_summary" for i in SG.check_part_structure(sl))


def test_part_structure_transition_owned_by_claim_match():
    """条款②归属兼容：转场页没填 part、但 claim 与章名逐字一致（"标题就是章名"填法）也算该章转场。"""
    sl = _part_storyline()
    for ln in sl["lines"]:
        if ln.get("page_type") == "转场" and ln.get("part") == "市场诊断":
            ln["part"] = None   # 只留 claim="市场诊断" 对上章名
    assert not any(i["rule"] == "part_no_transition" and i.get("part") == "市场诊断"
                   for i in SG.check_part_structure(sl))


def test_part_structure_opener_empty_claim_warns_not_errors():
    """条款④：转场后第一页 claim 为空 → warn（洞察陈述与否是语义判断·留人审）。"""
    sl = _part_storyline()
    sl["lines"][3]["claim"] = ""   # 行4=首 Part 转场后的第一页
    out = SG.check_part_structure(sl)
    hit = [i for i in out if i["rule"] == "part_opener_no_claim"]
    assert hit and all(i["sev"] == "warn" for i in hit)


def test_part_structure_wired_into_gate():
    """接线验证：run_storyline_gate 必须包含结构件硬门（error 拦交棒·fail-closed）。"""
    sl = {"lines": [{"n": i, "page_type": "数据论断", "claim": f"论断涨{i}%"} for i in range(1, 13)]}
    g = SG.run_storyline_gate(sl)
    assert g["passed"] is False
    assert {"no_toc_page", "no_parts"} <= {i["rule"] for i in g["issues"]}


def test_part_scaffold_hint_carries_paradigm_and_sample_provenance():
    """scaffold 四拍齐全 + 四真样本出处可追（标尺来自真样本非模型常识）。"""
    hint = SG.part_scaffold_hint()
    for beat in ("转场", "洞察陈述", "证据展开", "章小结", "bridge_from", "钩子"):
        assert beat in hint
    for sample in ("某品牌", "Lulu", "某品牌", "MTA"):
        assert sample in hint


# ── D18 FR1.2 交棒 ack 闸（storyline定稿必须有用户确认留痕才能交制作）──────────
def _d18_team(granularity="key_nodes", acks=None):
    """D18 后 new_planning_team 造的 team 形态（带 user_acks 机制的最小骨架）。"""
    return {"brief_purpose": "p", "order": [], "roles": {},
            "confirm_granularity": granularity, "granularity_quote": "按关键节点停",
            "user_acks": acks or [], "divergences": []}


def test_handoff_blocked_without_storyline_ack():
    from reinforce.storyline_state import handoff_to_production
    with pytest.raises(ValueError, match="storyline定稿"):
        handoff_to_production(_full_storyline(), team=_d18_team())


def test_handoff_passes_with_storyline_ack():
    from reinforce.storyline_state import handoff_to_production
    team = _d18_team(acks=[{"node": "storyline定稿", "user_quote": "就按这版定"}])
    assert handoff_to_production(_full_storyline(), team=team)["status"] == "策略定稿·待制作"


def test_handoff_minimal_granularity_skips_ack_gate():
    # minimal 是用户自己选的快进档（granularity_quote 有原话留痕）——尊重用户选择不查
    from reinforce.storyline_state import handoff_to_production
    h = handoff_to_production(_full_storyline(), team=_d18_team("minimal"))
    assert h["kind"] == "strategy_to_production_handoff"


def test_handoff_direct_through_granularity_skips_ack_gate():
    # D21 直通档同 minimal 待遇：用户开场亲选"字面直通"，storyline 定稿不等 ack 直接交棒制作
    from reinforce.storyline_state import handoff_to_production
    h = handoff_to_production(_full_storyline(), team=_d18_team("direct_through"))
    assert h["kind"] == "strategy_to_production_handoff"


def test_handoff_carries_granularity_and_quote():
    # 批③🔴7：交接卡带确认粒度+根授权原话——制作侧直通档调 publish_deck(direct_through_waiver=...)
    # 靠的就是这句 quote，不随卡走则审计链在交棒处断裂（只剩对话记忆·压缩即丢）
    from reinforce.storyline_state import handoff_to_production
    h = handoff_to_production(_full_storyline(), team=_d18_team("direct_through"))
    assert h["confirm_granularity"] == "direct_through"
    assert h["granularity_quote"] == "按关键节点停"   # _d18_team 骨架里的固定原话·逐字透传


def test_handoff_granularity_keys_none_without_team():
    # 批③🔴7 零破坏：不传 team 的旧调用两键为 None（键存在·值为 None，读卡方无需 hasattr 分叉）
    from reinforce.storyline_state import handoff_to_production
    h = handoff_to_production(_full_storyline())
    assert h["confirm_granularity"] is None and h["granularity_quote"] is None


def test_handoff_legacy_team_without_mechanism_not_gated():
    # D18 前落盘的 team（无 confirm_granularity 字段·某品牌 一代形态）传入只跑遗留问题收口，
    # 不触发 ack 闸——对旧调用零破坏（需求原文明确要求）
    from reinforce.storyline_state import handoff_to_production
    legacy = {"order": [], "roles": {}}
    assert handoff_to_production(_full_storyline(), team=legacy)["status"] == "策略定稿·待制作"


def test_handoff_require_acks_true_forces_gate_even_on_legacy():
    from reinforce.storyline_state import handoff_to_production
    with pytest.raises(ValueError, match="storyline定稿"):
        handoff_to_production(_full_storyline(), team={"order": [], "roles": {}}, require_acks=True)


def test_handoff_require_acks_false_explicitly_skips_gate():
    from reinforce.storyline_state import handoff_to_production
    h = handoff_to_production(_full_storyline(), team=_d18_team(), require_acks=False)
    assert h["status"] == "策略定稿·待制作"


def test_handoff_no_team_unchanged():
    # 不传 team 的旧调用完全不查 ack（零破坏底线）
    from reinforce.storyline_state import handoff_to_production
    assert handoff_to_production(_full_storyline())["status"] == "策略定稿·待制作"


def test_handoff_ack_gate_with_real_planning_team_api():
    # 真接线验证：new_planning_team → 缺 ack 被拦 → record_user_ack 留痕 → 放行
    from reinforce.planning_team import new_planning_team, record_user_ack
    from reinforce.storyline_state import handoff_to_production
    team = new_planning_team("p")
    with pytest.raises(ValueError, match="record_user_ack"):
        handoff_to_production(_full_storyline(), team=team)
    record_user_ack(team, "storyline定稿", "可以，定稿")
    assert handoff_to_production(_full_storyline(), team=team)["status"] == "策略定稿·待制作"


# ── D19 FR3 三值化 + FR5.1 brand 链 ──────────────────────────────────
def test_delivery_purpose_third_value():
    from reinforce.storyline_state import DELIVERY_PURPOSES, delivery_purpose_of
    assert "预读讲解版" in DELIVERY_PURPOSES
    assert delivery_purpose_of({"delivery_purpose": "预读讲解版"}) == "预读讲解版"
    # 两处兼容读同步（D19 需求点名）：deck_rules 内联版同样认第三态
    assert SG._delivery_purpose({"delivery_purpose": "预读讲解版"}) == "预读讲解版"


def test_rhythm_three_way_split():
    lines_no_structure = [{"n": 1, "page_type": "数据论断"}]
    # 演讲版：情绪+转场都查
    r1 = {i["rule"] for i in SG.check_rhythm({"delivery_purpose": "演讲版", "lines": lines_no_structure})}
    assert r1 == {"no_emotion_page", "no_transition"}
    # 预读讲解版（D19 FR3 柔化）：要转场不强制情绪页
    r2 = {i["rule"] for i in SG.check_rhythm({"delivery_purpose": "预读讲解版", "lines": lines_no_structure})}
    assert r2 == {"no_transition"}
    # 阅读版：不查（结构由 Part 门管）
    assert SG.check_rhythm({"delivery_purpose": "阅读版", "lines": lines_no_structure}) == []


def test_reading_subtitle_covers_preread_mode():
    # 预读讲解版"先发客户自读"——导读是自读的拐杖，同样要查
    sl = {"delivery_purpose": "预读讲解版",
          "lines": [{"n": 1, "page_type": "数据论断", "chart": "waterfall"}]}
    assert any(i["rule"] == "no_reading_subtitle" for i in SG.check_reading_subtitle(sl))


def test_brand_flows_to_outline_brand_terms():
    """D19 FR5.1：storyline.brand 交棒自动生成 outline.brand_terms（品牌名豁免链）。"""
    sl = new_storyline("b", purpose="p", intent="说服决策", audience=["a"],
                       decision_ask="选我们", domain="营销", brand="059某品牌精酿公社")
    set_hypothesis_tree(sl, "gt", [{"id": "h1", "test": "t"}, {"id": "h2", "test": "t"}])
    add_line(sl, 1, "S", "困局明确", "brief_recap", sowhat="s", subtitle="导读")
    add_line(sl, 2, "C", "缺口在情感", "gap_analysis", sowhat="s", subtitle="导读")
    add_line(sl, 3, "R", "选我们·打年味", "decision_box", page_type="决策")
    o = to_outline(sl)
    assert o["brand_terms"] == ["059某品牌精酿公社"]


# ── 2026-07-03 二轮扫盘批B回归 ──────────────────────────────────────────────
def test_gate_survives_line_with_explicit_none_n():
    """批B-5：n 显式为 None（手改坏的 storyline JSON/Part 中途手动跑质量门）此前在两处
    排序键 .get("n", 0) 原样返回 None，None<int 比较 TypeError 崩穿质量门——docstring
    自称"全文件已改 .get(key) or 默认值"但排序键漏网。改 (x.get("n") or 0) 后整门不崩。"""
    sl = _part_storyline()
    sl["lines"][4]["n"] = None                      # 行5 数据页 n 挖成 None
    assert SG.check_part_structure(sl) == []        # 排序键不崩·合规结论不变
    SG.check_adjacent_layout_repeat(sl["lines"])    # 另一处排序键同样不崩
    g = SG.run_storyline_gate(sl)                   # 整门跑通（不 TypeError）
    assert isinstance(g["passed"], bool)


def test_part_structure_unrelated_transition_claim_collision_still_blocks_missing_transition():
    """批B-6 反例①（fail-closed 收紧）：删掉"市场诊断"的转场页，再把"策略方案"的转场页
    claim 改成恰等于"市场诊断"——旧版对任意页用 claim==章名 兜底，这张别章转场页被误配进
    市场诊断章、缺转场被静默放行；收紧后（填了 part 的页只归自己声明的章）照拦。"""
    sl = _part_storyline()
    sl["lines"] = [ln for ln in sl["lines"]
                   if not (ln.get("part") == "市场诊断" and ln["page_type"] == "转场")]
    for ln in sl["lines"]:
        if ln.get("part") == "策略方案" and ln["page_type"] == "转场":
            ln["claim"] = "市场诊断"    # 无关章的转场页标题恰撞别章章名
    out = SG.check_part_structure(sl)
    assert any(i["rule"] == "part_no_transition" and i["part"] == "市场诊断" for i in out)


def test_part_structure_unrelated_summary_claim_collision_still_blocks_missing_summary():
    """批B-6 反例②：抹掉"策略方案"的章小结，另塞一张**无 part**的数据论断页（role=章小结、
    claim 恰等于"策略方案"）——旧版 claim==章名 兜底把它算进本章、part_no_summary 被静默
    放行；收紧后（无 part 页只有"转场页标题=章名"一种兜底）照拦。"""
    sl = _part_storyline()
    for ln in sl["lines"]:
        if ln.get("part") == "策略方案" and ln.get("role") == "章小结":
            ln["role"] = ""
    sl["lines"].append({"n": 13, "page_type": "数据论断", "claim": "策略方案",
                        "role": "章小结", "chart": "metric_callout"})
    out = SG.check_part_structure(sl)
    assert any(i["rule"] == "part_no_summary" and i["part"] == "策略方案" for i in out)
