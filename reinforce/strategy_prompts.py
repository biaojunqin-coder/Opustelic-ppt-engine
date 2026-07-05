"""策略五阶段 prompt 模板（拼装·非写死）——供外部 LLM provider 或运行时 Claude 参考。

对应策略工作流 SKILL 五阶段。每个拼「方法论引用 + brief/状态 + 输出格式 + 硬规范」。
默认运行时 Claude 按 SKILL 现场做·无需调本模块；接外部 API 苦力（providers.openai_compatible_provider）时喂这些 prompt 省主模型 token。

⚠️ **架构现实（研究/知识层扫盘暴露）**：制作层有 `engine/pipeline.py::build_deck` 这种真正被自动
调用的编排函数，`build_deck_prompt` 里的范本卡/表达手法卡检索因此是"代码强制"，Claude 想漏都漏不掉。
策略层**没有对应的自动编排器**——运行时是 Claude 按 SKILL.md 对话式推进，本模块的函数不在"不调用
就不可能生效"级别的强制调用链上。stage2/stage3 里接入的 `search_frameworks`/`search_facts` 检索
**只有在真调用了这些函数时才会生效**——比"纯文字指令靠 Claude 自觉手动 import search.py"更进一步
(至少封装成了可测试的真代码)，但仍不是"不可能漏掉"级别的强制，这是策略层"无编排器"这个架构现实
决定的，不是这次没做够。2026-07-01 补：`examples/demo_strategy.py` 已接入真调用（此前只有
`test_strategy_prompts.py` 调过，demo 层面从没验证过），证明"传 domain 就真检索到真实卡片"不是
纸面设计——但 demo 终究是脚本模拟，真正的强制力仍要靠 SKILL.md 指引 + Claude 现场自觉调用。
"""

from __future__ import annotations

from reinforce.retrieval import search as R


def prompt_stage1_purpose(brief_text: str) -> str:
    """阶段1·判目的 + 对齐理解（引导式·非批处理）。"""
    return (
        "# 阶段1·判目的 + 对齐理解（引导式·非批处理）\n"
        f"brief（节选）：{brief_text[:2500]}\n\n"
        "任务：① 把你对 brief 的理解摊开（主线/核心诉求/模块/人群/预算/约束/禁忌）"
        "② **一次只问一个点**请用户确认：先说「brief 里看到什么（带原文）→ 我的理解 → 我的推荐+理由+权衡」→ 用户定"
        "③ 由粗到细（主线→场地/范围→模块→细节），反复对齐到零偏差才出目的卡。\n"
        "输出目的卡：purpose / intent / audience / decision_ask + delivery_purpose(演讲/阅读·07双模式) "
        "+ mode(pyramid/narrative/briefing/showcase·08方法论·怎么论证)——独立锁定的轴，分开问用户；"
        "visual_style(视觉美学·18风格) 可先记录倾向，设计定稿阶段三档光谱再正式锁(D18 FR7.1)。\n"
        "⚠️ 绝不读完 brief 就一次性吐 storyline——必有偏差。"
    )


def prompt_stage2_tree(purpose: str, domain: list[str] | None = None, top_frameworks: int = 3) -> str:
    """阶段2·议题树/假设树（方法论03）。domain 传入时检索分析框架库（真实 deck 抽取的可复用
    分析工具）拼进 prompt，供拆分支前参考；不传/无命中则跳过（不强求套现成框架）。
    """
    L = [
        "# 阶段2·结构化思维（议题树/假设树·方法论03）",
        f"目的：{purpose}",
        "任务：MECE 拆问题空间。还不知道什么重要→议题树；Day-1 押答案→假设树。3 分支法则·每末端配可证伪检验（能杀死它的检验）。",
    ]
    if domain:
        frameworks = [c for c, _ in R.search_frameworks(domain=domain, top=top_frameworks)]
        if frameworks:
            L.append("\n## 可参考的分析框架库（真实 deck 抽取·找到合适的再用，找不到正常现拆）：")
            for f in frameworks:
                L.append(f"- {f.get('framework_name')}｜结构：{f.get('structure')}"
                         f"｜何时用：{f.get('pick_when')}｜何时不用：{f.get('skip_when')}")
    L.append("\n输出：tree(question / mode / branches[key, claim, test, confidence])。")
    return "\n".join(L)


