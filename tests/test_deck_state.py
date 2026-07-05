"""deck_state（⑦State）独立单测——schema 校验 fail-closed。"""

from __future__ import annotations

import json
import pathlib

import pytest

from reinforce import deck_state as S


def test_new_and_add_page():
    o = S.new_outline("t", "提案", "说服决策", "营销品牌")
    S.add_page(o, 1, "封面", "标题")
    assert o["pages"][0]["n"] == 1 and o["domain"] == ["营销品牌"]
    assert o["intent"] == ["说服决策"]  # 标量自动包成 list


def test_validate_ok():
    o = S.new_outline("t", "提案", ["说服决策"], ["营销品牌"])
    S.add_page(o, 1, "封面", "标题")
    S.add_page(o, 2, "洞察", "X", depends_on=[1])
    assert S.validate_outline(o)["valid"]


def test_missing_deck_field_is_error():
    assert not S.validate_outline({"title": "t"})["valid"]


def test_duplicate_page_number_error():
    o = S.new_outline("t", "提案", ["i"], ["d"])
    S.add_page(o, 1, "a", "x")
    S.add_page(o, 1, "b", "y")
    assert not S.validate_outline(o)["valid"]


def test_bad_dependency_error():
    o = S.new_outline("t", "提案", ["i"], ["d"])
    S.add_page(o, 1, "a", "x", depends_on=[9])
    assert not S.validate_outline(o)["valid"]


def test_save_refuses_invalid(tmp_path):
    o = {"title": "t"}  # 缺字段
    with pytest.raises(ValueError):
        S.save_outline(o, tmp_path / "x.json")


def test_save_load_roundtrip(tmp_path):
    o = S.new_outline("t", "提案", ["说服决策"], ["营销品牌"])
    S.add_page(o, 1, "封面", "标题")
    S.save_outline(o, tmp_path / "x.json")
    assert S.load_outline(tmp_path / "x.json")["title"] == "t"


def test_status_transition_forward_ok():
    assert S.check_status_transition("planned", "drafted") == []
    assert S.check_status_transition("drafted", "gated") == []
    assert S.check_status_transition("gated", "done") == []


def test_status_transition_same_state_idempotent():
    assert S.check_status_transition("drafted", "drafted") == []  # 断点重放·合法幂等


def test_status_transition_rework_downgrade_ok():
    # 2026-07-02 saopan修复：resume 硬门重跑失败是机器路径，必须有降级返工通道——
    # gated/done→drafted 改为合法（此前无降级边，门败页停在 gated 被收尾无条件升 done·假绿）。
    assert S.check_status_transition("gated", "drafted") == []
    assert S.check_status_transition("done", "drafted") == []


@pytest.mark.parametrize("old,new", [
    ("planned", "gated"), ("planned", "done"), ("drafted", "done"),  # 跳级
    ("done", "gated"), ("drafted", "planned"),  # 回退（gated/done→drafted 已成合法返工边·见上）
])
def test_status_transition_skip_or_backward_error(old, new):
    issues = S.check_status_transition(old, new)
    assert issues and issues[0]["sev"] == "error"


def test_status_transition_unknown_state_error():
    assert S.check_status_transition("planned", "shipped")[0]["sev"] == "error"
    assert S.check_status_transition("摸鱼中", "drafted")[0]["sev"] == "error"


def test_set_page_status_flows_and_rejects():
    o = S.new_outline("t", "提案", ["i"], ["d"])
    S.add_page(o, 1, "封面", "标题")
    S.set_page_status(o, 1, "drafted")
    assert o["pages"][0]["status"] == "drafted"
    with pytest.raises(ValueError, match="非法"):
        S.set_page_status(o, 1, "done")               # drafted 直接跳 done·拒
    with pytest.raises(ValueError, match="不存在"):
        S.set_page_status(o, 9, "drafted")            # 页不存在·拒


# ── D16 修复批（2026-07-02）──────────────────────────────────────────
def test_input_fingerprint_stable_and_sensitive():
    """D16 🟡②：输入指纹（Bazel action key 思路）——同输入同指纹；claim/facets/spec_lock
    任一变则指纹变；status / 指纹自身不参与（生命周期不是输入）。"""
    o = S.new_outline("t", "提案", ["i"], ["d"])
    S.add_page(o, 1, "数据论断", "收入增25%", facets={"chart": "waterfall"})
    p = o["pages"][0]
    fp = S.page_input_fingerprint(p, spec_lock={"palette": {"bg": "#FFF"}})
    assert fp == S.page_input_fingerprint(p, spec_lock={"palette": {"bg": "#FFF"}})  # 稳定
    p["status"] = "gated"
    p["input_fingerprint"] = fp
    assert S.page_input_fingerprint(p, {"palette": {"bg": "#FFF"}}) == fp  # status/指纹自身不敏感
    p2 = dict(p, claim="收入增30%")
    assert S.page_input_fingerprint(p2, {"palette": {"bg": "#FFF"}}) != fp  # claim 变→指纹变
    assert S.page_input_fingerprint(p, {"palette": {"bg": "#000"}}) != fp   # spec_lock 变→指纹变


def test_new_outline_has_schema_version():
    assert S.new_outline("t", "提案", ["i"], ["d"])["schema_version"] == 1  # D16 🟢③


# ── 2026-07-02 saopan扫盘修复回归 ─────────────────────────────────────
def test_save_outline_atomic_no_tmp_left(tmp_path):
    """🟡：outline.json 曾裸 write_text——断点续做唯一入口可被中断打成半截。改 tmp+rename。"""
    o = S.new_outline("t", "提案", ["i"], ["d"])
    S.add_page(o, 1, "封面", "标题")
    p = tmp_path / "outline.json"
    S.save_outline(o, p)
    assert p.is_file() and S.load_outline(p)["title"] == "t"
    assert not list(tmp_path.glob("*.tmp"))             # 原子写不残留


def test_load_outline_newer_schema_rejected(tmp_path):
    import json
    p = tmp_path / "o.json"
    p.write_text(json.dumps({"schema_version": 99, "title": "t", "pages": []}), encoding="utf-8")
    with pytest.raises(ValueError, match="schema_version=99"):
        S.load_outline(p)


def test_validate_outline_none_shapes_no_crash():
    """🟡：pages/depends_on 显式 None——校验器如实工作不崩。"""
    r = S.validate_outline({"title": "t", "doc_type": "d", "intent": ["i"], "domain": ["x"],
                            "pages": None})
    assert r["valid"]                                   # 空 deck 结构上合法·没崩即胜
    r2 = S.validate_outline({"title": "t", "doc_type": "d", "intent": ["i"], "domain": ["x"],
                             "pages": [{"n": 1, "page_function": "f", "claim": "c",
                                        "depends_on": None}]})
    assert r2["valid"]
