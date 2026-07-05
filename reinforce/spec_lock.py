"""spec_lock —— deck 级设计规范锁定。对应 ppt-master 的 `spec_lock.md` 机制。

来源：ppt-master 硬纪律「每页生成前必须重读 spec_lock，所有颜色/字体/图表选型必须来自这个文件，
不许凭记忆或现场现编」。这是长 deck 逐页手写时防"画着画着风格漂"的核心机制——
21 页如果每页都临场定一次配色，跨页视觉一致性必然崩。

⚠️ 真实教训（D1 决策记录 2026-07-01 补记）：这条纪律当初在 vendor 时就标了"遗留张力"，
制作层开工时（CFO/Descente demo）没回查决策记录、直接写脚本批量生成，原样踩坑。
spec_lock 不是"建议"，是阶段4 storyline 定稿后、逐页生成前的强制关卡——见制作工作流 SKILL。
"""

from __future__ import annotations

import re

REQUIRED_FIELDS = ["palette", "font_family"]
RHYTHM_STATES = {"anchor", "dense", "breathing"}  # 借鉴 ppt-master executor-base.md §2.1：
# anchor=慢下来的强停顿大焦点页 / dense=信息密集多元素页 / breathing=留白呼吸过渡页。
# 跟"一个论点拆2-3页"规则互补——那条管拆几页，这条管每页疏密，防长 deck 每页都是同一种卡片网格密度。

# ── 视觉美学轴（D18 FR7.1·ppt-master 机制考古接回）───────────────────────
# 18 种预设风格 + custom，每种对应 engine/ppt_master/references/visual-styles/<名>.md 一份
# 执行手册（形状语言/字体性格/色彩纪律/配图倾向——刻意不含 HEX，色值在 palette 现场锁）。
# 此前系统没有美学轴（visual_style 字段被挪用成演讲/阅读密度轴），prompt 写死"一个高亮色
# 其余灰"，产出塌缩到单色卡片网格单一吸引子——第一轮实测（某品牌 24页）确诊的病根第一名。
AESTHETIC_STYLES = {
    "blueprint", "brutalist", "chalkboard", "dark-tech", "data-journalism",
    "editorial", "glassmorphism", "ink-notes", "ink-wash", "memphis", "paper-cut",
    "photo-editorial", "pixel-art", "sketch-notes", "soft-rounded", "swiss-minimal",
    "vintage-poster", "zine", "custom",
}
# typography 角色槽（D18 FR7.6）：从"8级尺寸菜单"升级为"角色→值"映射——同角色跨页漂字号
# =不专业的元凶（ppt-master 纪律）。body 是锚点，其余按 delivery_purpose/风格派生。
TYPOGRAPHY_ROLES = {"title", "subtitle", "lead", "body", "annotation", "footnote", "hero"}
# images 清单行必填键（D18 FR7.4·沿用 ppt-master design_spec §VIII 行 schema 精简版）：
# pattern_id=图文版式模式（references/image-layout-patterns.md 81 模式编号·强制填防"永远左右分栏"），
# acquire_via ∈ {ai, web, user, formula, slice, placeholder}（六源获取）。
IMAGE_ROW_REQUIRED = ["filename", "purpose", "pattern_id", "acquire_via"]
IMAGE_ACQUIRE_VIAS = {"ai", "web", "user", "formula", "slice", "placeholder"}
# D22 视觉丰富度三档（第五轮实测"总推荐特别素"确诊：无显式契约·AI 保守天性收敛到素）：
# 素雅=克制专业（尽调/董事会）·标准=图文均衡·浓郁=图像/设计浓度高（比稿/创意/营销）。
# 默认档按 deck 类型智能推荐（engine.chart_template_map.default_richness_for），用户可改。
RICHNESS_LEVELS = ("素雅", "标准", "浓郁")
# D22 品牌视觉锚定（第五轮实测"不贴品牌视觉"确诊：色板只有风格手册一条来源，无品牌通道）：
# brand_vi=用户/客户给的品牌素材提取 > web_verified=联网查证官方色(必须带 URL 溯源·防
# "某品牌 绿记成蓝"的常识幻觉) > neutral=查不到用中性并如实标注。
PALETTE_SOURCE_KINDS = {"brand_vi", "web_verified", "neutral"}


