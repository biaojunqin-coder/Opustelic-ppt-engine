"""storyline 级机检硬门（策略层·区别于 rules.py 的文案级）。

来源：03 storyline「六条禁忌」(主题式 / 缺 so-what / 含糊用语 / 太碎 / 没结尾 / 逻辑跳跃)可机检部分
+ 01 共因(标题论断式 / 水平逻辑 / 末页决策强制)。结构合法性在 storyline_state.validate_storyline；
本门聚焦「质量项判死」——和结构校验分工（机检/人审 L2）。决策结尾=error(高 stakes 必须要决策)，其余多为 warn 喂人审。
"""

from __future__ import annotations

import re

from reinforce.review import check_evidence_directions, check_facts_grounded
# ↑ 2026-07-02 saopan扫盘揪出（孤岛A2/A3）：两层防假阳（数字↔原文摘录核验 + 方向词↔数字增减
# 校验）写好后 SKILL/architecture 都用自动语态宣称"会核验"，实际全仓零生产调用——文档喊自动、
# 代码没人调。接进 run_storyline_gate（交棒前必跑的综合硬门），宣称才成立。review.py 只 import
# 标准库 re，无循环依赖。

# 含糊用语（禁忌6·用模糊词替代具体数字）
VAGUE_WORDS = ["表现良好", "不错", "有所提升", "稳步", "持续优化", "明显改善",
               "大幅提升", "显著增强", "整体向好", "较为乐观"]
# 论断式信号（共因1·带数字 或 含结论性方向/决策词，非纯主题词）
CLAIM_SIGNALS = ["升", "降", "增", "减", "涨", "跌", "超", "致", "亏", "翻", "破",
                 "反", "批", "请", "建议", "定", "选", "没", "失控", "不"]
# 决策强制标记（末页 owner+日期决策）
DECISION_MARKERS = ["批准", "决策", "请董事会", "建议", "owner", "牵头", "下一步", "批",
                    "选我们", "选择", "进下一轮", "携手", "合作", "定标"]  # 含 pitch 决策词(选我们/进下一轮)
# 不按「数据论断」标准查 claim 论断式 / sowhat / evidence 的页型（情绪/封面/转场/落幕=金句留白·创意展示=pitch 活动方案）
NON_ARGUMENT_PAGE_TYPES = {"封面", "目录", "转场", "情绪slogan", "高潮", "落幕", "创意展示"}


def _is_claim_shaped(claim: str) -> bool:
    """论断式：带数字/百分比 或 含结论性方向/决策词（升/降/致/亏/批…）。"""
    if re.search(r"\d", claim):
        return True
    return any(w in claim for w in CLAIM_SIGNALS)


def _levenshtein(a: str, b: str) -> int:
    """标准编辑距离(DP)。Python 标准库无内置实现，给 check_duplicate_titles 用。"""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i] + [0] * len(b)
        for j, cb in enumerate(b, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb))
        prev = cur
    return prev[-1]


def check_duplicate_titles(lines) -> list[dict]:
    """近似重复标题检测（2026-07-01 yanjiu研究驱动评估🟢采纳，出处：
    research_lib/开源拆解/04制作/Instrumenta.md L141「重复/近似重复标题(Levenshtein距离≤2判近似)
    SlideGrader.bas:1437-1459」）：两两比较标题，编辑距离≤2(含完全相同) → warn——典型场景是手改
    大纲时复制一页漏改标题。warn 非 error：结构复用有时是刻意手法（_修订日志.md 2026-07-01"同结构
    页面刻意复用制造节奏感"），机检只标记"像不像"，是笔误还是有意留人审判断。
    只比非 NON_ARGUMENT_PAGE_TYPES 页——情绪/封面/转场/落幕这类标题本就该短促、彼此接近是常态，
    比了全是噪音（同 check_claim_titles/check_sowhat 排除同一批页型的理由）。
    """
    out = []
    candidates = [(ln.get("n"), ln.get("claim", "").strip()) for ln in lines
                  if ln.get("page_type", "数据论断") not in NON_ARGUMENT_PAGE_TYPES
                  and ln.get("claim", "").strip()]
    for i, (n1, c1) in enumerate(candidates):
        for n2, c2 in candidates[i + 1:]:
            dist = _levenshtein(c1, c2)
            if dist <= 2:
                # 2026-07-02 saopan扫盘揪出：中文语境下编辑距离 2≈换了一个词——刻意平行结构的
                # 两条正当论点（"Q1亏损2亿"vs"Q2亏损5亿"）被误标近似重复。判据：≥2 处数字
                # token 不同 = 系统性平行结构（期数+数值一起变），豁免；恰 1 处不同（"升至58%"
                # vs"升至59%"）更像复制漏改/页间数字冲突，照报（dist=0 时数字必全同不进此分支）。
                nums1, nums2 = re.findall(r"\d[\d,.]*", c1), re.findall(r"\d[\d,.]*", c2)
                if dist and nums1 != nums2 and (
                        len(nums1) != len(nums2)
                        or sum(a != b for a, b in zip(nums1, nums2)) >= 2):
                    continue
                desc = "完全相同" if dist == 0 else f"近似(编辑距离{dist})"
                out.append({"rule": "duplicate_title", "sev": "warn", "n": n2,
                            "note": f"行{n1}「{c1}」与行{n2}「{c2}」标题{desc}"
                                    f"——改大纲漏改，还是刻意结构复用？"})
    return out


