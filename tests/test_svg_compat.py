"""SVG→PPTX 导出兼容性机检测试（提炼自 ppt-master shared-standards.md·真实风险项补课）。"""

from __future__ import annotations

from pathlib import Path

from reinforce.deck_rules.svg_compat import check_svg_compat, check_viewbox_consistency


def test_clean_svg_passes():
    svg = '<svg><rect fill="#FFFFFF"/><text fill="#111111" fill-opacity="0.5">hi</text></svg>'
    assert check_svg_compat(svg) == []


def test_catches_rgba():
    out = check_svg_compat('<svg><rect fill="rgba(255,255,255,0.1)"/></svg>')
    assert any(i["rule"] == "svg_incompat_syntax" and "rgba" in i["note"] for i in out)


def test_catches_group_opacity():
    out = check_svg_compat('<svg><g opacity="0.2"><rect/></g></svg>')
    assert any("opacity" in i["note"] for i in out)


# ── <g fill-opacity> 误杀（2026-07-02 saopan扫盘揪出：\bopacity 的词边界在 fill-opacity
#    的 "-o" 处成立·官方推荐替代写法被自家 error 门拦）──
def test_g_fill_opacity_is_the_recommended_fix_not_flagged():
    # fill-opacity 恰是本条规则 fix 文案推荐的替代写法·绝不能被同一条规则误杀
    svg = '<svg><g fill="#FFFFFF" fill-opacity="0.92"><text x="1" y="1">x</text></g></svg>'
    assert not any(i["rule"] == "svg_incompat_syntax" for i in check_svg_compat(svg))
    svg2 = '<svg><g stroke="#000000" stroke-opacity="0.5"><rect/></g></svg>'
    assert not any(i["rule"] == "svg_incompat_syntax" for i in check_svg_compat(svg2))


def test_g_true_opacity_still_flagged_even_with_other_attrs():
    # 真正的 <g opacity=> 混在其他属性中间仍要逮住（负向后顾只排除 fill-/stroke- 前缀）
    out = check_svg_compat('<svg><g id="grp" fill="#FFF" opacity="0.5"><rect/></g></svg>')
    assert any(i["rule"] == "svg_incompat_syntax" and "<g opacity=>" in i["note"] for i in out)


def test_image_fill_opacity_not_flagged_but_true_opacity_is():
    # <image> 那条同一病根同一修法
    ok = check_svg_compat('<svg><image href="x.png" fill-opacity="0.3"/></svg>')
    assert not any("image opacity" in i["note"] for i in ok)
    bad = check_svg_compat('<svg><image href="x.png" opacity="0.3"/></svg>')
    assert any("image opacity" in i["note"] for i in bad)


def test_real_pyramid_template_not_killed_by_fill_opacity():
    # 项目自带模板(含 <g ... fill-opacity="0.92">)实测曾被误拦——真实生产样本当回归夹具
    tpl = Path(__file__).resolve().parent.parent / "engine/ppt_master/templates/charts/pyramid_isometric.svg"
    out = check_svg_compat(tpl.read_text(encoding="utf-8"))
    assert not any("<g opacity=>" in i["note"] for i in out)


def test_catches_image_opacity():
    out = check_svg_compat('<svg><image href="x.png" opacity="0.3"/></svg>')
    assert any("image opacity" in i["note"] for i in out)


def test_catches_style_tag():
    out = check_svg_compat('<svg><style>.a{fill:red}</style></svg>')
    assert any(i["rule"] == "svg_banned_feature" and "<style>" in i["note"] for i in out)


def test_catches_class_attr():
    out = check_svg_compat('<svg><rect class="foo"/></svg>')
    assert any("class" in i["note"] for i in out)


def test_catches_mask_symbol_textpath_script():
    for bad in ['<mask id="m">', '<symbol id="s">', 'textPath', '<script>alert(1)</script>']:
        out = check_svg_compat(f'<svg>{bad}</svg>')
        assert out, f"应逮住：{bad}"


def test_catches_bare_ampersand():
    out = check_svg_compat('<svg><text>R&D 部门</text></svg>')
    assert any(i["rule"] == "svg_unescaped_xml" for i in out)


def test_allows_legal_xml_entities():
    svg = '<svg><text>R&amp;D &lt;test&gt; &#160;</text></svg>'
    assert not any(i["rule"] == "svg_unescaped_xml" for i in check_svg_compat(svg))


def test_multiple_violations_all_caught():
    svg = '<svg><style>.a{}</style><rect class="x" fill="rgba(0,0,0,0.5)"/></svg>'
    out = check_svg_compat(svg)
    assert len(out) >= 3