def new_spec_lock(palette: dict, font_family: str, font_grid=None, hero_size=130,
                   zones=None, per_page=None, *, visual_style=None, typography=None,
                   icons=None, images=None, image_rendering=None, image_palette=None,
                   richness=None, palette_source=None) -> dict:
    """新建 spec_lock（storyline 定稿后、逐页生成前确定·全 deck 共享同一份，不可逐页另定）。

    palette：锁定色板 {bg, ink, accent, grey, ...}（十六进制）——SVG 里只许用这些颜色。
    font_family：锁定字体（如 "Arial"）。
    font_grid：锁定字号网格（默认 02 设计系统 8 级）——常规文字字号必须落在这个网格上。
    hero_size：焦点数字专用超大字号（默认 130）——8 级网格管常规文字，焦点数字另锁一档，
        不是"不守规范"，是"焦点数字也要锁死成一个值，不能每页 130/150/177 随便变"
        （真实踩过的坑：早期 hero_text 自动缩放公式漏 min() 封顶，没有锁定值就没有判断"对不对"的基准）。
    zones：deck 级页面分区坐标预算 {区名: {"y":..., "h":...}}（如 header/key_message_bar/content/footer）——
        借鉴 ppt-master government_blue/red 版式 design_spec.md 的分区表，逐页生成前一并提醒"留白边界"。
        ⚠️ 故意不做"SVG 实际渲染坐标是否越界"的几何机检（要真解析每个元素含 transform 后的包围盒，
        代价/误报率跟收益不成比例）——这是给生成时参考的预算，不是拿来自动拦截的硬门，越界判断留人审。
    per_page：{页号: {"chart": 图表/版式id, "rhythm": "anchor"|"dense"|"breathing", "hero": {"hook":str, "composition":str},
        "layout": 版式骨架名, "visual_concept": {"layout":str, "core_message":str, "blocks":[...]}}}
        —— 逐页专属锁定项，子键都可选、按需声明：
        chart 每页该用哪个图表提前定好，逐页生成时不临场现编选型；
        rhythm 逐页节奏标注，见上 RHYTHM_STATES；
        hero 封面/收尾这类"门面页"必须先声明具体钩子+构图策略再生成，禁止 default 成
        "标题+副标题+装饰背景"（声明是否完整由 validate_spec_lock 机检；钩子写得好不好是人审，见 review.py）；
        layout（D18 FR7.7）路由到 engine/ppt_master/templates/layouts/ 的骨架 SVG（供结构不供皮肤）；
        visual_concept（D18 FR7.3·问题A核心件）——本页"先想后画"契约：layout 版式声明 +
        core_message 一句断言"本页凭什么存在"（说不出就砍页）+ blocks 内容块按语体预写真句子
        （不留骨架点事后展开）。

    D18 FR7.2 设计契约扩容（keyword-only·全部可选保旧调用零破坏）：
    visual_style：美学轴，AESTHETIC_STYLES 18 风格之一（确认阶段三档光谱用户拍板后锁定）——
        Executor 只读锁定风格的手册文件；不锁=沿用旧的克制默认，但 deck_warnings 会提示。
    typography：字号角色槽 {"body":16, "title":28, ..., "title_font":str, "body_font":str}——
        body 是锚点、每角色一值 deck 级锁死；title_font 承载锁定风格的字体性格（正文可中性，
        标题不许默认中性 sans·ppt-master g GATE）。不传则按 font_grid 兼容旧行为。
    icons：{"library": 图标库名(5库锁1), "inventory": [允许用的图标名]}——Executor 只准用清单内图标。
    images：图像资源清单 [{filename, purpose, pattern_id(81版式模式#·强制), acquire_via(六源),
        intent?, size?, text_policy?}]——见 IMAGE_ROW_REQUIRED。
    image_rendering / image_palette：deck 级图像渲染风格锁 × 图像色调锁——多张图（尤其 AI 生成）
        读起来像同一份 deck 的机制（ppt-master h.5）。

    D22 视觉配置舱两字段（第五轮实测三反馈·可选保零破坏，填了必须合法）：
    richness：视觉丰富度档 RICHNESS_LEVELS 之一——浓郁档图像下限升 error 硬拦
        （check_image_quota·直通档下 warn 全架空，必须有 error 兜底），素雅不查。
    palette_source：{kind: PALETTE_SOURCE_KINDS 之一, brand: 品牌名, evidence: URL或素材路径}
        ——色板来源留痕；kind≠neutral 必须带 evidence（联网查证无溯源=幻觉色板风险，拒）。
    """
    # 2026-07-02 saopan扫盘揪出：per_page 用 int 页号做键，JSON 落盘（spec_lock.json 是制作
    # 工作流阶段1.5 的落盘产物）回读后键变 str → spec_lock_brief 按 int 查必 miss，逐页锁定项
    # （chart/rhythm/hero）静默全丢且 validate 照样 valid——跨会话断点续做时"强制重读"机制
    # 无声蒸发。源头归一成 str 键，brief 查询侧兼容旧 int 键数据。
    return {"palette": palette, "font_family": font_family,
            "font_grid": font_grid or [44, 28, 24, 22, 18, 16, 14, 9],
            "hero_size": hero_size, "zones": zones or {},
            "per_page": {str(k): v for k, v in (per_page or {}).items()},
            # D18 FR7.2/7.6 设计契约段（None/空=未锁·validate 只查"填了的对不对"，
            # "该不该填"由确认工序+pipeline warn 管——同 spec_lock 本身的分工哲学）
            "visual_style": visual_style,
            "typography": dict(typography) if typography else {},
            "icons": dict(icons) if icons else {},
            "images": list(images) if images else [],
            "image_rendering": image_rendering, "image_palette": image_palette,
            # D22 视觉配置舱：丰富度档 + 色板来源留痕（None=未锁·沿用旧行为）
            "richness": richness,
            "palette_source": dict(palette_source) if palette_source else None}


