"""D18 视觉管道包单测——FR3.1 chart→资产映射 / FR3.3 检索词表 / FR3.5 Part 视觉配额 /
FR3.6 gantt 标签修复 / FR7.5 图标接线 / FR7.7 版式骨架路由。

对应实测病（specs/需求_第一轮实测反馈.md）：声明 20 种 chart 兑现 0 张（模板零注入）、
search(page_function='数据论断') 召回错卡（词表错位）、gantt 行标签恒停左缘与色条脱节。
"""

from __future__ import annotations

import re

import pytest

from engine import chart_shapes
from engine import prompt_builder as P
from engine.chart_template_map import (CHART_TEMPLATE_MAP, TEMPLATES_DIR,
                                        check_part_visual_quota, template_for_chart)
from engine.icon_sync import ICONS_DIR, icon_svg, list_icon_libraries, verify_inventory
from reinforce import deck_state as S
from reinforce.retrieval import search as R
from reinforce.spec_lock import new_spec_lock


# ════════════════════ FR3.1 chart→资产映射表 ════════════════════

def test_map_templates_all_exist_on_disk():
    """映射到的模板文件必须真实存在（防映射到不存在的资产·71 张里挑的每张都核过）。"""
    for k, v in CHART_TEMPLATE_MAP.items():
        tpl = v.get("template")
        if tpl:
            assert (TEMPLATES_DIR / tpl).is_file(), f"{k} 映射的模板 {tpl} 不存在"
        assert v.get("engine") in (None, "waterfall", "gantt", "mekko"), f"{k} engine 值非法"
        if v.get("engine"):
            assert hasattr(chart_shapes, f"{v['engine']}_chart"), f"{k} 映射的引擎函数不存在"
        assert v.get("hint"), f"{k} 缺 hint（一句结构要点是映射表的必填件）"


def test_map_covers_all_field_test_charts():
    """第一轮实测 deck 声明过的 chart facet 全部有映射（这是 FR3.1 的覆盖底线）。"""
    field_test_charts = {"line_compare", "bar_callout", "kol_pyramid", "aipl_funnel",
                         "expansion_map", "wave_timeline", "metric_callout", "decision_box",
                         "trend_shift", "media_mix", "content_pillars", "checklist_table",
                         "budget_table", "mechanism_diagram", "design_logic", "video_concept",
                         "risk_statement", "brief_recap", "quote_callout", "consumer_insight",
                         "text_highlight", "creative_concept", "cover"}
    assert field_test_charts <= set(CHART_TEMPLATE_MAP), \
        f"实测 chart 缺映射：{field_test_charts - set(CHART_TEMPLATE_MAP)}"


def test_template_for_chart_exact():
    m = template_for_chart("line_compare")
    assert m["template"] == "line_chart.svg" and m["match"] == "exact"


def test_template_for_chart_normalizes_case_and_space():
    assert template_for_chart(" Line_Compare ")["template"] == "line_chart.svg"


def test_template_for_chart_fuzzy_key_substring():
    m = template_for_chart("line_compare_yoy")
    assert m["matched"] == "line_compare" and m["match"] == "fuzzy_key"
    assert m["template"] == "line_chart.svg"


def test_template_for_chart_fuzzy_template_stem():
    """词根级模糊：kol_pyramid→pyramid_chart 这条规则对非映射键同样生效。"""
    m = template_for_chart("value_pyramid")  # 不在映射键里·词根 pyramid 对上 pyramid_chart.svg
    assert m["template"] == "pyramid_chart.svg" and m["match"] == "fuzzy_template"
    m2 = template_for_chart("competitive_radar")
    assert m2["template"] == "radar_chart.svg"


def test_template_for_chart_no_pie_pipeline_false_match():
    """token 边界匹配：pie 不许因子串撞进 pipeline 类名字。"""
    m = template_for_chart("pieline_zzz_qqq")  # 故意的怪名·任何词根都不该按子串硬凑
    assert m is None or m.get("template") != "pie_chart.svg"


def test_template_for_chart_unknown_returns_none():
    assert template_for_chart("totally_unknown_zzz") is None
    assert template_for_chart(None) is None
    assert template_for_chart("  ") is None