def check_claim_titles(lines) -> list[dict]:
    """每行标题论断式（共因1）——疑似主题式（无数字无方向词）→ warn 人审。"""
    out = []
    for ln in lines:
        if ln.get("page_type", "数据论断") in NON_ARGUMENT_PAGE_TYPES:
            continue  # 情绪/转场/封面/落幕页标题=金句，不按论断式查
        c = ln.get("claim", "")
        if c and not _is_claim_shaped(c):
            out.append({"rule": "topic_title", "sev": "warn", "n": ln.get("n"),
                        "note": f"行{ln.get('n')}疑似主题式(非论断)：{c[:20]}"})
    return out


def check_vague_words(lines) -> list[dict]:
    """含糊用语（禁忌6）——用模糊词替代具体数字 → warn。"""
    out = []
    for ln in lines:
        c = ln.get("claim", "")
        for w in VAGUE_WORDS:
            if w in c:
                out.append({"rule": "vague", "sev": "warn", "n": ln.get("n"), "hit": w})
    return out


def check_sowhat(lines) -> list[dict]:
    """缺 so-what（禁忌2）——行无 sowhat 注解 → warn。

    2026-07-02 saopan对齐：补排除 NON_ARGUMENT_CHARTS（姊妹检查 evidence_depth/framing/
    reading_subtitle 都排除、唯独本条漏了）——决策页(decision_box)claim 即行动号召、焦点数字页
    (metric_callout)靠单数字冲击，都不是"论据页要回答所以呢"的语境。
    """
    return [{"rule": "no_sowhat", "sev": "warn", "n": ln.get("n")}
            for ln in lines
            if not ln.get("sowhat") and ln.get("page_type", "数据论断") not in NON_ARGUMENT_PAGE_TYPES
            and ln.get("chart") not in NON_ARGUMENT_CHARTS]


def check_decision_ending(lines) -> list[dict]:
    """决策强制（01）——末尾(末页或末两页)无决策标记 → error。演讲版允许「决策页 → 落幕页」收尾。"""
    if not lines:
        return [{"rule": "no_lines", "sev": "error"}]
    tail = lines[-2:]  # 末两页(演讲版决策→落幕·决策不一定落在最后一页)
    txt = "".join(ln.get("role", "") + ln.get("claim", "") for ln in tail)
    if not any(m in txt for m in DECISION_MARKERS):
        return [{"rule": "no_decision_ending", "sev": "error", "n": tail[-1].get("n"),
                 "note": "末尾无决策强制(高 stakes deck 必须以决策收尾·演讲版可决策→落幕)"}]
    return []


def check_horizontal_logic(sl) -> list[dict]:
    """水平逻辑弱测（共因·Stop-anywhere）——塔顶 Lead 应已含决策指向，否则 warn 人审。

    真正『只读全 deck 标题能复述推荐』是语义判断·归人审/独立 Agent(L2)；此处只做可机检的弱闭环。
    """
    if sl.get("mode") in ("narrative", "showcase"):
        return []  # 故事弧/视觉主导的塔顶是 big idea(创意主张)·不查"决策指向"——pyramid/briefing 才查
    gt = sl.get("governing_thought", "")
    if gt and not any(m in gt for m in DECISION_MARKERS):
        return [{"rule": "lead_no_decision", "sev": "warn",
                 "note": "塔顶 Lead 未含决策指向(stop-anywhere:读完执行摘要应知道你要什么)"}]
    return []


# 不需要「一组证据合围」的页型（封面/决策本身不是论证页）
NON_ARGUMENT_CHARTS = {"metric_callout", "decision_box"}


