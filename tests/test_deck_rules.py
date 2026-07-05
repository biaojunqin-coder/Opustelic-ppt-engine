"""deck_rules 确定性硬门独立单测——守铁律：机检判死、不依赖前端。"""

from __future__ import annotations

from reinforce.deck_rules import rules as G


def test_source_errors_on_naked_number():
    """2026-07-01 用户拍板从 warn 升级 error："数据必须能够溯源，这是100%的"。"""
    iss = G.check_source("市场增长 40%")
    assert iss and iss[0]["sev"] == "error" and iss[0]["rule"] == "number_no_source"
    assert G.check_source("市场增长 40% Source: NTD") == []


def test_source_ignores_page_labels():
    """2026-07-01 saopan扫盘揪出：页码类装饰数字(第4页/共10页/4/10页)不该被当成需要溯源的证据。"""
    assert G.check_source("共10页") == []
    assert G.check_source("第4/10页") == []
    assert G.check_source("第4页") == []


def test_source_still_catches_real_claim_next_to_page_label():
    """页码豁免不能连带放过页面里真正需要溯源的数字。"""
    iss = G.check_source("市场增长40% 第4页")
    assert iss and iss[0]["rule"] == "number_no_source"


def test_source_catches_single_digit_with_measure_unit():
    """2026-07-02 saopan扫盘揪出：\\d{2,} 放行一位数金额——error 级红线上的 fail-open。
    一位数+计量单位(亿/万/成/倍/%/个百分点)是如假包换的证据数字，必须触发溯源门。"""
    for text in ["亏损5亿元", "毛利率提升3成", "营收翻2倍", "增速2.5倍", "下降3个百分点", "投入8千万"]:
        iss = G.check_source(text)
        assert iss and iss[0]["rule"] == "number_no_source", f"应触发：{text}"
    assert G.check_source("亏损5亿元·数据来源：年报") == []


def test_source_single_digit_without_unit_still_exempt():
    """一位数补丁不能把非数据数字拉进来——\\d{2,} 当初就是防这个。"""
    assert G.check_source("我们提出3个方案") == []
    assert G.check_source("第5页") == []  # 页码豁免(_PAGE_LABEL_RE)不被破坏
    assert G.check_source("分4步走") == []


def test_page_budget_over_is_error():
    iss = G.check_page_budget("donut", 8)
    assert iss and iss[0]["sev"] == "error" and iss[0]["cap"] == 6


def test_page_budget_within_ok():
    assert G.check_page_budget("donut", 5) == []


def test_font_off_grid_warns():
    assert G.check_font(20)          # 20pt 不在网格
    assert G.check_font(22) == []     # 22pt 合法(内容页 action title)


def test_title_topic_word_warns():
    assert any(i["rule"] == "title_maybe_topic" for i in G.check_title("市场分析"))
    assert G.check_title("市场涨40%但收入跌5%") == []  # 论断式·过


def test_title_mixed_cjk_english_long_flagged():
    """2026-07-02 saopan扫盘揪出：中英混排长标题两分支都躲过——3个汉字+30个英文词，
    cjk=3 不超20、cjk 非零进不了英文分支。加权折算(1词=4/3字当量)后必须触发。"""
    title = "增长战略 " + " ".join(["strategic"] * 30)
    assert any(i["rule"] == "title_too_long" for i in G.check_title(title))


def test_title_pure_cjk_and_pure_english_boundaries_unchanged():
    """混排补丁不动纯中文(>20字)/纯英文(>15词)的既有边界——恰好压线不报、超一格才报。"""
    assert not any(i["rule"] == "title_too_long" for i in G.check_title("一二三四五六七八九十" * 2))   # 20字
    assert any(i["rule"] == "title_too_long" for i in G.check_title("一二三四五六七八九十" * 2 + "一"))  # 21字
    assert not any(i["rule"] == "title_too_long" for i in G.check_title(" ".join(["w"] * 15)))  # 15词
    assert any(i["rule"] == "title_too_long" for i in G.check_title(" ".join(["w"] * 16)))      # 16词