def test_engine_charts_carry_engine_field():
    assert template_for_chart("waterfall")["engine"] == "waterfall"
    assert template_for_chart("gantt")["engine"] == "gantt"
    assert template_for_chart("mekko")["engine"] == "mekko"


# ── FR3.1 prompt 接线（验收：声明 line_compare 的页 prompt 里出现 line_chart 模板结构）──

def _outline_with_chart(chart: str):
    o = S.new_outline("某品牌 Y25 策略提案", "品牌策略提案", ["推导策略"], ["营销品牌"], ["甲方高层"])
    S.add_page(o, 1, "封面/章节", "某品牌 Y25 策略提案")
    S.add_page(o, 2, "数据呈现", "销量三年翻番", depends_on=[1], facets={"chart": chart})
    return o


def test_prompt_injects_chart_template_structure():
    r = P.build_deck_prompt(_outline_with_chart("line_compare"), 2)
    assert "line_chart.svg" in r["prompt"]
    assert "供结构不供皮肤" in r["prompt"] and "spec_lock 锁定色板" in r["prompt"]
    # 模板 SVG 源码真的进了 prompt（开头 200 字符原样在——不是只提了个文件名）
    head = (TEMPLATES_DIR / "line_chart.svg").read_text(encoding="utf-8")[:200]
    assert head in r["prompt"]
    assert "该图型结构要点" in r["prompt"]


def test_prompt_engine_hint_and_template_coexist():
    """waterfall 页：既保留 chart_shapes 强制调用提示（既有），又注入模板结构（FR3.1 新增）。"""
    r = P.build_deck_prompt(_outline_with_chart("waterfall"), 2)
    assert "必须调用 `engine.chart_shapes.waterfall_chart()`" in r["prompt"]
    assert "waterfall_chart.svg" in r["prompt"]


def test_prompt_no_template_chart_gets_hint_only():
    """quote_callout（纯排版页型·映射 template=None）：hint 进 prompt、不出现模板源码段。"""
    r = P.build_deck_prompt(_outline_with_chart("quote_callout"), 2)
    assert "该图型结构要点" in r["prompt"]
    assert "## 图表结构参考模板" not in r["prompt"]


def test_template_source_truncated_at_limit():
    """超 8KB 模板截前段防爆 prompt（layered_architecture.svg 实测 24K）。"""
    src = P._read_template_source(TEMPLATES_DIR / "layered_architecture.svg")
    assert src is not None
    assert len(src) <= P._MAX_TEMPLATE_CHARS + 100  # 上限 + 截断标注的余量
    assert "已截取前" in src
    assert P._read_template_source(TEMPLATES_DIR / "不存在的模板.svg") is None


# ════════════════════ FR7.7 版式骨架路由 ════════════════════

def test_layout_route_theme_slash_pagename():
    p = P._layout_skeleton_path("ai_ops/cover")
    assert p is not None and p.name == "01_cover.svg" and p.parent.name == "ai_ops"
    assert P._layout_skeleton_path("government_red/ending").name == "04_ending.svg"


def test_layout_route_direct_relative_path():
    p = P._layout_skeleton_path("ai_ops/01_cover.svg")
    assert p is not None and p.is_file()


def test_layout_route_unresolvable_returns_none():
    assert P._layout_skeleton_path("ai_ops/不存在页型") is None
    assert P._layout_skeleton_path("不存在套/cover") is None
    assert P._layout_skeleton_path("") is None
    assert P._layout_skeleton_path("没有斜杠") is None


def _spec_lock(**kw):
    return new_spec_lock({"bg": "#FFFFFF", "ink": "#111111", "accent": "#C8102E"}, "Arial", **kw)


def test_prompt_injects_layout_skeleton_source():
    sl = _spec_lock(per_page={2: {"layout": "ai_ops/cover"}})
    r = P.build_deck_prompt(_outline_with_chart("quote_callout"), 2, spec_lock=sl)
    assert "## 版式骨架参考（ai_ops/cover" in r["prompt"]
    head = (P._LAYOUTS_DIR / "ai_ops" / "01_cover.svg").read_text(encoding="utf-8")[:200]
    assert head in r["prompt"]  # 骨架 SVG 源码真进了 prompt
    assert "供结构不供皮肤" in r["prompt"]