def check_evidence_depth(lines) -> list[dict]:
    """论证页应用一组数据合围（≥2 维）——单数据论点易被单点反驳（用户洞察：一个数能定论就太好做了）。"""
    out = []
    for ln in lines:
        if ln.get("page_type", "数据论断") != "数据论断" or ln.get("chart") in NON_ARGUMENT_CHARTS:
            continue
        ev = ln.get("evidence") or []
        if len(ev) < 2:
            out.append({"rule": "thin_evidence", "sev": "warn", "n": ln.get("n"),
                        "note": f"行{ln.get('n')}仅 {len(ev)} 个证据·论点易被单点反驳(应 ≥2 维合围)"})
    return out


def check_framing(lines) -> list[dict]:
    """论点应显式表态（framing.stance）——数据中性、靠论点解读，不做中性陈述（用户洞察：同一数据可正可负）。"""
    out = []
    for ln in lines:
        if ln.get("page_type", "数据论断") != "数据论断" or ln.get("chart") in NON_ARGUMENT_CHARTS:
            continue
        if not (ln.get("framing") or {}).get("stance"):
            out.append({"rule": "no_framing", "sev": "warn", "n": ln.get("n"),
                        "note": f"行{ln.get('n')}数据未表态·中性陈述(应有解读立场)"})
    return out


_DELIVERY_VALUES = ("演讲版", "阅读版", "预读讲解版")  # D19 FR3 三值·与 storyline_state.DELIVERY_PURPOSES 同步


def _delivery_purpose(sl) -> str | None:
    """密度轴兼容读（D18 FR7.1 迁移·D19 FR3 三值化）：新字段 delivery_purpose 优先，旧落盘数据
    visual_style 存密度值时兜底。本文件不 import storyline_state（会环），维护此内联版——逻辑与
    storyline_state.delivery_purpose_of 保持一致（值域改动必须两处同步·D19 需求点名）。"""
    dp = sl.get("delivery_purpose")
    if dp in _DELIVERY_VALUES:
        return dp
    legacy = sl.get("visual_style")
    return legacy if legacy in _DELIVERY_VALUES else None


def check_rhythm(sl) -> list[dict]:
    """节奏检查（07·D19 FR3 三态分流）：演讲版=全查（情绪起伏+转场）；预读讲解版=柔化
    （要转场不强制情绪页——先自读后讲的场景要章节骨架、不靠现场情绪曲线）；阅读版=不查
    （章节结构由 Part 结构门管）。"""
    dp = _delivery_purpose(sl)
    if dp not in ("演讲版", "预读讲解版"):
        return []
    types = [ln.get("page_type") for ln in (sl.get("lines") or [])]
    out = []
    if dp == "演讲版" and not any(t in ("情绪slogan", "高潮", "落幕") for t in types):
        out.append({"rule": "no_emotion_page", "sev": "warn",
                    "note": "演讲版无情绪/高潮/落幕页·全程匀速(应有情绪起伏)"})
    if "转场" not in types:
        out.append({"rule": "no_transition", "sev": "warn",
                    "note": f"{dp}无转场页·缺节奏骨架(章节切换)"})
    return out


def check_reading_subtitle(sl) -> list[dict]:
    """导读副标题检查：论证页必须有 subtitle——脱离演讲者自读的关键（用户洞察 / Lulu 真样本·07）。
    D19 FR3：预读讲解版同样要查——"先发客户自读"阶段没有讲解人在场，导读是自读的拐杖。"""
    if _delivery_purpose(sl) not in ("阅读版", "预读讲解版"):
        return []
    out = []
    for ln in (sl.get("lines") or []):
        if ln.get("page_type", "数据论断") != "数据论断" or ln.get("chart") in NON_ARGUMENT_CHARTS:
            continue
        if not ln.get("subtitle"):
            out.append({"rule": "no_reading_subtitle", "sev": "warn", "n": ln.get("n"),
                        "note": f"行{ln.get('n')}阅读版缺导读副标题(标题下应说明本页作用)"})
    return out


def check_evidence_source(lines) -> list[dict]:
    """数字溯源（01 雷区7）：evidence 的 data 含数字但无 source → warn（防编造·咨询 deck 的命）。

    source_type="client_provided" 豁免（2026-07-03 二轮扫盘批D·对齐 rules.check_source 的
    D18 FR5.1 口径）：客户自己给的资料数字不标 source（客户本来就有·内部台账已溯源），
    此前这里没同步豁免——设计上该干净的 storyline 总被这条 warn 噪音污染。external/未标注照查。
    """
    out = []
    for ln in lines:
        for e in ln.get("evidence") or []:
            if e.get("source_type") == "client_provided":
                continue  # 客户资料数字·页面不标源（与 rules.check_source 豁免语义一致）
            data = str(e.get("data", ""))
            if re.search(r"\d", data) and not e.get("source"):
                out.append({"rule": "evidence_no_source", "sev": "warn", "n": ln.get("n"),
                            "note": f"行{ln.get('n')}证据「{e.get('dim', '')}{data}」无 source（数字须可溯源·防编造）"})
    return out


