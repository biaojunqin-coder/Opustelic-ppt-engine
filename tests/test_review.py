"""三道审查 + Critic（策略阶段5·质量门人审）测试。"""

from __future__ import annotations

from reinforce.review import (
    REVIEWS,
    check_evidence_direction,
    check_evidence_directions,
    check_fact_grounded,
    check_facts_grounded,
    critic_light,
    extract_numeric_facts,
    new_review,
    score_review,
)


def _all(review, val):
    for cat in review:
        for item in review[cat]:
            review[cat][item] = val
    return review


def test_new_review_all_unrated_is_yellow():
    assert critic_light(score_review(new_review())) == "黄"


def test_all_pass_green():
    s = score_review(_all(new_review(), True))
    assert s["all_passed"] and critic_light(s) == "绿"


def test_any_fail_red():
    r = _all(new_review(), True)
    cat = next(iter(r)); item = next(iter(r[cat]))
    r[cat][item] = False
    s = score_review(r)
    assert not s[cat]["passed"] and critic_light(s) == "红"


def test_score_review_tolerates_missing_role_key():
    """批④容错：review 缺整道角色键（旧落盘/手编 JSON）=该道全部未评——保守计 0 通过率
    进汇总（critic_light 自然给黄），不再 KeyError 崩掉整个汇总。"""
    r = _all(new_review(), True)
    del r["slide_content"]
    s = score_review(r)   # 修复前：out 缺键 → all_passed 行 KeyError
    assert s["slide_content"] == {"rate": 0.0, "passed": False,
                                  "unrated": len(REVIEWS["slide_content"])}
    assert s["all_passed"] is False          # 缺道绝不算过（fail-closed）
    assert critic_light(s) == "黄"           # 全未评=待审完，不是绿


def test_threshold_90_percent():
    r = _all(new_review(), True)
    # action_title 4 项 → 1 项 False = 75% < 90% 不过
    item = next(iter(r["action_title"]))
    r["action_title"][item] = False
    s = score_review(r)
    assert not s["action_title"]["passed"] and s["action_title"]["rate"] == 0.75


# ── 跨页关键事实摘录（spec_lock 的事实层对应物·只罗列不判矛盾·人审用）──
def test_extract_numeric_facts_groups_by_dim():
    sl = {"lines": [
        {"n": 1, "claim": "p1", "evidence": [{"dim": "市场规模", "data": "10053亿元"}]},
        {"n": 5, "claim": "p5", "evidence": [{"dim": "市场规模", "data": "9800亿元"}]},  # 同 dim 不同数值
        {"n": 2, "claim": "p2", "evidence": [{"dim": "唯一出现的维度", "data": "100万"}]},
    ]}
    facts = extract_numeric_facts(sl)
    assert "市场规模" in facts and len(facts["市场规模"]) == 2
    assert "唯一出现的维度" not in facts  # 只出现1次·没有"跨页"可言·不列


def test_extract_numeric_facts_skips_non_numeric():
    sl = {"lines": [{"n": 1, "claim": "p1", "evidence": [
        {"dim": "立场", "data": "身份消费见顶"}, {"dim": "立场", "data": "身份消费仍在涨"}]}]}
    assert extract_numeric_facts(sl) == {}  # 无数字的 evidence 不纳入(这是审证据深度/framing的事·不是事实一致性的事)


# ── 两层防假阳第一层：数字是否在 source_quote 原文里字面出现过（Auto-Slides 启发）──
def test_fact_grounded_number_present_in_quote_passes():
    ev = {"dim": "市场规模", "data": "42%", "source_quote": "该行业渗透率达到42%，创历史新高"}
    assert check_fact_grounded(ev) == []


def test_fact_grounded_catches_number_missing_from_quote():
    ev = {"dim": "市场规模", "data": "42%", "source_quote": "该行业渗透率持续增长，前景看好"}
    out = check_fact_grounded(ev)
    assert any(i["rule"] == "number_not_in_source_quote" and "42" in i["note"] for i in out)
    assert all(i["sev"] == "warn" for i in out)  # warn非error·查不到不等于假


def test_fact_grounded_ignores_comma_formatting_difference():
    # data 写 "1,837.78万"·quote 原文写 "1837.78万"——只比数字本身，逗号分隔不算"对不上"
    ev = {"dim": "游客量", "data": "1,837.78万人次", "source_quote": "全年接待游客1837.78万人次"}
    assert check_fact_grounded(ev) == []


def test_fact_grounded_skips_without_source_quote():
    # 没有 source_quote 就没有"对不对得上"的基准·这层不查(check_source 管"有没有标source"这层更浅的)
    assert check_fact_grounded({"dim": "x", "data": "42%"}) == []


