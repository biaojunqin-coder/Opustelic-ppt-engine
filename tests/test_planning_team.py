"""策划团队（策略阶段1.5·多角色分工）测试。"""

from __future__ import annotations

import pytest

from reinforce.planning_team import (
    BOARDS,
    GRANULARITIES,
    ROLE_CATALOG,
    all_decisions_so_far,
    all_done,
    assign_roles,
    assumption_ledger,
    check_open_questions_carried,
    complete_role,
    divergence_history,
    divergence_ledger,
    handoff_briefs_for,
    load_team,
    new_direction_card,
    new_planning_team,
    record_divergence,
    record_user_ack,
    save_team,
    set_confirm_granularity,
    start_role,
    validate_direction_cards,
    validate_planning_team,
)

# D18 FR1.1：complete_role 必填 user_summary——既有测试的收工调用统一用这份合理样例
_US = {"conclusion": "市场在增长但集中度低，有切入窗口",
       "highlights": ["规模500亿", "CAGR12%", "CR5仅18%"],
       "next_step": "交下一个角色细化受众"}


def _team_market_creative():
    team = new_planning_team("说服品牌方选我们做campaign")
    return assign_roles(team, ["市场策划", "创意策划"])


def test_new_team_has_no_roles_until_assigned():
    team = new_planning_team("p")
    assert team["order"] == [] and not validate_planning_team(team)["valid"]


def test_assign_unknown_role_rejected():
    with pytest.raises(ValueError, match="未知角色"):
        assign_roles(new_planning_team("p"), ["市场策划", "隔壁老王策划"])


def test_valid_assignment_passes():
    assert validate_planning_team(_team_market_creative())["valid"]


def test_board_order_backward_rejected():
    # 创意策划(Idea板块)排在市场策划(研究板块)前面——跨板块倒退
    team = new_planning_team("p")
    assign_roles(team, ["创意策划", "市场策划"])
    r = validate_planning_team(team)
    assert not r["valid"]
    assert any("倒退" in i["msg"] for i in r["issues"])


def test_same_board_order_not_flagged_as_backward():
    team = new_planning_team("p")
    assign_roles(team, ["市场策划", "人群策划"])  # 都是研究板块·同板块内顺序不算倒退
    assert validate_planning_team(team)["valid"]


# ── 严格接力链（用户原话"A完成前期搭建交给B完成中期搭建"）──
def test_first_role_can_start_immediately():
    team = _team_market_creative()
    start_role(team, "市场策划")
    assert team["roles"]["市场策划"]["status"] == "in_progress"


def test_second_role_blocked_until_first_done():
    team = _team_market_creative()
    start_role(team, "市场策划")
    with pytest.raises(ValueError, match="前面还有角色未完成"):
        start_role(team, "创意策划")


def test_second_role_starts_after_first_completes():
    team = _team_market_creative()
    start_role(team, "市场策划")
    complete_role(team, "市场策划", key_findings=["市场规模500亿·CAGR12%", "竞品A/B主打功能性"],
                  user_summary=_US)
    start_role(team, "创意策划")  # 不该再抛异常
    assert team["roles"]["创意策划"]["status"] == "in_progress"


def test_unassigned_role_cannot_start():
    team = _team_market_creative()
    with pytest.raises(ValueError, match="未被 leader 分配"):
        start_role(team, "媒介策划")


# ── 结构化交接（2026-07-01 补·防"1+1"过程中信息丢失）──
def test_complete_role_requires_nonempty_key_findings():
    team = _team_market_creative()
    start_role(team, "市场策划")
    with pytest.raises(ValueError, match="key_findings 不能空"):
        complete_role(team, "市场策划", key_findings=[], user_summary=_US)


def test_complete_role_decisions_default_empty_list_not_none():
    team = _team_market_creative()
    start_role(team, "市场策划")
    complete_role(team, "市场策划", key_findings=["规模500亿"], user_summary=_US)
    assert team["roles"]["市场策划"]["handoff"]["decisions"] == []


def test_handoff_carries_decisions_for_next_role_to_read():
    team = _team_market_creative()
    start_role(team, "市场策划")
    complete_role(team, "市场策划", key_findings=["规模500亿"], user_summary=_US,
                  decisions=[{"question": "要不要覆盖下沉市场", "answer": "不要·只做一二线"}])
    briefs = handoff_briefs_for(team, "创意策划")
    assert briefs[0]["decisions"][0]["answer"] == "不要·只做一二线"