def check_temporal_freshness(lines, current_year: int | None = None) -> list[dict]:
    """逮"某年预计"挂过期——年份已过却还用未来时态（真实踩过的坑：2026年了还写"2025年预计"）。

    current_year 不传则跳过（引擎本身不读系统时钟·由调用方/工作流显式传入当前年份·守"核心不碰 Date.now()"原则）。
    只逮"预计/将/届时/有望"+年份的组合，逮到 warn 喂人审——这是启发式，会有漏报，不当 error。
    """
    if not current_year:
        return []
    out = []
    pat = re.compile(r"(20\d{2})年(预计|将|届时|有望)")
    for ln in lines:
        for e in ln.get("evidence") or []:
            text = f"{e.get('dim', '')}{e.get('data', '')}"
            m = pat.search(text)
            if m and int(m.group(1)) < current_year:
                out.append({"rule": "stale_forecast", "sev": "warn", "n": ln.get("n"),
                           "note": f"「{m.group(0)}」年份已过(现{current_year}年)却用未来时态·该年若已过应换实际数"})
    return out


def check_cross_page_consistency(lines) -> list[dict]:
    """deck 反向索引防前后冲突（05 质量门 constraint verify 一支·此前误记在 retrieval/_说明.md——
    实为 storyline 级机检非检索，2026-07-01 改正归属）：按 evidence 的 dim(维度) 建反向索引，
    同一 dim 在不同页给出不同 data(数值) → warn（口径不同还是真打架，人审判定）。
    """
    index: dict[str, list[tuple]] = {}
    for ln in lines:
        for e in ln.get("evidence") or []:
            dim, data = e.get("dim", ""), e.get("data", "")
            if dim and data:
                index.setdefault(dim, []).append((ln.get("n"), data))
    out = []
    for dim, occ in index.items():
        distinct = {d for _, d in occ}
        if len(distinct) > 1:
            where = "、".join(f"p{n}=「{d}」" for n, d in occ)
            out.append({"rule": "cross_page_conflict", "sev": "warn", "dim": dim,
                        "note": f"「{dim}」在不同页给出不同数值：{where}（口径不同还是真打架？）"})
    return out


def check_toc_matches_chapters(lines) -> list[dict]:
    """目录↔章节标题逐字匹配（05 质量门 constraint verify 一支）：目录页声明的 toc_items 须能在
    后续转场页的 claim 里逐字找到——防"改了大纲忘改目录"的真实踩坑。目录页未填 toc_items 也 warn
    （没这份数据就没法核对，鼓励补全而非静默跳过）。
    """
    out = []
    # strip 后再比（2026-07-02 saopan：尾空格这种不可见差异导致的"不一致"是纯噪音误报）
    chapter_claims = {(ln.get("claim") or "").strip() for ln in lines if ln.get("page_type") == "转场"}
    for toc in (ln for ln in lines if ln.get("page_type") == "目录"):
        items = toc.get("toc_items") or []
        if not items:
            out.append({"rule": "toc_items_missing", "sev": "warn", "n": toc.get("n"),
                        "note": f"行{toc.get('n')}是目录页但未声明 toc_items，无法核对与转场页是否一致"})
            continue
        for item in items:
            if (item or "").strip() not in chapter_claims:
                out.append({"rule": "toc_chapter_mismatch", "sev": "warn", "n": toc.get("n"),
                            "note": f"目录列了「{item}」，没有任何转场页标题与之逐字一致（改过大纲忘改目录？）"})
    return out


def check_counter_addressed(lines) -> list[dict]:
    """证据"要堵的反驳"承诺-兑现检查（2026-07-01·对标小说引擎伏笔未回收，问题收口调研 R-B）：
    ①evidence 声明了 counter(要堵的反驳)却无 data 支撑 → 空转的说服话术；
    ②framing 声明了 counter_read(反方会怎么解读)，但整行 evidence 没有任何一条挂 counter 去对应它
    → framing 写得头头是道但完全没配套证据去堵这个反方解读。两条都只查"声明没声明/配没配"，
    查不了"这份证据是否真的驳倒了反方"（语义判断留人审，见 reinforce/review.py REVIEWS["storyline"]）。
    """
    out = []
    for ln in lines:
        evidence = ln.get("evidence") or []
        for e in evidence:
            counter = e.get("counter")
            data = e.get("data")
            # 2026-07-01 saopan扫盘揪出：先转 str() 再 strip() 时，data=None 会变成非空字符串
            # "None"，被误判成"有数据"而放行——这条检查存在的目的就是防空转声明，data=None
            # 恰是最典型的"字段声明了没真填"场景，必须先判 None/falsy 再决定要不要 str().strip()。
            if counter and (data is None or not str(data).strip()):
                out.append({"rule": "counter_not_backed", "sev": "warn", "n": ln.get("n"),
                            "note": f"行{ln.get('n')}证据声明要堵反驳「{counter}」，但本条无 data 支撑"})
        counter_read = (ln.get("framing") or {}).get("counter_read")
        if counter_read and not any(e.get("counter") for e in evidence):
            out.append({"rule": "counter_read_unaddressed", "sev": "warn", "n": ln.get("n"),
                        "note": f"行{ln.get('n')} framing 声明反方会怎么解读「{counter_read}」，"
                                f"但没有任何 evidence 标注是用来堵这个反方解读的"})
    return out