def test_prompt_layout_missing_is_loud_not_silent():
    sl = _spec_lock(per_page={2: {"layout": "ai_ops/没这页"}})
    r = P.build_deck_prompt(_outline_with_chart("quote_callout"), 2, spec_lock=sl)
    assert "未解析到文件" in r["prompt"]  # fail-loud：声明了骨架但路由不到 → prompt 里明示


def test_prompt_layout_only_on_declared_page():
    sl = _spec_lock(per_page={1: {"layout": "ai_ops/cover"}})
    r = P.build_deck_prompt(_outline_with_chart("quote_callout"), 2, spec_lock=sl)
    assert "## 版式骨架参考" not in r["prompt"]  # 第 2 页没声明 layout·不注入


# ════════════════════ FR7.5 图标接线 ════════════════════

def test_list_icon_libraries_finds_all_five():
    libs = list_icon_libraries()
    assert {"chunk-filled", "phosphor-duotone", "simple-icons",
            "tabler-filled", "tabler-outline"} <= set(libs)


def test_verify_inventory_ok():
    r = verify_inventory("tabler-outline", ["abacus", "a-b"])
    assert r["valid"] and r["library_exists"] and r["missing"] == []


def test_verify_inventory_reports_missing_names():
    r = verify_inventory("tabler-outline", ["abacus", "绝不存在的图标xyz"])
    assert not r["valid"] and r["missing"] == ["绝不存在的图标xyz"]


def test_verify_inventory_bad_library_fails_closed():
    r = verify_inventory("不存在的库", ["abacus"])
    assert not r["valid"] and not r["library_exists"] and r["missing"] == ["abacus"]


def test_icon_svg_reads_source():
    src = icon_svg("tabler-outline", "abacus")
    assert "<svg" in src
    assert icon_svg("tabler-outline", "abacus.svg") == src  # 带不带 .svg 后缀都认


def test_icon_svg_missing_raises():
    with pytest.raises(FileNotFoundError, match="verify_inventory"):
        icon_svg("tabler-outline", "绝不存在的图标xyz")


def test_icon_path_escape_rejected():
    with pytest.raises(ValueError, match="穿越"):
        icon_svg("tabler-outline", "../tabler-filled/a")
    r = verify_inventory("tabler-outline", ["../tabler-filled/a"])
    assert not r["valid"] and r["missing"] == ["../tabler-filled/a"]  # 穿越名按缺失计


def test_prompt_icon_usage_line():
    sl = _spec_lock(icons={"library": "tabler-outline", "inventory": ["abacus", "activity"]})
    r = P.build_deck_prompt(_outline_with_chart("quote_callout"), 2, spec_lock=sl)
    assert 'data-icon' in r["prompt"] and "finalize" in r["prompt"]  # 占位+内嵌工序说明


def test_prompt_no_icon_line_without_inventory():
    r = P.build_deck_prompt(_outline_with_chart("quote_callout"), 2, spec_lock=_spec_lock())
    assert "finalize 工序会把占位替换" not in r["prompt"]


# ════════════════════ FR3.3 检索词表修复 ════════════════════

def test_search_data_assertion_recalls_data_cards():
    """验收：search(page_function='数据论断') 能召回数据呈现类卡（修复前主键 0 分全靠 domain 撑）。"""
    got = R.search(page_function="数据论断")
    names = [c.get("page_function", "") for c in got]
    assert names, "同义映射后必须有召回"
    assert "数据呈现" in names  # 卡库真实词
    assert any("数据" in nm for nm in names[:3])  # 头部召回是数据类


def test_search_toc_recalls_agenda_card():
    got = R.search(page_function="目录")
    assert any(c.get("page_function") == "议程" for c in got)  # 卡库里目录页手法卡叫"议程"


def test_search_exact_vocab_unaffected():
    got = R.search(page_function="金句主张")
    assert got and got[0]["page_function"] == "金句主张"  # 本就对齐的词不受同义扩词干扰