def test_all_decisions_so_far_aggregates_across_completed_roles():
    team = _team_market_creative()
    start_role(team, "市场策划")
    complete_role(team, "市场策划", key_findings=["f1"], user_summary=_US,
                  decisions=[{"question": "覆盖下沉市场吗", "answer": "不要"}])
    start_role(team, "创意策划")
    complete_role(team, "创意策划", key_findings=["big idea: 新世界的选择"], user_summary=_US,
                  decisions=[{"question": "idea要不要带英文slogan", "answer": "要"}])
    ds = all_decisions_so_far(team)
    assert len(ds) == 2
    assert ds[0]["role"] == "市场策划" and ds[1]["role"] == "创意策划"


def test_all_decisions_so_far_empty_for_fresh_team():
    assert all_decisions_so_far(_team_market_creative()) == []


# ── 交接简报"1+1累积"（越往后角色看到的上下文越完整，不是只看上一个人的）──
def test_handoff_briefs_accumulate_not_just_last_role():
    team = new_planning_team("p")
    assign_roles(team, ["市场策划", "人群策划", "创意策划"])
    start_role(team, "市场策划")
    complete_role(team, "市场策划", key_findings=["市场f1"], user_summary=_US)
    start_role(team, "人群策划")
    complete_role(team, "人群策划", key_findings=["人群f1"], user_summary=_US)
    briefs = handoff_briefs_for(team, "创意策划")
    assert len(briefs) == 2  # 创意策划能看到市场+人群两个角色的全部交接·不是只看人群策划一个
    assert {b["role"] for b in briefs} == {"市场策划", "人群策划"}


def test_handoff_briefs_empty_for_first_role():
    team = _team_market_creative()
    assert handoff_briefs_for(team, "市场策划") == []


# ── 全部完工判断（leader 用来确认整份deck架构是否搭完）──
def test_all_done_false_until_every_role_completes():
    team = _team_market_creative()
    start_role(team, "市场策划")
    complete_role(team, "市场策划", key_findings=["f1"], user_summary=_US)
    assert not all_done(team)
    start_role(team, "创意策划")
    complete_role(team, "创意策划", key_findings=["f2"], user_summary=_US)
    assert all_done(team)


def test_all_done_false_for_empty_team():
    assert not all_done(new_planning_team("p"))


def test_role_catalog_covers_user_named_six_roles():
    # 用户原话点名的6个角色都要在目录里，不能漏
    named = {"市场策划", "人群策划", "创意策划", "媒介策划", "线上推广策划", "线下推广策划"}
    assert named <= set(ROLE_CATALOG)


# ── 研究板块扩展（2026-07-01·`/yanjiu`四路调研咨询/投行PE/企业战略/pitch deck服务·D10）──
def test_role_catalog_covers_consulting_finance_roles():
    consulting_finance = {"行业专家策划", "商业尽调策划", "财务尽调策划", "法务尽调策划", "数据建模策划"}
    assert consulting_finance <= set(ROLE_CATALOG)
    for rid in consulting_finance:
        assert ROLE_CATALOG[rid]["board"] == "研究"


def test_no_redundant_visual_execution_role_added():
    # D10刻意不做的边界：视觉呈现属于制作工作流职责，策略层不该重复加角色
    assert not any("视觉呈现" in rid or "排版" in rid for rid in ROLE_CATALOG)


def test_diligence_team_assembly_end_to_end():
    # 真实场景：尽调估值类deck·组一个投行PE风格的团队跑完整链路(不含广告campaign角色)
    team = new_planning_team("尽调后向投委会推荐是否收购标的公司")
    assign_roles(team, ["商业尽调策划", "财务尽调策划", "法务尽调策划", "数据建模策划", "叙事策划"])
    assert validate_planning_team(team)["valid"]
    for rid in team["order"]:
        start_role(team, rid)
        complete_role(team, rid, key_findings=[f"{rid}的关键发现"], user_summary=_US)
    assert all_done(team)