def check_hypothesis_tested(sl) -> list[dict]:
    """假设树『可证伪检验』承诺-兑现检查（2026-07-01·对标小说引擎伏笔未回收，问题收口调研 R-B）：
    sub_hypotheses 声明了 test 却没回填 verified，是"押了答案却没人验证过就直接写进最终结论"——
    这个假设树在阶段2就已经过闸（validate_storyline 只查 test 字段非空），走到阶段4才是合理的
    核对时机：这条论点真要当定论用了，背后押的检验到底跑过没有？verified 建议结构
    {"answer": str, "source": str}，调研阶段真跑完 test 后由角色/Claude 显式回填。
    """
    out = []
    for h in sl.get("sub_hypotheses") or []:
        if h.get("test") and not h.get("verified"):
            out.append({"rule": "hypothesis_test_unverified", "sev": "warn", "id": h.get("id"),
                        "note": f"子假设「{h.get('claim', h.get('id'))}」声明了检验「{h.get('test')}」，"
                                f"但未回填 verified（这条检验真的跑过、有结论了吗？）"})
    return out


def check_page_count_consistency(sl) -> list[dict]:
    """实际页数 vs 阶段2声明的 expected_pages 一致性检查（2026-07-01·问题收口D）：不是拿实际页数
    比某个通用绝对阈值（项目没有真实数据支撑这种阈值），是比"当初策略阶段自己规划的数"——偏差不代表
    页数错了，只代表"范围变了还是没收住"，喂人审判断是哪种。expected_pages 未声明（None）→ 跳过，
    不是每份 storyline 都要求填这个。

    2026-07-01 saopan扫盘揪出：expected_pages 传成非二元(如裸 int)会直接 TypeError 崩穿
    run_storyline_gate/handoff_to_production 的 fail-closed 契约——现在改成 warn 而非崩溃；
    min/max 顺手写反(如(6,4))也不再报自相矛盾的错误文案，sorted() 自动纠正成合法区间。
    """
    expected = sl.get("expected_pages")
    if not expected:
        return []
    if (not isinstance(expected, (tuple, list)) or len(expected) != 2
            or not all(isinstance(x, int) for x in expected)):
        return [{"rule": "expected_pages_malformed", "sev": "warn",
                 "note": f"expected_pages 应为 (min,max) 整数二元组，收到 {expected!r}——本次跳过页数一致性检查"}]
    lo, hi = sorted(expected)
    actual = len(sl.get("lines") or [])
    if lo <= actual <= hi:
        return []
    direction = "多" if actual > hi else "少"
    return [{"rule": "page_count_drift", "sev": "warn",
             "note": f"实际 {actual} 页，比阶段2规划的 {lo}-{hi} 页{direction}出较多"
                     f"（是范围/受众/决策颗粒度变了，还是执行时没收住？确认是有意为之还是该收窄/该补充）"}]


