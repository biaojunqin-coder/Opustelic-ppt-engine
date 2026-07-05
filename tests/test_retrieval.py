"""页型卡检索（③RAG）独立单测——守铁律：引擎层独立可测。"""

from __future__ import annotations

from reinforce.retrieval import search as R


def test_load_cards_nonempty():
    cards = R.load_cards()
    assert len(cards) >= 11  # MVP 已入 13 张
    assert all("page_function" in c for c in cards)


def test_search_by_page_function_exact():
    res = R.search_deck_cards(page_function="二元对比")
    assert res and res[0][0]["page_function"] == "二元对比"
    assert res[0][1] >= 4  # 主键精确匹配


def test_search_by_domain_filters():
    res = R.search(domain=["咨询战略"])
    assert res and all("咨询战略" in c.get("domain", []) for c in res)


def test_page_function_outranks_domain_only():
    res = R.search_deck_cards(page_function="数据呈现", domain=["咨询战略"])
    assert res and res[0][0]["page_function"] == "数据呈现"
    assert res[0][1] >= 6  # 主键(4)+domain(2)


def test_no_facet_returns_all_by_rating():
    res = R.search_deck_cards()
    assert len(res) >= 11
    ratings = [c.get("rating", 0) for c, _ in res]
    assert ratings == sorted(ratings, reverse=True)


def test_pick_skip_rules_present():
    res = R.search(page_function="金句主张")
    assert res and "pick_when" in res[0] and "skip_when" in res[0]


def test_top_limits():
    assert len(R.search_deck_cards(top=3)) == 3


# ---------- 表达手法卡/分析框架库/行业知识库检索 ----------

def test_load_expression_cards_nonempty():
    cards = R.load_expression_cards()
    assert len(cards) >= 100
    assert all("expression_type" in c for c in cards)


def test_search_expression_cards_by_domain():
    res = R.search_expression_cards(domain=["营销品牌"])
    assert res and all("营销品牌" in c.get("domain", []) for c, _ in res)


def test_load_frameworks_nonempty():
    cards = R.load_frameworks()
    assert len(cards) >= 40
    assert all("framework_name" in c for c in cards)


def test_search_frameworks_by_type_exact():
    cards = R.load_frameworks()
    some_type = cards[0]["framework_type"]
    res = R.search_frameworks(framework_type=some_type)
    assert res and res[0][0]["framework_type"] == some_type


# ---------- D12新增：七域专业方法论框架卡可检索性(商业/财务/法务尽调+行业专家判断+媒介/线上/线下推广) ----------

def test_search_frameworks_finds_commercial_dd_domain():
    res = R.search_frameworks(domain=["商业尽调"])
    assert len(res) >= 8
    assert all("商业尽调" in c.get("domain", []) for c, _ in res)


def test_search_frameworks_finds_financial_dd_domain():
    res = R.search_frameworks(domain=["财务尽调"])
    assert len(res) >= 6
    assert all("财务尽调" in c.get("domain", []) for c, _ in res)


def test_search_frameworks_finds_legal_dd_domain():
    res = R.search_frameworks(domain=["法务尽调"])
    assert len(res) >= 7
    assert all("法务尽调" in c.get("domain", []) for c, _ in res)


def test_search_frameworks_finds_expert_judgment_domain():
    res = R.search_frameworks(domain=["行业专家判断"])
    assert len(res) >= 7
    assert all("行业专家判断" in c.get("domain", []) for c, _ in res)


def test_search_frameworks_finds_media_planning_domain():
    res = R.search_frameworks(domain=["媒介推广"])
    assert len(res) >= 6
    assert all("媒介推广" in c.get("domain", []) for c, _ in res)


def test_search_frameworks_finds_online_promotion_domain():
    res = R.search_frameworks(domain=["线上推广"])
    assert len(res) >= 7
    assert all("线上推广" in c.get("domain", []) for c, _ in res)