def test_expand_page_function_bidirectional():
    assert "数据呈现" in R._expand_page_function("数据论断")
    assert "数据论断" in R._expand_page_function("数据呈现")  # 反向也通
    assert R._expand_page_function("金句主张") == ()  # 无同义词 → 空
    assert R._expand_page_function(None) == ()


def test_synonym_values_exist_in_card_library():
    """映射值必须对得上卡库真实词（精确或子串可命中）——卡库词表漂了这里逮。"""
    vocab = [c.get("page_function", "") for c in R.load_cards()]
    for k, syns in R.PAGE_FUNCTION_SYNONYMS.items():
        for syn in syns:
            assert any(syn == v or syn in v or v in syn for v in vocab), \
                f"同义词 {k}→{syn} 在卡库 page_function 词表里对不到任何卡"


def test_synonym_scoring_prefers_exact_family():
    """同义词参与精确匹配：'数据论断' 对 page_function='数据呈现' 的卡打出 +4（非模糊 +2）。"""
    cards = [{"page_function": "数据呈现", "rating": 1},
             {"page_function": "随便别的", "rating": 9}]
    scored = R.search_deck_cards(page_function="数据论断", cards=cards)
    assert scored[0][0]["page_function"] == "数据呈现" and scored[0][1] == 4
    assert len(scored) == 1  # 不相干卡没分·不进结果


# ════════════════════ FR3.5 Part 级视觉配额 ════════════════════

def _outline_two_parts(part2_chart: str):
    o = S.new_outline("某品牌 Y25 策略提案", "品牌策略提案", ["推导策略"], ["营销品牌"], ["甲方高层"])
    S.add_page(o, 1, "数据呈现", "销量三年翻番", facets={"part": "P1", "chart": "line_compare"})
    S.add_page(o, 2, "洞察推导", "增长来自下沉市场", facets={"part": "P1"})
    S.add_page(o, 3, "金句主张", "把握下一个窗口", facets={"part": "P2", "chart": part2_chart})
    S.add_page(o, 4, "洞察推导", "窗口只有十八个月", facets={"part": "P2"})
    return o


def test_part_quota_warns_on_part_without_strong_visual():
    # P1 有 line_compare（映射到模板=强视觉）；P2 只有 quote_callout（template/engine 全 None=纯排版）
    issues = check_part_visual_quota(_outline_two_parts("quote_callout"))
    assert len(issues) == 1
    assert issues[0]["sev"] == "warn" and issues[0]["part"] == "P2"
    assert "无强视觉页" in issues[0]["msg"] and "1-2 页强视觉" in issues[0]["msg"]
    assert issues[0]["pages"] == [3, 4]


def test_part_quota_chart_with_template_counts_strong():
    assert check_part_visual_quota(_outline_two_parts("kol_pyramid")) == []  # P2 有金字塔 → 达标


def test_part_quota_engine_chart_counts_strong():
    assert check_part_visual_quota(_outline_two_parts("mekko")) == []  # 引擎图（无模板）也算强视觉


def test_part_quota_layout_or_hero_in_spec_lock_counts():
    o = _outline_two_parts("quote_callout")
    sl_hero = _spec_lock(per_page={3: {"hero": {"hook": "巨字钩子", "composition": "全幅"}}})
    assert check_part_visual_quota(o, sl_hero) == []
    sl_layout = _spec_lock(per_page={4: {"layout": "ai_ops/chapter"}})
    assert check_part_visual_quota(o, sl_layout) == []


def test_part_quota_pages_without_part_not_judged():
    """老 deck 没标 part → 评估不了就不评估（不误报），空输入不崩。"""
    o = S.new_outline("t", "d", ["i"], ["dm"], ["a"])
    S.add_page(o, 1, "数据呈现", "c1", facets={"chart": "quote_callout"})
    assert check_part_visual_quota(o) == []
    assert check_part_visual_quota({}) == []
    assert check_part_visual_quota({"pages": None}) == []


# ════════════════════ FR3.6 gantt 标签修复 ════════════════════