def check_adjacent_layout_repeat(lines) -> list[dict]:
    """相邻页版式去重检测（2026-07-01 yanjiu研究驱动评估🟢采纳，出处：05号本文档§四引
    02_页型手法精华.md L73「相邻页不得同版式」，源自 planning-guide.md L60-70）：物理相邻
    两页 chart 字段相同 → warn。warn 非 error：结构复用有时是刻意手法（_修订日志.md
    2026-07-01"同结构页面刻意复用制造节奏感"），机检只标记"相不相同"这个客观事实，是偷懒
    还是刻意节奏留人审判断（同 check_duplicate_titles 的措辞纪律，不能一刀切成 error）。
    两页任一属于 NON_ARGUMENT_PAGE_TYPES，或 chart 属于 NON_ARGUMENT_CHARTS（决策页/焦点
    数字页允许连续出现，本就不是论证节奏的一部分）→ 跳过。
    """
    out = []
    # 2026-07-03 二轮扫盘揪出：.get("n", 0) 在 n 显式为 None 时（手改坏的 storyline JSON/
    # Part 中途手动跑质量门）原样返回 None，None<int 比较 TypeError 崩穿质量门——run_storyline_gate
    # docstring 自称"全文件已改 .get(key) or 默认值"，排序键这两处漏网，补齐。
    ordered = sorted(lines, key=lambda x: x.get("n") or 0)
    for a, b in zip(ordered, ordered[1:]):
        if (a.get("page_type", "数据论断") in NON_ARGUMENT_PAGE_TYPES
                or b.get("page_type", "数据论断") in NON_ARGUMENT_PAGE_TYPES):
            continue
        chart_a, chart_b = a.get("chart"), b.get("chart")
        if not chart_a or not chart_b or chart_a != chart_b or chart_a in NON_ARGUMENT_CHARTS:
            continue
        out.append({"rule": "adjacent_layout_repeat", "sev": "warn", "n": b.get("n"),
                    "note": f"行{a.get('n')}与行{b.get('n')}连续用同一版式「{chart_a}」"
                            f"——是偷懒复用，还是刻意节奏复用制造韵律？"})
    return out


def check_content_density(sl) -> list[dict]:
    """内容密度/注水检查（01 方法论雷区4"太碎/注水·50页讲15页的事"，2026-07-01 补）：统计论证页里
    "内容单薄(evidence<2 且无 sowhat)"的占比——不重复判断单页对不对(那是 check_evidence_depth/
    check_sowhat 的活)，判断的是整份 deck 撑不撑得起这么多页。占比>40% 才 warn(论证页太少时统计
    没意义，跳过)。只能查"论证页内容单薄占比"这个结构信号，查不了"是不是真的注水"(语义判断留人审)。
    """
    lines = sl.get("lines") or []
    arg_lines = [ln for ln in lines if ln.get("page_type", "数据论断") == "数据论断"
                 and ln.get("chart") not in NON_ARGUMENT_CHARTS]
    if len(arg_lines) < 4:
        return []
    thin = [ln for ln in arg_lines if len(ln.get("evidence") or []) < 2 and not ln.get("sowhat")]
    ratio = len(thin) / len(arg_lines)
    if ratio > 0.4:
        return [{"rule": "content_thin_ratio_high", "sev": "warn",
                 "note": f"{len(arg_lines)}页论证页里有{len(thin)}页(证据<2条+无sowhat)同时单薄"
                         f"({ratio:.0%})——是不是为了凑页数硬撑？（太碎/注水）"}]
    return []


def _is_part_summary(ln) -> bool:
    """章小结行判定约定（D18 FR2.2）：`role=="章小结"` 或 page_function 含"小结"。

    为什么不新增 page_type="章小结"：PAGE_TYPES 词表在 storyline_state.py（本次开发铁纪律
    不可改动的文件），且页型=节奏角色的既有语义里"章小结"本质仍是数据论断（结论先行+证据回收），
    不是新节奏角色——用 role/page_function 这两个本就表达"页面职能"的字段做约定，不动词表。
    """
    if (ln.get("role") or "").strip() == "章小结":
        return True
    return "小结" in (ln.get("page_function") or "")


