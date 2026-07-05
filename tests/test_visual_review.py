"""视觉缺陷结构化机检测试（提炼自 ppt-master visual-review.md 的 H1/H4/H8/S6·结构级可判定子集）。"""

from __future__ import annotations

import pytest

from reinforce.deck_rules.visual_review import (
    _simulate_cvd,
    check_aspect_ratio,
    check_broken_image_href,
    check_chart_realized,
    check_colorblind_safe,
    check_contrast,
    check_edge_alignment,
    check_equal_distribution,
    check_font_grid,
    check_font_variety_per_page,
    check_invisible_text,
    check_letter_spacing,
    check_out_of_canvas,
    check_uniform_size,
    contrast_ratio,
    content_area_ratio,
    count_visual_blocks,
    run_visual_gate,
)


def _page(*body: str) -> str:
    return ('<svg viewBox="0 0 1280 720" xmlns="http://www.w3.org/2000/svg">'
            '<rect width="1280" height="720" fill="#FFFFFF"/>' + "".join(body) + "</svg>")


# ── H1 出画布 ──
def test_out_of_canvas_clean_rect_passes():
    assert check_out_of_canvas(_page('<rect x="100" y="100" width="200" height="80" fill="#000"/>')) == []


def test_out_of_canvas_catches_negative_x():
    out = check_out_of_canvas(_page('<rect x="-20" y="100" width="200" height="80" fill="#000"/>'))
    assert any(i["rule"] == "out_of_canvas" for i in out)


def test_out_of_canvas_catches_overflow_right():
    out = check_out_of_canvas(_page('<rect x="1200" y="100" width="200" height="80" fill="#000"/>'))
    assert any(i["rule"] == "out_of_canvas" for i in out)


def test_out_of_canvas_skips_transformed_elements():
    # 复合变换(非纯rotate)仍然需要矩阵运算才能算真实包围盒，宁可漏检不瞎猜
    out = check_out_of_canvas(_page('<rect x="-999" y="-999" width="50" height="50" '
                                     'transform="translate(999,999)" fill="#000"/>'))
    assert out == []


# ── H1 纯旋转闭式AABB（2026-07-01 yanjiu研究驱动评估🟡走样需修·Instrumenta启发但改用通用闭式解）──
def test_out_of_canvas_pure_rotate_around_origin_catches_overflow():
    # rect(600,600,100,50) 绕原点转90°后AABB=(-650,600)-(-600,700)，负x越界(已用实际代码验证)
    out = check_out_of_canvas(_page(
        '<rect x="600" y="600" width="100" height="50" transform="rotate(90)" fill="#000"/>'))
    assert out and out[0]["rule"] == "out_of_canvas" and "旋转" in out[0]["note"]


def test_out_of_canvas_pure_rotate_around_own_center_safely_inside_passes():
    # 画布中央的矩形绕自身中心转任意角度都不该出画布(已用实际代码验证)
    svg = _page('<rect x="600" y="300" width="80" height="60" transform="rotate(37 640 330)" fill="#000"/>')
    assert check_out_of_canvas(svg) == []


def test_out_of_canvas_pure_rotate_at_edge_around_own_center_catches_overflow():
    # 贴着(0,0)角的矩形绕自身中心转45°会有角探出画布(已用实际代码验证AABB=(-3,-28)-(103,78))
    svg = _page('<rect x="0" y="0" width="100" height="50" transform="rotate(45 50 25)" fill="#000"/>')
    out = check_out_of_canvas(svg)
    assert out and out[0]["rule"] == "out_of_canvas"


def test_out_of_canvas_composite_transform_still_skipped():
    # 有 translate 又有 rotate 的复合变换·不是"纯旋转"·仍跳过不瞎猜
    svg = _page('<rect x="-999" y="-999" width="10" height="10" '
                'transform="translate(5,5) rotate(10)" fill="#000"/>')
    assert check_out_of_canvas(svg) == []


def test_out_of_canvas_malformed_rotate_number_skipped_not_crashed():
    # 2026-07-02 saopan扫盘揪出：正则 [-\d.]+ 放行 "1.2.3"，裸 float() 一炸崩穿
    # run_visual_gate→build_deck 全链。修后走"复杂transform跳过不瞎猜"路径：不崩、该元素跳过
    # （坐标故意放越界，证明确实是跳过而非照常检查）。
    svg = _page('<rect x="-999" y="-999" width="10" height="10" '
                'transform="rotate(1.2.3)" fill="#000"/>')
    assert check_out_of_canvas(svg) == []
    assert run_visual_gate(svg) is not None  # 整条视觉门都不能被一个畸形数字击穿


def test_out_of_canvas_circle_pure_rotate_around_origin():
    svg = _page('<circle cx="600" cy="600" r="20" transform="rotate(90)" fill="#000"/>')
    out = check_out_of_canvas(svg)
    assert out and "circle" in out[0]["note"] and "旋转" in out[0]["note"]


