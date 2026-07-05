"""策略状态 State —— storyline 的结构化建模 + 校验 + 降解成制作层 deck_outline。

策略工作流（skills/策略工作流/）的产物落点：把模糊 brief 走完「判目的→假设树→storyline」后，
固化成可校验、可落盘、可交制作层的 storyline。对应 Novel kaishu 的 goal_tree + beat_sheet。
fail-closed：目的卡缺项 / 假设无可证伪 test / SCR 弧不全或乱序 / 行非完整 → 校验拦，save / 降解前必过。

storyline 三块（对应策略工作流三阶段产物）：
  ① 目的卡（阶段1 判目的）：purpose/intent/audience/decision_ask —— deck 为谁、推动什么决策
  ② 假设树（阶段2 结构化）：governing_thought(塔顶 Lead) + sub_hypotheses(每个带可证伪 test)
  ③ storyline（阶段4）：lines[] 每行=一页（scr 段 + claim 论断标题 + chart 图型 + role 作用 + sowhat）

降解 to_outline()：storyline → deck_state.deck_outline（claim→claim, page_function 见下方"page_function
怎么来"），交制作 pipeline。

⚠️ **page_function 怎么来（2026-07-01 修复·用户追问"接了这么多GitHub项目会不会互相冲突"揪出的真断链）**：
`chart`（图表/图型，如 waterfall/line_compare，策略层技术词汇）和 `page_function`（页型手法，如"金句主张"/
"数据论断"，`exemplars/页型卡库.json` 101张真实deck拆解出来的中文修辞词汇）是**两个正交维度**，不是一一
对应关系——旧版 `CHART_TO_PAGEFUNC` 把 chart 的英文技术名直接当 page_function 去检索页型卡，实测
`search_deck_cards(page_function="waterfall", ...)` 精确/模糊匹配全部 0 命中（英文子串永远匹配不上中文
卡），检索**静默退化成只看 domain/intent**，一张要放瀑布图的数据页，检索到的示范范本是"金句主张"/
"情绪slogan页"这类不相干的手法卡。现在的优先级链：`add_line(page_function=...)` 显式指定
（阶段4引导对齐时若已查过页型卡库、有贴切真实卡就传，見 SKILL.md"page_function选型查范本库"）
> `page_type`（节奏角色·封面/转场/数据论断/情绪slogan/高潮/落幕/决策/创意展示，5/9 类与卡库有真实子串命中）
> `chart`（技术名兜底·至少让人读 prompt 时知道这页要画什么图）。`chart` facet 独立传递给制作层，
真正驱动"要不要调 `engine/chart_shapes.py`"这件事，不再跟 page_function 混为一谈。
"""

from __future__ import annotations

import json
from pathlib import Path

from reinforce.deck_rules.storyline import run_storyline_gate
from reinforce.deck_state import add_page, new_outline

SCR = {"S", "C", "R"}  # Situation 建共识 / Complication 制造张力 / Resolution 数据+结论
REQUIRED_CARD = ["purpose", "intent", "audience", "decision_ask"]  # 目的卡必填