# ── 软依赖顺序提醒（2026-07-01·D11二次调研核实角色重叠·发现是递进关系非平行角色）──
def test_builds_on_missing_prereq_warns_not_errors():
    team = new_planning_team("p")
    assign_roles(team, ["商业尽调策划", "叙事策划"])  # 没带市场策划
    r = validate_planning_team(team)
    assert r["valid"]  # warn不阻断
    assert any("通常建立在 市场策划 之上" in i["msg"] for i in r["issues"])


def test_builds_on_prereq_present_no_warning():
    team = new_planning_team("p")
    assign_roles(team, ["市场策划", "商业尽调策划", "叙事策划"])
    r = validate_planning_team(team)
    assert not any("建立在" in i["msg"] for i in r["issues"])


def test_builds_on_wrong_order_warns():
    team = new_planning_team("p")
    assign_roles(team, ["商业尽调策划", "市场策划", "叙事策划"])  # 市场策划排在了商业尽调策划后面
    r = validate_planning_team(team)
    assert r["valid"]
    assert any("排在了 市场策划 前面" in i["msg"] for i in r["issues"])


def test_media_execution_roles_builds_on_media_planning():
    assert ROLE_CATALOG["线上推广策划"]["builds_on"] == "媒介策划"
    assert ROLE_CATALOG["线下推广策划"]["builds_on"] == "媒介策划"


def test_media_role_order_warns_when_reversed():
    team = new_planning_team("p")
    assign_roles(team, ["线上推广策划", "媒介策划", "叙事策划"])  # 媒介策划该先做
    r = validate_planning_team(team)
    assert any("排在了 媒介策划 前面" in i["msg"] for i in r["issues"])


def test_valuation_vs_financial_dd_remain_distinct_no_overlap_warning():
    # D11核实这对边界最清晰(前瞻建模 vs 回溯验证)，不该有builds_on关系(独立不是递进)
    assert "builds_on" not in ROLE_CATALOG["数据建模策划"]
    assert "builds_on" not in ROLE_CATALOG["财务尽调策划"]


def test_every_role_has_a_board_in_valid_sequence():
    for rid, meta in ROLE_CATALOG.items():
        assert meta["board"] in BOARDS, f"{rid} 的 board={meta['board']} 不在 {BOARDS} 内"


# ── 收尾整合角色"叙事策划"（2026-07-01 补·把全部产出顺成一份连贯storyline）──
def test_narrative_role_exists_in_integration_board():
    assert "叙事策划" in ROLE_CATALOG
    assert ROLE_CATALOG["叙事策划"]["board"] == "整合"


def test_narrative_role_not_last_warns():
    team = new_planning_team("p")
    assign_roles(team, ["市场策划", "叙事策划", "创意策划"])  # 顺序不对：叙事策划该排最后
    r = validate_planning_team(team)
    assert any("排最后" in i["msg"] for i in r["issues"])


def test_narrative_role_last_no_warning():
    team = new_planning_team("p")
    assign_roles(team, ["市场策划", "创意策划", "叙事策划"])
    r = validate_planning_team(team)
    assert not any("排最后" in i["msg"] for i in r["issues"])


def test_narrative_role_sees_all_prior_handoffs():
    team = new_planning_team("p")
    assign_roles(team, ["市场策划", "创意策划", "叙事策划"])
    start_role(team, "市场策划")
    complete_role(team, "市场策划", key_findings=["市场f1"], user_summary=_US)
    start_role(team, "创意策划")
    complete_role(team, "创意策划", key_findings=["idea f1"], user_summary=_US)
    start_role(team, "叙事策划")  # 前面全done·该能顺利开工
    briefs = handoff_briefs_for(team, "叙事策划")
    assert len(briefs) == 2


# ── 持久化（2026-07-01 补·防"本会话可能被压缩"导致交接内容丢失）──
def test_save_and_load_roundtrip(tmp_path):
    team = _team_market_creative()
    start_role(team, "市场策划")
    complete_role(team, "市场策划", key_findings=["f1"], user_summary=_US,
                  decisions=[{"question": "q1", "answer": "a1"}])
    start_role(team, "创意策划")
    complete_role(team, "创意策划", key_findings=["f2"], user_summary=_US)
    p = tmp_path / "team.json"
    save_team(team, p)
    loaded = load_team(p)
    assert loaded == team
    assert all_decisions_so_far(loaded)[0]["answer"] == "a1"