def test_out_of_canvas_catches_circle_overflow():
    out = check_out_of_canvas(_page('<circle cx="10" cy="10" r="50" fill="#000"/>'))
    assert any("circle" in i["note"] for i in out)


def test_out_of_canvas_catches_text_anchor_outside():
    out = check_out_of_canvas(_page('<text x="2000" y="100" font-size="20" fill="#000">x</text>'))
    assert any("text" in i["note"] for i in out)


# ── H4 对比度（WCAG 真实公式）──
def test_contrast_ratio_black_on_white_is_max():
    assert contrast_ratio("#000000", "#FFFFFF") == contrast_ratio("#FFFFFF", "#000000")
    assert round(contrast_ratio("#000000", "#FFFFFF"), 1) == 21.0


def test_contrast_ratio_same_color_is_one():
    assert contrast_ratio("#ABCDEF", "#ABCDEF") == 1.0


def test_contrast_ratio_invalid_hex_returns_none():
    assert contrast_ratio("url(#grad)", "#FFFFFF") is None


def test_check_contrast_passes_high_contrast_text():
    out = check_contrast(_page('<text x="10" y="10" font-size="20" fill="#000000">清晰可读</text>'))
    assert out == []


def test_check_contrast_catches_low_contrast_small_text():
    # 浅灰 on 白底·小字号(<24px)走 4.5 门槛
    out = check_contrast(_page('<text x="10" y="10" font-size="16" fill="#F5F5F5">几乎看不见</text>'))
    assert any(i["rule"] == "low_contrast" for i in out)


def test_check_contrast_large_text_uses_lower_threshold():
    # 这个对比度~3.5：小字会被判不过(4.5)，大字(≥24px)按3.0门槛能过
    color = "#949494"
    small = check_contrast(_page(f'<text x="10" y="10" font-size="16" fill="{color}">x</text>'))
    large = check_contrast(_page(f'<text x="10" y="10" font-size="28" fill="{color}">x</text>'))
    assert any(i["rule"] == "low_contrast" for i in small)
    assert large == []


def test_check_contrast_skips_when_no_page_bg_found():
    # 没有画布同尺寸的 rect·不猜·跳过
    svg = '<svg viewBox="0 0 1280 720"><text font-size="16" fill="#FFFFFF">x</text></svg>'
    assert check_contrast(svg) == []


# ── 隐形文字检测（2026-07-01 yanjiu研究驱动评估🟢采纳·Instrumenta RGB欧氏距离<30）──
def test_invisible_text_near_identical_color_warns():
    # 背景#FFFFFF·文字#FDFDFD·欧氏距离≈3.46<30
    out = check_invisible_text(_page('<text x="10" y="10" font-size="16" fill="#FDFDFD">隐形</text>'))
    assert out and out[0]["rule"] == "invisible_text" and out[0]["sev"] == "warn"


def test_invisible_text_clearly_different_color_passes():
    assert check_invisible_text(_page('<text x="10" y="10" font-size="16" fill="#000000">正常</text>')) == []


def test_invisible_text_distinct_from_low_contrast():
    # #F5F5F5 vs #FFFFFF：欧氏距离≈17.3(<30·隐形) 但 WCAG 对比度也技术性过线附近——
    # 两条检查各判各的，不是同一条规则改名，允许同时命中
    svg = _page('<text x="10" y="10" font-size="16" fill="#F5F5F5">浅灰</text>')
    assert any(i["rule"] == "invisible_text" for i in check_invisible_text(svg))


def test_invisible_text_skips_when_no_page_bg_found():
    svg = '<svg viewBox="0 0 1280 720"><text font-size="16" fill="#FFFFFF">x</text></svg>'
    assert check_invisible_text(svg) == []


def test_invisible_text_no_fill_skipped():
    assert check_invisible_text(_page('<text x="10" y="10" font-size="16">无fill属性</text>')) == []


# ── H8 图片引用破损 ──
def test_broken_image_href_catches_empty():
    out = check_broken_image_href(_page('<image href="" width="10" height="10"/>'))
    assert any(i["rule"] == "broken_image_href" for i in out)


def test_broken_image_href_passes_valid_href():
    assert check_broken_image_href(_page('<image href="data:image/png;base64,abc" width="10" height="10"/>')) == []


# ── S6 CJK 字距过松 ──
def test_letter_spacing_clean_passes():
    out = check_letter_spacing(_page('<text font-size="20" letter-spacing="0.5" fill="#000">正常</text>'))
    assert out == []


def test_letter_spacing_catches_loose():
    # 2/20 = 10% > 5%
    out = check_letter_spacing(_page('<text font-size="20" letter-spacing="2" fill="#000">字距过松</text>'))
    assert any(i["rule"] == "loose_letter_spacing" for i in out)