# ── 故事框架（2026-07-01·gist_AI-Presentation-Coach 价值评估🟢采纳·D6 决策记录）──
# SCR 是本项目默认叙事骨架【出处:ai-skills/deck-pipeline】，不属于下面 13 个——13 个来自
# 【出处:coach/AI-presentation-coach.md 原文 Storytelling Frameworks 1-13】，stage 名忠实取自原文
# 结构描述（不是凭空归纳的漂亮词），"适用"列取自原文各框架的 "Best suited for" 一句。
# `new_storyline(framework=...)` 缺省仍是 "SCR"（不破坏既有行为），这里只是新增可选项。
FRAMEWORK_STAGES = {
    "SCR": ["S", "C", "R"],
    "SCQA": ["Situation", "Complication", "Question", "Answer"],
    "minto_pyramid": ["结论", "论据"],
    "before_change_after": ["Before", "Change", "After"],
    "abt": ["And", "But", "Therefore"],
    "golden_circle": ["Why", "How", "What"],
    "three_act": ["铺设", "对抗", "解决"],
    "hero_journey": ["冒险", "胜利", "改变归来"],
    "pixar_spine": ["Once upon a time", "Every day", "Until one day"],
    "jtbd": ["客户的job", "方案被雇来解决", "达成的结果"],
    "challenger_sale": ["教新视角", "数据建论证", "定位唯一前路"],
    "nested_loops": ["开始主故事", "穿插案例小故事", "回归主故事收束"],
    "mountain": ["起势", "多重受阻", "climax成功"],
    "freytag": ["铺垫", "上升", "高潮", "下降", "结局"],
}
FRAMEWORK_PICK_WHEN = {
    "SCR": "本项目默认骨架·配 mode=pyramid 结论先行论证",
    "SCQA": "咨询·战略提案·说服分析型受众",
    "minto_pyramid": "高管简报·董事会·受众时间紧只要结论先行",
    "before_change_after": "销售·案例·要展示可衡量的 ROI/impact",
    "abt": "高管摘要·电梯陈述·要求简明逻辑清晰",
    "golden_circle": "愿景型·公司文化·发起运动/号召",
    "three_act": "一般商务陈述·项目进展汇报",
    "hero_journey": "励志主题·组织转型·颠覆性理念发布",
    "pixar_spine": "内部会议·快速 pitch·想简单建立情感连接",
    "jtbd": "产品 pitch·技术路线图·聚焦客户同理而非功能罗列",
    "challenger_sale": "高 stakes 销售·思想领导力演讲·想颠覆客户现有认知",
    "nested_loops": "领导力演讲·培训·用多个小案例讲透一个中心原则",
    "mountain": "项目复盘·产品研发历程·讲一段多次受挫后成功的旅程",
    "freytag": "深度案例研究·事后复盘·还原一个关键事件的完整build-up",
}
# mode×framework 软契合提示（2026-07-01·用户追问"接了这么多GitHub项目会不会冲突"揪出的第二个缺口）：
# mode(怎么论证，来自ppt-master 08方法论)和framework(逐行叙事弧，来自coach 13框架)此前完全独立校验，
# 理论上能选出 mode=pyramid(结论先行·Minto哲学)配 framework=hero_journey(先铺垫后揭晓)这种字面合法但
# 叙事哲学互相拧着的组合。下表按 coach gist 原文"Best suited for"一句归纳(非猜测)——只是软提示(warn)，
# 不是硬拦(error)：允许用户明知故犯选"不常见搭配"，但至少要有人看到提示、不是悄悄选歪都没人提醒。
# SCR 是项目默认骨架，CFO/Descente 两个真实demo都验证过能配任意mode，不设限制(不在此表=不检查)。
FRAMEWORK_MODE_AFFINITY = {
    "SCQA": {"pyramid", "briefing"},                    # 咨询战略提案·分析型受众
    "minto_pyramid": {"pyramid", "briefing"},            # 高管简报·结论先行
    "before_change_after": {"narrative", "showcase"},    # 案例/ROI展示
    "abt": {"pyramid", "briefing"},                      # 电梯陈述·精炼直接
    "golden_circle": {"narrative", "showcase"},          # 愿景/文化/运动
    "three_act": {"narrative", "showcase"},              # 戏剧张力·铺设对抗解决
    "hero_journey": {"narrative", "showcase"},           # 励志/组织转型
    "pixar_spine": {"narrative", "showcase"},            # 简单情感连接
    "jtbd": {"narrative", "briefing"},                   # 产品pitch·客户同理
    "challenger_sale": {"pyramid", "narrative"},         # 教新视角+数据论证并重
    "nested_loops": {"narrative", "briefing"},           # 培训·多案例讲principle
    "mountain": {"narrative", "showcase"},               # 历程/多次受挫后成功
    "freytag": {"narrative", "showcase"},                # 深度案例·戏剧build-up
}