# 真实样本页数参考（2026-07-01·问题收口D调研·样本量单薄·每场景仅1份·仅供参考起点非统计规律）
_PAGE_COUNT_SAMPLES = {
    "投资融资": ("Airbnb 2009 pitch", 14),
    "咨询诊断": ("McKinsey×MTA COVID财务影响评估", 38),
    "营销品牌": ("某品牌 130 Communication Plan", 52),
    "产品方案": ("LuluMP小程序改版方案", 37),
}


def prompt_stage2_page_scope(governing_thought: str, sub_hypotheses: list[dict], scene: str = "") -> str:
    """阶段2 收尾·页数区间引导对齐（2026-07-01·问题收口D·用户拍板"假设树定了才问篇幅，不是阶段1
    一上来瞎猜"）：基于已拆分支给内容感知的最少/可扩展建议，不是套用户根本还没有依据回答的抽象数字。
    """
    n = len(sub_hypotheses)
    branches_text = "\n".join(f"  - {h.get('claim', h.get('id', '?'))}" for h in sub_hypotheses)
    min_pages = n + 2  # 1 执行摘要 + 每分支至少 1 页核心论证 + 1 决策收尾
    sample = _PAGE_COUNT_SAMPLES.get(scene)
    sample_line = (f"\n参考样本（样本量单薄·每场景仅1份·仅供参考起点非统计规律）：「{scene}」场景真实样本"
                   f"「{sample[0]}」{sample[1]}页。" if sample else "")
    return (
        "# 阶段2 收尾·页数区间引导对齐（问题收口D·假设树定了才问篇幅）\n"
        f"塔顶 Lead：{governing_thought}\n"
        f"已拆 {n} 个分支：\n{branches_text}{sample_line}\n\n"
        f"任务·摊功课：① 最少 {min_pages} 页能讲完——1页执行摘要 + {n}页(每分支1页核心论证) + 1页决策收尾，"
        "对应上面每个分支各占1页，逐条列给用户看覆盖了什么。"
        "② 可扩展项（逐条给用户选，不是笼统说'多加几页'）：论证薄弱/有强反驳的分支 +1页专门堵反驳"
        "（配 check_counter_addressed 机检）；证据维度单薄的分支 +1页补充证据；"
        "需要先建立共识事实再冲突的 +1页共识铺垫（同真实咨询deck常见S-S-C结构）。"
        "③ 给推荐区间 + 理由 + 权衡，用户可直接采纳，也可基于评审时长/甲方偏好等AI没有的信息自己定"
        "——不是让用户瞎猜一个数，是基于已拆分支给结构化选项，用户拍板（CLAUDE.md 铁律0）。\n"
        "输出：expected_pages=(min, max)，喂 storyline_state.new_storyline(expected_pages=...)，"
        "阶段4 storyline 定稿时 deck_rules/storyline.py::check_page_count_consistency 核对"
        "『做出来的和当初定的差多少』。"
    )


def prompt_stage3_research(claim: str, domain: list[str] | None = None, top_facts: int = 3,
                            current_year: int | None = None) -> str:
    """阶段3·调研 + 数字溯源（方法论01 雷区7）。domain 传入时检索行业知识库（真实 deck 抽取的
    行业事实）拼进 prompt，能直接用的就省一趟外部调研；current_year 传入时用 flag_stale_facts
    标出候选里明显过期(≥2年)的条目，提醒必须核实或换 research() 找最新数据，不能直接照抄过期数字。
    """
    L = [
        "# 阶段3·调研 + 数字溯源",
        f"论断：{claim}",
        "任务：把论断挖到可溯源数据；数字**原值照抄·绝不概括**，每个带 source。运行时可用 WebSearch/WebFetch（免费）。",
    ]
    if domain:
        facts = [f for f, _ in R.search_facts(domain=domain, top=top_facts)]
        if facts:
            stale_ids = set()
            if current_year is not None:
                stale_ids = {s["id"] for s in R.flag_stale_facts(facts, current_year=current_year)}
            L.append("\n## 可参考的行业知识库（真实 deck 抽取·引用前核实 timeliness）：")
            for f in facts:
                flag = " ⚠️疑似过期，需核实或换最新数据" if f.get("id") in stale_ids else ""
                L.append(f"- {f.get('fact')}｜来源：{f.get('source_citation')}"
                         f"｜时效性：{f.get('timeliness')}{flag}")
    L.append("\n⚠️ 调研工具 fact-check 是 LLM 自评·不当硬信号；数字溯源走机检 check_evidence_source / 人审。")
    return "\n".join(L)