def test_letter_spacing_negative_tracking_not_flagged():
    # 负字距是收紧不是放松·S6 只管"过松"
    out = check_letter_spacing(_page('<text font-size="28" letter-spacing="-0.3" fill="#000">收紧</text>'))
    assert out == []


# ── 对齐（Instrumenta 启发）──
def test_edge_alignment_exact_match_not_flagged():
    # 差值=0 视为已对齐，不报
    out = check_edge_alignment(_page(
        '<rect x="100" y="200" width="80" height="40" fill="#000"/>',
        '<rect x="100" y="300" width="80" height="40" fill="#000"/>',
    ))
    assert out == []


def test_edge_alignment_catches_near_miss_x():
    # 100 vs 102·差2px<=tol(3)·像没对准
    out = check_edge_alignment(_page(
        '<rect x="100" y="200" width="80" height="40" fill="#000"/>',
        '<rect x="102" y="300" width="80" height="40" fill="#000"/>',
    ))
    assert any(i["rule"] == "near_miss_alignment" and "x" in i["note"] for i in out)


def test_edge_alignment_ignores_intentional_offset():
    # 差值远大于 tol·视为有意错开·不报
    out = check_edge_alignment(_page(
        '<rect x="100" y="200" width="80" height="40" fill="#000"/>',
        '<rect x="250" y="300" width="80" height="40" fill="#000"/>',
    ))
    assert out == []


# ── 等距分布（Instrumenta 启发）──
def test_equal_distribution_evenly_spaced_passes():
    # 三张卡片·宽100·间距均40
    out = check_equal_distribution(_page(
        '<rect x="0" y="200" width="100" height="60" fill="#000"/>',
        '<rect x="140" y="200" width="100" height="60" fill="#000"/>',
        '<rect x="280" y="200" width="100" height="60" fill="#000"/>',
    ))
    assert out == []


def test_equal_distribution_catches_uneven_gaps():
    # 间距 40 vs 200·明显不均
    out = check_equal_distribution(_page(
        '<rect x="0" y="200" width="100" height="60" fill="#000"/>',
        '<rect x="140" y="200" width="100" height="60" fill="#000"/>',
        '<rect x="440" y="200" width="100" height="60" fill="#000"/>',
    ))
    assert any(i["rule"] == "uneven_distribution" for i in out)


def test_equal_distribution_needs_at_least_three():
    # 只有两个元素不构成"一排"·不判
    out = check_equal_distribution(_page(
        '<rect x="0" y="200" width="100" height="60" fill="#000"/>',
        '<rect x="500" y="200" width="100" height="60" fill="#000"/>',
    ))
    assert out == []


# ── 同尺寸（Instrumenta 启发）──
def test_uniform_size_exact_match_not_flagged():
    out = check_uniform_size(_page(
        '<rect x="0" y="200" width="100" height="60" fill="#000"/>',
        '<rect x="140" y="200" width="100" height="60" fill="#000"/>',
    ))
    assert out == []


def test_uniform_size_catches_near_miss_height():
    # 同一行·高度 60 vs 62·像没量准
    out = check_uniform_size(_page(
        '<rect x="0" y="200" width="100" height="60" fill="#000"/>',
        '<rect x="140" y="200" width="100" height="62" fill="#000"/>',
    ))
    assert any(i["rule"] == "near_miss_size" for i in out)


def test_uniform_size_ignores_clearly_different_sizes():
    # 高度 60 vs 200·明显是有意不同尺寸(如封面大卡+小标签)·不报
    out = check_uniform_size(_page(
        '<rect x="0" y="200" width="100" height="60" fill="#000"/>',
        '<rect x="140" y="200" width="100" height="200" fill="#000"/>',
    ))
    assert out == []


# ── 字号网格接生产链路（2026-07-01 yanjiu研究驱动评估：rules.check_font 此前零生产调用点）──
def test_font_grid_on_grid_size_passes():
    assert check_font_grid(_page('<text x="10" y="10" font-size="18">正文</text>')) == []


def test_font_grid_off_grid_size_warns():
    out = check_font_grid(_page('<text x="10" y="10" font-size="20">正文</text>'))
    assert any(i["rule"] == "font_off_grid" and i["sev"] == "warn" for i in out)


def test_font_grid_no_font_size_attr_skipped():
    assert check_font_grid(_page('<text x="10" y="10">无字号属性</text>')) == []


def test_font_grid_reports_each_occurrence_not_deduped():
    out = check_font_grid(_page(
        '<text x="10" y="10" font-size="20">甲</text>',
        '<text x="10" y="30" font-size="20">乙</text>',
    ))
    assert len(out) == 2  # 同一违规字号出现两处，各判各的，不去重