def test_title_short_mixed_not_flagged():
    """正常长度的混排标题(几个汉字+少量英文)不能被加权判误伤。"""
    assert not any(i["rule"] == "title_too_long" for i in G.check_title("ROI提升3倍但NPS下滑"))


def test_text_gate_pass_clean():
    r = G.run_text_gate("收入增 25%·Source: NTD", title="收入增25%但成本翻倍")
    assert r["passed"] is True


def test_text_gate_fail_closed_on_naked_number():
    """run_text_gate 恢复 fail-closed 能力（此前唯一 error 来源是已移除的 AI 味检查）。"""
    assert G.run_text_gate("市场增长 40%，前景可期")["passed"] is False


# ── 字段级长度契约通用版（2026-07-01 yanjiu研究驱动评估🟢采纳·泛化check_page_budget模式）──
def test_field_budget_over_cap_is_error():
    iss = G.check_field_budget("subtitle", "x" * 31, 30)
    assert iss and iss[0]["sev"] == "error" and iss[0]["field"] == "subtitle" and iss[0]["got"] == 31


def test_field_budget_within_cap_ok():
    assert G.check_field_budget("subtitle", "x" * 30, 30) == []


def test_field_budget_empty_text_ok():
    assert G.check_field_budget("sowhat", "", 20) == []


def test_field_budget_none_text_treated_as_empty():
    assert G.check_field_budget("sowhat", None, 20) == []  # 字段未填不是"超限"，是另一个问题(缺失)


# ── D18 FR5.2 对客文案门（warn·坏例子清单靠飞轮逐单积累）─────────────────
from reinforce.deck_rules.client_tone import (ACRONYM_WHITELIST, check_client_facing_tone,
                                              run_client_tone_gate)


def test_client_tone_brief_locator_flagged():
    """第一轮实测坏例子①：'brief P3-4' 工作定位符永不上对客页面。"""
    out = check_client_facing_tone("来源：brief P3-4")
    assert any(i["rule"] == "internal_locator" for i in out)
    # D19 FR1.2 升级：定位符 warn→error（第二轮实测证明 warn 被忽略仍上页·用户拍板硬拦）
    assert any(i["rule"] == "internal_locator" and i["sev"] == "error" for i in out)
    assert any("来源" in i["note"] for i in out)   # note 给了改写方向(FR5.1 页脚溯源)


def test_client_tone_process_narration_flagged():
    """第一轮实测坏例子②（某品牌 page_2 原文）：流程自述句式是说给项目组听的。"""
    out = check_client_facing_tone("对齐我们对brief的理解，确保方向不跑偏")
    hits = {i["hit"] for i in out if i["rule"] == "process_narration"}
    assert {"对齐我们对", "确保方向不跑偏"} <= hits
    assert any("speaker_notes" in i["note"] for i in out)   # 改写方向指向语域分工(FR5.3)


def test_client_tone_internal_acronym_flagged_whitelist_passes():
    """第一轮实测坏例子③：GD/GX 区域内部代号报；营销通用白名单缩写(KOL/CNY/ROI…)放行。"""
    out = check_client_facing_tone("BPS品牌健康度GD领先GX待追赶")
    hits = {i["hit"] for i in out if i["rule"] == "internal_acronym"}
    assert hits == {"GD", "GX"}   # BPS 是客户 brief 自用术语·在白名单不报
    assert check_client_facing_tone("KOL与KOC组合投放，CNY档期ROI翻倍，UGC反哺SCRM") == []


def test_client_tone_acronym_boundary_lowercase_plural_not_hit():
    """'KOLs' 复数形态(后挨小写字母)整体不该命中缩写正则——lookaround 边界回归。"""
    assert not any(i["rule"] == "internal_acronym"
                   for i in check_client_facing_tone("头部KOLs负责背书"))