def seed_per_page_from_outline(spec: dict, outline: dict) -> dict:
    """把策略层逐页声明的 chart 播种进 spec_lock.per_page（D18 FR3.4·并入 FR7.2 执行）。

    第一轮实测确诊：per_page 一页都没填 → "模板供结构不供皮肤"的逐页提示一次没触发。
    策略 storyline 每页本来就声明了 chart（facets.chart 随 to_outline 带下来），设计定稿
    建 spec_lock 时调本函数自动填入——已有值不覆盖（人工声明优先），页号键按 str 归一
    （D17 契约）。原地改并返回 spec（链式友好）。
    """
    per_page = spec.setdefault("per_page", {})
    for p in outline.get("pages") or []:
        chart = (p.get("facets") or {}).get("chart")
        n = p.get("n")
        if not chart or n is None:
            continue
        entry = per_page.setdefault(str(n), {})
        entry.setdefault("chart", chart)
    return spec


def validate_spec_lock(spec: dict) -> dict:
    """校验 spec_lock 必填字段齐全 + per_page 里 rhythm/hero 声明完整 → {issues, valid}。

    只查"字段填没填"，不查"颜色本身好不好"——palette 的色盲友好度（CVD模拟视角下两两颜色对
    是否仍可区分）由 `reinforce.deck_rules.visual_review.check_colorblind_safe(spec["palette"])`
    另外提供；2026-07-02 起 build_deck 传入 spec_lock 时自动跑一次（此前登记"人工调用一次"
    但工序文档无落点、零生产调用，saopan 孤岛A1，已接线 pipeline，warn 进 deck_warnings）。
    """
    issues = []
    for k in REQUIRED_FIELDS:
        if not spec.get(k):
            issues.append({"sev": "error", "msg": f"spec_lock 缺 {k}"})
    # 2026-07-03 saopan批②：palette 值 None/非字符串在这里就拦（error issue·不崩）——
    # 此前带 None 值的 palette 能通过 validate，滑到 pipeline 的 check_colorblind_safe
    # 时 _hex_to_rgb(None).lstrip 裸栈崩溃。校验器 fail-closed=记 issue，不是被崩溃击穿。
    pal = spec.get("palette")
    if pal and not isinstance(pal, dict):
        issues.append({"sev": "error",
                       "msg": f"palette 不是对象（got {type(pal).__name__}·应为 {{色名: 十六进制值}}）"})
    elif isinstance(pal, dict):
        for name, v in pal.items():
            if not isinstance(v, str) or not v.strip():
                issues.append({"sev": "error",
                               "msg": f"palette[{name}]={v!r} 不是十六进制色值字符串"
                                      f"（None/脏值会击穿下游 CVD 检查——在 validate 就拦·fail-closed）"})
    # ── D18 FR7.2 设计契约段校验（原则：字段可不填，填了必须合法完整——填一半比不填更危险）──
    vs = spec.get("visual_style")
    if vs is not None and vs not in AESTHETIC_STYLES:
        issues.append({"sev": "error",
                       "msg": f"visual_style={vs!r} 不在 18 风格+custom 内（见 AESTHETIC_STYLES·"
                              f"手册在 engine/ppt_master/references/visual-styles/）"})
    typo = spec.get("typography") or {}
    if typo:
        unknown = set(typo) - TYPOGRAPHY_ROLES - {"title_font", "body_font"}
        if unknown:
            issues.append({"sev": "error", "msg": f"typography 含未知角色槽 {sorted(unknown)}"})
        if not typo.get("body"):
            issues.append({"sev": "error", "msg": "typography 填了但缺 body 锚点（其余角色从它派生）"})
    icons = spec.get("icons") or {}
    if icons:
        if not icons.get("library"):
            issues.append({"sev": "error", "msg": "icons 填了但缺 library（一 deck 锁一库）"})
        if not icons.get("inventory"):
            issues.append({"sev": "error", "msg": "icons 填了但 inventory 为空（Executor 只准用清单内图标·"
                                                  "空清单=没规划就别声明 icons）"})
    # ── D22 视觉配置舱段校验（同一原则：可不填，填了必须合法完整）──
    rich = spec.get("richness")
    if rich is not None and rich not in RICHNESS_LEVELS:
        issues.append({"sev": "error",
                       "msg": f"richness={rich!r} 不在 {RICHNESS_LEVELS} 内（D22 丰富度三档）"})
    ps = spec.get("palette_source")
    if ps is not None:
        kind = (ps or {}).get("kind") if isinstance(ps, dict) else None
        if kind not in PALETTE_SOURCE_KINDS:
            issues.append({"sev": "error",
                           "msg": f"palette_source.kind={kind!r} 不在 {sorted(PALETTE_SOURCE_KINDS)} 内"
                                  f"（D22 品牌锚定：brand_vi/web_verified/neutral 三选一）"})
        elif kind != "neutral" and not ps.get("evidence"):
            issues.append({"sev": "error",
                           "msg": f"palette_source.kind={kind} 但缺 evidence（brand_vi 要素材路径、"
                                  f"web_verified 要来源 URL——没有溯源的品牌色板=常识幻觉风险，"
                                  f"'某品牌 绿记成蓝'就翻车·D22 fail-closed）"})
    for i, row in enumerate(spec.get("images") or []):
        if not isinstance(row, dict):
            # saopan批②：行不是 dict 此前 row.get 直接裸栈——校验器自己先崩就谈不上拦
            issues.append({"sev": "error",
                           "msg": f"images[{i}] 不是对象（got {type(row).__name__}·"
                                  f"每行应为 {{{', '.join(IMAGE_ROW_REQUIRED)}, ...}}）"})
            continue
        missing = [k for k in IMAGE_ROW_REQUIRED if not row.get(k)]
        if missing:
            issues.append({"sev": "error", "msg": f"images[{i}] 缺 {missing}（版式模式 pattern_id 强制填·"
                                                  f"防'永远左右分栏'·81 模式见 image-layout-patterns.md）"})
        via = row.get("acquire_via")
        if via and via not in IMAGE_ACQUIRE_VIAS:
            issues.append({"sev": "error", "msg": f"images[{i}] acquire_via={via!r} 不在六源 {sorted(IMAGE_ACQUIRE_VIAS)}"})
    # per_page 显式传 None 也是合法输入（or {} 防崩·2026-07-02 saopan：校验器自己不能被崩溃击穿）
    for n, p in (spec.get("per_page") or {}).items():
        if not isinstance(p, dict):
            # saopan批②：值不是 dict 此前 p.get 裸栈——记 error issue 继续查其余页
            issues.append({"sev": "error",
                           "msg": f"p{n} per_page 值不是对象（got {type(p).__name__}·"
                                  f"应为 {{chart/rhythm/hero/... 子键}}）"})
            continue
        r = p.get("rhythm")
        if r is not None and r not in RHYTHM_STATES:
            issues.append({"sev": "error", "msg": f"p{n} rhythm={r!r} 不在 {sorted(RHYTHM_STATES)} 内"})
        h = p.get("hero")
        if h is not None and not (isinstance(h, dict) and h.get("hook") and h.get("composition")):
            issues.append({"sev": "error",
                            "msg": f"p{n} hero 声明不完整（须同时有 hook+composition，不能只填一半占位）"})
        vc = p.get("visual_concept")
        if vc is not None and not (isinstance(vc, dict) and vc.get("core_message")):
            issues.append({"sev": "error",
                            "msg": f"p{n} visual_concept 缺 core_message（一句断言'本页凭什么存在'·"
                                   f"说不出就砍页·D18 FR7.3）"})
    return {"issues": issues, "valid": not any(i["sev"] == "error" for i in issues)}


