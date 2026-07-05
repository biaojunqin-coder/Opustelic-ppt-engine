"""为 deck 某页动态拼 prompt：范本卡(RAG·few-shot) + 页型规范 + 大纲状态 + 硬门提醒。

「拼出来的 prompt」非写死模板（守组件①准入）。对应 Novel 写正文时拼装。
"""

from __future__ import annotations

from pathlib import Path

from engine.chart_template_map import TEMPLATES_DIR, template_for_chart
from reinforce.deck_rules import rules as G
from reinforce.retrieval import search as R
from reinforce.spec_lock import spec_lock_brief
from reinforce.storyline_state import CHARTS_WITH_ENGINE

# ── D18 FR3.1/FR7.7 模板源码注入 ─────────────────────────────────────────────
# 注入上限：<8KB 全文、超了截前 8000 字符（结构参考足够·防单页 prompt 被 24KB 大模板爆掉）
_MAX_TEMPLATE_CHARS = 8000
# 版式骨架库（D18 FR7.7）：7 套 × 各含 cover/toc/chapter/content/ending 五页
_LAYOUTS_DIR = Path(__file__).resolve().parent / "ppt_master" / "templates" / "layouts"
_STYLE_DIR = Path(__file__).resolve().parent / "ppt_master" / "references" / "visual-styles"  # D18 FR7.1 十八风格手册
# 页名 → 真实文件名（各套内文件名统一带序号前缀·2026-07-02 ls 核实 7 套全一致）
_LAYOUT_PAGE_FILES = {"cover": "01_cover.svg", "toc": "02_toc.svg", "chapter": "02_chapter.svg",
                      "content": "03_content.svg", "ending": "04_ending.svg"}


def _read_template_source(path: Path | None) -> str | None:
    """读模板/骨架 SVG 源码：缺文件/读失败 → None（调用方在 prompt 里明示·不静默）；
    超 _MAX_TEMPLATE_CHARS 截前段并标注。"""
    if path is None:
        return None
    try:
        src = Path(path).read_text(encoding="utf-8")
    except OSError:
        return None
    if len(src) > _MAX_TEMPLATE_CHARS:
        src = (src[:_MAX_TEMPLATE_CHARS]
               + f"\n<!-- 模板过长·已截取前 {_MAX_TEMPLATE_CHARS} 字符（结构参考足够） -->")
    return src


def _layout_skeleton_path(layout: str) -> Path | None:
    """D18 FR7.7 版式骨架路由约定（spec_lock.per_page[n].layout 的取值格式）：
    ① "套名/页名"        —— 如 "ai_ops/cover" → layouts/ai_ops/01_cover.svg
                             （页名 ∈ cover/toc/chapter/content/ending，见 _LAYOUT_PAGE_FILES）；
    ② 相对路径直给       —— 如 "ai_ops/01_cover.svg" → layouts/ 下原样解析。
    解析不到真实文件 → None（fail-loud 交给调用方拼提示，不静默吞）。"""
    if not layout or "/" not in str(layout):
        return None
    if str(layout).endswith(".svg"):
        p = _LAYOUTS_DIR / str(layout)
        return p if p.is_file() else None
    theme, _, page_name = str(layout).partition("/")
    fname = _LAYOUT_PAGE_FILES.get(page_name.strip())
    if not fname:
        return None
    p = _LAYOUTS_DIR / theme.strip() / fname
    return p if p.is_file() else None


