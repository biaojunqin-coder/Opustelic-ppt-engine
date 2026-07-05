"""SVG 排版安全网——自动换行 / 焦点数字自动缩字号 / 引用卡片。任何 deck 的 SVG 生成都该用这层，不重新发明。

来源：Descente 实战暴露的真实排版 bug（长文本塞进巨字号槽必然溢出画布·见 _hero_text 的 130px 封顶教训）。
对应制作工作流 SKILL「页面展示整组证据」规范——展示证据不能让文字溢出，这层是机制保障，不是凭手感画对。

2026-07-02 saopan扫盘揪出：本层此前不做 XML 转义——文本含 &/</>（如「M&A 交易额 <10亿」）直接拼进
<text> 产出非法 XML；而 SKILL 强制"必须用 svg_layout"+svg_compat 又拦裸 &，等于这类文本没有任何合法
路径。现在所有落进 SVG 的文本统一走 `xml.sax.saxutils.escape`（调用方一律传**原始文本**，别自己
预转义，否则会双重转义成 &amp;amp;）。
"""

from __future__ import annotations

from xml.sax.saxutils import escape


def wrap_text(text: str, max_chars: int) -> list[str]:
    """按字数把文本拆行（CJK 近似等宽·简单可靠·防长文本溢出画布）。"""
    text = text or ""
    return [text[i:i + max_chars] for i in range(0, len(text), max_chars)] or [""]


def text_block(x: int, y: int, text: str, size: int, max_chars: int, *,
               fill: str = "#111111", weight: str = "normal", line_h: int | None = None,
               anchor: str = "start") -> str:
    """多行文本块（自动换行·防溢出）。line_h 默认按字号 1.25 倍。文本自动做 XML 转义。"""
    line_h = line_h or int(size * 1.25)
    # 先按原始字符数换行、再逐行转义——反过来的话 &amp; 占 5 个字符会把字数换行算歪
    lines = wrap_text(text, max_chars)
    fw = f' font-weight="{weight}"' if weight != "normal" else ""
    ta = f' text-anchor="{anchor}"' if anchor != "start" else ""
    return "".join(
        f'<text x="{x}" y="{y + i * line_h}" font-family="Arial" font-size="{size}" fill="{fill}"{fw}{ta}>{escape(ln)}</text>'
        for i, ln in enumerate(lines))


def hero_text(x: int, y: int, data: str, *, max_w: int = 1100, max_size: int = 130,
             min_size: int = 40, fill: str = "#E2231A") -> str:
    """焦点数字：按字数自动缩字号·max_size 是硬上限不是基准值。文本自动做 XML 转义。

    ⚠️ 真实踩过的坑：早期版本公式漏了 min(max_size, …) 封顶，短字符串（10字）反而算出
    177px（比上限还大）。这里的 min() 调用就是那个教训——改这个函数前先想清楚这条。

    2026-07-02 saopan扫盘揪出：min_size=40 下限使超长文本（如 60 字→1392px）仍溢出 max_w，
    违背 docstring「防溢出」承诺。按项目 fail-closed 风格改成 raise——hero 是焦点数字位，
    文案超 ~30 字本身就是设计错误，静默缩小成普通字号只会把设计错误藏起来。
    """
    n = max(len(data or ""), 1)
    raw = max_w / n / 0.58
    if raw < min_size:
        max_chars = int(max_w / (min_size * 0.58))
        raise ValueError(
            f"hero 文案过长（{n} 字）——min_size={min_size}px 下 max_w={max_w}px 最多容纳约 {max_chars} 字。"
            f"hero 是焦点数字位，请精简文案（建议 30 字内），长段落改用 text_block")
    size = min(max_size, int(raw))
    return f'<text x="{x}" y="{y}" font-family="Arial" font-size="{size}" font-weight="bold" fill="{fill}">{escape(data)}</text>'


def source_card(x: int, y: int, w: int, h: int, *, title: str, outlet: str, date: str,
                quote: str, url: str) -> str:
    """引用卡片：标题/媒体/日期/原文片段/URL——清楚标"引用卡"，不冒充截图（防误导）。

    ⚠️ 内容必须是真实核验过的（亲自打开源网页确认），不能编造——这条和数字溯源同一条铁律。
    像素级网页截图当前环境做不到（截图存前端层·Bash 访问不到那个文件系统），引用卡是替代方案。
    """
    # 2026-07-02 saopan扫盘揪出：outlet/date/url 三处直拼 <text> 不走 text_block，含 &/< 时产非法 XML
    # （URL 带 query 参数天然含 &）——title/quote 走 text_block 已在里面转义，这三处补 escape。
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="#FFFFFF" stroke="#D8D6D0" stroke-width="1.5"/>'
        f'<rect x="{x}" y="{y}" width="{w}" height="24" rx="8" fill="#F2F1EE"/>'
        f'<text x="{x + 13}" y="{y + 16}" font-family="Arial" font-size="11" fill="#8A8A8A">🔗 引用卡 · 已核验源网页</text>'
        + text_block(x + 13, y + 46, title, 14, max(20, w // 9), fill="#111111", weight="bold", line_h=18)
        + f'<text x="{x + 13}" y="{y + 86}" font-family="Arial" font-size="11" fill="#A32D2D">{escape(outlet)} · {escape(date)}</text>'
        + text_block(x + 13, y + 108, f'"{quote}"', 11, max(24, w // 7), fill="#8A8A8A", line_h=15)
        + f'<text x="{x + 13}" y="{y + h - 10}" font-family="Arial" font-size="10" fill="#B0AEA8">{escape(url)}</text>')


def source_card_from_evidence(x: int, y: int, w: int, h: int, evidence_item: dict) -> str | None:
    """从 evidence 条目自动取引用卡（约定字段 source_title/source_outlet/source_date/source_quote/source_url）。

    任一字段缺失 → 返回 None（调用方应 fallback 成纯文字 source）。这是声明式的：
    storyline 数据里填了这些字段，渲染层自动出卡，不用按页号另开一张硬编码表（Descente 早期版本的反模式）。
    """
    need = ("source_title", "source_outlet", "source_date", "source_quote", "source_url")
    if not all(evidence_item.get(k) for k in need):
        return None
    return source_card(x, y, w, h, title=evidence_item["source_title"], outlet=evidence_item["source_outlet"],
                       date=evidence_item["source_date"], quote=evidence_item["source_quote"],
                       url=evidence_item["source_url"])
