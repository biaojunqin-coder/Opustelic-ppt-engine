"""三道审查 + Critic 红黄绿（策略阶段5 · 质量门人审）——对应方法论 05。

⚠️ **人审非机检**：这是给人勾的结构化清单 + 汇总，绝不 LLM 自动打分当 🟢 硬信号（防假绿 L2）。
机检硬门在 deck_rules（能判死的项）；本模块承载"审美 / 逻辑"这类必须人审的判断（出口 = 人填的分）。
三道审查各 ≥90% 且 Critic 非 Red 才可交（方法论 05）。
"""

from __future__ import annotations

import re

# 三道审查的检查点（方法论 05 · 咨询级可勾选清单）
REVIEWS = {
    "action_title": ["标题是论断非主题", "带数字/方向·可证伪", "只读标题能复述推荐(水平逻辑)", "无含糊用语"],
    "storyline": ["SCR 三段齐全有序", "≤3 核心洞察", "逻辑无跳跃", "末页带 owner+日期决策", "一组证据合围非单数据",
                  "跨页关键事实一致(同一指标不同页数值不矛盾)",
                  "每条声明要堵的反驳(counter)，证据是否真的驳倒了它(非仅声明未兑现，语义判断见人审)"],
    "slide_content": ["一页一焦点", "数字带 source", "视觉重心明确", "留白充分", "演讲版有情绪节奏/阅读版有导读副标题",
                       "封面/收尾有具体钩子+构图策略(非默认标题+副标题+背景)",
                       "强调色≤2种·其余灰(不喧宾夺主)", "同行/同列元素对齐无漂移·无意外重叠",
                       "呼吸节奏页(per_page[n].rhythm=breathing)不堆卡片网格",
                       "AI生成底图确认无字(生成台账kind=generation的图逐张过目·prompt指令≠成图保证·无AI生图的deck直接判True·D26)",
                       "整页零工作语言——把看 deck 的人当客户(无字段标签/无推演话术/无内部定位符·D19)",
                       "全部标题串读像连贯的商业论证而非操作手册(Read-Through·无一句在谈论deck自身·D20)"],
}
# 上面三项(强调色/对齐/呼吸页)对应 ppt-master visual-review.md 的 S7/S4+H3+H6/S10——
# 这几条要"看渲染后的样子"才能准判，机检做不动(几何近似误报率太高，见 deck_rules/visual_review.py
# 的范围声明)，所以放人审清单不是机检；H1/H4/H8/S6 这几条能从 SVG 源码结构直接算出来的，已经是
# pipeline.build_deck 自动跑的机检(reinforce/deck_rules/visual_review.py::run_visual_gate)，不用人工勾。
PASS_THRESHOLD = 0.9  # 每道审查 ≥90% 过线


def new_review() -> dict:
    """建空审查表（给人勾）。每项默认 None=未评。"""
    return {r: {item: None for item in items} for r, items in REVIEWS.items()}


def score_review(review: dict) -> dict:
    """汇总人填的审查 → 每道通过率 + 是否过线（≥90%）。未评(None)按未过算（保守·防假绿）。

    批④容错：review 缺某道角色键（旧落盘/手编 JSON/REVIEWS 后来加了新道）＝该道**全部未评**
    ——按 0 通过率+全 unrated 计入汇总（critic_light 自然给黄），不再 KeyError 崩掉整个汇总。
    方向仍是保守：缺道绝不算过（fail-closed），只是"读得懂"。"""
    out = {}
    for r, items in review.items():
        vals = list(items.values())
        passed = sum(1 for v in vals if v is True)
        rate = passed / len(vals) if vals else 0.0
        out[r] = {"rate": round(rate, 2), "passed": rate >= PASS_THRESHOLD,
                  "unrated": sum(1 for v in vals if v is None)}
    for r, ref_items in REVIEWS.items():
        if r not in out:  # 缺整道=该道全部未评（保守计分，见 docstring）
            out[r] = {"rate": 0.0, "passed": False, "unrated": len(ref_items)}
    out["all_passed"] = all(out[r]["passed"] for r in REVIEWS)
    return out


def critic_light(score: dict) -> str:
    """Critic 红黄绿（方法论 05）：有未评=黄(待审完)·全过=绿·有不过=红。**非 Red 才可交**。"""
    if any(score[r].get("unrated", 0) for r in REVIEWS):
        return "黄"
    return "绿" if score["all_passed"] else "红"