def prompt_divergence(node: str, findings_digest: str | list[str], n_cards: int = 3,
                      history: list[dict] | None = None) -> str:
    """发散环节引导 prompt（D18 FR1.3 + D19 FR4.1/FR4.2）：在 node 节点产出 n_cards 张方向卡摊给用户收敛。

    第一轮实测确诊"策略单主线无发散"——研究群收工后一条道走到黑，用户从没被给过"还能怎么打"
    的选择空间。默认触发点：策略方向（研究群收工后）与创意概念（策略定稿后），其余 leader 按单
    规划、用户可随时要求。findings_digest=已有角色交接的 key_findings 摘要（str 或 list）——
    发散的原料是已经做完的研究，**不重新调研**：同一批洞察的不同组合解读才叫方向，边发散边补
    研究会把发散点拖成研究点。

    D19 FR4.1（第二轮实测确诊"程序给的方向不考虑执行难度"）：每张卡必须实评执行难度
    （团队能力/预算/周期/供应链依赖四维·结果由 fit 字段承载），且 N 张卡执行难度**拉开梯度**
    ——059 实测三张卡里两张被用户判"执行难度太高"被迫三选一，发散等于白做了一半。
    D19 FR4.2：history 传入 planning_team.divergence_history() 的跨 deck 聚合结果
    （[{deck_id, node, chosen, reason}]）时，把该用户过往收敛拍板的**原话理由**注入 prompt
    末尾——用途是把执行可行性等已知偏好前置进方向设计，不是让生成器只出保守方向。
    """
    digest = ("\n".join(f"  - {f}" for f in findings_digest)
              if isinstance(findings_digest, list) else str(findings_digest))
    p = (
        f"# 发散环节·「{node}」产出 {n_cards} 张方向卡（D18 FR1.3·发散点=硬停点）\n"
        f"已有 key_findings（发散只准引用它们·**不重新调研**）：\n{digest}\n\n"
        f"任务：基于上面已有洞察，产出 {n_cards} 张**真正不同打法**的方向卡（不是同一方向的几种"
        "措辞），按三档拉开呈现给用户——safe（贴行业惯例·稳妥承接共识）→ shifted（外放一档）→ "
        "bold（挑战默认）。\n"
        "每张卡 schema（用 planning_team.new_direction_card 构造）：name 方向名 / core_logic "
        "一句话核心逻辑 / supporting_findings 支撑洞察（逐条引用上面 key_findings 原文）/ "
        "play_summary 打法概要 / why_win 为什么可能赢 / risks 主要风险 / fit 适配度+执行难度实评。"
        "**每张必须带「为什么可能赢/主要风险」**——不给权衡的选项等于替用户做决定（越俎代庖·必偏差）。\n"
        f"⚠️ 执行难度硬要求（D19 FR4.1·059 实测确诊）：① 每张卡必须**实评执行难度**并写进 fit "
        "字段——团队能力/预算/周期/供应链依赖四维逐一写实话（写「中等」「较高」这类敷衍词不算"
        "评估，要写「需自建 12 人内容团队」「供应链依赖 3 家上游且无替代」级别的具体判断）；"
        f"② {n_cards} 张卡的执行难度必须**拉开梯度**——至少一张是现有团队/预算直接落地的轻量"
        "打法，不许全部高难炫技：上一单用户实测三张卡里两张「执行难度太高」被迫三选一，"
        "创意再好落不了地也是白发散。\n"
        "⚠️ 发散点=硬停点：摊完卡必须停下等用户收敛拍板（选哪张/为什么），绝不自行选定往下推进"
        "（铁律0）。用户拍板后用 planning_team.record_divergence(team, node, cards, chosen, reason, "
        "user_quote) 留痕——reason（用户为什么选它）是飞轮要内化的偏好知识（FR6.4），必须问到，"
        "留痕会自动记该发散点的 ack。"
    )
    # D19 FR4.2 历史偏好原话注入：只注原话不注画像（暂不做偏好画像提炼——2 条样本抽象必歪，
    # 等 5+ 条决策再人工评估是否提炼，过早抽象是飞轮大忌·D19 用户拍板）。
    if history:
        lines = [f"- 『{h.get('reason')}』（{h.get('deck_id')}·{h.get('node')}）"
                 for h in history if h.get("reason")]
        if lines:
            p += (
                "\n\n## 该用户过往收敛拍板（原话·D19 FR4.2）\n"
                "供你把执行可行性等已知偏好**前置进方向设计**——不是让你只出保守方向"
                "（bold 档照出，但每张都得过「这个用户拍板时最在意什么」这道筛）：\n"
                + "\n".join(lines))
    return p