# ── mode × delivery_purpose × visual_style 三个独立锁定的轴 ──────────────────
# 「mode = 你怎么论证；delivery_purpose = 交付密度（演讲/阅读）；visual_style = 长什么样（美学）」
# 收窄到 4 种 mode（CLAUDE.md 硬纪律4：排除 instructional 培训教程场景，不是我们的高 stakes 定位）。
MODES = {"pyramid", "narrative", "briefing", "showcase"}
# pyramid   = 结论先行·MECE论据·每数字配comparison（决策支持/分析/战略/董事会·≈原"论证型"·与00-06强候选交叉印证）
# narrative = 情景→张力→解决的故事弧（pitch/案例/品牌故事/融资·≈原"创意提案型"）
# briefing  = 中性完整·可扫读·无预设立场（状态汇报/参考资料/周报）
# showcase  = 视觉主导·大图大数字·情绪节奏（发布会/品牌揭幕/活动开场）
#
# D18 FR7.1 正名（ppt-master 机制考古揪出的挪用）：本字段集此前叫 VISUAL_STYLES——那其实是
# ppt-master 的 delivery_purpose（密度轴·07 双模式·真样本 某品牌/Lulu 背书），真正的视觉美学轴
# 在系统里不存在，prompt 还写死"一个高亮色其余灰"→ 产出塌缩单色卡片网格（第一轮实测病根第一名）。
# 现在两轴分开：delivery_purpose 管密度节奏，visual_style 管美学语言（18 风格手册·spec_lock 锁定）。
# D19 FR3 三值化：新增「预读讲解版」——用户真实场景（方案先发客户自读、看完再开会讲）在
# 两态间没有归宿（第二轮实测提出）。三特征：密度取中/subtitle 导读保留（支持自读）/备注按
# 现场讲写（支持后讲）；节奏=要转场不强制情绪页（check_rhythm 柔化分流）。07 方法论扩展。
DELIVERY_PURPOSES = {"演讲版", "阅读版", "预读讲解版"}
VISUAL_STYLES = DELIVERY_PURPOSES  # 兼容别名·勿在新代码使用（旧测试/demo 引用它·一并迁移后删）
PAGE_TYPES = {"封面", "目录", "转场", "数据论断", "情绪slogan", "高潮", "落幕", "决策", "创意展示"}  # 页型=节奏角色(创意展示=pitch 活动方案页)

# chart_shapes.py 有确定性几何引擎的三种高stakes图表——命中时 build_deck_prompt 会强制注入调用提示
# （2026-07-01·不再靠 CHART_TO_PAGEFUNC 这层已删除的错位映射去"猜"该不该用，chart facet 独立传递）。
CHARTS_WITH_ENGINE = {"waterfall", "gantt", "mekko"}