def spec_lock_brief(spec: dict, page_n: int | None = None) -> str:
    """spec_lock → 一段拼进 prompt 的简报文字（强制"重读"体现在：这段文字进了每页的 prompt）。

    page_n 传入时追加该页专属锁定项（per_page 里 page_n 对应的 chart/rhythm/hero，
    没有就跳过不提）；不传 page_n 则只给 deck 级通用项（向后兼容旧调用）。
    """
    palette_str = " / ".join(f"{k}={v}" for k, v in spec.get("palette", {}).items())
    grid_str = ", ".join(str(s) for s in spec.get("font_grid", []))
    lines = [
        "【spec_lock 锁定规范·本页必须遵守，禁止现场另定新颜色/字体】",
        f"色板（只许用这些·禁用其它十六进制色值）：{palette_str}",
    ]
    vs = spec.get("visual_style")
    if vs:
        # D18 FR7.1：锁定美学风格进每页 prompt——形状语言/装饰密度/字体性格的法源。
        # 手册全文由 prompt_builder 在 deck 级注入一次，这里每页给锚点提醒（强制重读机制）。
        lines.append(f"视觉美学风格（deck 级锁定·本页所有形状/装饰/留白决策以它为法源）：{vs}"
                     f"（执行手册 engine/ppt_master/references/visual-styles/{vs}.md·"
                     f"禁止退回默认的'单色卡片网格'）")
    rich = spec.get("richness")
    if rich:
        # D22：丰富度档进每页 prompt——"素"是被选择的不是被默认的；浓郁档逐页别偷懒退素。
        _hint = {"素雅": "克制专业·数据与留白主导，装饰性元素少而准",
                 "标准": "图文均衡·该有图像的位置不空着",
                 "浓郁": "图像/色彩/设计浓度拉满——本页若适合配图像/大色块/强视觉就必须给，禁止退回纯文字卡片"}
        lines.append(f"视觉丰富度（deck 级锁定·用户拍板档位）：{rich}——{_hint.get(rich, '')}")
    ps = spec.get("palette_source")
    if ps and ps.get("kind") in ("brand_vi", "web_verified"):
        lines.append(f"色板来源：品牌「{ps.get('brand', '')}」官方视觉（{ps.get('kind')}·{ps.get('evidence', '')}）"
                     f"——accent 主导色即品牌色，关键页可品牌色铺场，气质贴品牌不跑偏")
    typo = spec.get("typography") or {}
    if typo:
        roles_str = " / ".join(f"{r}={typo[r]}" for r in
                               ("title", "subtitle", "lead", "body", "annotation", "footnote", "hero")
                               if typo.get(r))
        fonts_str = ""
        if typo.get("title_font") or typo.get("body_font"):
            fonts_str = (f" · 标题字体：{typo.get('title_font') or spec.get('font_family')}"
                         f"（承载风格性格·不许默认中性）· 正文字体：{typo.get('body_font') or spec.get('font_family')}")
        lines.append(f"字号角色槽（同角色跨页漂字号=不专业·每角色锁死一值）：{roles_str}{fonts_str}")
    else:
        lines.append(f"字体：{spec.get('font_family', '')} · 常规字号网格：{grid_str} · "
                     f"焦点数字专用字号：{spec.get('hero_size', 130)}px（仅焦点数字用·不在常规网格内但同样锁死单一值）")
    icons = spec.get("icons") or {}
    if icons.get("inventory"):
        inv = icons["inventory"]
        shown = ", ".join(inv[:24]) + (f" …等{len(inv)}个" if len(inv) > 24 else "")
        lines.append(f"图标（库：{icons.get('library')}·只准用清单内·用 <use data-icon=\"名\"> 占位）：{shown}")
    if spec.get("image_rendering") or spec.get("image_palette"):
        lines.append(f"图像统一风格锁：rendering={spec.get('image_rendering')} · "
                     f"palette={spec.get('image_palette')}（多图读起来像同一份 deck）")
    zones = spec.get("zones") or {}
    if zones:
        # saopan批②：区值不是 dict 此前 z.get 裸栈（brief 是拼 prompt 的展示函数，
        # 不该被脏数据崩掉）——跳过异常区并在 brief 里如实标注，合法区照常给
        good = [(name, z) for name, z in zones.items() if isinstance(z, dict)]
        bad = [name for name, z in zones.items() if not isinstance(z, dict)]
        zones_str = " / ".join(f"{name}(y={z.get('y')},h={z.get('h')})" for name, z in good)
        if bad:
            zones_str += ("（异常分区已跳过：" + ", ".join(str(b) for b in bad) +
                          "——值不是对象，请修 spec_lock）") if zones_str else \
                         ("（全部分区值异常已跳过：" + ", ".join(str(b) for b in bad) + "）")
        lines.append(f"页面分区预算（留白边界参考·不是像素级硬约束）：{zones_str}")
    if page_n is not None:
        per_page = spec.get("per_page") or {}
        # str 键为正（new_spec_lock 源头归一+JSON 回读天然一致）；int 键兜底兼容本修复前落盘的旧数据
        page = per_page.get(str(page_n)) or per_page.get(page_n) or {}
        if not isinstance(page, dict):
            page = {}  # saopan批②同批：页值非 dict 容错成"无逐页锁定项"，不崩 brief
        chart = page.get("chart")
        if chart:
            lines.append(f"本页指定图表/版式：{chart}（已提前定好，不临场改选型；若该图表模板自带颜色，"
                          f"必须换成本 spec_lock 锁定色板，禁止照搬模板原色——模板供结构不供皮肤）")
        rhythm = page.get("rhythm")
        if rhythm:
            note = "·本页禁止堆卡片网格" if rhythm == "breathing" else ""
            lines.append(f"本页节奏：{rhythm}（anchor=强停顿大焦点 / dense=信息密集 / breathing=留白过渡{note}）")
        hero = page.get("hero")
        if hero:
            lines.append(f"本页是门面页·已锁定钩子「{hero.get('hook')}」+ 构图策略「{hero.get('composition')}」"
                          f"——禁止退化成默认的「标题+副标题+装饰背景」")
        layout = page.get("layout")
        if layout:
            lines.append(f"本页版式骨架：{layout}（继承 templates/layouts/ 该骨架的结构·供结构不供皮肤·"
                          f"D18 FR7.7）")
        vc = page.get("visual_concept")
        if vc:
            # D18 FR7.3：本页"先想后画"契约——生成前先按此声明布局策略，再动笔
            lines.append(f"本页视觉概念（先想后画契约）：凭什么存在=「{vc.get('core_message')}」"
                          + (f" · 版式声明：{vc.get('layout')}" if vc.get("layout") else ""))
            blocks = vc.get("blocks") or []
            if blocks:
                lines.append("本页内容块（策划期已预写·按此呈现别再现编）：" +
                             " ｜ ".join(str(b) for b in blocks[:8]))
    return "\n".join(lines)