# ── 字号带单位解析（2026-07-02 saopan扫盘揪出：_num 对 "14px" 静默归0）──
def test_font_grid_px_unit_equivalent_to_bare_number():
    # "14px" 此前被 _num 归 0 → 报幽灵违规 got:0；修后 "14" 与 "14px" 完全等价（14 在网格·不报）
    assert check_font_grid(_page('<text x="10" y="10" font-size="14px">x</text>')) == []
    assert (check_font_grid(_page('<text x="10" y="10" font-size="20px">x</text>'))
            == check_font_grid(_page('<text x="10" y="10" font-size="20">x</text>')))


def test_font_grid_relative_unit_skipped_not_guessed():
    # em/% 没有绝对像素语义·跳过不瞎猜（此前 "1.2em"→0 也报幽灵违规）
    assert check_font_grid(_page('<text x="10" y="10" font-size="1.2em">x</text>')) == []
    assert check_font_grid(_page('<text x="10" y="10" font-size="120%">x</text>')) == []


def test_font_variety_px_unit_counted_as_real_size():
    # 此前 "44px"/"28px"… 全被 _num 归成同一种 0·种类数失真；修后按真实字号计数
    svg = _page(*[f'<text x="{i*10}" y="10" font-size="{s}px">x</text>'
                  for i, s in enumerate([44, 28, 24, 22, 18])])  # 5种·应报超限
    out = check_font_variety_per_page(svg)
    assert out and out[0]["got"] == 5


def test_check_contrast_px_unit_large_text_uses_lower_threshold():
    # "28px" 此前被 _num 归 0 → 大字被误按小字阈值 4.5 判；修后与裸 "28" 同走 3.0 门槛
    color = "#949494"  # 对比度~3.5：小字判不过(4.5)·大字(≥24px)过(3.0)
    assert check_contrast(_page(f'<text x="10" y="10" font-size="28px" fill="{color}">x</text>')) == []
    out = check_contrast(_page(f'<text x="10" y="10" font-size="16px" fill="{color}">x</text>'))
    assert any(i["rule"] == "low_contrast" for i in out)


# ── 单页字号种类数上限（2026-07-01 yanjiu研究驱动评估🟡走样需修·Instrumenta启发≤4）──
def test_font_variety_within_limit_passes():
    svg = _page(*[f'<text x="{i*10}" y="10" font-size="{s}">x</text>' for i, s in enumerate([44, 28, 24, 22])])
    assert check_font_variety_per_page(svg) == []


def test_font_variety_over_limit_warns():
    svg = _page(*[f'<text x="{i*10}" y="10" font-size="{s}">x</text>'
                  for i, s in enumerate([44, 28, 24, 22, 18])])  # 5种·超过默认上限4
    out = check_font_variety_per_page(svg)
    assert out and out[0]["rule"] == "font_variety_over_limit" and out[0]["sev"] == "warn"
    assert out[0]["got"] == 5


def test_font_variety_repeated_same_size_not_counted_twice():
    # 同一字号出现多次只算1种，不是按出现次数算
    svg = _page(*[f'<text x="{i*10}" y="10" font-size="16">x</text>' for i in range(10)])
    assert check_font_variety_per_page(svg) == []


def test_font_variety_custom_max_sizes():
    svg = _page(
        '<text x="0" y="10" font-size="44">a</text>',
        '<text x="0" y="30" font-size="28">b</text>',
    )
    assert check_font_variety_per_page(svg, max_sizes=1) != []
    assert check_font_variety_per_page(svg, max_sizes=2) == []


# ── 色盲友好配色检测（2026-07-01 yanjiu研究驱动评估🟢采纳·CVD模拟，联网核实DaltonLens等同类实现）──
def test_simulate_cvd_preserves_grayscale():
    # 三种矩阵每行系数和=1.0·灰阶(r=g=b)理论上应保持不变(色盲影响色相辨别·不影响明度感知)
    for kind in ("protanopia", "deuteranopia", "tritanopia"):
        assert _simulate_cvd((128, 128, 128), kind) == pytest.approx((128, 128, 128), abs=0.01)


def test_simulate_cvd_preserves_white_and_black():
    for kind in ("protanopia", "deuteranopia", "tritanopia"):
        assert _simulate_cvd((255, 255, 255), kind) == pytest.approx((255, 255, 255), abs=0.01)
        assert _simulate_cvd((0, 0, 0), kind) == pytest.approx((0, 0, 0), abs=0.01)