_LABEL_RE = re.compile(r'<text x="(-?\d+)" y="(-?\d+)"[^>]*?>([^<]+)</text>')


def _label_pos(svg: str, label: str):
    for m in _LABEL_RE.finditer(svg):
        if m.group(3) == label:
            full = m.group(0)
            return int(m.group(1)), int(m.group(2)), 'text-anchor="end"' in full
    raise AssertionError(f"标签 {label} 没找到")


def test_gantt_label_follows_bar_not_stuck_at_left_edge():
    """实测病：色条起点 x=400+ 时行标签恒停图表左缘。修后：标签右缘紧贴色条左侧 gap=8。"""
    tasks = [{"label": "筹备", "start": "2026-01-01", "end": "2026-02-01"},
             {"label": "上市", "start": "2026-03-01", "end": "2026-03-10"}]
    svg = chart_shapes.gantt_chart(0, 0, 680, 300, tasks)
    # 任务1 色条起点 = 59天 × (680/68)px/天 = 590.0
    assert 'x="590.0"' in svg
    lx, _, anchored_end = _label_pos(svg, "上市")
    assert anchored_end, "远离左缘的行标签必须右对齐锚定（text-anchor=end）"
    gap = 590.0 - lx
    assert 0 < gap <= 10, f"标签与其色条水平间距 {gap}px 超出合理值（应≈8px）"


def test_gantt_label_near_left_edge_stays_at_origin():
    tasks = [{"label": "筹备", "start": "2026-01-01", "end": "2026-02-01"},
             {"label": "上市", "start": "2026-03-01", "end": "2026-03-10"}]
    svg = chart_shapes.gantt_chart(0, 0, 680, 300, tasks)
    lx, _, anchored_end = _label_pos(svg, "筹备")
    assert lx == 0 and not anchored_end  # 色条本来就在左缘 → 标签留左缘（左对齐·同旧版）


def test_gantt_label_y_follows_own_row_and_stays_in_canvas():
    """旧版首行标签 y=row_y-6 会画出画布顶（header=0 时 y=-6）——修后垂直居中于本行色条。"""
    tasks = [{"label": "任务甲", "start": "2026-01-01", "end": "2026-01-05"},
             {"label": "任务乙", "start": "2026-01-05", "end": "2026-01-09"}]
    svg = chart_shapes.gantt_chart(0, 0, 400, 300, tasks, header_height=0)
    ya = _label_pos(svg, "任务甲")[1]
    yb = _label_pos(svg, "任务乙")[1]
    assert ya >= 0, "首行标签不许画出画布顶"
    stride = 28 + 12  # bar_height + row_gap 默认
    assert yb - ya == stride  # y 逐行跟随
    # 垂直居中：标签基线落在本行色条 y 区间内（row0 色条 y∈[0,28]）
    assert 0 <= ya <= 28


def test_gantt_label_color_parameterized():
    tasks = [{"label": "筹备", "start": "2026-01-01", "end": "2026-02-01"}]
    default_svg = chart_shapes.gantt_chart(0, 0, 400, 300, tasks)
    assert 'fill="#374151"' in default_svg  # 默认=修复前硬编码值·向后兼容
    custom_svg = chart_shapes.gantt_chart(0, 0, 400, 300, tasks, colors={"label": "#ABCDEF"})
    assert 'fill="#ABCDEF"' in custom_svg and 'fill="#374151"' not in custom_svg


def test_gantt_milestone_label_clears_diamond_tip():
    """里程碑菱形左尖比 bx 多伸出半个条高——标签锚点按视觉左缘算，不压菱形。"""
    tasks = [{"label": "筹备", "start": "2026-01-01", "end": "2026-02-01"},
             {"label": "发布", "start": "2026-03-01", "end": "2026-03-01"}]  # 里程碑
    svg = chart_shapes.gantt_chart(0, 0, 680, 300, tasks)
    lx, _, anchored_end = _label_pos(svg, "发布")
    # 全局区间 59 天铺满 680px → 里程碑 bx=680（右缘）·bar_h=28 → 菱形左尖 666 → 标签右缘 int(666-8)=658
    assert anchored_end and lx == 658
    assert 0 < 666 - lx <= 10  # 与菱形视觉左缘的间距 ≈8px·不压菱形