def test_save_refuses_invalid_team(tmp_path):
    team = new_planning_team("p")  # 未分配角色·非法
    with pytest.raises(ValueError, match="拒写"):
        save_team(team, tmp_path / "bad.json")


# ── 遗留问题收口弱提示（2026-07-01·问题收口 R-B）──
def test_open_question_flagged_when_never_echoed():
    team = _team_market_creative()
    start_role(team, "市场策划")
    complete_role(team, "市场策划", key_findings=["市场规模500亿"], user_summary=_US,
                  open_questions=["三个数据源关于竞对数量互相矛盾，未核实"])
    start_role(team, "创意策划")
    complete_role(team, "创意策划", key_findings=["big idea: 新世界的选择"],
                  user_summary=_US)  # 完全没提这条遗留问题
    out = check_open_questions_carried(team)
    assert any("竞对数量" in i["question"] for i in out)


def test_open_question_not_flagged_when_echoed_in_later_findings():
    team = _team_market_creative()
    start_role(team, "市场策划")
    complete_role(team, "市场策划", key_findings=["市场规模500亿"], user_summary=_US,
                  open_questions=["下沉市场覆盖策略待定"])
    start_role(team, "创意策划")
    complete_role(team, "创意策划", key_findings=["已核实下沉市场覆盖策略：暂不覆盖，聚焦一二线"],
                  user_summary=_US)
    assert check_open_questions_carried(team) == []


def test_open_questions_carried_ignores_in_progress_roles():
    team = _team_market_creative()
    start_role(team, "市场策划")  # 未 complete_role·仍 in_progress
    assert check_open_questions_carried(team) == []


# ── D18 FR1.1 结论强制（角色收工必须向用户摊结论·铁律0）──────────────────────
def test_complete_role_without_user_summary_rejected():
    team = _team_market_creative()
    start_role(team, "市场策划")
    with pytest.raises(ValueError, match="铁律0"):
        complete_role(team, "市场策划", key_findings=["规模500亿"])


def test_complete_role_user_summary_missing_conclusion_rejected():
    team = _team_market_creative()
    start_role(team, "市场策划")
    with pytest.raises(ValueError, match="user_summary"):
        complete_role(team, "市场策划", key_findings=["规模500亿"],
                      user_summary={"highlights": ["h1", "h2", "h3"]})


def test_complete_role_user_summary_empty_highlights_rejected():
    team = _team_market_creative()
    start_role(team, "市场策划")
    for bad in ([], ["", ""]):  # 空列表 / 全空串凑数——都不算"摊了发现"
        with pytest.raises(ValueError, match="摊结论"):
            complete_role(team, "市场策划", key_findings=["规模500亿"],
                          user_summary={"conclusion": "市场可入", "highlights": bad})


def test_complete_role_stores_user_summary_in_handoff():
    team = _team_market_creative()
    start_role(team, "市场策划")
    complete_role(team, "市场策划", key_findings=["规模500亿"],
                  user_summary={"conclusion": "市场可入", "highlights": ["规模500亿", "", "CR5低"]})
    us = team["roles"]["市场策划"]["handoff"]["user_summary"]
    assert us["conclusion"] == "市场可入"
    assert us["highlights"] == ["规模500亿", "CR5低"]  # 空串条目被过滤·不算数
    assert us["next_step"] == ""  # 未给 next_step 时落空串（不硬拦·FR1.1 只硬拦 conclusion/highlights）


def test_validate_flags_done_role_with_incomplete_user_summary():
    # 绕过 complete_role 手搓 status="done" 的旁路——validate 出口复查要能兜住（D18 FR1.1）
    team = _team_market_creative()
    start_role(team, "市场策划")
    complete_role(team, "市场策划", key_findings=["f1"], user_summary=_US)
    del team["roles"]["市场策划"]["handoff"]["user_summary"]
    r = validate_planning_team(team)
    assert not r["valid"]
    assert any("user_summary" in i["msg"] and "铁律0" in i["msg"] for i in r["issues"])