def test_colorblind_safe_flags_classic_red_green_pairs():
    # 2026-07-02 saopan扫盘揪出后重写：三对教科书等亮度红/绿混淆对——旧算法(WCAG亮度对比度
    # 门控+判定)下全 0 检出，因为正常视觉区分红绿靠色相不靠亮度、等亮度对被门控直接跳过。
    # 新算法(Machado 2009 线性模拟+sRGB距离)下三对模拟后距离实测 29.5/36.2/76.9，必须全检出。
    for a, b in [("#CC0000", "#009900"), ("#D62728", "#2CA02C"), ("#E74C3C", "#2ECC71")]:
        out = check_colorblind_safe({"red": a, "green": b})
        assert out and out[0]["rule"] == "colorblind_unsafe", f"{a}/{b} 应检出"
        assert "deuteranopia" in out[0]["cvd_type"], f"{a}/{b} 应命中 deuteranopia"


def test_colorblind_safe_one_problem_pair_reports_once():
    # 同一对问题色即使在多种 CVD 模拟下都混淆，也只报一条（逐 kind 各报会把一个问题刷成 2-3 条）
    out = check_colorblind_safe({"red": "#CC0000", "green": "#009900"})
    assert len(out) == 1


def test_colorblind_safe_high_luminance_gap_red_green_not_flagged():
    # 旧测试拿 #460917/#02FD5E 当"混淆对"——那是暗红vs荧光绿，亮度差巨大（正常sRGB距离263，
    # Machado 模拟后仍 274+），色盲者靠明度就能区分，不是真混淆对。旧算法拿亮度对比度当判据
    # 才把它判成"问题对"，恰暴露判据本末倒置。新算法下不报是正确行为，学理见
    # visual_review.check_colorblind_safe 文档注释。
    assert check_colorblind_safe({"a": "#460917", "b": "#02FD5E"}) == []


def test_colorblind_safe_blue_orange_safe_pair_not_flagged():
    # 蓝/橙是经典色盲安全对(matplotlib tab10 前两色)·模拟后距离仍近200·不得误报
    assert check_colorblind_safe({"blue": "#1F77B4", "orange": "#FF7F0E"}) == []


def test_colorblind_safe_skips_pair_already_close_in_normal_vision():
    # 正常视觉下已经很接近(非色盲特有问题)，不在这条检查范围内
    palette = {"a": "#F5F5F5", "b": "#FAFAFA"}
    assert check_colorblind_safe(palette) == []


def test_colorblind_safe_black_white_always_passes():
    # 灰阶不变性·黑白在任何CVD模拟下都应保持强对比
    assert check_colorblind_safe({"ink": "#000000", "bg": "#FFFFFF"}) == []


def test_colorblind_safe_single_color_no_pairs():
    assert check_colorblind_safe({"only": "#123456"}) == []


def test_colorblind_safe_invalid_hex_skipped_not_crashed():
    assert check_colorblind_safe({"a": "url(#gradient)", "b": "#000000"}) == []


# ── 视觉块计数+内容区使用率（2026-07-01 yanjiu研究驱动评估🟢采纳·02号页型手法L73·测量原语，
#    阈值来源薄弱不预置机检门，理由同 rules.py::check_field_budget）──
def test_count_visual_blocks_empty_page_is_zero():
    assert count_visual_blocks(_page()) == 0  # 只有整页背景rect·不算视觉块


def test_count_visual_blocks_counts_non_background_elements():
    svg = _page(
        '<rect x="10" y="10" width="100" height="50" fill="#000"/>',
        '<circle cx="50" cy="50" r="10" fill="#000"/>',
        '<image href="x.png" x="0" y="0" width="10" height="10"/>',
    )
    assert count_visual_blocks(svg) == 3


def test_count_visual_blocks_ignores_text():
    assert count_visual_blocks(_page('<text x="10" y="10" font-size="16">文字不算视觉块</text>')) == 0


def test_content_area_ratio_empty_page_is_zero():
    assert content_area_ratio(_page()) == 0.0


def test_content_area_ratio_half_canvas_rect():
    svg = _page('<rect x="0" y="0" width="640" height="720" fill="#000"/>')
    assert content_area_ratio(svg) == pytest.approx(0.5)


def test_content_area_ratio_avoids_double_counting_overlap():
    # 两个完全重叠的同尺寸rect·用网格并集不是面积求和，不应该翻倍
    svg = _page(
        '<rect x="0" y="0" width="640" height="720" fill="#000"/>',
        '<rect x="0" y="0" width="640" height="720" fill="#111"/>',
    )
    assert content_area_ratio(svg) == pytest.approx(0.5)


# ── 画布尺寸从 SVG 解析（2026-07-02 saopan扫盘揪出：out_of_canvas/_page_background 硬编码
#    1280x720，1920x1080 合法页整页误报越界、背景 rect 配不上导致 contrast/invisible_text 静默跳过）──
def _page_1080(*body: str) -> str:
    return ('<svg viewBox="0 0 1920 1080" xmlns="http://www.w3.org/2000/svg">'
            '<rect width="1920" height="1080" fill="#FFFFFF"/>' + "".join(body) + "</svg>")


