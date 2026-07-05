"""议题树 / 假设树（策略阶段2）测试。"""

from __future__ import annotations

import pytest

from reinforce.issue_tree import add_branch, new_tree, to_sub_hypotheses, validate_tree
from reinforce.storyline_state import new_storyline, set_hypothesis_tree


def _hyp_tree() -> dict:
    t = new_tree("Q3 增长健康吗·该不该管控成本", mode="假设树",
                 hypothesis="增长是虚假繁荣·需立即管控否则明年转亏")
    add_branch(t, "H1", "成本增速 > 收入增速", "成本同比50% vs 收入25%", "高")
    add_branch(t, "H2", "失控在人力", "人力占比42%→58% + 人均产出-12%", "中")
    add_branch(t, "H3", "明年由盈转亏", "净利率外推 + 敏感性", "低")
    return t


def test_valid_hypothesis_tree():
    assert validate_tree(_hyp_tree())["valid"]


def test_hypothesis_tree_needs_dayone_answer():
    t = new_tree("Q", mode="假设树")
    add_branch(t, "H1", "c", "test")
    assert not validate_tree(t)["valid"]


def test_branch_needs_falsifiable_test():
    t = _hyp_tree(); t["branches"][0].pop("test")
    assert not validate_tree(t)["valid"]


def test_issue_tree_no_dayone_needed():
    t = new_tree("成本为什么涨", mode="议题树")
    add_branch(t, "B1", "人力", "拆人力占比", "中")
    add_branch(t, "B2", "物料", "拆物料成本", "中")
    assert validate_tree(t)["valid"]


def test_too_many_branches_warns():
    t = _hyp_tree()
    for i in range(4, 8):
        add_branch(t, f"H{i}", "c", "test")
    r = validate_tree(t)
    assert r["valid"]  # warn 不拦
    assert any("3 的法则" in i["msg"] for i in r["issues"])


def test_to_sub_hypotheses_feeds_storyline():
    subs = to_sub_hypotheses(_hyp_tree())
    assert len(subs) == 3 and all(s["test"] for s in subs)
    sl = new_storyline("b", "p", "说服决策", ["董事会"], "批")
    set_hypothesis_tree(sl, "gt 含批", subs)
    assert all(s["test"] for s in sl["sub_hypotheses"])


def test_to_sub_hypotheses_refuses_invalid():
    t = _hyp_tree(); t["question"] = ""
    with pytest.raises(ValueError, match="拒降解"):
        to_sub_hypotheses(t)


# ── 2026-07-02 saopan扫盘修复回归 ─────────────────────────────────────
def test_validate_tree_none_branches_no_crash():
    """🟡：branches 显式 None——校验器如实报"无分支"不崩。"""
    from reinforce.issue_tree import validate_tree
    r = validate_tree({"mode": "议题树", "question": "q", "branches": None})
    assert not r["valid"] and any("无分支" in i["msg"] for i in r["issues"])