def test_save_refuses_done_role_without_user_summary(tmp_path):
    team = _team_market_creative()
    start_role(team, "市场策划")
    complete_role(team, "市场策划", key_findings=["f1"], user_summary=_US)
    team["roles"]["市场策划"]["handoff"]["user_summary"]["conclusion"] = ""  # 手改成空
    with pytest.raises(ValueError, match="拒写"):
        save_team(team, tmp_path / "bad.json")


# ── D18 FR1.2 确认粒度 + 关键节点 ack 留痕 ────────────────────────────────
def test_new_team_defaults_key_nodes_granularity():
    team = new_planning_team("p")
    assert team["confirm_granularity"] == "key_nodes"  # 默认=关键节点硬停（需求 FR1.2 拍板）
    assert team["user_acks"] == [] and team["divergences"] == []


def test_new_team_rejects_unknown_granularity():
    with pytest.raises(ValueError, match="非法"):
        new_planning_team("p", confirm_granularity="总之你看着办")


def test_granularities_catalog_is_four_tier():
    # D21 扩四档：direct_through=直通档（2026-07-03 用户拍板"字面直通"·brief 问完直接到成品）
    assert set(GRANULARITIES) == {"every_role", "key_nodes", "minimal", "direct_through"}


def test_set_confirm_granularity_records_user_quote():
    team = new_planning_team("p")
    set_confirm_granularity(team, "every_role", "每个角色做完都停下来问我")
    assert team["confirm_granularity"] == "every_role"
    assert team["granularity_quote"] == "每个角色做完都停下来问我"


def test_set_confirm_granularity_rejects_unknown_or_empty_quote():
    team = new_planning_team("p")
    with pytest.raises(ValueError, match="非法"):
        set_confirm_granularity(team, "自由发挥", "随便")
    with pytest.raises(ValueError, match="原话"):
        set_confirm_granularity(team, "minimal", "")


def test_record_user_ack_appends_node_and_quote():
    team = new_planning_team("p")
    record_user_ack(team, "storyline定稿", "可以，就按这版定稿")
    assert team["user_acks"] == [{"node": "storyline定稿", "user_quote": "可以，就按这版定稿"}]


def test_record_user_ack_requires_node_and_quote():
    team = new_planning_team("p")
    with pytest.raises(ValueError, match="node 不能空"):
        record_user_ack(team, "", "好的")
    with pytest.raises(ValueError, match="原话"):
        record_user_ack(team, "storyline定稿", "")
    assert team["user_acks"] == []  # 校验失败不留半截记录


def test_record_user_ack_works_on_legacy_team_without_field():
    # D18 前落盘的 team_state.json 没有 user_acks 字段（某品牌 一代实测形态）——setdefault 兼容
    legacy = {"brief_purpose": "p", "order": [], "roles": {}}
    record_user_ack(legacy, "交棒制作", "开始做吧")
    assert legacy["user_acks"][0]["node"] == "交棒制作"


def test_acks_survive_save_load_roundtrip(tmp_path):
    team = _team_market_creative()
    start_role(team, "市场策划")
    complete_role(team, "市场策划", key_findings=["f1"], user_summary=_US)
    start_role(team, "创意策划")
    complete_role(team, "创意策划", key_findings=["f2"], user_summary=_US)
    record_user_ack(team, "storyline定稿", "定稿吧")
    p = tmp_path / "team.json"
    save_team(team, p)
    assert load_team(p)["user_acks"][-1]["user_quote"] == "定稿吧"


# ── D18 FR1.3 方向卡发散（≥2 张才叫发散·发散点=硬停点·收敛留痕）───────────────
def _three_cards():
    return [
        new_direction_card("国民情绪牌", "把CNY流量押在归家情绪共鸣", ["市场规模500亿"],
                           "TVC+社媒共创", "情绪资产竞品无法复制", "创意产能要求高", "高"),
        new_direction_card("渠道渗透牌", "放弃大创意·all-in零售终端触点", ["CR5仅18%"],
                           "终端物料+O2O", "预算转化效率最高", "品牌资产积累弱", "中"),
        new_direction_card("电竞跨界牌", "借电竞人群重做年轻化", ["Z世代渗透率升至41%"],
                           "战队联名+直播", "人群增量最明确", "跟品牌调性有距离", "中"),
    ]