def test_out_of_canvas_uses_declared_canvas_not_hardcoded():
    # 元素在 1920x1080 内、但超出写死的 1280x720——此前整片区域全是误报
    svg = _page_1080('<rect x="1500" y="800" width="200" height="100" fill="#000"/>')
    assert check_out_of_canvas(svg) == []
    # 真越界 1920x1080 的仍要报
    out = check_out_of_canvas(_page_1080('<rect x="1900" y="100" width="100" height="50" fill="#000"/>'))
    assert any(i["rule"] == "out_of_canvas" for i in out)


def test_page_background_found_on_1080p_canvas():
    # 1920x1080 的背景 rect 此前配不上"整页背景"→ contrast/invisible_text 静默失效
    low = _page_1080('<text x="10" y="10" font-size="16" fill="#F5F5F5">浅灰小字</text>')
    assert any(i["rule"] == "low_contrast" for i in check_contrast(low))
    assert any(i["rule"] == "invisible_text" for i in check_invisible_text(
        _page_1080('<text x="10" y="10" font-size="16" fill="#FDFDFD">隐形</text>')))


def test_canvas_fallback_when_svg_declares_nothing():
    # 根标签啥也没声明·退默认 1280x720（宁可有基准不瞎猜出一个）
    svg = ('<svg xmlns="http://www.w3.org/2000/svg">'
           '<rect x="1300" y="100" width="50" height="50" fill="#000"/></svg>')
    assert any(i["rule"] == "out_of_canvas" for i in check_out_of_canvas(svg))


# ── run_visual_gate 汇总 ──
def test_run_visual_gate_clean_page_passes():
    svg = _page('<text x="100" y="100" font-size="18" fill="#000000">干净的一页</text>')
    assert run_visual_gate(svg) == []


def test_run_visual_gate_aggregates_multiple_categories():
    # D18 FR1.5 改夹具注明理由：原夹具浅灰字锚点(10,10)恰好落在越界黑rect(-50..50,10..60)里，
    # 背景推断升级为"最近包含矩形"后被正确判定"浅字在黑底上清晰"不再误报——这正是本次升级
    # 要的行为。把文字挪到白色页面背景区(y=100)，low_contrast 依旧触发，测试聚合意图不变。
    svg = _page(
        '<rect x="-50" y="10" width="100" height="50" fill="#000"/>',
        '<text x="200" y="100" font-size="16" fill="#F5F5F5">浅色小字</text>',
        '<image href="" width="10" height="10"/>',
    )
    out = run_visual_gate(svg)
    rules = {i["rule"] for i in out}
    assert {"out_of_canvas", "low_contrast", "broken_image_href"} <= rules
    assert all(i["sev"] == "warn" for i in out)  # 全 warn·不阻断导出


# ── D18 FR1.5 背景推断升级：最近包含矩形（单层几何包含·不做透明度叠加合成）──
def test_contrast_white_text_on_dark_card_no_longer_false_positive():
    """第一轮实测病根抽象形态：深色卡片上的白字，旧逻辑拿整页白背景比出对比度1.0误报，
    新逻辑找到包含锚点的深色卡片 → 对比度充足不报。"""
    svg = _page('<rect x="600" y="200" width="500" height="280" fill="#0F3D2E"/>',
                '<text x="628" y="250" font-size="14" fill="#FFFFFF">深卡上的白字</text>')
    assert check_contrast(svg) == []
    assert check_invisible_text(svg) == []


def test_contrast_still_flags_genuinely_low_pair_on_card():
    """升级不放水：卡片底色与文字真低对比（深绿卡配深灰字）照报——消的是基准错位，不是消检查。"""
    svg = _page('<rect x="600" y="200" width="500" height="280" fill="#0F3D2E"/>',
                '<text x="628" y="250" font-size="14" fill="#33443C">深卡上的深字</text>')
    assert any(i["rule"] == "low_contrast" for i in check_contrast(svg))


def test_invisible_text_same_color_as_card_still_caught():
    """卡片同色字（真隐形）照抓——基准换成了卡片色，检查本身没被削弱。"""
    svg = _page('<rect x="600" y="200" width="500" height="280" fill="#0F3D2E"/>',
                '<text x="628" y="250" font-size="14" fill="#0F3D2E">卡片同色字</text>')
    assert any(i["rule"] == "invisible_text" for i in check_invisible_text(svg))


def test_text_outside_any_card_falls_back_to_page_background():
    """没有包含矩形 → 退回整页背景：白底白字这类真问题照报（旧检测面不丢）。"""
    svg = _page('<rect x="600" y="200" width="500" height="280" fill="#0F3D2E"/>',
                '<text x="100" y="600" font-size="14" fill="#FFFFFF">页面背景上的白字</text>')
    assert any(i["rule"] == "invisible_text" for i in check_invisible_text(svg))
    assert any(i["rule"] == "low_contrast" for i in check_contrast(svg))