# ---------- D22 丰富度：类型智能默认 + 图像配额分级执法 ----------

def _outline_pages(n):
    return {"pages": [{"n": i + 1, "facets": {}} for i in range(n)]}


def test_default_richness_for_three_types():
    from engine.chart_template_map import default_richness_for
    assert default_richness_for("某品牌 品牌比稿 40页")[0] == "浓郁"
    assert default_richness_for("投委会尽调汇报")[0] == "素雅"
    assert default_richness_for("内部季度经营回顾")[0] == "标准"
    # 每档都带一句为什么（推荐时要摊给用户）
    for p in ("比稿", "尽调", "回顾"):
        assert default_richness_for(p)[1]


def test_image_quota_rich_below_floor_is_error():
    from engine.chart_template_map import check_image_quota
    spec = {"richness": "浓郁", "images": [{"filename": "a.png"}]}  # 40页下限 max(3,5)=5
    issues = check_image_quota(_outline_pages(40), spec)
    assert issues and issues[0]["sev"] == "error"


def test_image_quota_rich_at_floor_passes():
    from engine.chart_template_map import check_image_quota
    spec = {"richness": "浓郁", "images": [{"filename": f"{i}.png"} for i in range(5)]}
    assert check_image_quota(_outline_pages(40), spec) == []


def test_image_quota_standard_zero_is_warn_only():
    from engine.chart_template_map import check_image_quota
    issues = check_image_quota(_outline_pages(20), {"richness": "标准", "images": []})
    assert issues and issues[0]["sev"] == "warn"


def test_image_quota_plain_or_unlocked_not_checked():
    from engine.chart_template_map import check_image_quota
    assert check_image_quota(_outline_pages(40), {"richness": "素雅", "images": []}) == []
    assert check_image_quota(_outline_pages(40), {"images": []}) == []   # 未锁=旧deck零破坏
    assert check_image_quota(_outline_pages(40), None) == []


def test_template_for_chart_short_key_skips_fuzzy():
    """2026-07-03 saopan批②：单字/双字输入是任意映射键的子串（'e' in 'mechanism_diagram'
    恒真）——len<3 不进模糊①，垃圾短输入返回 None 而非假配。"""
    assert template_for_chart("e") is None
    assert template_for_chart("x") is None
    assert template_for_chart("ab") is None
    # 合法短键的精确命中不受影响（exact 分支在长度门之前）
    assert template_for_chart("donut") is not None


# ---------- D26 兑现机检：图标/图片声明→落地 ----------

def test_icons_realized_warns_when_declared_but_absent():
    from reinforce.deck_rules.visual_review import check_icons_realized
    spec = {"icons": {"library": "tabler-outline", "inventory": ["abacus", "users"]}}
    svgs = ["<svg><rect/></svg>", "<svg><text>x</text></svg>"]   # 零 data-icon
    issues = check_icons_realized(svgs, spec)
    assert issues and issues[0]["sev"] == "warn" and "零 data-icon" in issues[0]["note"]
    # 任一页有占位即算兑现；未声明 icons 不查
    assert check_icons_realized(['<g data-icon="abacus"/>'], spec) == []
    assert check_icons_realized(svgs, {"icons": {}}) == []


def test_images_realized_reports_missing(tmp_path):
    from reinforce.deck_rules.visual_review import check_images_realized
    spec = {"images": [
        {"filename": "kv.png", "acquire_via": "web"},
        {"filename": "moment.png", "acquire_via": "ai"},
        {"filename": "手工位.png", "acquire_via": "placeholder"},   # 真人接管·不计缺失
    ]}
    (tmp_path / "kv.png").write_bytes(b"x")                       # 落地在 images/ 目录
    issues = check_images_realized(["<svg/>"], spec, images_dir=tmp_path)
    assert issues and issues[0]["missing"] == ["moment.png"]
    # SVG 引用也算落地
    assert check_images_realized(['<image href="images/moment.png"/>'], spec, images_dir=tmp_path) == []