def test_direction_card_schema_complete():
    c = _three_cards()[0]
    assert set(c) == {"name", "core_logic", "supporting_findings", "play_summary",
                      "why_win", "risks", "fit"}  # 需求 FR1.3 的 schema 七字段·一个不少


def test_validate_direction_cards_pass():
    assert validate_direction_cards(_three_cards()) == []


def test_single_card_is_not_divergence():
    errs = validate_direction_cards(_three_cards()[:1])
    assert any("≥2" in e["msg"] for e in errs)


def test_direction_card_missing_required_field_rejected():
    for k in ("name", "core_logic", "why_win"):
        cards = _three_cards()
        cards[1][k] = ""
        assert any(k in e["msg"] for e in validate_direction_cards(cards)), f"缺 {k} 该报 error"


def test_duplicate_card_names_rejected():
    cards = _three_cards()
    cards[2]["name"] = cards[0]["name"]
    assert any("重复" in e["msg"] for e in validate_direction_cards(cards))


def test_record_divergence_appends_and_auto_acks():
    team = new_planning_team("p")
    record_divergence(team, "策略方向", _three_cards(), "国民情绪牌",
                      "brief明确要情绪共鸣·渠道打法客户去年用过了", "就第一个方向吧")
    d = team["divergences"][0]
    assert d["node"] == "策略方向" and d["chosen"] == "国民情绪牌"
    assert "去年用过" in d["reason"] and len(d["cards"]) == 3
    # 收敛即确认：自动记了该发散点的 ack（发散点=硬停点·FR1.2/FR1.3 接口处）
    assert any(a["node"] == "方向收敛:策略方向" and a["user_quote"] == "就第一个方向吧"
               for a in team["user_acks"])


def test_record_divergence_rejects_chosen_not_in_cards():
    with pytest.raises(ValueError, match="chosen"):
        record_divergence(new_planning_team("p"), "策略方向", _three_cards(),
                          "隔壁公司的方案", "理由", "原话")


def test_record_divergence_accepts_mixed_choice_prefix():
    team = new_planning_team("p")
    record_divergence(team, "策略方向", _three_cards(), "混合:情绪牌主线+渠道牌终端打法",
                      "要情绪也要终端转化", "两个都要一点")
    assert team["divergences"][0]["chosen"].startswith("混合:")


def test_record_divergence_requires_reason():
    with pytest.raises(ValueError, match="reason"):
        record_divergence(new_planning_team("p"), "策略方向", _three_cards(),
                          "国民情绪牌", "", "原话")


def test_record_divergence_rejects_invalid_cards():
    with pytest.raises(ValueError, match="方向卡不合法"):
        record_divergence(new_planning_team("p"), "策略方向", _three_cards()[:1],
                          "国民情绪牌", "理由", "原话")


def test_record_divergence_no_partial_state_on_failure():
    # 校验先行·全过才写：user_quote 缺失时 divergences 和 user_acks 都不该留半截记录
    team = new_planning_team("p")
    with pytest.raises(ValueError, match="user_quote"):
        record_divergence(team, "策略方向", _three_cards(), "国民情绪牌", "理由", "")
    assert team["divergences"] == [] and team["user_acks"] == []


# ── D18 FR6.4 选择偏好内化（用户为什么选它=飞轮最金贵的知识）──────────────────
def test_divergence_ledger_minimal_shape():
    team = new_planning_team("p")
    record_divergence(team, "策略方向", _three_cards(), "国民情绪牌", "brief要情绪共鸣", "第一个")
    ledger = divergence_ledger(team)
    assert ledger == [{"node": "策略方向", "chosen": "国民情绪牌", "reason": "brief要情绪共鸣"}]
    assert "cards" not in ledger[0]  # 精简台账不背全量卡·全量在 team["divergences"] 可回放


def test_divergence_ledger_empty_for_legacy_team():
    assert divergence_ledger({"brief_purpose": "p", "order": [], "roles": {}}) == []


def test_divergences_survive_save_load_roundtrip(tmp_path):
    team = _team_market_creative()
    start_role(team, "市场策划")
    complete_role(team, "市场策划", key_findings=["f1"], user_summary=_US)
    start_role(team, "创意策划")
    complete_role(team, "创意策划", key_findings=["f2"], user_summary=_US)
    record_divergence(team, "策略方向", _three_cards(), "渠道渗透牌", "预算有限先保转化", "选渠道那个")
    p = tmp_path / "team.json"
    save_team(team, p)
    assert divergence_ledger(load_team(p)) == divergence_ledger(team)