def test_client_tone_work_jargon_flagged():
    """第一轮实测坏例子④：Engine 内部工位口语（"填肉"/"埋点位"）任何语境不上页面。"""
    out = check_client_facing_tone("这一页先埋点位后续填肉")
    hits = {i["hit"] for i in out if i["rule"] == "work_jargon"}
    assert {"填肉", "埋点位"} <= hits


def test_client_tone_clean_client_copy_passes():
    """正常对客文案零命中——门的存在感应该只在踩线时出现。"""
    assert check_client_facing_tone("在CNY营销同质化红海里，某品牌该做减法") == []
    assert check_client_facing_tone("") == []
    assert check_client_facing_tone(None) == []


def test_client_tone_gate_extracts_svg_text_and_annotates():
    """run_client_tone_gate 抽 <text> 内容(剥 tspan)逐条查，issue 附文案摘要供人审定位。"""
    svg = ('<svg viewBox="0 0 1280 720"><rect width="1280" height="720" fill="#FFF"/>'
           '<text x="90" y="68">对齐我们对brief的理解</text>'
           '<text x="90" y="120"><tspan>来源：</tspan><tspan>brief P9</tspan></text>'
           '<text x="90" y="200">正常的对客结论文案</text></svg>')
    out = run_client_tone_gate(svg)
    rules = {i["rule"] for i in out}
    assert {"process_narration", "internal_locator"} <= rules
    # D19 分级：定位符=error·流程自述=warn；全部带文案摘要
    sev_by_rule = {i["rule"]: i["sev"] for i in out}
    assert sev_by_rule["internal_locator"] == "error" and sev_by_rule["process_narration"] == "warn"
    assert all(i.get("text") for i in out)


def test_client_tone_whitelist_is_extensible_constant():
    """白名单是可扩常量（frozenset）——新单客户自用缩写的收编入口存在且形态稳定。"""
    assert "KOL" in ACRONYM_WHITELIST and "GD" not in ACRONYM_WHITELIST
    assert isinstance(ACRONYM_WHITELIST, frozenset)


# ── D19 FR5.1/FR1.3 check_source 豁免机制 ─────────────────────────────
def test_check_source_brand_term_exemption():
    """「059」曾被当统计数字 error 误报（第二轮实测复现）——品牌词豁免后不报，真统计数字照拦。"""
    from reinforce.deck_rules.rules import check_source
    assert check_source("059 用一杯精酿把福建讲给你听") != []               # 未豁免·误报复现
    assert check_source("059 用一杯精酿把福建讲给你听", exempt_terms=["059"]) == []
    assert check_source("市场规模 1342 亿元", exempt_terms=["059"]) != []   # 真统计数字照拦


def test_check_source_client_provided_numbers_exempt():
    """FR1.3：客户资料数字页面不标来源（内部台账已溯源）——豁免值放行·外部数字照拦。"""
    from reinforce.deck_rules.rules import check_source
    text = "品牌健康度从 41 升至 49，市场空间广阔"
    assert check_source(text) != []                                        # 无豁免拦
    assert check_source(text, exempt_terms=["41", "49"]) == []             # 客户数字豁免
    assert check_source(text + "，行业增速 23.6%", exempt_terms=["41", "49"]) != []  # 混入外部数字仍拦


# ── D19 FR1.2 文案门分级（标签冒号 error·自然句不拦）──────────────────
def test_field_label_colon_is_error_natural_sentence_not():
    from reinforce.deck_rules.client_tone import check_client_facing_tone
    r = check_client_facing_tone("立场：阵地转移是机会窗口")
    assert any(i["rule"] == "field_label_leak" and i["sev"] == "error" for i in r)
    r2 = check_client_facing_tone("聚焦判断：这次要解决的是哪个缺口")
    assert any(i["sev"] == "error" for i in r2)
    r3 = check_client_facing_tone("反方会怎么看这个方案")
    assert any(i["sev"] == "error" for i in r3)
    # 自然句（无冒号紧随标签）不拦——白名单原则
    assert not any(i["rule"] == "field_label_leak"
                   for i in check_client_facing_tone("我们的立场是与消费者站在一起"))
    assert not any(i["rule"] == "field_label_leak"
                   for i in check_client_facing_tone("基于三个依据得出结论"))


