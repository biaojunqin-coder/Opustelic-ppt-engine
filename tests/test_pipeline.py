"""端到端编排 pipeline.build_deck 冒烟测试——串通 State→Prompt→硬门→vendor 导出。

用手写 svg_provider 当 LLM，验证：大纲非法拒做、合规页全过且产原生 pptx、SVG 导出不兼容页被硬门逮住。
"""

from __future__ import annotations

import zipfile

import pytest

from engine.pipeline import build_deck, _extract_text
from reinforce.deck_state import add_page, new_outline
from reinforce.spec_lock import new_spec_lock


def _clean_svg(ctx: dict) -> str:
    """合规 svg_provider：把本页论断渲成一行文字（数字带 source）。"""
    claim = ctx["page"]["claim"]
    return (
        '<svg viewBox="0 0 1280 720" xmlns="http://www.w3.org/2000/svg">'
        '<rect x="80" y="80" width="1120" height="80" rx="12" fill="#051C2C"/>'
        f'<text x="100" y="135" font-family="Arial" font-size="28" fill="#fff">{claim}</text>'
        '<text x="100" y="300" font-family="Arial" font-size="16" fill="#333">'
        '数据来源：公司财报 2024</text></svg>'
    )


def _incompatible_svg(ctx: dict) -> str:
    """带 SVG 导出不兼容标签的 svg_provider（应被 check_svg_compat 硬门逮住）。"""
    return ('<svg viewBox="0 0 1280 720" xmlns="http://www.w3.org/2000/svg">'
            '<style>.a{fill:red}</style>'
            '<text x="100" y="135" font-size="28">收入增长</text></svg>')


def _outline_2p() -> dict:
    o = new_outline("收入增但成本翻倍", "数据报告", "复盘总结", "财务")
    add_page(o, 1, "waterfall", "收入增25%但成本翻倍致净利下滑")
    add_page(o, 2, "donut", "成本结构中人力占比升至58%", depends_on=[1])
    return o


def test_build_deck_happy_path(tmp_path):
    res = build_deck(_outline_2p(), _clean_svg, tmp_path)
    assert res["all_passed"] is True
    assert len(res["pages"]) == 2
    # 产出原生可编辑 pptx（解包验证·绕 python-pptx 3.14 bug）
    with zipfile.ZipFile(res["pptx_path"]) as z:
        names = z.namelist()
        assert "ppt/slides/slide1.xml" in names and "ppt/slides/slide2.xml" in names
        xml1 = z.read("ppt/slides/slide1.xml").decode("utf-8")
    assert "收入增25%但成本翻倍致净利下滑" in xml1   # 论断作为原生文字进了 pptx
    assert "<p:pic>" not in xml1                       # 非图片栅格化


def test_build_deck_strict_blocks_incompatible_svg(tmp_path):
    with pytest.raises(ValueError, match="硬门未过"):
        build_deck(_outline_2p(), _incompatible_svg, tmp_path, strict=True)


def test_build_deck_nonstrict_flags_incompatible_svg(tmp_path):
    res = build_deck(_outline_2p(), _incompatible_svg, tmp_path)
    assert res["all_passed"] is False                 # 标记不过但仍产草稿供人审


def test_build_deck_rejects_invalid_outline(tmp_path):
    bad = new_outline("x", "", "复盘总结", "财务")     # 缺 doc_type
    with pytest.raises(ValueError, match="大纲非法"):
        build_deck(bad, _clean_svg, tmp_path)


def test_extract_text_handles_tspan():
    svg = '<svg><text x="1"><tspan>收入</tspan><tspan>增长</tspan></text></svg>'
    assert "收入" in _extract_text(svg) and "增长" in _extract_text(svg)


# ── spec_lock 集成（ppt-master 纪律：逐页生成前重读 spec_lock·禁现场现编颜色）──
def test_build_deck_spec_lock_reaches_prompt(tmp_path):
    seen = {}

    def _spy_svg(ctx: dict) -> str:
        seen["spec_lock"] = ctx.get("spec_lock")
        seen["prompt_has_brief"] = "spec_lock" in ctx["prompt"]
        return _clean_svg(ctx)

    spec = new_spec_lock({"bg": "#FFFFFF", "ink": "#051C2C"}, "Arial")
    build_deck(_outline_2p(), _spy_svg, tmp_path, spec_lock=spec)
    assert seen["spec_lock"] == spec and seen["prompt_has_brief"]  # 强制"重读"：ctx 里有+prompt 文本里有