def extract_numeric_facts(storyline: dict) -> dict:
    """提取全 storyline 各页 evidence 的数字，按 dim(维度名) 分组列出——喂"跨页关键事实一致"人审项用。

    ⚠️ 只做摘录罗列（确定性·机器干得动的活），**不判断"是不是矛盾"**——
    "10053亿元" vs "1万亿"算不算一回事是语义判断，机器判不准，硬做会要么漏报要么把同一事实的不同表述误报成矛盾。
    这是 spec_lock(设计层一致性锁定) 的事实层对应物，但故意不做成自动判定，原因见上。
    返回 {dim: [{n, data, claim}]}——同一 dim 下出现多条，人审时一眼扫描有没有可疑的数值差异。
    """
    # 2026-07-02 saopan扫盘揪出：lines=None / evidence=None / data 为数字类型(12.5) / 行缺 n
    # 四种合法 JSON 形态在这里崩 TypeError/KeyError——deck_rules/storyline.py 当年宣布"全文件
    # .get(key,[]) 改成 .get(key) or 默认值"的同类修复漏掉了本文件，按同款纪律补齐。
    by_dim: dict[str, list] = {}
    for ln in sorted(storyline.get("lines") or [], key=lambda x: x.get("n") or 0):
        for e in ln.get("evidence") or []:
            dim = e.get("dim", "")
            data = str(e.get("data") or "")
            if dim and re.search(r"\d", data):
                by_dim.setdefault(dim, []).append({"n": ln.get("n"), "data": data, "claim": ln.get("claim", "")})
    return {k: v for k, v in by_dim.items() if len(v) > 1}  # 只列出现 ≥2 次的维度(单次出现没有"跨页"可言)


_NUM_RE = re.compile(r"\d[\d,]*\.?\d*")


def _numbers_in(text) -> set[str]:
    """从文本抽取数字 token 集合（去逗号统一比较）——只抠纯数字部分，不管单位/符号
    （单位换算/进制是人审的活，机检只管"这串数字有没有在原文字面出现过"，同 extract_numeric_facts
    "只摘录不判语义"的克制原则）。入参容忍数字类型（JSON 里 data: 12.5 合法·str 化再抠）。"""
    return {m.replace(",", "") for m in _NUM_RE.findall(str(text or ""))}


def check_fact_grounded(evidence: dict) -> list[dict]:
    """两层防假阳第一层（2026-07-01·Auto-Slides 启发，D6 决策记录🟢采纳）：
    evidence["data"] 里的数字是否在其 `source_quote`（`engine/research.py::attach_citation` 填的
    原文摘录）里字面出现过。

    出处【Auto-Slides】"正则先验证数字是否在原文出现，LLM 在白名单约束下复核、不准推翻已核验项"——
    这里只落地第一层（确定性正则核验），第二层"LLM 复核"不额外起一个自动化 LLM 调用（同 D5 摄入候选
    "先有候选池再看要不要自动化，避免过早工程化"同一条克制原则）——机检产出的 warn 信号本身就是喂给
    生成时的 LLM/人审复核用的，复核本来就在发生，不需要在这层再嵌一次调用。

    ⚠️ 查不到不等于假：可能是原文用了不同表述（单位换算/四舍五入/全角数字），也可能真是编造/篡改——
    机检只给"信号"不给"结论"，warn 而非 error，跟 check_source 的"有没有标 source"这层更浅的检查
    互补（那层查'有没有引用'，这层查'引用对不对得上'，只在两者都有时才查得动，见函数体判断）。
    """
    quote = evidence.get("source_quote")
    data = evidence.get("data")  # 数字类型也合法，_numbers_in 内部 str 化
    if not quote or not data:
        return []
    data_nums = _numbers_in(data)
    if not data_nums:
        return []
    missing = data_nums - _numbers_in(quote)
    if missing:
        return [{"rule": "number_not_in_source_quote", "sev": "warn",
                  "note": f"evidence 数字 {sorted(missing)} 在标注的 source_quote 原文里找不到"
                          f"（疑似编造/篡改，或原文表述不同如单位换算/四舍五入——需人核实，"
                          f"机检不能自动判定就是假，两层防假阳第一层·Auto-Slides）"}]
    return []


def check_facts_grounded(storyline: dict) -> list[dict]:
    """跨全 storyline 逐条 evidence 跑 `check_fact_grounded`，附页号(n)/维度(dim)方便人审定位。"""
    issues = []
    for ln in sorted(storyline.get("lines") or [], key=lambda x: x.get("n") or 0):
        for e in ln.get("evidence") or []:
            for issue in check_fact_grounded(e):
                issues.append({**issue, "n": ln.get("n"), "dim": e.get("dim", "")})
    return issues