def new_storyline(brief, purpose, intent, audience, decision_ask,
                  domain=None, audience_note="", scene="战略汇报", visual_style=None,
                  mode="pyramid", framework="SCR", expected_pages=None,
                  delivery_purpose=None, brand=None) -> dict:
    """建 storyline 骨架（先填目的卡·阶段1产物）。mode / delivery_purpose / visual_style 三个独立轴，分开问用户。

    expected_pages = (min, max) 页数区间，可选（2026-07-01 补·问题收口D）：**不是阶段1这里问的**
    ——阶段1还没拆分支，问页数只能瞎猜。这个字段设计给阶段2假设树定了之后再回填（见
    `reinforce.strategy_prompts.prompt_stage2_page_scope` 生成的内容感知推荐，用户拍板后回填这里）。
    留 None 表示未声明预期页数，`deck_rules/storyline.py::check_page_count_consistency` 会跳过不查。

    mode = pyramid/narrative/briefing/showcase（怎么论证：叙事骨架/标题语态/决定硬门分流）。
    delivery_purpose = 演讲版/阅读版（交付密度：07 双模式·节奏/留白/密度，真样本背书）。
    visual_style = 视觉美学风格（D18 FR7.1 新增真美学轴·spec_lock.AESTHETIC_STYLES 18 风格+custom）
      ——策略层可先记录用户倾向，设计定稿阶段（制作 SKILL 阶段1.5）三档光谱确认后锁进 spec_lock；
      留 None = 到设计定稿再选。
      ⚠️ 兼容迁移：D18 前本参数被挪用为{演讲版,阅读版}（其实是密度轴）——旧调用传这两个值时
      自动挪进 delivery_purpose，不当美学值（否则 61 处既有调用全炸）。
    framework = 逐行 stage 用哪套故事框架（缺省 "SCR"·本项目默认骨架，向后兼容），
      可选 `FRAMEWORK_STAGES` 里其余 13 个——**跟 mode/delivery_purpose 一样是引导对齐项，
      不是自动选**：按 `FRAMEWORK_PICK_WHEN[候选]` 给用户一句推荐理由+权衡，用户拍板（CLAUDE.md 铁律0）。
    """
    if visual_style in DELIVERY_PURPOSES:
        # 旧语义调用（visual_style="阅读版"）：值挪去密度轴，美学轴置空——静默兼容不破坏任何旧调用
        delivery_purpose = delivery_purpose or visual_style
        visual_style = None
    return {
        "brief": brief, "purpose": purpose, "scene": scene,
        "delivery_purpose": delivery_purpose or "阅读版",
        # brand（D19 FR5.1）：客户品牌名——交棒时自动生成 outline.brand_terms（品牌名含数字如
        # "059"时豁免 check_source 误判）；回灌管线的 brand 归属也从这读，不再靠调用方手传。
        "brand": brand,
        "visual_style": visual_style, "mode": mode, "framework": framework,
        "intent": intent if isinstance(intent, list) else [intent],
        "audience": audience if isinstance(audience, list) else [audience],
        "audience_note": audience_note,
        "domain": domain if isinstance(domain, list) else ([domain] if domain else []),
        "decision_ask": decision_ask, "expected_pages": expected_pages,
        "governing_thought": "", "sub_hypotheses": [], "lines": [],
    }


def delivery_purpose_of(sl: dict) -> str | None:
    """读密度轴（演讲版/阅读版）——统一兼容口：新字段 delivery_purpose 优先；旧落盘数据
    （D18 前 visual_style 存的就是密度值）兜底。所有判定点（check_rhythm 等）经此读取，
    不要直接摸字段。"""
    dp = sl.get("delivery_purpose")
    if dp in DELIVERY_PURPOSES:
        return dp
    legacy = sl.get("visual_style")
    return legacy if legacy in DELIVERY_PURPOSES else None


def set_hypothesis_tree(sl, governing_thought, sub_hypotheses) -> dict:
    """填假设树（阶段2）：塔顶 Lead + 子假设（每个必须带可证伪 test·『能杀死该分支的检验』）。

    sub_hypotheses 每项可选带 `verified`（结构建议 {"answer": str, "source": str}，2026-07-01 补·
    问题收口调研 R-B）：test 声明的检验阶段3调研真跑完、有结论后回填，喂
    `deck_rules/storyline.py::check_hypothesis_tested` 核对"押的答案有没有真被验证过"，
    不回填不拦（warn），但阶段4 storyline 定稿前该扫一眼有没有假设声明了检验却从没人验证。
    """
    sl["governing_thought"] = governing_thought
    sl["sub_hypotheses"] = sub_hypotheses
    return sl