def test_brief_locator_upgraded_to_error():
    from reinforce.deck_rules.client_tone import check_client_facing_tone
    r = check_client_facing_tone("（来源：brief P17/P21）")
    assert any(i["rule"] == "internal_locator" and i["sev"] == "error" for i in r)


# ── 2026-07-03 saopan批② 机检边界修复回归 ────────────────────────────────
def test_check_source_exempt_is_token_bounded_not_substring():
    """🔴1：豁免曾是全文子串删除(fail-open)——豁免"3"挖走"3%消费者"的3、把"35%"肢解成
    "5%"。改数字 token 边界匹配后：只豁免独立完整的数字 token。"""
    # 豁免"3"不得放行"3%"（3% 是另一个数字断言）
    assert G.check_source("3%消费者已尝新", exempt_terms=["3"]) != []
    # 豁免"20"不得放行"20%"
    assert G.check_source("增速20%", exempt_terms=["20"]) != []
    # 豁免"20%"本身应命中"20%"
    assert G.check_source("增速20%", exempt_terms=["20%"]) == []
    # "35%"不被肢解：豁免"3"后 35% 仍完整、照拦；豁免"5%"也啃不掉它的尾巴
    assert G.check_source("渗透率35%", exempt_terms=["3"]) != []
    assert G.check_source("渗透率35%", exempt_terms=["5%"]) != []
    # 千分位逗号形态整 token 豁免；豁免"200"不得命中"1,200"的尾段
    assert G.check_source("投放预算 1,200 万元", exempt_terms=["1,200"]) == []
    assert G.check_source("投放预算 1,200 万元", exempt_terms=["200"]) != []
    # 小数形态：豁免"3"不得肢解"3.5"；豁免"3.5"整 token 放行
    assert G.check_source("平均客单 3.5 万元", exempt_terms=["3"]) != []
    assert G.check_source("平均客单 3.5 万元", exempt_terms=["3.5"]) == []


def test_check_source_exempt_original_behavior_not_regressed():
    """🔴1 回归护栏：原有豁免功能（客户数字/品牌词整 token 放行）不回归。"""
    text = "品牌健康度从 41 升至 49，市场空间广阔"
    assert G.check_source(text, exempt_terms=["41", "49"]) == []
    assert G.check_source("059 用一杯精酿把福建讲给你听", exempt_terms=["059"]) == []
    # 混入未豁免的外部数字仍拦
    assert G.check_source(text + "，行业增速 23.6%", exempt_terms=["41", "49"]) != []


def test_structure_preview_requires_deck_process_word():
    """🔴2：三段式句式 × deck 工序词才 error——纯业务三步走（试点/推广/种草/收割/铺开）
    是正当分阶段打法文案，零 error。"""
    from reinforce.deck_rules.client_tone import check_client_facing_tone
    # D20 原目标句（含"诊断/方向"工序词）仍 error
    r = check_client_facing_tone("先诊断，再给方向，最后落到执行")
    assert any(i["sev"] == "error" and i["rule"] == "meta_narration" for i in r)
    # 纯业务三步走零 error
    for t in ("先试点，再推广，最后全国铺开", "先种草，再收割，然后沉淀私域"):
        assert not any(i["sev"] == "error" for i in check_client_facing_tone(t)), t