def check_part_structure(sl) -> list[dict]:
    """结构件硬门（D18 FR2.2 ★·error 级拦交棒）——第一轮实测确诊：24 页 deck 平铺直叙，
    0 目录 0 转场 0 章小结，9 类页型只用 3 类，阅读者在长 deck 里没有任何结构导航。
    真实 4A deck 是"封面→目录→[Part×N]→收尾"的章节结构（四真样本交叉实证，见
    part_scaffold_hint）。四条判定：

    ① 页数≥12 必须有目录页（page_type="目录"）且至少一张 toc_items 非空 → 否则 error；
    ② 凡 lines 里填了 part 字段：每个 part 必须有一张转场页（page_type="转场"，归属判定
       = 转场页自己填了该 part；或该页**没填 part 且是转场页**且 claim 与 part 名逐字一致
       ——兼容"转场页标题就是章名"的常见填法。2026-07-03 二轮扫盘收紧：兜底只认无 part
       的转场页，防无关页标题撞章名被误配、缺转场/缺小结被静默放行）且 bridge_from 非空
       （**首个 part 豁免 bridge_from**——前面没有章可承接，
       强要一句"承接上章"反而逼人编造）；每个 part 还必须有一张章小结行（约定见
       _is_part_summary docstring）→ 缺则 error；
    ③ 全 deck 一个 part 都没填：页数≥12 → error（≥12 页的 deck 必须做 Part 分章·第一轮
       实测 24 页平铺确诊）；页数<12 → 不查（短 deck 允许无章节，硬纪律 4：简单需求不加锁）；
    ④ 转场页后的第一页应是洞察陈述类（非空 claim）→ 空则 warn（"Part 首页该开门见山给
       本章洞察"是语义判断，机检只查 claim 空不空，判断力留人审）。

    12 页阈值出处：需求 FR2.2 验收条款（4A 比稿 deck 场景基线 20-50 页，12 页以下属
    短简报，目录/分章反而是仪式负担）。
    """
    lines = sl.get("lines") or []
    n_pages = len(lines)
    out = []
    # ① 目录页硬门
    if n_pages >= 12:
        toc_pages = [ln for ln in lines if ln.get("page_type") == "目录"]
        if not toc_pages:
            out.append({"rule": "no_toc_page", "sev": "error",
                        "note": f"{n_pages}页 deck 无目录页（page_type=目录）——≥12页必须给读者"
                                f"结构导航（第一轮实测 24 页 0 目录确诊·D18 FR2.2）"})
        elif not any(ln.get("toc_items") for ln in toc_pages):
            out.append({"rule": "toc_items_empty", "sev": "error",
                        "note": "目录页存在但 toc_items 全空——没有结构化章节清单，目录↔转场"
                                "一致性核对（check_toc_matches_chapters）无从谈起（D18 FR2.2）"})
    # n 显式为 None 不崩（2026-07-03 二轮扫盘·同 check_adjacent_layout_repeat 处注释）
    ordered = sorted(lines, key=lambda x: x.get("n") or 0)
    parts: list = []  # 保序去重·首个 part 的转场豁免 bridge_from 要靠出现顺序判定
    for ln in ordered:
        p = ln.get("part")
        if p and p not in parts:
            parts.append(p)
    # ③ 全 deck 零 part
    if not parts:
        if n_pages >= 12:
            out.append({"rule": "no_parts", "sev": "error",
                        "note": f"{n_pages}页 deck 没有任何一页声明 part 归属——≥12页的deck必须做"
                                f"Part分章·第一轮实测24页平铺确诊（D18 FR2.2）"})
        return out
    # ② 每 part 转场+bridge_from+章小结
    for idx, p in enumerate(parts):
        # 归属兜底收紧（2026-07-03 二轮扫盘揪出 fail-open）：旧版对**任意页**用"claim==章名"
        # 兜底归属——无关页（别章的转场页/别章的小结页）标题恰与本章名一致就被误配进本章，
        # 缺转场/缺小结两条 error 被静默放行。兜底的设计初衷只是"转场页标题就是章名"这一种
        # 常见填法（见 docstring ②），故收紧为三条件同时成立才兜底：页面自己没填 part、
        # page_type=转场、claim 与章名逐字一致——填了 part 的页永远只归自己声明的章。
        plines = [ln for ln in ordered
                  if ln.get("part") == p
                  or (not ln.get("part") and ln.get("page_type") == "转场"
                      and (ln.get("claim") or "").strip() == p)]
        transitions = [ln for ln in plines if ln.get("page_type") == "转场"]
        if not transitions:
            out.append({"rule": "part_no_transition", "sev": "error", "part": p,
                        "note": f"Part「{p}」没有转场页——章节切换没有承接/预告骨架"
                                f"（某品牌 6 Part 每章一张转场页·D18 FR2.2）"})
        elif idx > 0 and not any((t.get("bridge_from") or "").strip() for t in transitions):
            out.append({"rule": "transition_no_bridge", "sev": "error", "part": p,
                        "note": f"Part「{p}」的转场页 bridge_from 为空——转场职责是接住上章结论"
                                f"再预告本章（某品牌 淡灰副标承接机制），空转场只是换背景色"
                                f"（首个 Part 无上章可承接·已豁免·D18 FR2.2）"})
        if not any(_is_part_summary(ln) for ln in plines):
            out.append({"rule": "part_no_summary", "sev": "error", "part": p,
                        "note": f"Part「{p}」没有章小结行（role=章小结 或 page_function 含'小结'）"
                                f"——章内证据没有收口，读者带不走本章结论"
                                f"（Lulu Summaries 编号小结机制·D18 FR2.2）"})
    # ④ 转场后首页应有非空 claim（warn·语义留人审）
    for i, ln in enumerate(ordered[:-1]):
        if ln.get("page_type") == "转场":
            nxt = ordered[i + 1]
            if not (nxt.get("claim") or "").strip():
                out.append({"rule": "part_opener_no_claim", "sev": "warn", "n": nxt.get("n"),
                            "note": f"转场页(行{ln.get('n')})后的第一页(行{nxt.get('n')}) claim 为空"
                                    f"——Part 首页应开门见山给本章洞察陈述（是否洞察类留人审·D18 FR2.2）"})
    return out