def test_build_deck_spec_lock_catches_rogue_color(tmp_path):
    def _rogue_svg(ctx: dict) -> str:
        return ('<svg viewBox="0 0 1280 720" xmlns="http://www.w3.org/2000/svg">'
                f'<rect fill="#00FF00"/><text font-size="28">{ctx["page"]["claim"]}</text>'
                '<text font-size="16">数据来源：测试</text></svg>')

    spec = new_spec_lock({"bg": "#FFFFFF", "ink": "#051C2C"}, "Arial")  # 不含 #00FF00
    res = build_deck(_outline_2p(), _rogue_svg, tmp_path, spec_lock=spec)
    assert any(i["rule"] == "off_spec_color" for i in res["pages"][0]["gate"]["issues"])


# ── SVG 导出兼容性机检（shared-standards.md·真实风险项补课）──
def test_build_deck_catches_incompat_svg(tmp_path):
    def _incompat_svg(ctx: dict) -> str:
        return (f'<svg viewBox="0 0 1280 720" xmlns="http://www.w3.org/2000/svg">'
                f'<rect fill="rgba(0,0,0,0.5)"/><text font-size="28">{ctx["page"]["claim"]}</text>'
                f'<text font-size="16">数据来源：测试</text></svg>')

    res = build_deck(_outline_2p(), _incompat_svg, tmp_path)
    issues = res["pages"][0]["gate"]["issues"]
    assert any(i["rule"] == "svg_incompat_syntax" for i in issues)
    assert res["pages"][0]["gate"]["passed"] is False  # rgba 是 error 级·拦下来


def test_build_deck_strict_blocks_incompat_svg(tmp_path):
    def _bad_svg(ctx: dict) -> str:
        return '<svg><style>.a{}</style></svg>'

    with pytest.raises(ValueError, match="硬门未过"):
        build_deck(_outline_2p(), _bad_svg, tmp_path, strict=True)


# ── 预览渲染（D7路线A拍板·render_previews 可选开关）──
def test_build_deck_default_no_preview(tmp_path):
    # 缺省 False：不装 playwright 也不该受影响，preview_path 留 None
    res = build_deck(_outline_2p(), _clean_svg, tmp_path)
    assert all(pr["preview_path"] is None for pr in res["pages"])


# 2026-07-02 saopan扫盘：旧测试锁的"优雅降级"是错误行为——制作 SKILL 承诺"未装会抛清楚的
# ImportError，不会静默跳过让你误以为自检发生过"，显式要求的自检关无声蒸发是假绿。
# 新行为（raise）的测试见文末 test_render_previews_raises_when_playwright_missing。


# ── check_page_budget/spec_lock强制接线（2026-07-01 yanjiu研究驱动评估揪出零接线·补线）──
def test_build_deck_page_budget_fires_via_facets_chart(tmp_path):
    o = new_outline("成本分析", "数据报告", "复盘总结", "财务")
    add_page(o, 1, "数据论断", "成本结构里七项费用都在增长", facets={
        "chart": "donut",  # PAGE_BUDGET["donut"] = 6
        "evidence": [{"dim": f"费用{i}", "data": f"{i}%"} for i in range(7)],  # 7 > 6·超限
    })
    res = build_deck(o, _clean_svg, tmp_path)
    issues = res["pages"][0]["gate"]["issues"]
    assert any(i["rule"] == "over_budget" and i["sev"] == "error" for i in issues)
    assert res["all_passed"] is False


def test_build_deck_page_budget_within_cap_silent(tmp_path):
    o = new_outline("成本分析", "数据报告", "复盘总结", "财务")
    add_page(o, 1, "数据论断", "成本结构人力占比最高", facets={
        "chart": "donut", "evidence": [{"dim": f"费用{i}", "data": f"{i}%"} for i in range(4)],
    })
    res = build_deck(o, _clean_svg, tmp_path)
    assert not any(i["rule"] == "over_budget" for i in res["pages"][0]["gate"]["issues"])


