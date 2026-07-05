"""SVG 排版安全网测试——焦点数字封顶 / 自动换行 / 引用卡声明式渲染。"""

from __future__ import annotations

import re
from xml.etree import ElementTree as ET

import pytest

from engine.svg_layout import hero_text, source_card_from_evidence, text_block, wrap_text


def _parse_fragment(fragment: str) -> ET.Element:
    """SVG 片段包上根元素解析——非法 XML 直接抛 ParseError（转义回归测试的硬判据）。"""
    return ET.fromstring(f"<svg>{fragment}</svg>")


def test_wrap_text_splits_by_chars():
    assert wrap_text("一二三四五六七", 3) == ["一二三", "四五六", "七"]


def test_wrap_text_empty():
    assert wrap_text("", 10) == [""]


def test_hero_text_short_data_uses_max_size():
    svg = hero_text(90, 430, "9700亿元")
    assert 'font-size="130"' in svg


def test_hero_text_never_exceeds_max_size():
    # 真实踩过的坑：早期公式漏 min() 封顶·10字符串曾算出177px。这里锁死永不超 130。
    svg = hero_text(90, 430, "1837.78万人次")
    assert 'font-size="130"' in svg
    assert "font-size=\"1" not in svg.replace('font-size="130"', "")  # 排除掉130后不该有任何"1xx"以上


def test_hero_text_long_data_shrinks_below_max():
    svg = hero_text(90, 430, "这是一段非常非常非常长的焦点数字描述文本超过二十个字符")
    import re
    size = int(re.search(r'font-size="(\d+)"', svg).group(1))
    assert size < 130


def test_text_block_multiline():
    svg = text_block(0, 0, "一二三四五六", 20, 3)
    assert svg.count("<text") == 2  # 6字按3字/行拆成2行


def test_source_card_from_evidence_complete():
    ev = {"source_title": "标题", "source_outlet": "媒体", "source_date": "2026-01-01",
          "source_quote": "引述", "source_url": "example.com"}
    svg = source_card_from_evidence(0, 0, 480, 150, ev)
    assert svg is not None and "引用卡" in svg and "example.com" in svg


def test_source_card_from_evidence_missing_fields_returns_none():
    assert source_card_from_evidence(0, 0, 480, 150, {"dim": "x", "data": "y"}) is None


# ── B2-4 回归（2026-07-02 saopan扫盘）：不做 XML 转义 → 「M&A」直接产非法 XML，
#    而 SKILL 强制"必须用 svg_layout"+svg_compat 拦裸 &，含 &/< 的文本此前没有任何合法路径 ──
def test_text_block_escapes_ampersand_and_lt():
    svg = text_block(10, 20, "M&A 交易额 <10亿", 14, 20)
    root = _parse_fragment(svg)  # 能解析 = 转义正确（旧版这里直接 ParseError）
    assert root[0].text == "M&A 交易额 <10亿"  # 解析回来还是原文·没双重转义


def test_text_block_escapes_each_wrapped_line():
    # 换行按原始字符数（&amp; 是 5 个字符·先转义再换行会把行宽算歪）——3字/行拆两行后逐行转义
    svg = text_block(0, 0, "A&B下一行", 12, 3)
    root = _parse_fragment(svg)
    assert [t.text for t in root] == ["A&B", "下一行"]


def test_hero_text_escapes_xml_specials():
    svg = hero_text(90, 430, "P&G <50亿")
    assert _parse_fragment(svg)[0].text == "P&G <50亿"


def test_source_card_escapes_url_with_query_params():
    ev = {"source_title": "标题<里带尖括号>", "source_outlet": "媒体&周刊", "source_date": "2026-01-01",
          "source_quote": "引述", "source_url": "example.com/a?x=1&y=2"}
    svg = source_card_from_evidence(0, 0, 480, 150, ev)
    texts = [t.text for t in _parse_fragment(svg).iter("text")]
    assert "example.com/a?x=1&y=2" in texts        # URL 带 query 的 & 不再产非法 XML
    assert any("媒体&周刊" in (t or "") for t in texts)


# ── B2-5 回归（2026-07-02 saopan扫盘）：min_size=40 下限让超长文本仍溢出 max_w（60字→1392px>1100），
#    违背 docstring「防溢出」——按项目 fail-closed 风格改 raise，hero 文案过长是设计错误别帮着藏 ──
def test_hero_text_overlong_raises_instead_of_overflowing():
    with pytest.raises(ValueError, match="hero 文案过长"):
        hero_text(90, 430, "这" * 60)


def test_hero_text_at_fit_boundary_still_renders():
    # max_w=1100/min_size=40：临界约 1100/(40*0.58)=47.4 字——47 字还放得下（size=40 恰好贴 max_w）
    svg = hero_text(90, 430, "字" * 47)
    size = int(re.search(r'font-size="(\d+)"', svg).group(1))
    assert size == 40
    with pytest.raises(ValueError):
        hero_text(90, 430, "字" * 48)  # 48 字就得 raise·边界另一侧