# ── D19 FR4.2 跨 deck divergence 聚合读取器 ─────────────────────────────────

def test_divergence_history_skips_dirty_data_and_sorts_by_mtime(tmp_path):
    """聚合读取器对脏数据要韧：坏 JSON/缺字段跳过并继续，绝不 raise 拒全部；按 mtime 排序。"""
    import json as _json
    import os
    from reinforce.planning_team import divergence_history
    for name, payload in (
        ("deck_new", _json.dumps({"divergences": [
            {"node": "n1", "chosen": "c1", "reason": "r1"}]})),
        ("deck_broken", "{broken json"),                       # 坏 JSON → 跳过
        ("deck_missing", _json.dumps({"divergences": [
            {"node": "n2", "chosen": "c2"}]})),                # 缺 reason → 该条跳过
        ("deck_notdict", _json.dumps(["not", "a", "dict"])),   # 非 dict → 跳过
        ("deck_old", _json.dumps({"divergences": [
            {"node": "n3", "chosen": "c3", "reason": "r3"}]})),
    ):
        d = tmp_path / name
        d.mkdir()
        (d / "team_state.json").write_text(payload, encoding="utf-8")
    os.utime(tmp_path / "deck_new" / "team_state.json", (2000, 2000))
    os.utime(tmp_path / "deck_old" / "team_state.json", (1000, 1000))  # 更旧 → 排前
    hist = divergence_history(tmp_path)
    assert [(h["deck_id"], h["reason"]) for h in hist] == [
        ("deck_old", "r3"), ("deck_new", "r1")]                # 旧→新时间线·脏数据全被跳过


def test_divergence_history_missing_root_returns_empty(tmp_path):
    from reinforce.planning_team import divergence_history
    assert divergence_history(tmp_path / "no_such_dir") == []


def test_divergence_history_docstring_bans_premature_profiling():
    """D19 用户拍板的克制必须写在 docstring 里防手痒——2 条样本抽象必歪，等 5+ 条。"""
    from reinforce.planning_team import divergence_history
    doc = divergence_history.__doc__ or ""
    assert "暂不做偏好画像" in doc and "5+" in doc and "过早抽象" in doc


# ---------- D21 直通档（direct_through）：auto 代拍留痕 + 防飞轮污染 ----------

def _direct_team():
    team = new_planning_team("p", confirm_granularity="key_nodes")
    set_confirm_granularity(team, "direct_through", "直通档就是字面上的直通，问完直接到出成品")
    return team


def test_auto_divergence_records_with_auth_and_no_ack():
    team = _direct_team()
    record_divergence(team, "策略方向", _three_cards(), "国民情绪牌",
                      "brief 明确要情绪共鸣·三卡中唯一有竞品不可复制护城河", auto_decided=True)
    d = team["divergences"][0]
    assert d["auto_decided"] is True and d["user_quote"] == ""
    assert "字面上的直通" in d["auth_quote"]        # 根授权原话跟着条目走·事后可对质
    assert team["user_acks"] == []                  # ack 列表只放真人确认·auto 不伪造


def test_auto_divergence_rejected_outside_direct_through():
    team = new_planning_team("p")                   # 默认 key_nodes
    with pytest.raises(ValueError, match="direct_through"):
        record_divergence(team, "策略方向", _three_cards(), "国民情绪牌",
                          "理由", auto_decided=True)


def test_auto_divergence_rejects_fabricated_user_quote():
    # AI 不能编造用户原话——有真原话就不该走 auto 路径（防假绿同一条纪律）
    with pytest.raises(ValueError, match="user_quote 必须为空"):
        record_divergence(_direct_team(), "策略方向", _three_cards(), "国民情绪牌",
                          "理由", "用户说选这个", auto_decided=True)


def test_auto_divergence_requires_root_auth_quote():
    # 手改 json 塞 direct_through 但没有根授权原话——代拍即越权，拒
    team = new_planning_team("p")
    team["confirm_granularity"] = "direct_through"  # 绕过 set_confirm_granularity 的旁路
    with pytest.raises(ValueError, match="根授权"):
        record_divergence(team, "策略方向", _three_cards(), "国民情绪牌",
                          "理由", auto_decided=True)