def test_build_deck_missing_spec_lock_warns_not_silent(tmp_path):
    res = build_deck(_outline_2p(), _clean_svg, tmp_path)  # 不传 spec_lock
    issues = res["pages"][0]["gate"]["issues"]
    assert any(i["rule"] == "spec_lock_missing" and i["sev"] == "warn" for i in issues)
    assert res["all_passed"] is True  # warn 不拦：向后兼容旧调用/fixture 场景


def test_build_deck_incomplete_spec_lock_rejected(tmp_path):
    spec = new_spec_lock({"bg": "#FFFFFF"}, "")  # 缺 font_family(空字符串·falsy)
    with pytest.raises(ValueError, match="spec_lock 不完整"):
        build_deck(_outline_2p(), _clean_svg, tmp_path, spec_lock=spec)


# ── 批④孤岛接线（FR7.5·第5次孤岛复发）：spec_lock 声明 icons 即验图标真实在磁盘 ──
def _spec_with_icons(icons: dict) -> dict:
    return new_spec_lock({"bg": "#FFFFFF", "ink": "#051C2C"}, "Arial", icons=icons)


def test_build_deck_icons_nonexistent_library_rejected(tmp_path):
    """锁定不存在的库 → 拒做（validate_spec_lock 只查字段形态，磁盘存在性靠本接线兜）。"""
    spec = _spec_with_icons({"library": "绝不存在的库", "inventory": ["abacus"]})
    with pytest.raises(ValueError, match="icons 清单校验失败.*缺名强制重选"):
        build_deck(_outline_2p(), _clean_svg, tmp_path, spec_lock=spec)


def test_build_deck_icons_missing_name_rejected(tmp_path):
    """库存在但清单里有缺名图标 → 拒做，报文点名 missing（缺名强制重选，不许空 <use> 占位滑过）。"""
    spec = _spec_with_icons({"library": "tabler-outline",
                             "inventory": ["abacus", "绝不存在的图标xyz"]})
    with pytest.raises(ValueError, match="绝不存在的图标xyz"):
        build_deck(_outline_2p(), _clean_svg, tmp_path, spec_lock=spec)


def test_build_deck_icons_real_inventory_passes(tmp_path):
    """真实库+真实存在的图标名 → 正常通过（接线不误伤合法声明）。"""
    spec = _spec_with_icons({"library": "tabler-outline", "inventory": ["abacus", "a-b"]})
    res = build_deck(_outline_2p(), _clean_svg, tmp_path, spec_lock=spec)
    assert res["all_passed"] is True


def test_build_deck_render_previews_produces_png(tmp_path):
    from engine.render_preview import preview_available
    if not preview_available():
        pytest.skip("playwright/chromium 未装·真实预览渲染验证跳过")
    from pathlib import Path
    res = build_deck(_outline_2p(), _clean_svg, tmp_path, render_previews=True)
    for pr in res["pages"]:
        assert pr["preview_path"] and Path(pr["preview_path"]).exists()


# ── ④数据产物层接线（2026-07-02·workspace/只读锁/状态流转/断点续做/溯源台账）──
def _ws(tmp_path) -> dict:
    from reinforce.deck_workspace import new_workspace
    return new_workspace("测试deck", root=tmp_path / "decks")


def test_build_deck_workspace_missing_warns_not_silent(tmp_path):
    res = build_deck(_outline_2p(), _clean_svg, tmp_path)  # 不传 workspace
    assert any(w["rule"] == "workspace_missing" and w["sev"] == "warn"
               for w in res["deck_warnings"])          # deck 级警示一条·不再静默


def test_build_deck_blocks_published_deck(tmp_path):
    """铁律4真接线：已交付 deck 拒重做（此前 assert_editable 全仓零生产调用点）。"""
    from reinforce.deck_memory import mark_published
    ws = _ws(tmp_path)
    mark_published("测试deck", ws["published_ledger"])
    with pytest.raises(PermissionError, match="只读真相源"):
        build_deck(_outline_2p(), _clean_svg, ws["pages"], workspace=ws)