def test_nested_rects_pick_smallest_enclosing():
    """嵌套场景选面积最小的包含矩形——大深色面板里嵌白色小徽章，徽章上的白字该按白徽章判（报），
    不是按外层深色面板判（漏）。"""
    svg = _page('<rect x="100" y="100" width="800" height="500" fill="#0F3D2E"/>',
                '<rect x="150" y="150" width="200" height="80" fill="#FFFFFF"/>',
                '<text x="160" y="180" font-size="14" fill="#FFFFFF">白徽章上的白字</text>')
    assert any(i["rule"] == "invisible_text" for i in check_invisible_text(svg))


def test_semi_transparent_cover_skipped_not_guessed():
    """边界声明落地（某品牌 page_22 实测形态·fill-opacity=0.55 色条上的白字）：
    半透明矩形的可见色是合成结果，单层推断算不准 → 该文字跳过，既不按声明色比（会漏报方向
    误判）也不退页面背景比（旧假阳性病根），宁可漏检不瞎猜。"""
    svg = _page('<rect x="329" y="260" width="191" height="90" fill="#0B6E4F" fill-opacity="0.55"/>',
                '<text x="343" y="300" font-size="14" fill="#FFFFFF">半透明条上的白字</text>')
    assert check_contrast(svg) == []
    assert check_invisible_text(svg) == []


def test_transformed_rect_not_used_as_background():
    """带 transform 的矩形定位不了真实落点，不当背景候选（同 H1 宁可漏检不瞎猜哲学）——
    锚点几何上落在其声明坐标内的文字退回页面背景判定。"""
    svg = _page('<rect x="100" y="100" width="400" height="200" fill="#0F3D2E" transform="rotate(90)"/>',
                '<text x="150" y="150" font-size="14" fill="#FFFFFF">白字</text>')
    assert any(i["rule"] == "invisible_text" for i in check_invisible_text(svg))  # 按白页面背景判


def test_chart_realized_line_missing_warns():
    """声明折线页却只有卡片矩形 → warn（第一轮实测"声明20种兑现0"的最小复现）。"""
    svg = _page('<rect x="90" y="200" width="400" height="200" fill="#0F3D2E"/>')
    out = check_chart_realized(svg, "line_compare")
    assert out and out[0]["rule"] == "chart_not_realized" and out[0]["sev"] == "warn"


def test_chart_realized_line_with_polyline_passes():
    svg = _page('<polyline points="100,300 300,200 500,260 700,150" fill="none" stroke="#0B6E4F"/>')
    assert check_chart_realized(svg, "line_compare") == []


def test_chart_realized_line_with_multi_segment_path_passes():
    svg = _page('<path d="M100 300 L300 200 L500 260 L700 150" stroke="#0B6E4F" fill="none"/>')
    assert check_chart_realized(svg, "line") == []


def test_chart_realized_line_straight_decoration_not_enough():
    """单段直线(M+单L)是分隔线装饰，不算折线图证据——d 须含曲线命令或多段折线。"""
    svg = _page('<path d="M90 400 L1190 400" stroke="#EEE"/>')
    assert check_chart_realized(svg, "line") != []


def test_chart_realized_bar_needs_two_differing_heights():
    same = _page('<rect x="100" y="300" width="60" height="200" fill="#0B6E4F"/>'
                 '<rect x="200" y="300" width="60" height="200" fill="#0B6E4F"/>')
    assert check_chart_realized(same, "bar_callout") != []  # 等高矩形是装饰卡不是柱
    bars = _page('<rect x="100" y="300" width="60" height="200" fill="#0B6E4F"/>'
                 '<rect x="200" y="380" width="60" height="120" fill="#0B6E4F"/>')
    assert check_chart_realized(bars, "bar_callout") == []


def test_chart_realized_funnel_polygon_passes_flat_cards_warn():
    poly = _page('<polygon points="200,100 800,100 700,200 300,200" fill="#0B6E4F"/>')
    assert check_chart_realized(poly, "aipl_funnel") == []
    flat = _page('<rect x="90" y="100" width="500" height="80" fill="#EEE"/>'
                 '<rect x="90" y="200" width="500" height="80" fill="#EEE"/>')
    assert check_chart_realized(flat, "funnel") != []


def test_chart_realized_donut_dasharray_or_arc_path():
    ring = _page('<circle cx="400" cy="360" r="120" fill="none" stroke="#0B6E4F" '
                 'stroke-width="40" stroke-dasharray="188 565"/>')
    assert check_chart_realized(ring, "donut") == []
    arc = _page('<path d="M400 240 A120 120 0 0 1 520 360" fill="#0B6E4F"/>')
    assert check_chart_realized(arc, "pie") == []
    plain = _page('<circle cx="400" cy="360" r="120" fill="#0B6E4F"/>')
    assert check_chart_realized(plain, "donut") != []  # 纯圆是装饰点不是环图