def test_fact_grounded_skips_without_numeric_data():
    ev = {"dim": "立场", "data": "身份消费见顶", "source_quote": "随便什么原文"}
    assert check_fact_grounded(ev) == []


def test_facts_grounded_aggregates_across_storyline_with_page_number():
    sl = {"lines": [
        {"n": 3, "claim": "p3", "evidence": [
            {"dim": "净利率", "data": "-20%", "source_quote": "净利润率下滑，具体数字待核实"}]},
    ]}
    out = check_facts_grounded(sl)
    assert len(out) == 1 and out[0]["n"] == 3 and out[0]["dim"] == "净利率"


# ── 方向词与数字实际增减一致性（2026-07-01 yanjiu研究驱动评估🟡走样需修·Auto-Slides语义方向校验）──
def test_evidence_direction_consistent_up_passes():
    assert check_evidence_direction({"dim": "占比", "data": "占比42%升至58%"}) == []


def test_evidence_direction_consistent_down_passes():
    assert check_evidence_direction({"dim": "净利率", "data": "净利率从18%降至11%"}) == []


def test_evidence_direction_catches_up_word_but_actual_decrease():
    # 说"提升"但58→42实际是下降
    out = check_evidence_direction({"dim": "占比", "data": "占比从58%提升至42%"})
    assert out and out[0]["rule"] == "evidence_direction_mismatch" and out[0]["sev"] == "warn"


def test_evidence_direction_catches_down_word_but_actual_increase():
    # 说"下降"但42→58实际是上升
    out = check_evidence_direction({"dim": "占比", "data": "占比从42%下降至58%"})
    assert out and out[0]["rule"] == "evidence_direction_mismatch"


def test_evidence_direction_skips_no_direction_word():
    assert check_evidence_direction({"dim": "占比", "data": "42%到58%"}) == []  # 无方向词·没有可对照的说法


def test_evidence_direction_skips_single_number():
    assert check_evidence_direction({"dim": "占比", "data": "占比提升明显"}) == []  # 没有2个数字·没有"变化前后"


def test_evidence_direction_skips_more_than_two_numbers():
    assert check_evidence_direction({"dim": "x", "data": "从42%到58%再到65%提升"}) == []  # 3个数字·语义不清不瞎猜


def test_evidence_direction_skips_equal_numbers():
    assert check_evidence_direction({"dim": "x", "data": "维持在42%提升至42%"}) == []  # 没变化·不是方向问题


def test_evidence_directions_aggregates_across_storyline_with_page_number():
    sl = {"lines": [
        {"n": 5, "claim": "p5", "evidence": [{"dim": "占比", "data": "占比从58%提升至42%"}]},
    ]}
    out = check_evidence_directions(sl)
    assert len(out) == 1 and out[0]["n"] == 5 and out[0]["dim"] == "占比"


# ── 2026-07-02 saopan扫盘修复回归 ─────────────────────────────────────
def test_direction_year_pattern_no_false_positive():
    """③🔴3：「2025年增长12%」曾被抠成 2025→12 误报下降——收窄到显式过渡结构后不判。"""
    from reinforce.review import check_evidence_direction
    assert check_evidence_direction({"data": "2025年增长12%"}) == []
    assert check_evidence_direction({"data": "Q3下降5%"}) == []


def test_direction_explicit_transitions_still_caught():
    from reinforce.review import check_evidence_direction
    assert check_evidence_direction({"data": "从120家增长到150家"}) == []          # 方向一致不报
    r = check_evidence_direction({"data": "毛利率从58%提升到42%"})                 # 显式结构+矛盾
    assert r and r[0]["rule"] == "evidence_direction_mismatch"
    r2 = check_evidence_direction({"data": "转化率 30%→18%，持续增长"})            # 箭头结构+矛盾
    assert r2 and r2[0]["rule"] == "evidence_direction_mismatch"
    r3 = check_evidence_direction({"data": "门店数由30家降至25家"})                # 由…降至·一致不报
    assert r3 == []


def test_grounded_tolerates_numeric_and_none_shapes():
    """🟡：data 为数字类型 / lines=None / 行缺 n——合法 JSON 形态不再崩。"""
    from reinforce.review import check_fact_grounded, check_facts_grounded, extract_numeric_facts
    assert check_fact_grounded({"data": 12.5, "source_quote": "12.5亿"}) == []
    assert check_facts_grounded({"lines": None}) == []
    assert check_facts_grounded({"lines": [{"evidence": [{"data": "1", "source_quote": "1"}]}]}) != None  # 缺 n 不崩
    assert extract_numeric_facts({"lines": None}) == {}