def test_build_deck_status_lifecycle_and_persists(tmp_path):
    """页状态真实流转（planned→drafted→gated→done）+ 逐页落盘 outline.json。"""
    from reinforce.deck_state import load_outline
    ws = _ws(tmp_path)
    o = _outline_2p()
    res = build_deck(o, _clean_svg, ws["pages"], workspace=ws)
    assert res["all_passed"]
    assert all(p["status"] == "done" for p in o["pages"])       # 过门+导出 → done
    saved = load_outline(ws["outline"])                          # 状态已落盘·活文件
    assert all(p["status"] == "done" for p in saved["pages"])


def test_build_deck_failed_gate_page_stays_drafted(tmp_path):
    """硬门没过的页停在 drafted（如实不升 gated/done·供人审返工）。"""
    ws = _ws(tmp_path)
    o = _outline_2p()
    res = build_deck(o, _incompatible_svg, ws["pages"], workspace=ws)
    assert res["all_passed"] is False
    assert all(p["status"] == "drafted" for p in o["pages"])


def test_build_deck_writes_asset_ledger(tmp_path):
    """收尾自动汇集素材/证据溯源台账（声明式·不用人另填）。"""
    from reinforce.asset_ledger import load_asset_ledger
    ws = _ws(tmp_path)
    o = new_outline("收入分析", "数据报告", "复盘总结", "财务")
    add_page(o, 1, "数据论断", "收入增25%", facets={"evidence": [
        {"dim": "营收", "data": "+25%", "source": "公司财报2024"}]})
    build_deck(o, _clean_svg, ws["pages"], workspace=ws)
    led = load_asset_ledger(ws["asset_ledger"])
    assert led["total"] == 1 and led["entries"][0]["source"] == "公司财报2024"
    assert led["unsourced_count"] == 0


def test_build_deck_resume_skips_provider_reruns_gate(tmp_path):
    """断点续做：gated/done 页跳过 svg_provider（贵的那步），硬门照样重跑（防假绿）。"""
    ws = _ws(tmp_path)
    o = _outline_2p()
    build_deck(o, _clean_svg, ws["pages"], workspace=ws)         # 第一遍全做完 → 全 done
    calls = []

    def _spy_svg(ctx: dict) -> str:
        calls.append(ctx["page"]["n"])
        return _clean_svg(ctx)

    res2 = build_deck(o, _spy_svg, ws["pages"], workspace=ws, resume=True)
    assert calls == []                                           # 没有一页重新生成
    assert all(pr["resumed"] for pr in res2["pages"])
    assert res2["all_passed"]                                    # 硬门重跑仍全过


def test_build_deck_gated_page_refuses_silent_redo(tmp_path):
    """已过门的页不许被悄悄重写：非 resume 场景直接拒（同只读锁一个精神）。"""
    ws = _ws(tmp_path)
    o = _outline_2p()
    build_deck(o, _clean_svg, ws["pages"], workspace=ws)
    with pytest.raises(ValueError, match="拒绝静默重做"):
        build_deck(o, _clean_svg, ws["pages"], workspace=ws)     # resume=False 重跑·拦


# ── D16 修复批（2026-07-02）──────────────────────────────────────────
def test_build_deck_resume_rejects_stale_input(tmp_path):
    """D16 🟡②：claim 改了之后 resume 拒复用过期 SVG（Bazel 输入摘要思路）——
    此前只查 status+文件存在，输入漂移的过期产物照样复用且硬门逮不住。"""
    ws = _ws(tmp_path)
    o = _outline_2p()
    build_deck(o, _clean_svg, ws["pages"], workspace=ws)          # 全 done + 记指纹
    o["pages"][0]["claim"] = "收入增40%但成本翻三倍"               # 事后改输入
    with pytest.raises(ValueError, match="拒复用过期产物"):
        build_deck(o, _clean_svg, ws["pages"], workspace=ws, resume=True)