def check_against_spec(svg_text: str, spec: dict) -> list[dict]:
    """机检：扫 SVG 里出现的十六进制颜色是否都在 spec.palette 锁定范围内（逮"现场现编新颜色"）。

    warn 而非 error——颜色越界不代表内容错，但破坏跨页一致性，喂人审/下次生成纠正。
    """
    def _norm_hex(c: str) -> str:
        # 2026-07-02 saopan扫盘揪出：不展开 3 位 hex——palette 写 "#fff" 时 6 位用色全被误报
        # 越板、3 位用色全不可见。统一展开成 6 位大写再比对（#abc ≡ #aabbcc，CSS/SVG 同义）。
        c = c.upper()
        if len(c) == 4:  # "#RGB"
            c = "#" + "".join(ch * 2 for ch in c[1:])
        return c

    allowed = {_norm_hex(str(v)) for v in (spec.get("palette") or {}).values()}
    used = {_norm_hex(m) for m in re.findall(r"#(?:[0-9A-Fa-f]{6}|[0-9A-Fa-f]{3})\b", svg_text)}
    rogue = used - allowed
    if rogue:
        return [{"rule": "off_spec_color", "sev": "warn",
                 "note": f"用了 spec_lock 外的颜色：{sorted(rogue)}（应只用锁定色板，防跨页风格漂）"}]
    return []