def test_banned_features_case_insensitive_variants_caught():
    """2026-07-03 二轮扫盘批D：黑名单此前大小写敏感——<MASK>/<Style>/CLASS=/RGBA( 变体漏检
    （转换引擎不认这些写法·大小写变了照样导出损坏）。改 IGNORECASE 后一律拦。"""
    for bad, rule in [('<MASK id="m">', "svg_banned_feature"),
                      ("<Style>.a{fill:red}</Style>", "svg_banned_feature"),
                      ('<rect CLASS="foo"/>', "svg_banned_feature"),
                      ('<text><textpath href="#p">x</textpath></text>', "svg_banned_feature"),
                      ("@FONT-FACE{}", "svg_banned_feature"),
                      ('<rect fill="RGBA(0,0,0,0.5)"/>', "svg_incompat_syntax")]:
        out = check_svg_compat(f"<svg>{bad}</svg>")
        assert any(i["rule"] == rule for i in out), f"大小写变体漏检：{bad}"


def test_uppercase_entity_still_counts_as_bare_ampersand():
    """IGNORECASE 只放宽黑名单，不放宽合法实体白名单——&AMP; 不是合法 XML 实体，仍按裸 & 拦。"""
    out = check_svg_compat("<svg><text>R&AMP;D</text></svg>")
    assert any(i["rule"] == "svg_unescaped_xml" for i in out)


# ── viewBox 一致性（2026-07-01 yanjiu研究驱动评估🟢采纳·出处 ppt-master svg_quality_checker.py）──
def test_viewbox_matching_width_height_passes():
    assert check_viewbox_consistency('<svg viewBox="0 0 1280 720" width="1280" height="720"/>') == []


def test_viewbox_only_no_width_height_passes():
    assert check_viewbox_consistency('<svg viewBox="0 0 1280 720"/>') == []  # 只声明viewBox是常规写法


def test_neither_viewbox_nor_wh_skipped():
    assert check_viewbox_consistency('<svg><rect/></svg>') == []  # 还没到画布尺寸这步·不瞎猜


def test_width_height_without_viewbox_flagged():
    out = check_viewbox_consistency('<svg width="1280" height="720"/>')
    assert out and out[0]["rule"] == "svg_viewbox_missing" and out[0]["sev"] == "error"


def test_width_height_mismatch_viewbox_flagged():
    out = check_viewbox_consistency('<svg viewBox="0 0 1280 720" width="1000" height="600"/>')
    assert out and out[0]["rule"] == "svg_viewbox_mismatch"


def test_width_height_within_tolerance_passes():
    # 1280*1.01=1292.8·2%容差内
    assert check_viewbox_consistency('<svg viewBox="0 0 1280 720" width="1290" height="720"/>') == []


def test_viewbox_malformed_flagged():
    out = check_viewbox_consistency('<svg viewBox="0 0 1280" width="1280" height="720"/>')
    assert out and out[0]["rule"] == "svg_viewbox_malformed"


def test_percentage_width_height_skipped():
    # width/height 带单位不是纯数字，跳过不瞎猜(该场景不常见但不该崩)
    assert check_viewbox_consistency('<svg viewBox="0 0 1280 720" width="100%" height="100%"/>') == []


def test_check_svg_compat_includes_viewbox_check():
    out = check_svg_compat('<svg viewBox="0 0 1280 720" width="1000" height="600"><rect/></svg>')
    assert any(i["rule"] == "svg_viewbox_mismatch" for i in out)


# ── 单引号属性/逗号分隔 viewBox（2026-07-02 saopan扫盘揪出：属性正则只认双引号·
#    数值只按空白切——两种 SVG 规范合法写法被误报 error）──
def test_viewbox_single_quoted_attrs_recognized():
    assert check_viewbox_consistency("<svg viewBox='0 0 1280 720' width='1280' height='720'/>") == []


def test_viewbox_comma_separated_numbers_valid():
    # SVG 规范：viewBox 列表允许 comma-or-space 分隔
    assert check_viewbox_consistency('<svg viewBox="0,0,1280,720" width="1280" height="720"/>') == []
    assert check_viewbox_consistency('<svg viewBox="0, 0, 1280, 720" width="1280" height="720"/>') == []


def test_viewbox_single_quote_mismatch_still_flagged():
    # 单引号写法解析出来后·数值对不上照样要拦（支持单引号≠放松检查）
    out = check_viewbox_consistency("<svg viewBox='0 0 1280 720' width='1000' height='600'/>")
    assert out and out[0]["rule"] == "svg_viewbox_mismatch"