def test_chart_realized_map_paths_or_image():
    paths = _page('<path d="M1 1 C2 2 3 3 4 4Z"/><path d="M5 5 C6 6 7 7 8 8Z"/>'
                  '<path d="M9 9 C1 1 2 2 3 3Z"/>')
    assert check_chart_realized(paths, "expansion_map") == []
    img = _page('<image href="map.png" x="90" y="150" width="600" height="400"/>')
    assert check_chart_realized(img, "map") == []
    flat = _page('<rect x="90" y="150" width="600" height="400" fill="#EEE"/>')
    assert check_chart_realized(flat, "expansion_map") != []


def test_chart_realized_unknown_chart_not_checked():
    """未知 chart 名（映射表外）不查——宁漏勿噪，坏例子映射靠飞轮逐单积累。"""
    svg = _page('<rect x="90" y="200" width="400" height="200" fill="#0F3D2E"/>')
    assert check_chart_realized(svg, "quote_callout") == []
    assert check_chart_realized(svg, None) == []
    assert check_chart_realized(svg, "") == []


def test_aspect_ratio_16_9_viewbox_passes():
    assert check_aspect_ratio('<svg viewBox="0 0 1280 720"><rect/></svg>') == []


def test_aspect_ratio_4_3_width_height_passes():
    assert check_aspect_ratio('<svg width="1024" height="768"><rect/></svg>') == []


def test_aspect_ratio_off_is_flagged():
    out = check_aspect_ratio('<svg viewBox="0 0 1000 800"><rect/></svg>')
    assert len(out) == 1 and out[0]["rule"] == "aspect_ratio_off" and out[0]["sev"] == "warn"
    assert "16:9" in out[0]["note"]  # 报最接近的那个比例


def test_aspect_ratio_no_dimensions_is_skipped():
    assert check_aspect_ratio('<svg><rect/></svg>') == []  # 没画布尺寸信息·宁可漏检不瞎猜


def test_run_visual_gate_includes_aspect_ratio():
    svg = '<svg viewBox="0 0 1000 800" xmlns="http://www.w3.org/2000/svg"><rect width="1000" height="800" fill="#FFFFFF"/></svg>'
    assert any(i["rule"] == "aspect_ratio_off" for i in run_visual_gate(svg))


# ── 2026-07-03 二轮扫盘批B回归 ──────────────────────────────────────────────
def test_hex_to_rgb_supports_3_digit_shorthand():
    """批B-3：#fff 简写此前返回 None → 对比度/隐形文字检查静默漏检（#abc ≡ #aabbcc·
    CSS/SVG 同义·对照 spec_lock.py::_norm_hex 同款修法）。"""
    from reinforce.deck_rules.visual_review import _hex_to_rgb
    assert _hex_to_rgb("#fff") == (255, 255, 255)
    assert _hex_to_rgb("#abc") == (170, 187, 204)
    assert _hex_to_rgb("#ABC") == (170, 187, 204)
    # 非法输入仍拒（2位/渐变引用不瞎猜）
    assert _hex_to_rgb("#ff") is None and _hex_to_rgb("url(#g)") is None


def test_invisible_text_shorthand_fill_no_longer_missed():
    """批B-3：白底(#FFFFFF)上 fill="#fff" 的文字此前因简写解析失败被静默放行——现在照拦。"""
    out = check_invisible_text(_page('<text x="10" y="10" font-size="16" fill="#fff">隐形</text>'))
    assert any(i["rule"] == "invisible_text" for i in out)


def test_invisible_text_shorthand_distinct_color_still_passes():
    """批B-3 护栏：简写色解析后正常走判定——白底黑字(#000)不误报。"""
    assert check_invisible_text(_page('<text x="10" y="10" font-size="16" fill="#000">正常</text>')) == []


def test_aspect_ratio_comma_separated_viewbox_parsed():
    """批B-4：viewBox="0,0,1280,720" 逗号形态（SVG 规范合法）此前只按空白切、解析成 1 段
    整条检查静默跳过——改逗号+空白兼容（对照 _canvas_size/svg_compat.py 统一）后：
    16:9 照常放行，方形画布照常拦。"""
    assert check_aspect_ratio('<svg viewBox="0,0,1280,720"><rect/></svg>') == []
    assert check_aspect_ratio('<svg viewBox="0, 0, 1280, 720"><rect/></svg>') == []
    out = check_aspect_ratio('<svg viewBox="0,0,1000,1000"><rect/></svg>')
    assert out and out[0]["rule"] == "aspect_ratio_off"
