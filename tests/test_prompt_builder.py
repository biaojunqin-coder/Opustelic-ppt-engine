"""Prompt 引擎（①）独立单测——验证 prompt 是拼出来的(含 RAG 卡+状态+硬门)。"""

from __future__ import annotations

import pytest

from engine import prompt_builder as P
from reinforce import deck_state as S


def _outline():
    o = S.new_outline("某品牌 Y25 策略提案", "品牌策略提案", ["推导策略"], ["营销品牌"], ["甲方高层"])
    S.add_page(o, 1, "封面/章节", "某品牌 Y25 策略提案")
    S.add_page(o, 2, "金句主张", "我们就是新世界的选择", depends_on=[1])
    return o


def test_prompt_injects_action_title_and_function():
    r = P.build_deck_prompt(_outline(), 2)
    assert "金句主张" in r["prompt"]
    assert "我们就是新世界的选择" in r["prompt"]
    assert r["page"]["n"] == 2


def test_prompt_injects_rag_cards():
    r = P.build_deck_prompt(_outline(), 2)
    assert any(c["page_function"] == "金句主张" for c in r["cards"])
    assert "示范" in r["prompt"]  # few-shot 段在


def test_prompt_injects_hard_rules():
    r = P.build_deck_prompt(_outline(), 2)
    assert "硬规范" in r["prompt"] and "source" in r["prompt"].lower()


def test_prompt_has_prev_page_context():
    assert "上一页" in P.build_deck_prompt(_outline(), 2)["prompt"]


# ── B2-12 回归（2026-07-02 saopan扫盘）：旧版按列表下标取 idx-1 当"上一页"——pages 补页/重排后
#    顺序乱（[1,3,2] 很常见）时叙事承接提示指向错误页；正确语义 = 页号小于当页的最大者 ──
def _outline_pages_out_of_order():
    o = S.new_outline("某品牌 Y25 策略提案", "品牌策略提案", ["推导策略"], ["营销品牌"], ["甲方高层"])
    S.add_page(o, 1, "封面/章节", "第一页封面")
    S.add_page(o, 3, "金句主张", "第三页主张")   # 先加 3 再加 2 → 列表序 [1,3,2]
    S.add_page(o, 2, "洞察推导", "第二页推导")
    return o


def test_prev_page_by_page_number_not_list_order():
    r = P.build_deck_prompt(_outline_pages_out_of_order(), 3)
    assert "上一页：p2「第二页推导」" in r["prompt"]     # 旧版会取列表前一项 p1·错


def test_prev_page_skips_gap_in_page_numbers():
    o = S.new_outline("某品牌 Y25 策略提案", "品牌策略提案", ["推导策略"], ["营销品牌"], ["甲方高层"])
    S.add_page(o, 1, "封面/章节", "封面")
    S.add_page(o, 5, "金句主张", "跳号页")   # 页号不连续·上一页应是 1 而不是不存在的 4
    r = P.build_deck_prompt(o, 5)
    assert "上一页：p1「封面」" in r["prompt"]


def test_lowest_page_number_has_no_prev_even_if_not_first_in_list():
    o = S.new_outline("某品牌 Y25 策略提案", "品牌策略提案", ["推导策略"], ["营销品牌"], ["甲方高层"])
    S.add_page(o, 2, "金句主张", "后加的大页号")
    S.add_page(o, 1, "封面/章节", "列表尾部的页1")   # 页 1 在列表尾·旧版会给它算出"上一页 p2"
    r = P.build_deck_prompt(o, 1)
    assert "上一页" not in r["prompt"]


def test_missing_page_raises():
    with pytest.raises(ValueError):
        P.build_deck_prompt(_outline(), 99)


def test_prompt_injects_expression_cards_by_default():
    r = P.build_deck_prompt(_outline(), 2)
    assert r["expression_cards"]  # domain=["营销品牌"] 应该有真实命中
    assert "表达手法卡" in r["prompt"]
    assert r["expression_cards"][0]["formula"] in r["prompt"]


def test_expression_cards_can_be_disabled():
    r = P.build_deck_prompt(_outline(), 2, top_expression_cards=0)
    assert r["expression_cards"] == []
    assert "表达手法卡" not in r["prompt"]


