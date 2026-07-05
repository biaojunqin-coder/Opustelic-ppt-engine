"""策略五阶段 prompt 模板（待办②）+ brief_parse MinerU 接口（待办③）测试。"""

from __future__ import annotations

from engine.brief_parse import parse_brief
from reinforce.strategy_prompts import (prompt_divergence, prompt_stage1_purpose, prompt_stage2_page_scope,
                                        prompt_stage2_tree, prompt_stage3_research, prompt_stage4_storyline,
                                        prompt_stage5_review)


def test_stage1_prompt_has_alignment():
    p = prompt_stage1_purpose("某 brief 内容")
    assert "对齐" in p and "visual_style" in p and "mode" in p and "一次只问一个" in p


def test_stage2_prompt_has_tree():
    assert "议题树" in prompt_stage2_tree("赢pitch") and "可证伪" in prompt_stage2_tree("x")


def test_stage2_prompt_no_domain_skips_frameworks():
    p = prompt_stage2_tree("赢pitch")
    assert "分析框架库" not in p


def test_stage2_prompt_injects_real_frameworks_by_domain():
    p = prompt_stage2_tree("赢pitch", domain=["精酿啤酒行业"])
    assert "分析框架库" in p and "何时用" in p


def test_stage2_page_scope_computes_content_aware_minimum():
    branches = [{"id": "H1", "claim": "成本增速>收入增速"}, {"id": "H2", "claim": "失控在人力"}]
    p = prompt_stage2_page_scope("增长是虚假繁荣", branches)
    assert "最少 4 页" in p  # n=2 分支 → 1执行摘要+2分支+1决策 = 4
    assert "成本增速>收入增速" in p and "失控在人力" in p  # 逐条列分支不是抽象数字
    assert "expected_pages" in p


def test_stage2_page_scope_no_scene_skips_sample():
    p = prompt_stage2_page_scope("gt", [{"id": "H1", "claim": "c"}])
    assert "参考样本" not in p


def test_stage2_page_scope_injects_real_sample_by_scene():
    p = prompt_stage2_page_scope("gt", [{"id": "H1", "claim": "c"}], scene="投资融资")
    assert "Airbnb" in p and "样本量单薄" in p  # 诚实标注样本量


def test_stage3_prompt_no_domain_skips_facts():
    p = prompt_stage3_research("市场在增长")
    assert "行业知识库" not in p


def test_stage4_prompt_has_modes():
    p = prompt_stage4_storyline({"visual_style": "演讲版", "mode": "narrative"})
    assert "narrative" in p and "pyramid" in p


def test_stage5_prompt_has_review():
    assert "三道审查" in prompt_stage5_review({}) and "Critic" in prompt_stage5_review({})


def test_brief_parse_mineru_fallback(tmp_path):
    # prefer_mineru 但未装 MinerU → fallback 不崩（txt 走文本分支）
    f = tmp_path / "b.txt"; f.write_text("x", encoding="utf-8")
    assert parse_brief(f, prefer_mineru=True)["format"] == "text"


# ── D18 FR1.3 发散环节引导 prompt ─────────────────────────────────────────
def test_prompt_divergence_schema_findings_and_hard_stop():
    p = prompt_divergence("策略方向", ["市场规模500亿", "Z世代渗透率升至41%"])
    assert "3 张" in p and "方向卡" in p and "策略方向" in p          # 默认 N=3·点名节点
    assert "市场规模500亿" in p and "Z世代渗透率升至41%" in p          # 注入已有 key_findings
    assert "不重新调研" in p                                          # 发散只重组已有洞察
    for field in ("name", "core_logic", "supporting_findings", "play_summary",
                  "why_win", "risks", "fit"):
        assert field in p                                             # schema 七字段讲全
    assert "为什么可能赢" in p and "主要风险" in p                     # 每张卡必带权衡
    assert "硬停" in p and "record_divergence" in p                   # 发散点=硬停点·留痕指引


def test_prompt_divergence_three_tier_presentation():
    p = prompt_divergence("创意概念", ["洞察A"])
    for tier in ("safe", "shifted", "bold"):
        assert tier in p  # 三档拉开呈现（与 FR7.1 风格光谱同构）


def test_prompt_divergence_custom_count_and_str_digest():
    p = prompt_divergence("媒介组合", "全部发现的一段话摘要", n_cards=4)
    assert "4 张" in p and "全部发现的一段话摘要" in p and "媒介组合" in p


# ── D19 FR4.1 方向卡执行难度四维实评 + 梯度硬要求 ────────────────────────
def test_prompt_divergence_demands_four_dim_difficulty_in_fit():
    p = prompt_divergence("策略方向", ["洞察A"])
    for dim in ("团队能力", "预算", "周期", "供应链依赖"):
        assert dim in p, f"执行难度四维缺「{dim}」（D19 FR4.1）"
    assert "fit" in p and "执行难度" in p          # fit 字段承载难度评估结果
    assert "中等" in p                              # 点名"中等"类敷衍词不算实评


def test_prompt_divergence_demands_difficulty_gradient():
    p = prompt_divergence("策略方向", ["洞察A"])
    assert "拉开梯度" in p
    assert "高难炫技" in p                          # 明令不许全部高难
    assert "执行难度太高" in p                      # 引上一单实测教训（两张被判太高被迫三选一）


# ── D19 FR4.2 历史偏好原话注入 ───────────────────────────────────────────
def test_prompt_divergence_without_history_has_no_history_section():
    p = prompt_divergence("策略方向", ["洞察A"])
    assert "过往收敛拍板" not in p
    # 显式空列表/None 同样不出该节（不给生成器一个空标题误导）
    assert "过往收敛拍板" not in prompt_divergence("策略方向", ["洞察A"], history=[])


def test_prompt_divergence_injects_history_verbatim():
    history = [{"deck_id": "059_imc", "node": "策略方向", "chosen": "跟着好奇心去福建",
                "reason": "另外两个方向执行难度太高，用户按落地可行性拍板选②"}]
    p = prompt_divergence("策略方向", ["洞察A"], history=history)
    assert "过往收敛拍板" in p and "原话" in p
    assert "『另外两个方向执行难度太高，用户按落地可行性拍板选②』" in p   # 原话逐字注入
    assert "059_imc" in p and "策略方向" in p                              # 带 deck_id·node 出处
    assert "不是让你只出保守方向" in p                                     # 前置偏好≠只出保守


def test_prompt_divergence_history_skips_entries_without_reason():
    history = [{"deck_id": "x", "node": "n", "chosen": "c", "reason": ""}]
    p = prompt_divergence("策略方向", ["洞察A"], history=history)
    assert "过往收敛拍板" not in p   # 全部条目无 reason → 该节整个不出


