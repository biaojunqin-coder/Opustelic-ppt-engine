"""字体嵌入授权检查（2026-07-01 yanjiu研究驱动评估🟢采纳）。

出处：联网核实 OpenType/TrueType 标准 OS/2 表 fsType 位标志字段——0=可安装嵌入 / 2=限制授权
禁止嵌入 / 4=仅预览打印嵌入 / 8=可编辑嵌入，另有 0x0100 禁止子集化 / 0x0200 仅位图嵌入等附加位。
微软官方博客确认 Word/PowerPoint 等桌面应用会真实读取并遵守 fsType（区别于"浏览器普遍忽略
fsType"）——即 PowerPoint 生态本身认这个机制，直接适配本项目 PPTX 导出场景。

不依赖 fontTools（本项目对新依赖一贯审慎——同 Playwright"新依赖+本地渲染管线，代价/收益不成
比例"同一条决策逻辑；fsType 是 sfnt 表结构里一个固定偏移量的 2 字节字段，标准库 struct 直接
解析足够，没必要为读2个字节引入一整个字体处理库）：解析 sfnt Table Directory 找 "OS/2" 表
偏移，该表 version/xAvgCharWidth/usWeightClass/usWidthClass 各占2字节后即 fsType(2字节)。

适用场景：本项目当前制作纪律不嵌入自定义字体（SVG 走 spec_lock.font_family 声明字体名，
导出交给系统/PowerPoint 自带字体渲染）——这条检查是给未来做客户品牌字体嵌入时准备的零成本
硬门，不必等 PowerPoint 弹错误框才发现授权不允许嵌入。当前未接入任何生产调用链（没有嵌入
字体文件这个功能存在，接了也无处触发），是能力就绪、按需调用。
"""

from __future__ import annotations

import struct
from pathlib import Path

_OS2_TAG = b"OS/2"
_SFNT_SIGNATURES = (b"\x00\x01\x00\x00", b"OTTO", b"true", b"typ1")

# 按 OpenType spec OS/2.fsType 规范分档（出处：OpenType 规范 OS/2 表 fsType 字段，微软官方文档
# "OS/2 — OS/2 and Windows metrics table"）：
#   0x0000 可安装嵌入 / bit3(0x0008) 可编辑嵌入 → 都是 PPTX 嵌入的理想授权档，不报；
#   bit2(0x0004) 仅预览打印 / bit8(0x0100) 禁止子集化 / bit9(0x0200) 仅位图嵌入 → 可嵌入但有限制，warn；
#   bit1(0x0002) 限制性授权 → 未经字体所有者许可禁止嵌入，error（见 check_font_embeddable）。
# 2026-07-02 saopan扫盘揪出：此前 0x0008 也在 warn 表里——Arial/Times 等常用字体 fsType 实测恰=8，
# 常用字体全中招，警报稀释成背景噪音，真正该看的限制位反而没人看。
_FSTYPE_LABELS = {
    0x0004: "仅预览打印嵌入·嵌入后收件人只读不能编辑文档",
    0x0100: "禁止子集化·嵌入必须携带完整字体文件会显著变大",
    0x0200: "仅位图嵌入·只允许嵌入位图轮廓矢量信息丢失",
}
_FSTYPE_NOT_EMBEDDABLE = 0x0002


def read_font_fstype(font_path: str | Path) -> int | None:
    """读字体文件 OS/2 表的 fsType 位标志。返回 None：文件不是合法 sfnt 字体，或没有 OS/2 表
    （极老的纯 TrueType 字体可能没有）——读不到不等于"可以随便嵌入"，是"这条检查判不了"，
    调用方应视为未知而非放行。
    """
    try:
        data = Path(font_path).read_bytes()
    except OSError:
        return None
    if len(data) < 12 or data[0:4] not in _SFNT_SIGNATURES:
        return None
    num_tables = struct.unpack(">H", data[4:6])[0]
    table_dir_start = 12
    for i in range(num_tables):
        entry_start = table_dir_start + i * 16
        if entry_start + 16 > len(data):
            return None
        if data[entry_start:entry_start + 4] == _OS2_TAG:
            offset = struct.unpack(">I", data[entry_start + 8:entry_start + 12])[0]
            if offset + 10 > len(data):
                return None
            return struct.unpack(">H", data[offset + 8:offset + 10])[0]
    return None


def check_font_embeddable(font_path: str | Path) -> list[dict]:
    """fsType bit1(0x0002) 置位 = 限制授权禁止嵌入 → error（嵌入了也是违反字体授权协议，不是
    "技术上能不能嵌入"，是"授权允不允许这么做"）；bit2(仅预览打印)/bit8(禁止子集化)/bit9(仅
    位图嵌入) 附加限制 → warn（嵌入本身不违规，但有使用限制需要留意）；0x0000(可安装)与
    bit3(0x0008 可编辑嵌入)是理想授权档 → 不报。读不到 fsType（非法字体文件/缺OS/2表）→ warn
    提醒人工核实，不代填放行；TTC 集合容器单独给文案（是"本检查暂不支持"不是"文件非法"）。
    """
    fstype = read_font_fstype(font_path)
    if fstype is None:
        # 2026-07-02 saopan扫盘揪出：TTC(ttcf 集合容器)是完全合法的字体打包格式，此前一律
        # 文案"非合法字体文件"——把"本检查解析不了"错说成"文件有问题"，会误导人扔掉好字体。
        try:
            head = Path(font_path).read_bytes()[:4]
        except OSError:
            head = b""
        if head == b"ttcf":
            return [{"rule": "font_fstype_unknown", "sev": "warn",
                     "note": f"{font_path}：TTC 集合容器暂不支持解析 fsType·转人工确认嵌入授权"}]
        return [{"rule": "font_fstype_unknown", "sev": "warn",
                 "note": f"{font_path}：读不到 fsType(非合法字体文件或缺OS/2表)，"
                         f"无法确认嵌入授权，需人工核实"}]
    issues = []
    if fstype & _FSTYPE_NOT_EMBEDDABLE:
        issues.append({"rule": "font_not_embeddable", "sev": "error", "fstype": fstype,
                       "note": f"{font_path}：fsType={fstype:#06x} 含限制授权位(0x0002)，"
                               f"该字体禁止嵌入，不能用于 PPTX 导出打包"})
    for bit, label in _FSTYPE_LABELS.items():
        if fstype & bit:
            issues.append({"rule": "font_embed_restricted", "sev": "warn", "fstype": fstype,
                           "note": f"{font_path}：fsType={fstype:#06x} 含「{label}」限制位(bit={bit:#06x})"})
    return issues