# 方向词（涨/跌类关键词模式匹配·跟 check_fact_grounded 同一严重度的纯规则，不是 LLM 判断）
_UP_WORDS = ["提升", "改善", "增长", "上升", "增加", "扩大", "提高", "转好", "好转"]
_DOWN_WORDS = ["下降", "减少", "降低", "下滑", "萎缩", "收窄", "走低", "恶化", "转差"]

# 显式"变化前→变化后"结构（2026-07-02 saopan扫盘揪出：旧实现"恰好2个数字=前→后"被最常见的
# 中文证据形态击穿——「2025年增长12%」抠出 (2025,12) 被当成 2025→12 下降、「Q3下降5%」抠出 (3,5)
# 被当成上升，年份/季度序号+单数字必误报，warn 信号被噪声淹没。收窄到下面三种高置信过渡结构，
# 匹配不到就不判——宁漏勿噪，跟"只处理恰好2个数字、不瞎猜"是同一条克制原则的正确执行版）：
_NUM = r"(\d[\d,]*\.?\d*)"
_TRANSITION_RES = [
    re.compile(rf"从\s*{_NUM}[^\d]{{0,12}}?(?:到|至|变为|变成)\s*{_NUM}"),   # 从120家增长到150家
    re.compile(rf"{_NUM}\s*[%％]?\s*(?:→|->|⟶|—>)\s*{_NUM}"),               # 58%→42%
    re.compile(rf"由\s*{_NUM}[^\d]{{0,12}}?(?:升|降|增|减|涨|跌)[^\d]{{0,4}}?(?:到|至)\s*{_NUM}"),  # 由30%降至25%
]


def _extract_transition(data: str) -> tuple[float, float] | None:
    """抠显式"前→后"结构的两个数字；无该结构返回 None（不判）。"""
    for pat in _TRANSITION_RES:
        m = pat.search(data)
        if m:
            try:
                return float(m.group(1).replace(",", "")), float(m.group(2).replace(",", ""))
            except ValueError:
                return None
    return None


def check_evidence_direction(evidence: dict) -> list[dict]:
    """证据方向词与数字实际增减方向校验（2026-07-01 yanjiu研究驱动评估🟡走样需修，出处：
    research_lib/开源拆解/02架构/Auto-Slides.md §2.A「语义方向校验」`_validate_semantic_context`
    L559-641——用"improvement/reduction"类关键词模式匹配判断方向性矛盾，纯规则不需要LLM）。

    `check_fact_grounded` 文档自述"两层防假阳只落地第一层，第二层LLM复核不额外起调用"——但
    Auto-Slides 原始设计的第二层其实是关键词方向校验，不是 LLM 判断，被误判成"需要LLM"而没做，
    这条补上。跟 check_fact_grounded 是互补关系（那层查"数字真不真"，这层查"方向词说得对不对"，
    只在两者都有数据时才查得动）。

    只在 data 含**显式过渡结构**（从X到Y / X→Y / 由X降至Y，见 _TRANSITION_RES）时判——
    2026-07-02 起不再用"恰好2个数字"猜前后关系（年份/季度序号场景必误报，见上方注释）。
    """
    data = str(evidence.get("data") or "")
    pair = _extract_transition(data)
    if pair is None:
        return []
    before, after = pair
    if before == after:
        return []
    actual_up = after > before
    hit_up = [w for w in _UP_WORDS if w in data]
    hit_down = [w for w in _DOWN_WORDS if w in data]
    if actual_up and hit_down:
        return [{"rule": "evidence_direction_mismatch", "sev": "warn",
                 "note": f"「{data}」含下降类用词{hit_down}，但数字{before:g}→{after:g}实际是上升"
                         f"（方向词跟数字对不上，笔误还是数字填反了？）"}]
    if not actual_up and hit_up:
        return [{"rule": "evidence_direction_mismatch", "sev": "warn",
                 "note": f"「{data}」含上升类用词{hit_up}，但数字{before:g}→{after:g}实际是下降"
                         f"（方向词跟数字对不上，笔误还是数字填反了？）"}]
    return []


def check_evidence_directions(storyline: dict) -> list[dict]:
    """跨全 storyline 逐条 evidence 跑 `check_evidence_direction`，附页号(n)/维度(dim)方便人审定位。"""
    issues = []
    for ln in sorted(storyline.get("lines") or [], key=lambda x: x.get("n") or 0):
        for e in ln.get("evidence") or []:
            for issue in check_evidence_direction(e):
                issues.append({**issue, "n": ln.get("n"), "dim": e.get("dim", "")})
    return issues