def test_ledgers_split_auto_from_human():
    # 同一 team 混两种收敛：偏好回灌只见人工，假设台账只见 auto（防飞轮污染·D21）
    team = _direct_team()
    record_divergence(team, "创意概念", _three_cards(), "渠道渗透牌",
                      "用户亲口要终端打法", user_quote="就渠道这个")
    record_divergence(team, "策略方向", _three_cards(), "国民情绪牌",
                      "AI 代选：唯一有护城河", auto_decided=True)
    assert [d["node"] for d in divergence_ledger(team)] == ["创意概念"]
    ledger = assumption_ledger(team)
    assert [d["node"] for d in ledger] == ["策略方向"]
    assert "字面上的直通" in ledger[0]["auth_quote"]


# ---------- 批③🟡 根授权原话代填拒收（启发式·防假绿）----------

def test_jargon_quote_rejected_at_all_three_entries():
    # "用户原话"混进机制黑话（waiver/留痕豁免…）→ 疑似 AI 代填，三个留痕写入口全拒且不留半截
    bad = "人审闸waiver留痕豁免"
    team = new_planning_team("p")
    with pytest.raises(ValueError, match="代填"):
        set_confirm_granularity(team, "direct_through", bad)
    with pytest.raises(ValueError, match="代填"):
        record_user_ack(team, "storyline定稿", bad)
    with pytest.raises(ValueError, match="代填"):
        record_divergence(team, "策略方向", _three_cards(), "国民情绪牌", "理由", bad)
    assert team["granularity_quote"] == "" and team["confirm_granularity"] == "key_nodes"
    assert team["user_acks"] == [] and team["divergences"] == []


def test_jargon_check_case_insensitive():
    with pytest.raises(ValueError, match="代填"):
        record_user_ack(new_planning_team("p"), "storyline定稿", "OK，按 AUTO_DECIDED 走")


def test_normal_user_quote_passes_jargon_check():
    # 正常原话不含机制术语·照常通过（启发式的误伤面：用户不说机制黑话）
    team = new_planning_team("p")
    set_confirm_granularity(team, "direct_through", "直通档就是字面上的直通")
    assert team["granularity_quote"] == "直通档就是字面上的直通"
    record_user_ack(team, "storyline定稿", "可以，就按这版定稿")
    assert team["user_acks"][0]["user_quote"] == "可以，就按这版定稿"


def test_divergence_history_filters_auto(tmp_path):
    import json as _json
    deck = tmp_path / "deck_a"
    deck.mkdir()
    team = _direct_team()
    record_divergence(team, "创意概念", _three_cards(), "渠道渗透牌",
                      "用户亲口要终端打法", user_quote="就渠道这个")
    record_divergence(team, "策略方向", _three_cards(), "国民情绪牌",
                      "AI 代选", auto_decided=True)
    (deck / "team_state.json").write_text(_json.dumps(team, ensure_ascii=False), encoding="utf-8")
    hist = divergence_history(tmp_path)
    assert [h["node"] for h in hist] == ["创意概念"]   # 跨 deck 偏好注入永远不含 AI 代拍


def test_pre_d18_team_user_summary_missing_is_warn_not_error():
    # D26 历史豁免：无 confirm_granularity 字段=pre-D18 形态（某品牌 一代）——缺 user_summary
    # 如实降 warn（不回填不伪造·防假绿），新单（有粒度机制字段）缺失仍 error
    legacy = {"brief_purpose": "p", "order": ["市场策划"],
              "roles": {"市场策划": {"status": "done", "handoff": {"key_findings": ["f"],
                                                                   "decisions": [], "open_questions": []}}}}
    r = validate_planning_team(legacy)
    assert r["valid"]   # warn 不阻断
    assert any("pre-D18" in i["msg"] and i["sev"] == "warn" for i in r["issues"])
    modern = {**legacy, "confirm_granularity": "key_nodes", "granularity_quote": "按默认",
              "user_acks": [], "divergences": []}
    r2 = validate_planning_team(modern)
    assert not r2["valid"]  # 新单同样缺失=error 不放行