def test_prompt_injects_chart_shapes_call_for_engine_chart():
    o = S.new_outline("成本管控", "战略汇报", ["说服决策"], ["财务"], ["董事会"])
    S.add_page(o, 1, "数据论断", "成本增速是收入2倍", facets={"chart": "waterfall"})
    r = P.build_deck_prompt(o, 1)
    assert "本页图型（chart）：waterfall" in r["prompt"]
    assert "engine.chart_shapes.waterfall_chart()" in r["prompt"]
    assert "禁止手算" in r["prompt"]


def test_prompt_shows_chart_without_hard_call_for_non_engine_chart():
    # 非 waterfall/gantt/mekko 的图型(如折线对比)只展示 chart 值，不该编造一个不存在的 chart_shapes 函数
    o = S.new_outline("成本管控", "战略汇报", ["说服决策"], ["财务"], ["董事会"])
    S.add_page(o, 1, "数据论断", "净利率逐年下滑", facets={"chart": "line_compare"})
    r = P.build_deck_prompt(o, 1)
    assert "本页图型（chart）：line_compare" in r["prompt"]
    assert "chart_shapes" not in r["prompt"]


def test_prompt_omits_chart_line_when_no_chart_facet():
    o = S.new_outline("成本管控", "战略汇报", ["说服决策"], ["财务"], ["董事会"])
    S.add_page(o, 1, "封面/章节", "标题页")
    r = P.build_deck_prompt(o, 1)
    assert "本页图型" not in r["prompt"]


# ── D20 FR1.3/1.4 槽位注入与姿态契约 ─────────────────────────────────
def test_slot_cards_injected_by_page_position():
    from engine.prompt_builder import build_deck_prompt
    from reinforce.deck_state import add_page, new_outline
    o = new_outline("槽位路由验证", "提案", ["说服决策"], ["营销品牌"])
    add_page(o, 1, "转场", "第二章 人群真相", facets={"page_type": "转场"})
    add_page(o, 2, "数据论断", "增速见顶", facets={"page_type": "数据论断"})
    add_page(o, 3, "决策", "选我们", facets={"page_type": "决策", "chart": "decision_box"})
    ctx1 = build_deck_prompt(o, 1)
    assert "结构性文案范式" in ctx1["prompt"] and "章间桥" in ctx1["prompt"]
    assert any("禁形态" in ctx1["prompt"] for _ in [1])            # anti_pattern 对照在场
    ctx2 = build_deck_prompt(o, 2)
    assert "结构性文案范式" not in ctx2["prompt"]                   # 普通论证页不注（防噪音）
    ctx3 = build_deck_prompt(o, 3)
    assert "ask收尾" in ctx3["prompt"] and "SOW" in ctx3["prompt"]  # 决策页给 ask 范式


def test_slot_route_diagnosis_wrapup():
    """批④补第六槽位出口：诊断页（role/page_function 含「诊断」或含「洞察陈述」）路由到
    「诊断收束」槽位卡（D20 首批 3 张·对比定位/设问自答范式），此前 elif 链只开五支拿不到。"""
    from engine.prompt_builder import build_deck_prompt
    from reinforce.deck_state import add_page, new_outline
    o = new_outline("诊断槽位路由验证", "提案", ["说服决策"], ["营销品牌"])
    add_page(o, 1, "诊断", "情感连接是真缺口", facets={"role": "诊断收束"})
    add_page(o, 2, "洞察陈述", "TA 不再向外索求认同")
    ctx1 = build_deck_prompt(o, 1)
    assert "结构性文案范式" in ctx1["prompt"] and "诊断收束" in ctx1["prompt"]
    assert all(c.get("slot") == "诊断收束" for c in ctx1["slot_cards"]) and ctx1["slot_cards"]
    ctx2 = build_deck_prompt(o, 2)   # pf 含「洞察陈述」同样命中
    assert "诊断收束" in ctx2["prompt"]


def test_narrative_posture_contract_in_every_prompt():
    from engine.prompt_builder import build_deck_prompt
    from reinforce.deck_state import add_page, new_outline
    o = new_outline("契约验证", "提案", ["说服决策"], ["营销"])
    add_page(o, 1, "数据论断", "论点")
    p = build_deck_prompt(o, 1)["prompt"]
    assert "每句话都在讲客户的生意" in p and "禁止元叙述" in p       # D20 FR1.4 总契约每页在场