def test_search_frameworks_finds_offline_promotion_domain():
    res = R.search_frameworks(domain=["线下推广"])
    assert len(res) >= 3
    assert all("线下推广" in c.get("domain", []) for c, _ in res)


def test_search_facts_no_facet_returns_all_by_rating():
    res = R.search_facts()
    assert len(res) == len(R.load_facts())


# ---------- 时效性巡检 ----------

def test_flag_stale_facts_detects_old_year():
    facts = [{"id": "f1", "timeliness": "2020年数据，已过期需重新核实"},
              {"id": "f2", "timeliness": "无具体年份标注"},
              {"id": "f3", "timeliness": "2026年最新数据"}]
    flagged = R.flag_stale_facts(facts, current_year=2026, threshold_years=2)
    ids = [f["id"] for f in flagged]
    assert "f1" in ids and "f2" not in ids and "f3" not in ids
    assert flagged[0]["age_years"] == 6


def test_flag_stale_facts_uses_latest_year_when_multiple():
    facts = [{"id": "f1", "timeliness": "2018年到2023年历史数据"}]
    flagged = R.flag_stale_facts(facts, current_year=2026, threshold_years=2)
    assert flagged[0]["latest_year"] == 2023
    assert flagged[0]["age_years"] == 3


def test_related_by_source_empty_for_unknown():
    related = R.related_by_source("这个source绝对不存在于任何库")
    assert all(v == [] for v in related.values())


# ── source 键归一化（2026-07-02 saopan扫盘揪出：同一 deck 的括号备注变体各占一键，
#    25 份 deck 裂成 123 个键，related_by_source 同源接不上）──

def test_norm_source_strips_paren_variants():
    base = "某品牌 2025 Social Campaign提案"
    assert R._norm_source(base) == base
    assert R._norm_source("某品牌 2025 Social Campaign提案(47页demo版)") == base
    assert R._norm_source("某品牌 2025 Social Campaign提案(47页demo版+69页完整版共同印证)") == base
    assert R._norm_source("某提案（中文括号备注）") == "某提案"
    assert R._norm_source("  多  空格   提案 ") == "多 空格 提案"


def test_related_by_source_all_paren_query_returns_empty():
    """归一后为空（纯括号）→ 全空：空串子串匹配恒真，不拦会把整库都"命中"。"""
    related = R.related_by_source("(47页demo版)")
    assert all(v == [] for v in related.values())


# ---------- 诚实性回归：facts 库没有 rating 字段，兜底排序不该假装有意义 ----------

def test_search_facts_real_library_has_no_rating_field():
    """守住"行业知识库 schema 没有 rating 字段"这个前提——一旦以后有人给facts加了rating，
    上面 search_facts 的"无facet不按重要性排"这条文档说明就该跟着改，靠这条测试提醒。"""
    facts = R.load_facts()
    assert all("rating" not in f for f in facts)


def test_search_facts_no_facet_all_scores_zero_not_a_real_ranking():
    res = R.search_facts()
    assert all(score == 0 for _, score in res)  # 确认是"退化成0"而非真排序，别被表面的"有序"迷惑


def test_slot_filter_is_orthogonal_to_type_search():
    from reinforce.retrieval.search import search_expression_cards
    assert len(search_expression_cards()) > len(search_expression_cards(slot="章间桥"))  # slot 是过滤不是全集


def test_empty_key_card_scores_zero_for_any_query():
    """2026-07-03 saopan批②：主键空串/None 的卡此前 '' in query 恒真白得 2 分——
    空键=没这个 facet，对任意查询 0 分（s>0 才入选，即整卡不出现在结果里）。"""
    from reinforce.retrieval.search import _score_by_key
    for kv in ("", None):
        cards = [{"page_function": kv, "rating": 5}]
        assert _score_by_key(cards, "page_function", "封面") == []
        assert _score_by_key(cards, "page_function", "任意别的词") == []
    # 正常模糊匹配不回归：真子串关系照旧 2 分
    hit = _score_by_key([{"page_function": "封面页", "rating": 3}], "page_function", "封面")
    assert hit and hit[0][1] == 2