def build_deck_prompt(outline: dict, page_n: int, top_cards: int = 2, spec_lock: dict | None = None,
                       top_expression_cards: int = 2) -> dict:
    """为 outline 第 page_n 页拼 prompt。返回 {prompt(文本), page, cards, expression_cards, deps, spec_lock}。

    spec_lock 传入时强制"重读"——拼进 prompt 文本本身（ppt-master 纪律：逐页生成前必须重读 spec_lock，
    颜色/字体禁止现场现编）。不传则跳过（向后兼容现有调用）。

    expression_cards（表达手法卡·D6扫盘后接入）：按 domain 检索文案/修辞公式一并拼进 prompt——
    outline 阶段还没有具体文案，无法按 expression_type 精确检索，用 domain 兜底召回，
    `top_expression_cards=0` 可关闭（不想要就传 0，向后兼容现有调用不受影响）。
    """
    pages = outline.get("pages", [])
    page = next((p for p in pages if p.get("n") == page_n), None)
    if not page:
        raise ValueError(f"页 {page_n} 不存在于大纲")

    pf = page.get("page_function")
    domain = outline.get("domain")
    intent = outline.get("intent")
    chart = (page.get("facets") or {}).get("chart")

    # ① RAG 取范本卡（few-shot·示范 >> 描述）
    cards = R.search(page_function=pf, domain=domain, intent=intent, top=top_cards)

    # ①.5 RAG 取表达手法卡（文案/修辞公式·同样 few-shot 供参考不强制套用）
    expression_cards = ([c for c, _ in R.search_expression_cards(domain=domain, top=top_expression_cards)]
                        if top_expression_cards else [])

    # ①.6 结构性文案槽位卡（D20 FR1.3·按页面位置精确路由）——第三轮实测确诊：元叙述
    # （"三条线诊断完毕，下一步…"）全长在目录/转场/小结/决策/落幕这些结构性文案位置，
    # 病根=这些位置没有正向范式，AI 用最字面的方式兑现"承接+预告"。命中位置页型时把
    # 对应槽位的真提案范式卡注入（真实 demo+禁形态对照），语言有了法源。
    facets_early = page.get("facets") or {}
    _pos_text = f"{pf or ''}|{facets_early.get('page_type', '')}|{facets_early.get('role', '')}"
    slot = None
    if "目录" in _pos_text:
        slot = "目录命名"
    elif "转场" in _pos_text:
        slot = "章间桥"
    elif "小结" in _pos_text:
        slot = "章小结"
    elif "决策" in _pos_text or facets_early.get("chart") == "decision_box":
        slot = "ask收尾"
    elif "落幕" in _pos_text or "高潮" in _pos_text:
        slot = "落幕"
    elif "诊断" in _pos_text or "洞察陈述" in _pos_text:
        # 批④补第六槽位出口：六槽位卡库有「诊断收束」3 张（D20 首批），路由链此前只开五支——
        # 诊断页（真提案"诊断一步给判断"的对比定位/设问自答范式）拿不到自己的槽位卡。
        slot = "诊断收束"
    slot_cards = [c for c, _ in R.search_expression_cards(slot=slot, top=3)] if slot else []

    # ② 状态：上一页（叙事承接）+ 依赖页
    # 2026-07-02 saopan扫盘揪出：旧版按列表下标取 idx-1——pages 顺序乱（补页/重排后 [1,3,2] 很常见）
    # 时"上一页"抓错，叙事承接提示指向错误页。正确语义：页号 n 小于当页的最大者（页号可以不连续），
    # 没有比它小的页号则视为无上一页。
    prev_candidates = [p for p in pages if isinstance(p.get("n"), (int, float)) and p["n"] < page_n]
    prev = max(prev_candidates, key=lambda p: p["n"]) if prev_candidates else None
    deps = [p for p in pages if p.get("n") in page.get("depends_on", [])]

    # ③ 拼 prompt
    L = [
        f"# 任务：为《{outline.get('title')}》第 {page_n} 页产出 deck 页",
        f"deck 类型：{outline.get('doc_type')} · 受众：{'、'.join(outline.get('audience') or ['—'])} "
        f"· 领域：{'、'.join(domain or [])}",
        f"本页论点（action title）：{page.get('claim')}",
        f"页功能：{pf}",
    ]
    chart_map = template_for_chart(chart) if chart else None
    if chart:
        L.append(f"本页图型（chart）：{chart}"
                  + (f"｜**必须调用 `engine.chart_shapes.{chart}_chart()` 算坐标，禁止手算浮空柱/列宽占比**"
                     f"（waterfall/gantt/mekko 三种坐标算术极易出 bug，见制作工作流 SKILL 阶段2"
                     f"「waterfall/Gantt/Mekko 图表几何必须用 chart_shapes.py」这条硬规则）"
                     if chart in CHARTS_WITH_ENGINE else ""))
        # ── D18 FR3.1：chart→资产映射强制注入——第一轮实测确诊"声明 20 种 chart 兑现 0 张"，
        #    病根是 71 张模板全程零注入；这里按映射表把对口模板 SVG 源码直接喂进 prompt ──
        if chart_map:
            if chart_map.get("hint"):
                L.append(f"该图型结构要点：{chart_map['hint']}")
            tpl = chart_map.get("template")
            if tpl:
                src = _read_template_source(TEMPLATES_DIR / tpl)
                if src is not None:
                    L.append(f"\n## 图表结构参考模板（{tpl}·模板供结构不供皮肤——布局/元素组织照学，"
                             f"颜色/字体**必须换成 spec_lock 锁定色板**，禁止照搬模板原色）：\n"
                             f"```svg\n{src}\n```")
                else:
                    L.append(f"⚠️ 图型 {chart} 映射的模板 {tpl} 在 templates/charts/ 读不到——"
                             f"检查资产完整性，别凭空想象结构")
    # ── D19 FR1.1 两筐分法（第二轮实测"说明书感"确诊：工作字段原样摊给生成器无使用契约，
    #    framing 被忠实渲染成"立场/反方会怎么看/依据"版式块 ≥8 页、"来源：brief P17"上页）──
    facets_d = page.get("facets") or {}
    _evidence = facets_d.get("evidence") or []
    if _evidence:
        ev_lines = []
        for e in _evidence:
            if e.get("source_type") == "client_provided":
                # 客户资料：数字可用·页面不标来源（客户本来就有·内部台账已溯源·FR5.1）
                ev_lines.append(f"- [{e.get('dim')}] {e.get('data')}（客户资料·页面不标来源）")
            else:
                ev_lines.append(f"- [{e.get('dim')}] {e.get('data')}"
                                f"｜页脚来源：{e.get('source', '待补')}")
        L.append("\n## 本页呈现内容（证据数据·据此设计页面）：\n" + "\n".join(ev_lines))
    _bg = []
    _framing = facets_d.get("framing") or {}
    if _framing:
        _bg.append(f"论证立场：{_framing.get('stance')}｜反方视角：{_framing.get('counter_read')}"
                   f"｜立场依据：{_framing.get('basis')}")
    if facets_d.get("sowhat"):
        _bg.append(f"本页推演落点：{facets_d['sowhat']}")
    _client_refs = [f"{e.get('dim')}←{e.get('source')}" for e in _evidence
                    if e.get("source_type") == "client_provided" and e.get("source")]
    if _client_refs:
        _bg.append("客户资料定位（仅内部溯源台账用）：" + "；".join(_client_refs))
    if _bg:
        L.append("\n## 理解背景（帮助你理解论证与立场·⚠️绝不渲染成页面文字）：\n"
                 "以下材料**绝不出现在页面上**——不出现「立场」「反方」「依据」「来源：brief」等"
                 "字样、不做成版式块（对客文案门会以 error 拦下）；它们的价值体现在你如何**组织与"
                 "措辞**上面的呈现内容：把反方视角消化成'有人可能质疑…而答案是…'式的自然论证，"
                 "把推演落点化进标题与结构，而不是当小标题印出来。\n- " + "\n- ".join(_bg))
    if prev:
        L.append(f"上一页：p{prev['n']}「{prev.get('claim')}」（本页承接它）")
    if deps:
        L.append("依赖页：" + "；".join(f"p{d['n']}「{d.get('claim')}」" for d in deps))
    if cards:
        L.append("\n## 范本手法卡（示范 >> 描述·学手法不照抄）：")
        for c in cards:
            line = (f"- [{c.get('page_function')}] {c.get('technique')}"
                    f"｜机制：{c.get('mechanism')}｜何时用：{c.get('pick_when')}｜demo：{c.get('demo')}")
            budget = c.get("char_budget")
            if budget:
                line += f"｜**本页型字数上限约{budget}字**（生成前就按这个上限写，不是写完超了再截·presenton字段级长度契约启发）"
            L.append(line)
    if expression_cards:
        L.append("\n## 表达手法卡（文案/修辞公式·参考不照抄原句）：")
        for c in expression_cards:
            L.append(f"- [{c.get('expression_type')}] {c.get('formula')}"
                     f"｜机制：{c.get('mechanism')}｜何时用：{c.get('pick_when')}｜demo：{c.get('demo')}")
    if slot_cards:
        # D20 FR1.3：本页是结构性文案位置——真提案范式卡（含 AI 腔禁形态对照）按槽位送达
        L.append(f"\n## 结构性文案范式（本页位置=「{slot}」·真提案怎么写这类页·禁形态别踩）：")
        for c in slot_cards:
            L.append(f"- [{c.get('expression_type')}] 公式：{c.get('formula')}"
                     f"｜机制：{c.get('mechanism')}｜真实范例：{c.get('demo')}"
                     + (f"｜⛔禁形态：{c.get('anti_pattern')}" if c.get("anti_pattern") else ""))
    vs = (spec_lock or {}).get("visual_style")
    L += [
        "\n## 硬规范（违反 = 返工）：",
        # D20 FR1.4 叙事姿态总契约（第三轮实测确诊元叙述·"这是这份提案的第一个判断"式）
        "- 每句话都在讲客户的生意，不讲这份 deck 自己——禁止元叙述（谈论提案结构/页面关系/"
        "写作过程，如「诊断完毕」「下一步是」「这份提案」「后面每一页」）；结构信息走版式组件"
        "（tracker/Part编号），不写成句子",
        "- 标题 = 论断非主题（claim-shaped）· 一页一核心论点 · 数字必带 source",
        # D18 FR7.1：锁定美学风格后色彩/密度纪律以风格手册为准——删掉此前写死的"一个高亮色
        # 其余灰"（正是它把产出摁死在单色卡片网格单一吸引子上·第一轮实测病根）；未锁风格
        # 的旧调用保留旧默认（向后兼容·克制底线仍在）。
        ("- 字号/字体走 spec_lock 角色槽 · 色彩纪律按锁定风格手册执行 · 留白" if vs
         else "- 字号走 8 级网格 · 一个高亮色其余灰 · 留白"),
    ]
    if spec_lock:
        L.append("\n" + spec_lock_brief(spec_lock, page_n=page_n))
        # ── D18 FR7.1：锁定风格手册注入——每页生成时风格法源必须在场（"强制重读"哲学：
        #    形状语言/装饰密度/字体性格/配图倾向的判例都在手册里，只给风格名等于没锁）──
        if vs and vs != "custom":
            src = _read_template_source(_STYLE_DIR / f"{vs}.md")
            if src is not None:
                L.append(f"\n## 锁定视觉风格执行手册（{vs}·本页所有形状/装饰/留白/字体性格决策的法源）：\n{src}")
            else:
                L.append(f"⚠️ 锁定风格 {vs} 的手册在 references/visual-styles/ 读不到——检查资产完整性")
        # ── D18 FR7.7：版式骨架路由——per_page[n].layout 有值就把骨架 SVG 源码拼进 prompt
        #    （spec_lock_brief 只给了一行锚点提醒，结构本体在这里注入·同 chart 模板做法）──
        per_page = spec_lock.get("per_page") or {}
        page_lock = per_page.get(str(page_n)) or per_page.get(page_n) or {}
        layout = page_lock.get("layout")
        if layout:
            src = _read_template_source(_layout_skeleton_path(layout))
            if src is not None:
                L.append(f"\n## 版式骨架参考（{layout}·供结构不供皮肤——分区/占位/层级组织照学，"
                         f"颜色/字体/装饰必须换成 spec_lock 锁定色板与风格）：\n```svg\n{src}\n```")
            else:
                L.append(f"⚠️ 声明的版式骨架 {layout} 在 templates/layouts/ 未解析到文件——"
                         f"检查 spec_lock（约定：套名/页名 如 ai_ops/cover，或相对路径 ai_ops/01_cover.svg）")
        # ── D18 FR7.5：图标占位用法说明（inventory 清单本身已由 spec_lock_brief 拼入）──
        if (spec_lock.get("icons") or {}).get("inventory"):
            L.append("图标用法：页面里以 <use data-icon=\"图标名\"/> 占位（名字只准来自上方 inventory 清单），"
                     "finalize 工序会把占位替换为内嵌的真 SVG 源码——不要自己手画图标路径。")
    return {"prompt": "\n".join(L), "page": page, "cards": cards,
            "expression_cards": expression_cards, "slot_cards": slot_cards,
            "deps": deps, "spec_lock": spec_lock}