def add_line(sl, n, stage, claim, chart, role="", sowhat="",
             evidence=None, framing=None, page_type="数据论断", subtitle="", page_function=None,
             toc_items=None, part=None, bridge_from=None) -> dict:
    """加一行 storyline = 一页。

    stage = 本行在故事框架里的阶段标签（取值范围由 storyline 声明的 `framework` 决定，见
      `FRAMEWORK_STAGES`——缺省 framework="SCR" 时仍是 "S"/"C"/"R"，向后兼容旧调用不受影响；
      2026-07-01 前参数名叫 `scr`，改名 `stage` 是因为现在不止 SCR 一种框架，字面意思不对了，
      纯改名不改行为，61 处既有调用全是位置参数、无 keyword=scr 用法，改名零破坏性）。
    claim = action title 论点；chart = 图型（技术词汇·waterfall/line_compare/…·驱动是否调
      `engine/chart_shapes.py`，见 `CHARTS_WITH_ENGINE`）；
    evidence = 论证 claim 的一组数据 [{dim 维度, data 数据, counter 堵住的反驳}]——
      一个观点要一组数据从不同维度**合围**（单数据易被单点反驳·用户洞察）；
    framing = 数据的解读立场 {stance 本论点解读, counter_read 反方会怎么解读, basis 选此立场的依据}——
      数据是中性的、靠论点赋义（同一数据可正可负·用户洞察）；framing ≠ 篡改数字，是选真实数据的哪一面强调；
    page_type = 页型/节奏角色（数据论断/情绪slogan/转场/高潮/落幕…·07 演讲版靠它造情绪起伏）；
    subtitle = 导读副标题（阅读版标题下一行说明本页作用·脱离演讲者自读·07 阅读版必填）；
    page_function = 页型手法（`exemplars/页型卡库.json` 的真实中文卡名·如"金句主张"/"案例效果against行业
      中位数柱状对标"）——**2026-07-01 补·可选但建议填**：阶段4写storyline时若已经用
      `reinforce.retrieval.search.search_deck_cards` 查过范本库、有贴切的真实卡，传进来精确检索；
      不传时 `to_outline()` 按 page_type→chart 顺序兜底（`chart` 是技术词汇，不在页型卡词汇体系里，
      检索大概率落空，纯兜底让人读 prompt 时至少知道这页要画什么，别指望它能查到范本）。

    evidence 条目可选带引用字段（source_title/source_outlet/source_date/source_quote/source_url，
    用 engine/research.py::attach_citation 生成）——制作层 engine/svg_layout.py::source_card_from_evidence
    见到这些字段会自动渲染引用卡（标题/媒体/日期/原文片段/URL）。声明式：填了就自动出卡，
    不要在制作脚本里按页号另开一张硬编码表（早期 Descente demo 踩过的反模式）。

    toc_items = 目录页专用（page_type="目录" 时填）：本页列出的章节/小节名列表——喂
    `deck_rules/storyline.py::check_toc_matches_chapters` 核对是否跟后续转场页标题逐字一致
    （2026-07-01 补·此前目录页只有 claim 一个字符串，没地方结构化记录列了哪几项，没数据没法核对）。

    part = 本页所属 Part/章节名（D18 FR2.1·第一轮实测 24 页平铺无章界确诊）——真实 4A deck
    是"封面→目录→[Part×N]→收尾"的章节结构（四真样本交叉实证）；填了它，结构件硬门才能查
    "每 Part 有转场页+章小结"。封面/目录/收尾这类 deck 级页可不填。
    bridge_from = 转场页专用（page_type="转场" 时填）：承接上一章结论的一句话——转场页的职责
    是"接住上章结论+预告本章"（某品牌 章封面淡灰副标机制），空转场只是换个背景色没有承接价值。
    """
    sl["lines"].append({"n": n, "stage": stage, "claim": claim, "chart": chart,
                        "role": role, "sowhat": sowhat,
                        "evidence": evidence or [], "framing": framing or {},
                        "page_type": page_type, "subtitle": subtitle, "page_function": page_function,
                        "toc_items": toc_items or [], "part": part, "bridge_from": bridge_from})
    return sl