def prompt_stage4_storyline(meta: dict, *, with_slot_patterns: bool = True) -> str:
    """阶段4·Storyline（方法论01/03/07/08）。

    with_slot_patterns（D20 FR1.3）：拼入六槽位结构性文案范式速查——bridge_from/subtitle/
    章小结行/决策 claim 的**写作**发生在本阶段，正向范式必须在写作现场在场（第三轮实测
    确诊：元叙述全长在结构性文案位置，病根之一是策略层写这些字段时无范式可依）。
    """
    L = [
        "# 阶段4·Storyline（方法论 01/03/07/08）",
        f"delivery_purpose：{meta.get('delivery_purpose') or meta.get('visual_style')} · mode：{meta.get('mode')}",
        "任务：每行=一页。**pyramid/briefing**→论点 + 一组证据合围(≥2 维·覆盖反驳) + framing(立场+反方)；"
        "**narrative/showcase**→big idea + 创意展开（创意展示页不要求 evidence/溯源）。",
        "按 SCR 分组·演讲版有情绪节奏(转场/情绪/高潮/落幕)·阅读版/预读讲解版每页有导读副标题。",
        "输出：lines[n, stage, claim, chart, page_type, evidence, framing, subtitle, part, bridge_from]。",
        "硬规范：标题论断式（创意页除外）· pyramid/briefing 数字带 source · 页面展示整组证据且与讲解同源"
        "· **每句话讲客户的生意不讲这份 deck 自己**（禁元叙述：诊断完毕/下一步是/这份提案…·D20）。",
    ]
    if with_slot_patterns:
        slots = ["章间桥", "章小结", "诊断收束", "ask收尾", "目录命名", "落幕"]
        lines = []
        for s in slots:
            top = R.search_expression_cards(slot=s, top=1)
            if top:
                c = top[0][0]
                lines.append(f"- 「{s}」{c.get('formula')}｜真例：{str(c.get('demo'))[:60]}"
                             + (f"｜⛔{str(c.get('anti_pattern'))[:50]}" if c.get("anti_pattern") else ""))
        if lines:
            L.append("\n## 结构性文案槽位范式速查（写 bridge_from/subtitle/小结行/决策 claim 时按此·"
                     "全量卡 `search_expression_cards(slot=...)` 检索）：\n" + "\n".join(lines))
    return "\n".join(L)


def prompt_stage5_review(meta: dict) -> str:
    """阶段5·质量门 + 文字 demo（方法论05）。"""
    return (
        "# 阶段5·质量门 + 文字 demo（方法论 05）\n"
        "任务：三道审查（action title / storyline / slide content 各 ≥90%）+ Critic 红黄绿（非 Red 才可交）。\n"
        "输出「文字 demo」（每页=标题+要点+解读）给用户拍板——**生成≠批准**，用户确认才交制作。\n"
        "🚪 闸：三道审查过线 + Critic 非 Red + 用户确认（🟢 落在人·防假绿）。"
    )