def test_doc_part_words_content_semantics_not_error():
    """🟡7：「这一部分」「这个判断」是高频内容语义（人群细分/策略判断）——摘出 error
    组合部件词筐；真元叙述（部分词+我们+讲述动词=主持人语态）用更强共现条件仍拦。"""
    from reinforce.deck_rules.client_tone import check_client_facing_tone
    assert not any(i["sev"] == "error"
                   for i in check_client_facing_tone("这一部分消费者的需求尚未被满足"))
    assert not any(i["sev"] == "error"
                   for i in check_client_facing_tone("这个判断落到渠道层面：聚焦即饮"))
    r = check_client_facing_tone("这一部分我们讲品牌资产")
    assert any(i["rule"] == "meta_narration" and i["sev"] == "error" for i in r), "真元叙述仍拦"


def test_field_label_after_cn_punctuation_caught():
    """🟡8：标签冒号形态跟在中文句读（。，、；—）后此前漏拦——前缀允许集补中文标点。"""
    from reinforce.deck_rules.client_tone import check_client_facing_tone
    r = check_client_facing_tone("结论已明。立场：坚定站位")
    assert any(i["rule"] == "field_label_leak" and i["sev"] == "error" for i in r)
    r2 = check_client_facing_tone("三点说完，依据：市场数据")
    assert any(i["rule"] == "field_label_leak" and i["sev"] == "error" for i in r2)
    # 自然句白名单不回归
    assert not any(i["rule"] == "field_label_leak"
                   for i in check_client_facing_tone("我们的立场是与消费者站在一起"))


def test_imperative_ask_needs_left_boundary():
    """🟢12：「邀请媒体到场确认排期」的"请"长在"邀请"里——句首/标点后才算祈使开头。"""
    from reinforce.deck_rules.client_tone import check_client_facing_tone
    assert not any(i["rule"] == "imperative_ask"
                   for i in check_client_facing_tone("邀请媒体到场确认排期"))
    # 真祈使（句首/逗号后/敬语前缀）照拦
    for t in ("请某品牌批准，由我们担任这一轮代理", "方案已备，请董事会批准", "恳请评审确认"):
        assert any(i["rule"] == "imperative_ask"
                   for i in check_client_facing_tone(t)), t


# ── 2026-07-03 二轮扫盘批B-7：元叙述组合判定加邻近约束 ────────────────────
def test_meta_narration_pair_requires_proximity_in_same_clause():
    """批B-7：部件词×工序词此前各自全文 search，隔半句话、语义无关也判 error——
    "这份提案的核心创意是价格要落到消费者能接受的区间"（"这份提案"是主语定语、"落到"在
    谓语深处讲价格带·间距9字符）被误判。加同子句+间距≤6 邻近约束后该句零 error；
    部件词单维 warn 保留（不静默放行·仍喂人审）。"""
    from reinforce.deck_rules.client_tone import check_client_facing_tone
    r = check_client_facing_tone("这份提案的核心创意是价格要落到消费者能接受的区间")
    assert not any(i["sev"] == "error" for i in r), r
    assert any(i["rule"] == "meta_narration" and i["sev"] == "warn" for i in r)


def test_meta_narration_adjacent_pair_still_error():
    """批B-7 护栏：真元叙述（工序词直接谓述部件词·同子句紧邻）仍 error 照拦。"""
    from reinforce.deck_rules.client_tone import check_client_facing_tone
    for t in ("这份提案先诊断，再给方向",                       # 间距0（任务指定护栏句）
              "三条线诊断完毕，下一步，需要一个能把它们连起来的创意"):  # 间距2（D20 实测原句）
        r = check_client_facing_tone(t)
        assert any(i["sev"] == "error" and i["rule"] == "meta_narration" for i in r), t


def test_meta_narration_cross_clause_pair_downgrades_to_warn():
    """批B-7：部件词与工序词分属不同子句（，。；切分）→ 不判组合 error，降回部件词单维 warn。"""
    from reinforce.deck_rules.client_tone import check_client_facing_tone
    r = check_client_facing_tone("这份提案聚焦即饮渠道，预算将落到重点城市")
    assert not any(i["sev"] == "error" for i in r), r
    assert any(i["rule"] == "meta_narration" and i["sev"] == "warn" for i in r)