def validate_storyline(sl) -> dict:
    """校验 storyline 结构合法性 → {issues, valid}。fail-closed 底线（拒写/拒降解）。

    只管 schema 合法（目的卡/假设树/故事框架弧/行完整）；质量项（论断式/含糊/决策结尾）走机检硬门。
    """
    issues = []
    # ① 目的卡必填
    for k in REQUIRED_CARD:
        if not sl.get(k):
            issues.append({"sev": "error", "msg": f"目的卡缺 {k}"})
    # D18 FR7.1 两轴分开校验（delivery_purpose_of 兼容旧落盘数据里 visual_style 存密度值的形态）
    if delivery_purpose_of(sl) is None:
        issues.append({"sev": "error", "msg": "delivery_purpose 非法或缺失(应 演讲版 / 阅读版·07 双模式·"
                                              "旧字段名 visual_style 的密度值可被兼容读取)"})
    vs = sl.get("visual_style")
    if vs is not None and vs not in DELIVERY_PURPOSES:
        from reinforce.spec_lock import AESTHETIC_STYLES  # 延迟 import·spec_lock 是美学轴真相源
        if vs not in AESTHETIC_STYLES:
            issues.append({"sev": "error",
                           "msg": f"visual_style={vs!r} 不是合法美学风格（18 风格+custom·"
                                  f"见 spec_lock.AESTHETIC_STYLES；密度请用 delivery_purpose 字段）"})
    mode = sl.get("mode", "pyramid")
    if mode not in MODES:
        issues.append({"sev": "error", "msg": f"mode 非法(应 {sorted(MODES)} 之一·08 方法论)"})
    framework = sl.get("framework", "SCR")
    if framework not in FRAMEWORK_STAGES:
        issues.append({"sev": "error",
                       "msg": f"framework 非法(应 {sorted(FRAMEWORK_STAGES)} 之一·coach 13框架+默认SCR)"})
        framework = "SCR"  # 非法时仍按 SCR 走完剩下的行校验，不因这一项错就整段跳过(尽量暴露更多问题)
    affinity = FRAMEWORK_MODE_AFFINITY.get(framework)
    if affinity and mode in MODES and mode not in affinity:
        issues.append({"sev": "warn",
                       "msg": f"mode={mode} 配 framework={framework} 不是常见搭配"
                               f"（{framework} 更常配 {sorted(affinity)}·出处 gist coach「Best suited for」）"
                               f"——不是不能选，确认是不是有意为之，别是顺手选歪没人发现"})
    stages = FRAMEWORK_STAGES[framework]
    # ② 假设树
    if not sl.get("governing_thought"):
        issues.append({"sev": "error", "msg": "缺 governing_thought(塔顶 Lead)"})
    # 2026-07-02 saopan扫盘揪出：sub_hypotheses/lines 显式为 None（set_hypothesis_tree(sl,gt,None)
    # 正是 deck_rules/storyline.py:384 docstring 自己举的"合法但误用"例子）时，第一道结构门先于
    # run_storyline_gate 在这里崩 TypeError——校验器自己不能被崩溃击穿，.get(k,默认) 改 or 兜底。
    subs = sl.get("sub_hypotheses") or []
    for h in subs:
        if not h.get("test"):
            issues.append({"sev": "error", "msg": f"子假设 {h.get('id', '?')} 无可证伪 test"})
    if subs and not (2 <= len(subs) <= 5):
        issues.append({"sev": "warn", "msg": f"子假设 {len(subs)} 条(3 的法则建议 2-5)"})
    # ③ storyline 行
    lines = sl.get("lines") or []
    if not lines:
        issues.append({"sev": "error", "msg": "storyline 无行"})
    seen = set()
    for ln in lines:
        n = ln.get("n")
        if n is None:
            # 行缺 n 此前不查——validate 放行后 to_outline 的 sorted(key=x["n"]) 直接 KeyError，
            # "校验容忍的输入在下一步崩"（saopan 同批）；n 是行主键，缺了就是 error。
            issues.append({"sev": "error", "msg": "有行缺页号 n（行主键必填）"})
            continue
        if n in seen:
            issues.append({"sev": "error", "msg": f"行号重复 {n}"})
        seen.add(n)
        if not ln.get("claim"):
            issues.append({"sev": "error", "msg": f"行 {n} 无 claim"})
        if not ln.get("chart"):
            issues.append({"sev": "warn", "msg": f"行 {n} 无 chart 映射"})
        if ln.get("stage") not in stages:
            issues.append({"sev": "error", "msg": f"行 {n} stage={ln.get('stage')!r} 不在 {framework} 框架的"
                                                    f"{stages} 内"})
    # 框架弧：全部阶段齐全 + 顺序不回头（按 FRAMEWORK_STAGES 声明的顺序，SCR 是这套通用逻辑的默认特例）
    seq = [ln.get("stage") for ln in lines if ln.get("stage") in stages]
    for seg in stages:
        if seg not in seq:
            issues.append({"sev": "error", "msg": f"{framework} 弧缺 {seg} 段"})
    rank = {seg: i for i, seg in enumerate(stages)}
    if seq and any(rank[seq[i]] > rank[seq[i + 1]] for i in range(len(seq) - 1)):
        issues.append({"sev": "error", "msg": f"{framework} 顺序乱(应 {'→'.join(stages)} 不回头)"})
    return {"issues": issues, "valid": not any(i["sev"] == "error" for i in issues)}


