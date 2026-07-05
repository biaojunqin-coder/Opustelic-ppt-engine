"""asset_ledger（④数据产物层）独立单测——素材/证据溯源台账自动汇集。"""

from __future__ import annotations

import pytest

from reinforce.asset_ledger import (
    build_asset_ledger,
    image_cost_summary,
    load_asset_ledger,
    record_image_generation,
    save_asset_ledger,
)
from reinforce.deck_state import add_page, new_outline


def _outline_with_evidence() -> dict:
    o = new_outline("收入分析", "数据报告", "复盘总结", "财务")
    add_page(o, 1, "封面/章节", "收入分析")                       # 无 evidence 的页
    add_page(o, 2, "数据论断", "收入增25%", facets={"evidence": [
        {"dim": "营收", "data": "+25%", "source": "公司财报2024",
         "source_title": "FY2024 年报", "source_outlet": "公司财报",
         "source_date": "2025-03", "source_url": "https://example.com/ar"},
        {"dim": "同行对比", "data": "行业均值+8%"},               # 无 source·应标 unsourced
    ]})
    return o


def test_build_ledger_collects_evidence_per_page():
    led = build_asset_ledger(_outline_with_evidence())
    assert led["deck_title"] == "收入分析"
    assert led["total"] == 2
    assert led["pages_without_evidence"] == [1]        # 无证据页照实列出·供人扫
    e0 = led["entries"][0]
    assert e0["page"] == 2 and e0["dim"] == "营收" and e0["sourced"] is True
    assert e0["citation"]["source_title"] == "FY2024 年报"   # 引用五件套进台账


def test_build_ledger_flags_unsourced():
    led = build_asset_ledger(_outline_with_evidence())
    assert led["unsourced_count"] == 1                 # 「行业均值」没 source·如实标出不代判
    assert led["entries"][1]["sourced"] is False


def test_ledger_empty_outline():
    o = new_outline("空deck", "数据报告", "复盘总结", "财务")
    led = build_asset_ledger(o)
    assert led["total"] == 0 and led["entries"] == [] and led["unsourced_count"] == 0


def test_ledger_save_load_roundtrip(tmp_path):
    led = build_asset_ledger(_outline_with_evidence())
    save_asset_ledger(led, tmp_path / "asset_ledger.json")
    assert load_asset_ledger(tmp_path / "asset_ledger.json") == led


# ── D16 修复批（2026-07-02）──────────────────────────────────────────
def test_ledger_collects_image_hrefs():
    """D16 🟢②：svgs 传入时抽 <image href>（SVG2 裸 href + SVG1.1 xlink:href 都认）。"""
    o = _outline_with_evidence()
    svgs = {1: '<svg><image href="a.png"/><image xlink:href="b.jpg"/></svg>'}
    led = build_asset_ledger(o, svgs=svgs)
    assert [(i["page"], i["href"]) for i in led["images"]] == [(1, "a.png"), (1, "b.jpg")]
    assert all(i["license_note"] == "" for i in led["images"])  # 版权判断留给人·台账只保证不漏


def test_ledger_truncates_data_uri():
    """data URI 只记媒体类型不存 base64 全文（台账要可读）。"""
    o = _outline_with_evidence()
    svgs = {1: '<svg><image href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUg=="/></svg>'}
    led = build_asset_ledger(o, svgs=svgs)
    assert led["images"][0]["href"] == "data:image/png;base64,<内嵌 base64·原文见 SVG>"


def test_ledger_schema_version():
    assert build_asset_ledger(_outline_with_evidence())["schema_version"] == 1  # D16 🟢③


# ── 图像正则补漏（2026-07-02 saopan扫盘揪出：只认双引号 href·单引号整条漏抽；
#    data-href 自定义属性被误抽进台账）──
def test_ledger_single_quoted_href_collected():
    o = _outline_with_evidence()
    svgs = {1: "<svg><image href='logo.png'/><image xlink:href='pic.jpg'/></svg>"}
    led = build_asset_ledger(o, svgs=svgs)
    assert [(i["page"], i["href"]) for i in led["images"]] == [(1, "logo.png"), (1, "pic.jpg")]


def test_ledger_data_href_not_collected():
    o = _outline_with_evidence()
    svgs = {1: '<svg><image data-href="x.png" href="real.png"/></svg>'}
    led = build_asset_ledger(o, svgs=svgs)
    assert [i["href"] for i in led["images"]] == ["real.png"]  # data-href 不是图像引用·不进台账


def test_ledger_double_quoted_href_not_regressed():
    o = _outline_with_evidence()
    svgs = {1: '<svg><image href="a.png"/></svg>'}
    led = build_asset_ledger(o, svgs=svgs)
    assert [i["href"] for i in led["images"]] == ["a.png"]