def test_build_deck_resume_without_fingerprint_warns(tmp_path):
    """无指纹旧页（机制上线前产物）：resume 不拦但 deck_warnings 如实标'无法验证是否过期'。"""
    ws = _ws(tmp_path)
    o = _outline_2p()
    build_deck(o, _clean_svg, ws["pages"], workspace=ws)
    for p in o["pages"]:
        p.pop("input_fingerprint", None)                          # 模拟旧产物
    res = build_deck(o, _clean_svg, ws["pages"], workspace=ws, resume=True)
    assert all(pr["resumed"] for pr in res["pages"])
    assert sum(1 for w in res["deck_warnings"] if w["rule"] == "fingerprint_missing") == 2


def test_build_deck_asset_ledger_collects_images(tmp_path):
    """D16 🟢②：台账收 SVG <image href> 图像素材（版权来源合规面·license_note 留空供人补）。"""
    from reinforce.asset_ledger import load_asset_ledger

    def _svg_with_image(ctx: dict) -> str:
        return ('<svg viewBox="0 0 1280 720" xmlns="http://www.w3.org/2000/svg">'
                '<image href="assets/logo.png" x="0" y="0" width="100" height="40"/>'
                f'<text font-size="28">{ctx["page"]["claim"]}</text>'
                '<text font-size="16">数据来源：测试</text></svg>')

    ws = _ws(tmp_path)
    (ws["pages"] / "assets").mkdir(parents=True)       # vendor 导出要能真找到这张图
    import base64
    (ws["pages"] / "assets" / "logo.png").write_bytes(base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="))
    o = new_outline("图页", "数据报告", "复盘总结", "财务")
    add_page(o, 1, "封面/章节", "带logo的封面")
    build_deck(o, _svg_with_image, ws["pages"], workspace=ws)
    led = load_asset_ledger(ws["asset_ledger"])
    assert led["images"] == [{"page": 1, "href": "assets/logo.png", "license_note": ""}]


# ── 2026-07-02 saopan扫盘修复回归（核心接缝包）─────────────────────────

def _drop_passed_review(ws):
    """D18 FR6.1 适配：publish 前落盘全勾完的人审清单（本文件的 publish 测试测 checksum 链路）。"""
    import json as _json
    from reinforce.review import new_review as _nr
    r = _nr()
    for section in r.values():
        for k in section:
            section[k] = True
    ws["review"].write_text(_json.dumps(r, ensure_ascii=False), encoding="utf-8")


def test_workspace_pptx_lands_at_ws_pptx_and_checksum_closes(tmp_path):
    """④🔴1：成品统一落 ws["pptx"]——publish 后 checksum 非空、verify ok（此前 100% 空转）。"""
    from reinforce.deck_workspace import new_workspace, publish_deck, verify_published
    ws = new_workspace("t_checksum", root=tmp_path)
    res = build_deck(_outline_2p(), _clean_svg, ws["pages"], workspace=ws)
    assert res["pptx_path"] == str(ws["pptx"]) and ws["pptx"].is_file()
    _drop_passed_review(ws)
    pub = publish_deck("t_checksum", root=tmp_path)
    assert pub["checksum"]                              # 不再 no_checksum
    assert verify_published(root=tmp_path)[0]["status"] == "ok"


def test_publish_twice_rejected_no_checksum_whitewash(tmp_path):
    """④🔴2：重复 publish 拒——防篡改后重发布洗白 mismatch 证据。"""
    from reinforce.deck_workspace import new_workspace, publish_deck, verify_published
    ws = new_workspace("t_wash", root=tmp_path)
    build_deck(_outline_2p(), _clean_svg, ws["pages"], workspace=ws)
    _drop_passed_review(ws)
    publish_deck("t_wash", root=tmp_path)
    ws["pptx"].write_bytes(b"tampered")                 # 绕 API 直接改文件
    assert verify_published(root=tmp_path)[0]["status"] == "mismatch"
    with pytest.raises(PermissionError, match="拒重复 publish"):
        _drop_passed_review(ws)
        publish_deck("t_wash", root=tmp_path)           # 想洗白？拒
    assert verify_published(root=tmp_path)[0]["status"] == "mismatch"   # 证据仍在


def test_resume_gate_fail_downgrades_status_on_disk(tmp_path):
    """resume 假绿（三路交叉确认）：复用页重检失败 → 落盘状态降回 drafted，不再假 done。"""
    from reinforce.deck_state import load_outline
    from reinforce.deck_workspace import new_workspace
    ws = new_workspace("t_resume_fail", root=tmp_path)
    o = _outline_2p()
    build_deck(o, _clean_svg, ws["pages"], workspace=ws)          # 全过·全 done
    (ws["pages"] / "page_1.svg").write_text(
        '<svg viewBox="0 0 1280 720" xmlns="http://www.w3.org/2000/svg"><style>.a{}</style>'
        '<text x="1" y="9" font-size="16">数据来源：财报</text></svg>', encoding="utf-8")  # 手改坏 SVG(带禁用 style)
    o2 = load_outline(ws["outline"])
    res = build_deck(o2, _clean_svg, ws["pages"], workspace=ws, resume=True)
    assert res["all_passed"] is False
    statuses = {p["n"]: p["status"] for p in load_outline(ws["outline"])["pages"]}
    assert statuses[1] == "drafted"                     # 门败页如实降级落盘
    assert statuses[2] == "done"                        # 过门页不受牵连


def test_title_with_slash_sanitized_without_workspace(tmp_path):
    """④🟡：无 workspace 时 title 含 '/' 消毒成 '_'——不再静默写进子目录。"""
    o = _outline_2p()
    o["title"] = "FY24/25 增长计划"
    res = build_deck(o, _clean_svg, tmp_path)
    from pathlib import Path
    p = Path(res["pptx_path"])
    assert p.parent == tmp_path and "/" not in p.name and p.is_file()


def test_render_previews_raises_when_playwright_missing(tmp_path, monkeypatch):
    """②🟡：显式 render_previews=True 且 playwright 缺 → raise，不再静默蒸发自检关。"""
    import engine.render_preview as RP
    monkeypatch.setattr(RP, "preview_available", lambda: False)
    with pytest.raises(ImportError, match="渲染自检"):
        build_deck(_outline_2p(), _clean_svg, tmp_path, render_previews=True)


def test_workspace_incomplete_dict_warns(tmp_path):
    """孤岛B5：手拼残缺 workspace（缺 deck_id/published_ledger）→ warn 不再全静默。"""
    res = build_deck(_outline_2p(), _clean_svg, tmp_path, workspace={"outline": tmp_path / "o.json"})
    assert any(w["rule"] == "workspace_incomplete" for w in res["deck_warnings"])


def test_spec_lock_palette_cvd_wired(tmp_path, monkeypatch):
    """孤岛A1接线：spec_lock 传入 → check_colorblind_safe 自动跑、结果进 deck_warnings。"""
    import engine.pipeline as P
    monkeypatch.setattr(P, "check_colorblind_safe",
                        lambda palette: [{"rule": "cvd_probe", "sev": "warn", "note": "wired"}])
    spec = new_spec_lock(palette={"bg": "#FFFFFF", "ink": "#111111"}, font_family="Arial")
    res = build_deck(_outline_2p(), _clean_svg, tmp_path, spec_lock=spec)
    assert any(w["rule"] == "cvd_probe" for w in res["deck_warnings"])


# ── D18 FR5.2/FR3.2 机检接线 pipeline ─────────────────────────────────
def test_client_tone_gate_wired_into_build_deck(tmp_path):
    """FR5.2：内部语言上页在逐页 gate 里被逮（warn·不拦）。"""
    def _leaky_svg(ctx):
        return ('<svg viewBox="0 0 1280 720" xmlns="http://www.w3.org/2000/svg">'
                f'<text x="100" y="135" font-size="28">{ctx["page"]["claim"]}</text>'
                '<text x="100" y="300" font-size="14">来源：brief P3-4</text>'
                '<text x="100" y="340" font-size="16">数据来源：财报2024</text></svg>')
    res = build_deck(_outline_2p(), _leaky_svg, tmp_path)
    issues = res["pages"][0]["gate"]["issues"]
    # D19 FR1.2：定位符升 error（不再限定 warn·strict 模式会真拦）
    assert any(i["rule"] == "internal_locator" and i["sev"] == "error" for i in issues)


def test_chart_realized_gate_wired_into_build_deck(tmp_path):
    """FR3.2：声明 line_compare 实际画卡片 → warn 提示可能未兑现。"""
    o = new_outline("兑现检", "数据报告", "复盘总结", "财务")
    add_page(o, 1, "数据论断", "增速对比拉开差距", facets={"chart": "line_compare"})
    res = build_deck(o, _clean_svg, tmp_path)   # _clean_svg 只有 rect+text·无折线
    assert any("line" in str(i).lower() or "兑现" in str(i.get("note", ""))
               for i in res["pages"][0]["gate"]["issues"] if i["sev"] == "warn")


def test_build_deck_none_palette_value_fails_closed_not_crash(tmp_path):
    """2026-07-03 saopan批②链路验证（单测绿≠链路通）：palette 带 None 值此前能穿过
    validate_spec_lock，滑到 check_colorblind_safe 时 _hex_to_rgb(None) AttributeError
    裸栈——现在 validate 就拦，fail-closed 抛的是带 issues 的 ValueError 不是崩溃。"""
    spec = new_spec_lock({"bg": "#FFFFFF", "ink": None}, "Arial")
    with pytest.raises(ValueError, match="spec_lock 不完整"):
        build_deck(_outline_2p(), _clean_svg, tmp_path, spec_lock=spec)


# ---------- D27 素材在场未用机检（第七轮某品牌单：素材异步投放 vs 扫描单点） ----------

def _d27_minimal(tmp_path, palette_source):
    from reinforce.deck_state import add_page, new_outline
    from reinforce.deck_workspace import new_workspace
    from reinforce.spec_lock import new_spec_lock
    ws = new_workspace("t_d27", root=tmp_path / "decks")
    o = new_outline("素材机检", "数据报告", "复盘总结", "财务")
    add_page(o, 1, "text_highlight", "本季核心指标增长两成")
    spec = new_spec_lock({"bg": "#ffffff", "ink": "#111111"}, "Arial",
                         palette_source=palette_source)
    return ws, o, spec


def _d27_provider(ctx):
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720">'
            '<text x="10" y="40" fill="#111111">本季核心指标增长两成</text></svg>')