def to_outline(sl) -> dict:
    """storyline 降解成制作层 deck_outline（校验通过才转·claim→claim；page_function 见模块顶部
    "page_function 怎么来"说明：显式指定 > page_type 兜底 > chart 技术名垫底）。"""
    r = validate_storyline(sl)
    if not r["valid"]:
        raise ValueError(f"storyline 非法·拒降解：{r['issues']}")
    title = sl.get("purpose") or sl["brief"][:20]
    o = new_outline(title, doc_type=sl.get("scene", "战略汇报"), intent=sl["intent"],
                    domain=sl.get("domain") or ["通用"], audience=sl["audience"],
                    # D19 FR5.1：品牌名自动进豁免表（brand 含数字如"059"时防 check_source 误判）
                    brand_terms=[sl["brand"]] if sl.get("brand") else [])
    prev = None
    for ln in sorted(sl["lines"], key=lambda x: x["n"]):
        # chart 缺失在 validate 里只是 warn（合法），这里硬下标会 KeyError——.get 兜底，
        # pf 三级全空时留空串，由 build_deck 入口的 validate_outline 报"缺 page_function"拦（fail-closed 且报错清楚）
        pf = ln.get("page_function") or ln.get("page_type") or ln.get("chart") or ""
        add_page(o, ln["n"], page_function=pf, claim=ln["claim"],
                 depends_on=[prev] if prev is not None else [],
                 facets={"stage": ln["stage"], "chart": ln.get("chart", ""), "role": ln.get("role", ""),
                         # 制作层渲染数据论断页(callout/合围证据)必须拿到这些·此前漏带是真实管线缺口
                         "page_type": ln.get("page_type", ""), "sowhat": ln.get("sowhat", ""),
                         "subtitle": ln.get("subtitle", ""), "evidence": ln.get("evidence", []),
                         "framing": ln.get("framing", {}), "toc_items": ln.get("toc_items", [])})
        prev = ln["n"]
    return o


