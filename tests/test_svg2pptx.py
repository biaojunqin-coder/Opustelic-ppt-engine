"""vendor SVG→pptx 引擎（ppt-master·MIT·D1）冒烟测试——验证导出原生可编辑 pptx（非图片）。

用 zipfile 解包验证 slide XML（绕 python-pptx 在 Python 3.14 的 shapes 读回 bug）。
"""

from __future__ import annotations

import zipfile

from engine.svg2pptx import export_deck

SVG = (
    '<svg viewBox="0 0 1280 720" xmlns="http://www.w3.org/2000/svg">'
    '<rect x="100" y="100" width="1080" height="520" rx="20" fill="#051C2C"/>'
    '<text x="640" y="380" font-family="Arial" font-size="48" fill="#ffffff" '
    'text-anchor="middle">收入增25%但成本翻倍</text></svg>'
)


def test_export_native_editable_pptx(tmp_path):
    svgf = tmp_path / "t.svg"
    svgf.write_text(SVG, encoding="utf-8")
    out = tmp_path / "t.pptx"

    assert export_deck([svgf], out)  # 默认 use_native_shapes=True
    assert out.exists() and out.stat().st_size > 0

    with zipfile.ZipFile(out) as z:
        xml = z.read("ppt/slides/slide1.xml").decode("utf-8")
    assert "收入增25%但成本翻倍" in xml   # 文字原生可编辑（在 <a:t> 里）
    assert "<p:pic>" not in xml           # 无图片栅格化（D1 质量基准）
    assert xml.count("<p:sp>") >= 1       # 有原生形状


# ── B2-13 回归（2026-07-02 saopan扫盘）：scalar 路径子级 translate 未乘父级 scale——
#    translate(10) scale(2) 内嵌 translate(100) 的 x=5 旧算 120，数学正确值 220 ──
def test_child_context_translate_scaled_by_parent():
    from engine.svg2pptx.svg_to_pptx.drawingml_context import ConvertContext
    from engine.svg2pptx.svg_to_pptx.drawingml_utils import ctx_x, ctx_y

    outer = ConvertContext().child(10, 20, 2.0, 3.0)   # translate(10,20) scale(2,3)
    inner = outer.child(100, 100, 1.0, 1.0)            # 嵌套 translate(100,100)
    # 不变量 x_abs = x*scale + translate（ctx_x）：复合后 translate = 10 + 2*100 = 210
    assert inner.translate_x == 210 and inner.scale_x == 2.0
    assert inner.translate_y == 320 and inner.scale_y == 3.0   # y 同理：20 + 3*100
    assert ctx_x(5, inner) == 220    # 旧版这里算出 120（漏乘父 scale 的确诊值）
    assert ctx_y(0, inner) == 320


def test_nested_translate_scale_equals_flattened_transform_end_to_end():
    # 端到端走 convert_g 的 scalar 路径（组里有 <text> 就进不了 matrix 路径）。
    # 数学恒等式：translate(10)∘scale(2)∘translate(100) ≡ translate(210)∘scale(2)——
    # 两种写法必须产出逐字节相同的文本框 XML（不依赖字体度量/内边距，只考 translate 复合）。
    # 旧版嵌套写法把内层 translate(100) 少乘了父 scale(2)，两者会差出 100px。
    from xml.etree import ElementTree as ET
    from engine.svg2pptx.svg_to_pptx.drawingml_context import ConvertContext
    from engine.svg2pptx.svg_to_pptx.drawingml_converter import convert_element

    def _convert(svg: str) -> str:
        root = ET.fromstring(f'<svg xmlns="http://www.w3.org/2000/svg">{svg}</svg>')
        result = convert_element(root[0], ConvertContext())
        assert result is not None
        return result.xml

    nested = _convert('<g transform="translate(10) scale(2)"><g transform="translate(100)">'
                      '<text x="5" y="10" font-size="12">X</text></g></g>')
    flat = _convert('<g transform="translate(210) scale(2)">'
                    '<text x="5" y="10" font-size="12">X</text></g>')
    assert nested == flat


# ── B2-14 回归（2026-07-02 saopan扫盘）：rotate pivot 补偿漏乘祖先 scale（与 B2-13 同型病）——
#    scale(2) 组里 rotate(θ,100,100) 的 pivot 在 slide 上是 200px，旧版按 100px 补偿、整组错位。
#    用 90°（180° 的矩阵 b=c=0 会被 parse_transform 分解成 flip、走不到 pivot 补偿路径）──
def test_rotate_pivot_compensation_honours_ancestor_scale():
    import re
    from xml.etree import ElementTree as ET
    from engine.svg2pptx.svg_to_pptx.drawingml_context import ConvertContext
    from engine.svg2pptx.svg_to_pptx.drawingml_converter import convert_element
    from engine.svg2pptx.svg_to_pptx.drawingml_utils import EMU_PER_PX

    # 组里有 <text> → 走不了 matrix 路径 → 触发 grpSp rot + pivot 补偿这条 fallback
    root = ET.fromstring(
        '<svg xmlns="http://www.w3.org/2000/svg">'
        '<g transform="scale(2)"><g transform="rotate(90 100 100)">'
        '<rect x="60" y="80" width="40" height="20" fill="#111111"/>'
        '<text x="60" y="120" font-size="12">L</text>'
        '</g></g></svg>')
    result = convert_element(root[0], ConvertContext())
    assert result is not None and '<p:grpSp>' in result.xml

    def _attr(pattern: str) -> float:
        return float(re.search(pattern, result.xml).group(1))

    off_x, off_y = _attr(r'<a:off x="(-?\d+)"'), _attr(r'<a:off [^/]*y="(-?\d+)"')
    ch_x, ch_y = _attr(r'<a:chOff x="(-?\d+)"'), _attr(r'<a:chOff [^/]*y="(-?\d+)"')
    ch_w, ch_h = _attr(r'<a:chExt cx="(-?\d+)"'), _attr(r'<a:chExt [^/]*cy="(-?\d+)"')
    assert _attr(r'rot="(-?\d+)"') == 90 * 60000  # grpSp 确实带上了 90° 旋转

    # 90° 补偿的封闭式（converter 的 delta 公式代入 cos=0/sin=1）：
    #   off_x−chOff_x = (px−bcx) + (py−bcy)；off_y−chOff_y = −(px−bcx) + (py−bcy)
    # 联立反解出转换器真实用的 pivot（bbox 中心从输出读回·不依赖 text 字体度量）
    bcx, bcy = ch_x + ch_w / 2, ch_y + ch_h / 2
    A, B = off_x - ch_x, off_y - ch_y
    pivot_x_used = bcx + (A - B) / 2
    pivot_y_used = bcy + (A + B) / 2
    expect = 100 * 2 * EMU_PER_PX  # pivot(100,100)×祖先scale(2) = slide 上 200px
    assert abs(pivot_x_used - expect) <= 3 * EMU_PER_PX  # 旧版会算成 100px·差一半
    assert abs(pivot_y_used - expect) <= 3 * EMU_PER_PX