def test_assets_present_but_unused_is_rejected(tmp_path):
    import pytest

    from engine.pipeline import build_deck
    ws, o, spec = _d27_minimal(tmp_path, {"kind": "web_verified", "brand": "B",
                                          "evidence": "https://x.example/vi"})
    (ws["brand_assets"] / "brand_book.pdf").write_bytes(b"pdf")   # 用户投放了素材
    with pytest.raises(ValueError, match="品牌素材在场未用"):
        build_deck(o, _d27_provider, tmp_path / "out", workspace=ws, spec_lock=spec)


def test_assets_used_or_reviewed_or_absent_pass(tmp_path):
    from engine.pipeline import build_deck
    # ① 素材在场 + brand_vi 正用 → 过
    ws, o, spec = _d27_minimal(tmp_path, {"kind": "brand_vi", "brand": "B",
                                          "evidence": "brand_assets/brand_book.pdf"})
    (ws["brand_assets"] / "brand_book.pdf").write_bytes(b"pdf")
    r = build_deck(o, _d27_provider, tmp_path / "out1", workspace=ws, spec_lock=spec)
    assert r["pptx_path"]
    # ② 素材在场 + 显式已阅弃用 → 过（决策留痕不是事故）
    ws2, o2, spec2 = _d27_minimal(tmp_path / "b", {"kind": "web_verified", "brand": "B",
                                                   "evidence": "https://x.example/vi",
                                                   "assets_reviewed": True})
    (ws2["brand_assets"] / "old_deck.pptx").write_bytes(b"p")
    assert build_deck(o2, _d27_provider, tmp_path / "out2", workspace=ws2, spec_lock=spec2)["pptx_path"]
    # ③ 收集点空（只有引导说明）→ 不拦
    ws3, o3, spec3 = _d27_minimal(tmp_path / "c", {"kind": "neutral"})
    assert build_deck(o3, _d27_provider, tmp_path / "out3", workspace=ws3, spec_lock=spec3)["pptx_path"]