def load_storyline(path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_storyline(sl, path) -> dict:
    """校验通过才写（fail-closed·非法拒写）。"""
    r = validate_storyline(sl)
    if not r["valid"]:
        raise ValueError(f"storyline 非法·拒写：{r['issues']}")
    Path(path).write_text(json.dumps(sl, ensure_ascii=False, indent=2), encoding="utf-8")
    return r


def handoff_to_production(sl, path=None, *, current_year: int | None = None,
                          team: dict | None = None, require_acks: bool | None = None) -> dict:
    """策略定稿 → 制作交接卡（出口=入口）：打包 storyline 定稿 + 降解 outline + 对齐元信息，交制作工作流。

    fail-closed：storyline 非法拒交接 + 质量机检（run_storyline_gate）有 error 同样拒交接（2026-07-01 接入——
    此前只查 schema 合法，决策结尾/证据合围等质量项只在 SKILL.md 靠 Claude 对话里手动调 run_storyline_gate，
    没调用也无从拦，是写好测试全绿却没接入任何自动链路的孤岛代码）。给 path 则落盘 json。
    对应 Novel 交接卡（跨阶段续上、不靠上下文）。制作侧拿 handoff['outline'] 直接 build_deck。
    current_year：透传给 run_storyline_gate 查"过期预计"（引擎核心不碰系统时钟·由调用方显式传入当前年份）。
    team：多角色策划团队状态（planning_team dict）——传入则跑 check_open_questions_carried
    把"遗留问题被遗忘"弱提示并进 quality_warnings（2026-07-02 saopan·孤岛A4摘帽：该检查此前
    零生产调用点，策略 SKILL 引用清单点名了它、正文却没有任何调用步骤；交棒是全流程遗留问题
    的最后收口点，接在这里。warn 不拦，语义判断留人审）。
    require_acks（D18 FR1.2 关键节点 ack 闸）：storyline 定稿是交棒前最硬的关键节点——用户没说
    "定了"，机器不能自作主张交棒（第一轮实测确诊"机检假阳性完稿才发现"的上游病根就是没人等确认）。
    三态：None（默认·自动）=team 传入且带 user_acks 机制（有 confirm_granularity 字段·D18 后
    new_planning_team 造的 team 都有）才查——旧落盘 team（某品牌 一代·无此字段）与不传 team
    的旧调用零破坏；True=强制查（team 缺字段按默认 key_nodes 对待）；False=显式跳过（留痕回放
    旧数据等场景）。confirm_granularity="minimal"/"direct_through" 是用户自己选的快进档
    （granularity_quote 有用户原话留痕），尊重用户选择不查；直通档下策略定稿直接进制作不等
    用户说"做 deck"（D21·跨流直通）。
    """
    r = validate_storyline(sl)
    if not r["valid"]:
        raise ValueError(f"storyline 非法·拒交接：{r['issues']}")
    gate = run_storyline_gate(sl, current_year=current_year)
    if not gate["passed"]:
        raise ValueError(f"storyline 质量机检未过·拒交接（fail-closed）：{gate['issues']}")
    if team is not None:
        from reinforce.planning_team import check_open_questions_carried  # 延迟 import 防环
        gate["issues"] = gate["issues"] + check_open_questions_carried(team)
    # D18 FR1.2 ack 闸（fail-closed·宁拦勿放）：只认 record_user_ack 留的用户原话记录，
    # 不认任何布尔位——"用户确认过"必须有原话可回放，防假绿同一条纪律。
    check_acks = require_acks if require_acks is not None else (
        team is not None and "confirm_granularity" in team)
    if check_acks:
        t = team or {}
        gran = t.get("confirm_granularity", "key_nodes")
        if gran not in ("minimal", "direct_through"):  # 两档快进放行——granularity_quote 留有用户亲选原话（D21）
            acks = t.get("user_acks") or []
            if not any("storyline定稿" in (a.get("node") or "") for a in acks):
                raise ValueError(
                    f"缺关键节点确认·拒交棒（D18 FR1.2·fail-closed）：team['user_acks'] 里没有 "
                    f"node 含「storyline定稿」的记录（本单确认粒度={gran}）——storyline 必须用户"
                    f"亲口确认定稿才能交制作，用 planning_team.record_user_ack(team, "
                    f"'storyline定稿', 用户确认原话) 留痕后再交棒（铁律0 以人为主）")
    handoff = {
        "kind": "strategy_to_production_handoff",
        "purpose": sl.get("purpose"),
        "visual_style": sl.get("visual_style"),
        "richness": sl.get("richness"),  # D22 视觉丰富度档（开场配置舱/设计定稿拍板·可 None=制作侧按类型默认推荐）
        "delivery_purpose": delivery_purpose_of(sl),  # D18 FR7.1·交接卡两轴都带全
        "mode": sl.get("mode"),
        # 批③🔴7：确认粒度+根授权原话随交接卡走——制作侧直通档要调 publish_deck(
        # direct_through_waiver=granularity_quote)，不带过去就只能靠对话记忆（会话压缩即丢，
        # 审计链在交棒处断裂）。team=None / 旧 team 缺字段时两键都是 None（零破坏）。
        "confirm_granularity": (team or {}).get("confirm_granularity"),
        "granularity_quote": (team or {}).get("granularity_quote"),
        "governing_thought": sl.get("governing_thought"),
        "storyline": sl,
        "outline": to_outline(sl),      # 制作直接拿这个 build_deck(outline, svg_provider, notes_map)
        "quality_warnings": gate["issues"],  # run_storyline_gate 的 warn 级问题（error 已在上面拦）·喂人审（铁律2）
        "status": "策略定稿·待制作",
    }
    if path:
        Path(path).write_text(json.dumps(handoff, ensure_ascii=False, indent=2), encoding="utf-8")
    return handoff