def part_scaffold_hint() -> str:
    """Part 范式 scaffold（D18 FR2.3）——storyline 规划阶段的章结构模板文字，供 SKILL/规划
    prompt 引用（策略 prompt 文件不在本次可改范围，故以纯函数形式在规则层提供唯一真相源）。
    范式从四份真实顶级样本提取（"标尺来自真样本非模型常识"纪律），非模型自由发挥。
    """
    return (
        "【Part 章结构范式（D18 FR2.3·四真样本提取）】\n"
        "每个 Part 按四拍展开：\n"
        "1. 章封面/转场页（page_type=转场·填 part + bridge_from）：一句接住上一章结论"
        "（bridge_from），再预告本章要回答的问题——首个 Part 无上章、bridge_from 可空；\n"
        "2. 洞察陈述页（转场后第一页）：开门见山给本章核心洞察，论断式标题 + 来源标注"
        "（evidence 挂 source），不做主题式铺垫；\n"
        "3. 证据展开页（1-N 页）：一组数据多维合围洞察（≥2 维·防单点反驳），每页论断递进；\n"
        "4. 章小结页（role=章小结 或 page_function 含'小结'）：结论先行收拢本章论证，"
        "末尾抛下一章钩子（一句话预告，跟下章转场页的 bridge_from 首尾咬合）。\n"
        "四真样本出处：某品牌 52页（6 Part 每章一张转场页）；Lulu 37页（阅读版·诊断章+"
        "Summaries 编号小结+SOW 三栏收尾+侧边导航）；某品牌 18页（章封面巨字+淡灰副标预告承接+"
        "洞察→本质→公式页）；MTA（目录页中段复现+当前章加粗追踪）。\n"
        "规划时配合库内结构卡使用（转场页/议程页/阶段总览卡已在 101 张页型卡内）。"
    )


def run_storyline_gate(sl, *, current_year: int | None = None) -> dict:
    """storyline 综合硬门。有 error → passed=False（fail-closed）。warn 喂人审。

    按 mode 分流数字溯源：pyramid/briefing 严格(陈述事实导向)；narrative/showcase 的"方案数字"
    (10滑手/3天2晚)是我们提议的·非引用事实·不溯源。
    current_year 传入时额外查"过期预计"(check_temporal_freshness)·不传则跳过该项。

    2026-07-01 saopan扫盘揪出：sl["lines"]显式为 None（比如手改坏的storyline JSON、或
    set_hypothesis_tree(sl,gt,None)这类合法但误用的调用）时，dict.get(key,default)只在
    key不存在才生效、key存在但值是None时原样返回None——这是本文件系统性的假设错误，本函数
    自己的入口就会被打穿。这里以及全文件同构的 .get(key,[])/.get(key,{}) 调用点已改成
    .get(key) or 默认值，正确兜住"key存在但值是None"这种情况。
    """
    lines = sl.get("lines") or []
    issues = (check_claim_titles(lines) + check_duplicate_titles(lines) + check_vague_words(lines)
              + check_sowhat(lines) + check_decision_ending(lines)
              + check_horizontal_logic(sl)
              + check_evidence_depth(lines) + check_framing(lines)
              + check_rhythm(sl) + check_reading_subtitle(sl)
              + check_temporal_freshness(lines, current_year)
              + check_cross_page_consistency(lines) + check_toc_matches_chapters(lines)
              + check_counter_addressed(lines) + check_hypothesis_tested(sl)
              + check_page_count_consistency(sl) + check_content_density(sl)
              + check_adjacent_layout_repeat(lines)
              + check_part_structure(sl)
              # ↑ 结构件硬门（D18 FR2.2）：≥12页无目录/无Part分章/Part缺转场缺小结 = error
              # 拦交棒——对存量 storyline 是 breaking change（需求§七明示：某品牌 重跑被拦
              # 是预期行为，属验收用例）。
              + check_facts_grounded(sl) + check_evidence_directions(sl))
    # ↑ 两层防假阳接线（2026-07-02 saopan·孤岛A2/A3摘帽）：数字↔source_quote 原文核验 +
    # 方向词↔数字增减校验，均 warn 喂人审——策略 SKILL"check_facts_grounded 会核验"的宣称
    # 自此才是真话（此前零生产调用点）。
    if sl.get("mode", "pyramid") in ("pyramid", "briefing"):
        issues += check_evidence_source(lines)   # 数字溯源只对陈述事实导向的 mode(防编造)
    return {"issues": issues, "passed": not any(i["sev"] == "error" for i in issues)}