# ── D18 FR4.4 AI 生成台账（2026-07-02）─────────────────────────────────────
def _gen_kwargs(**over):
    base = dict(filename="hero.png", prompt="beer glass, flat design, NO text",
                model="gemini-3-pro-image-preview", iterations=2,
                ref_images=["brand_manual_p3.png"], cost_estimate=0.134,
                timestamp="2026-07-02T10:00:00+08:00")
    base.update(over)
    return base


def test_record_image_generation_appends_evidence_chain():
    """维权证据链五要素（prompt/模型/迭代/参考图/时间）齐进 images 段·kind 标 generation。"""
    led = build_asset_ledger(_outline_with_evidence())
    entry = record_image_generation(led, **_gen_kwargs())
    assert led["images"][-1] is entry
    assert entry["kind"] == "generation" and entry["filename"] == "hero.png"
    assert entry["prompt"].endswith("NO text") and entry["iterations"] == 2
    assert entry["ref_images"] == ["brand_manual_p3.png"]
    assert entry["timestamp"] == "2026-07-02T10:00:00+08:00"   # 时间由调用方传·引擎不碰时钟


def test_record_generation_coexists_with_svg_refs():
    """生成行与 SVG 引用行共存互不干扰——引用行无 kind 字段（旧 schema 原样保留）。"""
    led = build_asset_ledger(_outline_with_evidence(),
                             svgs={1: '<svg><image href="hero.png"/></svg>'})
    record_image_generation(led, **_gen_kwargs())
    refs = [i for i in led["images"] if "kind" not in i]
    gens = [i for i in led["images"] if i.get("kind") == "generation"]
    assert len(refs) == 1 and refs[0]["href"] == "hero.png"
    assert len(gens) == 1


@pytest.mark.parametrize("missing", ["filename", "prompt", "model", "timestamp"])
def test_record_generation_missing_required_raises(missing):
    """证据链四必填缺一即拒（fail-closed——缺 prompt/时间的记录没有举证价值）。"""
    led = build_asset_ledger(_outline_with_evidence())
    with pytest.raises(ValueError, match=missing):
        record_image_generation(led, **_gen_kwargs(**{missing: ""}))


def test_image_cost_summary_totals_and_unknown():
    """§六成本可见：已知成本求和、未知成本如实计数（不猜不编·总额是下界）。"""
    led = build_asset_ledger(_outline_with_evidence())
    record_image_generation(led, **_gen_kwargs(cost_estimate=0.10))
    record_image_generation(led, **_gen_kwargs(filename="bg.png", cost_estimate=0.24))
    record_image_generation(led, **_gen_kwargs(filename="cn.png", cost_estimate=None,
                                               model="doubao-seedream-4-5-251128"))
    s = image_cost_summary(led)
    assert s["generation_count"] == 3
    assert s["total_cost_estimate"] == 0.34
    assert s["unknown_cost_count"] == 1
    assert s["by_model"]["gemini-3-pro-image-preview"] == {
        "count": 2, "cost": 0.34, "unknown_cost_count": 0}
    assert s["by_model"]["doubao-seedream-4-5-251128"]["unknown_cost_count"] == 1


def test_image_cost_summary_ignores_svg_ref_rows():
    """SVG 引用行没有成本概念——汇总只认 kind=generation。"""
    led = build_asset_ledger(_outline_with_evidence(),
                             svgs={1: '<svg><image href="a.png"/></svg>'})
    s = image_cost_summary(led)
    assert s["generation_count"] == 0 and s["total_cost_estimate"] == 0.0


def test_generation_rows_survive_save_load_roundtrip(tmp_path):
    led = build_asset_ledger(_outline_with_evidence())
    record_image_generation(led, **_gen_kwargs())
    save_asset_ledger(led, tmp_path / "asset_ledger.json")
    back = load_asset_ledger(tmp_path / "asset_ledger.json")
    assert back == led and image_cost_summary(back)["generation_count"] == 1


# ---------- D26 二轮扫盘🔴：重建台账不许清零 AI 生图维权证据 ----------

def test_merge_generation_records_survives_rebuild():
    from reinforce.asset_ledger import (build_asset_ledger, merge_generation_records,
                                        record_image_generation)
    old = build_asset_ledger({"pages": []})
    record_image_generation(old, filename="kv.png", prompt="春节餐桌暖光", model="m1",
                            timestamp="2026-07-03T10:00:00")
    rebuilt = build_asset_ledger({"pages": []})          # pipeline 收尾的重建形态
    merge_generation_records(rebuilt, old)
    gens = [r for r in rebuilt["images"] if r.get("kind") == "generation"]
    assert len(gens) == 1 and gens[0]["prompt"] == "春节餐桌暖光"
    merge_generation_records(rebuilt, old)               # 再合并一次不重复
    assert len([r for r in rebuilt["images"] if r.get("kind") == "generation"]) == 1
    assert merge_generation_records(rebuilt, None) is rebuilt   # 无旧台账零破坏
