"""字体嵌入授权检查测试（2026-07-01 yanjiu研究驱动评估🟢采纳·OS/2表fsType位标志）。

构造最小合法 sfnt 二进制(header + 1条OS/2表目录 + OS/2表体)当测试夹具——不依赖系统真实字体
文件是否存在，跨机器/CI 稳定可复现。
"""

from __future__ import annotations

import struct

from reinforce.deck_rules.font_embed import check_font_embeddable, read_font_fstype


def _fake_font(fstype: int | None) -> bytes:
    header = b"\x00\x01\x00\x00" + struct.pack(">HHHH", 1, 0, 0, 0)  # sfnt版本 + numTables=1 + 占位
    os2_offset = 12 + 16  # header(12) + 1条表目录(16)
    table_entry = b"OS/2" + struct.pack(">III", 0, os2_offset, 10)  # tag+checksum+offset+length
    os2_body = struct.pack(">HHHH", 0, 0, 0, 0)  # version/xAvgCharWidth/usWeightClass/usWidthClass
    if fstype is not None:
        os2_body += struct.pack(">H", fstype)
    return header + table_entry + os2_body


def test_read_fstype_installable(tmp_path):
    p = tmp_path / "a.ttf"
    p.write_bytes(_fake_font(0x0000))
    assert read_font_fstype(p) == 0


def test_read_fstype_restricted(tmp_path):
    p = tmp_path / "b.ttf"
    p.write_bytes(_fake_font(0x0002))
    assert read_font_fstype(p) == 0x0002


def test_read_fstype_not_sfnt_returns_none(tmp_path):
    p = tmp_path / "not_a_font.ttf"
    p.write_bytes(b"this is not a font file at all")
    assert read_font_fstype(p) is None


def test_read_fstype_missing_file_returns_none(tmp_path):
    assert read_font_fstype(tmp_path / "does_not_exist.ttf") is None


def test_read_fstype_no_os2_table_returns_none(tmp_path):
    # 合法 sfnt 头但 numTables=0(没有任何表，包括 OS/2)
    p = tmp_path / "no_os2.ttf"
    p.write_bytes(b"\x00\x01\x00\x00" + struct.pack(">HHHH", 0, 0, 0, 0))
    assert read_font_fstype(p) is None


def test_check_font_embeddable_installable_passes(tmp_path):
    p = tmp_path / "free.ttf"
    p.write_bytes(_fake_font(0x0000))
    assert check_font_embeddable(p) == []


def test_check_font_embeddable_restricted_is_error(tmp_path):
    p = tmp_path / "restricted.ttf"
    p.write_bytes(_fake_font(0x0002))
    out = check_font_embeddable(p)
    assert any(i["rule"] == "font_not_embeddable" and i["sev"] == "error" for i in out)


def test_check_font_embeddable_preview_print_only_is_warn(tmp_path):
    p = tmp_path / "preview.ttf"
    p.write_bytes(_fake_font(0x0004))
    out = check_font_embeddable(p)
    assert any(i["rule"] == "font_embed_restricted" and i["sev"] == "warn" for i in out)
    assert not any(i["rule"] == "font_not_embeddable" for i in out)  # 0x0004≠0x0002·不是禁止嵌入


def test_check_font_embeddable_no_subsetting_flagged(tmp_path):
    p = tmp_path / "no_subset.ttf"
    p.write_bytes(_fake_font(0x0100))
    out = check_font_embeddable(p)
    assert any(i["rule"] == "font_embed_restricted" and "子集化" in i["note"] for i in out)


def test_check_font_embeddable_editable_embedding_not_flagged(tmp_path):
    """2026-07-02 saopan扫盘揪出：fsType=8(bit3·可编辑嵌入)此前也进 warn 表——实测 Arial/Times
    等常用字体全是 8，这是 OpenType 规范里 PPTX 嵌入的理想授权档(OpenType spec OS/2.fsType)，
    常用字体全体报警=信号稀释成噪音。0 和 8 都必须干干净净不报。"""
    p = tmp_path / "editable.ttf"
    p.write_bytes(_fake_font(0x0008))
    assert check_font_embeddable(p) == []


def test_check_font_embeddable_multiple_restriction_bits(tmp_path):
    # 2026-07-02 改断言：旧断言期待 0x0008|0x0100 报 2 条——锁的是"0x0008(可编辑嵌入)也 warn"
    # 的错误行为(B1-9 病根本身)。0x0008 是理想授权档不报，只有 0x0100(禁止子集化)该报，共 1 条。
    p = tmp_path / "multi.ttf"
    p.write_bytes(_fake_font(0x0008 | 0x0100))  # 可编辑嵌入(不报) + 禁止子集化(warn)
    out = check_font_embeddable(p)
    rules = [i["rule"] for i in out]
    assert rules.count("font_embed_restricted") == 1
    assert "font_not_embeddable" not in rules


def test_check_font_embeddable_preview_print_note_says_readonly(tmp_path):
    """bit2(0x0004) 的 warn 文案必须讲清后果——嵌入后收件人打开是只读，不是泛泛"有限制"。"""
    p = tmp_path / "preview2.ttf"
    p.write_bytes(_fake_font(0x0004))
    out = check_font_embeddable(p)
    assert any("只读" in i["note"] for i in out)


def test_check_font_embeddable_ttc_gets_dedicated_note(tmp_path):
    """2026-07-02 saopan扫盘揪出：TTC(ttcf 集合容器)是合法字体格式，此前文案一律"非合法字体文件"
    ——把"本检查暂不支持解析"错说成"文件有问题"。TTC 单独给"转人工确认"文案。"""
    p = tmp_path / "collection.ttc"
    p.write_bytes(b"ttcf" + b"\x00" * 28)
    out = check_font_embeddable(p)
    assert out and out[0]["rule"] == "font_fstype_unknown" and out[0]["sev"] == "warn"
    assert "TTC" in out[0]["note"] and "人工" in out[0]["note"]
    assert "非合法字体文件" not in out[0]["note"]


def test_check_font_embeddable_unreadable_file_warns(tmp_path):
    p = tmp_path / "garbage.ttf"
    p.write_bytes(b"garbage not a font")
    out = check_font_embeddable(p)
    assert out and out[0]["rule"] == "font_fstype_unknown" and out[0]["sev"] == "warn"
