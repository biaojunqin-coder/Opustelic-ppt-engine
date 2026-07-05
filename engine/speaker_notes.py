"""从 storyline 生成 speaker notes（演讲者备注）——演讲版「每页一观点·信息靠口头补」的那段脚本。

策略层已存下每页的思路（论点 / 证据 / framing / 叙事作用），组装成演讲提示写进 pptx 备注页。
对应 ppt-master 的「思路讲解」。演示时演讲者看备注、观众只看极简页。把扎实的策略层直接变现成演讲脚本。

D18 FR7.8（备注叙事·问题 A 核心件三）：备注/讲解词的输入不再是"页面文字的复读"，而是
**storyline 推演链**——除 claim/evidence 外，还吃 sowhat（这页在故事里的作用）、framing
（stance/counter_read/basis 的反方处理逻辑）、part（章节位置）、bridge_from（承接上章什么结论）。
产出目标是"完整讲述逻辑"：承接上文 → 本页位置 → 亮数 → 解读 → 堵反方 → 落点——参照 ppt-master
真样本的备注水准（pritzker"第七站，阿布扎比…"沿叙事线一路讲；swiss 备注在推导设计系统
"基本单位 16px、所有尺寸由此派生"）。本模块的模板只保证推演链**结构齐**（可兜底、确定性可测），
真正亮眼靠 LLM 按制作 SKILL 阶段 5 的备注标准逐页手写。
"""

from __future__ import annotations

import re

# 按 page_type 的讲法提示（来自 07 演讲版节奏）
SPEAK_TIPS = {
    "封面": "开场定调，报出主标题后留一拍。",
    "情绪slogan": "慢下来、留白，让这句话沉下去；先别讲数据，讲感受。",
    "数据论断": "先抛结论（标题），再用数据支撑；重读关键数字。",
    "转场": "停顿，切换节奏，一句话预告下一段。",
    "高潮": "情感顶点，加重语气、放慢，制造紧迫感。",
    "决策": "明确 ask，要一个当场的行动 / 批准。",
    "落幕": "回扣开篇那句，语气收住，留余韵。",
}


def notes_for_line(line: dict, nxt: dict | None = None) -> str:
    """从一行 storyline 生成该页演讲备注（输入=storyline 推演链，不是页面文字·D18 FR7.8）。

    备注要能独立读出"这页在整个故事里的位置 + 为什么这么讲"：章节位置（part）、承接上章什么
    （bridge_from）、叙事作用（sowhat）、立场与反方怎么堵（framing）都进备注——讲的人照着备注
    就能沿叙事线讲，不是照页面文字复读。
    """
    L = []
    role = line.get("role") or line.get("page_type", "")
    # 2026-07-01 起 storyline 字段叫 stage（framework 不止 SCR 后改名）；旧落盘数据的 scr 键兜底。
    # D18 FR7.8 顺手修复：此前这里还在读已改名的 scr，新数据备注里"段"位恒空。
    stage = line.get("stage", line.get("scr", ""))
    head = f"【p{line.get('n')}｜{role}｜{stage} 段"
    if line.get("part"):
        head += f"｜Part·{line['part']}"   # D18 FR2.1/FR7.8：先报章节位置——讲的人要知道自己在故事哪一站
    L.append(head + "】")
    if line.get("bridge_from"):            # D18 FR7.8：转场页承接上章结论（某品牌 章封面淡灰副标机制的口头版）
        L.append(f"● 承接上章：{line['bridge_from']}")
    L.append(f"● 要讲的观点：{line.get('claim', '')}")
    if line.get("sowhat"):
        L.append(f"● 作用：{line['sowhat']}")
    tip = SPEAK_TIPS.get(line.get("page_type", ""))
    if tip:
        L.append(f"● 讲法：{tip}")
    ev = line.get("evidence", [])
    if ev:
        L.append("● 口头展开的证据：" + "；".join(
            f"{e.get('dim', '')}" + (f"={e['data']}" if e.get("data") else "") for e in ev))
    fr = line.get("framing", {})
    if fr.get("stance"):
        s = f"● 立场：{fr['stance']}"
        if fr.get("counter_read"):
            s += f"（反方会说「{fr['counter_read']}」"
            s += (f"，预先堵：{fr['basis']}）" if fr.get("basis") else "）")
        L.append(s)
    if nxt:
        L.append(f"● 过渡：自然带到「{nxt.get('claim', '')}」")
    return "\n".join(L)


def notes_for_storyline(sl: dict) -> dict:
    """整本 storyline → {页号: notes 文本}。"""
    lines = sorted(sl.get("lines", []), key=lambda x: x.get("n", 0))
    out = {}
    for i, ln in enumerate(lines):
        nxt = lines[i + 1] if i + 1 < len(lines) else None
        out[ln["n"]] = notes_for_line(ln, nxt)
    return out


# 2026-07-02 saopan扫盘揪出（B2-9）：旧版 "→"一律念"降到"——「30%→45%」明明是升，讲出来跟事实
# 矛盾；"-"一律念"负"——「2023-2025」被念成"2023负2025"。修法："→"改念方向中立的"到"；
# "-"分语境：数字/%后接数字 = 范围/年份念"到"，前无数字的负号念"负"，其余保留（如英文连字词）。
# 范围规则的 lookbehind 收进 %（30%-45% 也是范围）——比 bug 单给的 (?<=\d) 多护一类真实场景。
_RANGE_DASH_RE = re.compile(r"(?<=[\d%])-(?=\d)")   # 2023-2025 / 30%-45% → "到"
_NEG_DASH_RE = re.compile(r"(?<![\d%])-(?=\d)")     # -5% / 增速-3% → "负"


def _spoken(s: str) -> str:
    """把念不出的符号转成中文（→ / − / - / ~），让 TTS 念得顺、且不念反方向/念错语义。"""
    s = s.replace("→", "到").replace("−", "-").replace("~", "到")  # U+2212 数学负号先归一成 "-" 再分语境
    s = _RANGE_DASH_RE.sub("到", s)
    return _NEG_DASH_RE.sub("负", s)


# 讲解词措辞池——多页连续数据论断时轮换用词，别让每页都喊"先看数据"（用户验收教训：千篇一律=没用心）。
_OPENERS_FRESH = ["先看一组数据：", "我们来看：", "有组数字值得注意：", "数据是这样的：", "先摆个事实："]
_OPENERS_CONTINUE = ["更值得注意的是，", "另一个信号是，", "同时，", "再看一组，", "紧接着，", "还有一点，"]
_CONCLUDERS = ["所以，这是", "这说明，这是", "换句话说，这是", "结论是，", "归根结底，这是"]
_COUNTER_LINKERS = ["也许有人会说是", "可能有人会反驳，说这是", "有一种解读认为是"]
_TRANSITION_TAILS = ["我们接着往下看。", "顺着这个往下讲。", "这就引出下一个问题。"]


def narration_for_line(line: dict, *, continuing: bool = False, seed: int = 0,
                       prev_line: dict | None = None, part_opened: bool = False) -> str:
    """给 TTS 念的口语讲解稿——把页面观点**沿推演链讲透**（非复述·按页型·数据页围绕数据）。

    continuing=True 表示上一页也是数据论断页（连续数据页要换措辞·不重复开场白）；
    seed 用于在措辞池里轮换选词（建议传页号 n·保证同一份 deck 内不同页选不同词，确定性可测）。

    D18 FR7.8（向后兼容新增·keyword-only，不传=旧行为基础上多吃 sowhat/bridge_from）：
    - 转场页优先念 bridge_from（承接上章结论），没填才退回 prev_line 的 claim——承接材料
      必须来自 storyline 推演链，不允许模板现编；
    - 数据论断页在证据→论点→立场/堵反方之后补 sowhat 落点（"这一页想说明的，是…"），
      完整讲述逻辑=承接→亮数→解读→堵反方→落点；
    - part_opened=True（本页开启新 Part）时开头先报章节位置（"进入××这一部分"），
      对标 pritzker 备注"第七站，阿布扎比…"的站位感。
    规范见 makedeck SKILL 阶段 5。真正「亮眼」是模板天花板·产品里应由 LLM 按规范生成·此为结构化兜底。
    """
    pt = line.get("page_type", "数据论断")
    claim = (line.get("claim", "") or "").strip()
    ev = [e for e in line.get("evidence", []) if e.get("data")]
    fr = line.get("framing", {})
    sowhat = (line.get("sowhat") or "").strip()
    part_prefix = f"进入{line['part']}这一部分。" if (part_opened and line.get("part")) else ""

    if pt in ("情绪slogan", "封面", "落幕"):
        return claim + "。"                                   # 一句·留白·不堆料
    if pt == "转场":
        # D18 FR7.8：转场职责是"接住上章结论+预告本章"——bridge_from 是 storyline 里的显式承接字段
        # （FR2.2 结构件硬门要求转场页必填）；旧数据没填时退回上一行 claim（同样来自推演链，非编造）。
        bridge = (line.get("bridge_from") or "").strip() or \
                 ((prev_line or {}).get("claim", "") or "").strip()
        lead = f"到这里，{bridge}。" if bridge else ""
        return lead + claim + _TRANSITION_TAILS[seed % len(_TRANSITION_TAILS)]
    if pt == "决策":
        return f"{_CONCLUDERS[seed % len(_CONCLUDERS)]}，{claim}。"
    if pt == "高潮":
        return claim + (f"。{fr['stance']}。" if fr.get("stance") else "。")
    if pt == "数据论断" and ev:                               # 围绕数据展开（亮数→论点→立场→反方→落点）
        openers = _OPENERS_CONTINUE if continuing else _OPENERS_FRESH
        opener = openers[seed % len(openers)]
        L = [part_prefix + opener + "、".join(_spoken(f"{e['dim']}{e['data']}") for e in ev), claim]
        if fr.get("stance"):
            s = f"{_CONCLUDERS[seed % len(_CONCLUDERS)]}{fr['stance']}"
            if fr.get("counter_read"):
                linker = _COUNTER_LINKERS[seed % len(_COUNTER_LINKERS)]
                s += f"。{linker}{fr['counter_read']}，但{_spoken(fr.get('basis', ''))}"
            L.append(s)
        if sowhat and sowhat not in claim:                    # D18 FR7.8：sowhat 落点收尾（推演链最后一环）
            L.append(f"这一页想说明的，是{sowhat}")
        return "。".join(L) + "。"
    tail = f"。说到底，这是{fr['stance']}。" if fr.get("stance") else "。"
    if sowhat and sowhat not in claim:
        tail += f"这一页想说明的，是{sowhat}。"                # D18 FR7.8：无证据的一般页同样落 sowhat
    return part_prefix + claim + tail


def narration_for_storyline(sl: dict) -> dict:
    """整本 storyline → {页号: 口语讲解稿}（喂 TTS）。连续数据论断页自动换措辞，不重复开场白。

    D18 FR7.8：逐行传递推演链上下文——prev_line（转场承接兜底）+ part_opened（Part 边界报站）。
    """
    lines = sorted(sl.get("lines", []), key=lambda x: x.get("n", 0))
    out = {}
    prev_pt, prev_part, prev_ln = None, None, None
    for ln in lines:
        pt = ln.get("page_type", "数据论断")
        continuing = pt == "数据论断" and prev_pt == "数据论断"
        cur_part = ln.get("part")
        part_opened = bool(cur_part) and cur_part != prev_part
        out[ln["n"]] = narration_for_line(ln, continuing=continuing, seed=ln.get("n", 0),
                                          prev_line=prev_ln, part_opened=part_opened)
        prev_pt = pt
        if cur_part:
            prev_part = cur_part      # 封面/目录/收尾这类 deck 级页 part=None，不重置章节跟踪
        prev_ln = ln
    return out


def narration_list_for_pptx(sl: dict, total_pages: int | None = None) -> list[str]:
    """storyline → 按页序的讲解词列表（D18 FR7.8·喂 `engine.narration.narrate_pptx`）。

    narrate_pptx 按 slide 顺序 zip 讲解词，这里把 {页号: 讲解词} 铺成 1..N 的列表，
    storyline 里没有的页号（如附录页）填空串=不配音。total_pages 不传（None）时取 storyline
    最大页号；显式传 0 = 0 页 → 空列表（2026-07-03 二轮扫盘批D：此前 `or` 把 0 当"未传"
    回退到最大页号——判 None 而非 falsy）。
    """
    nar = narration_for_storyline(sl)
    if not nar and total_pages is None:
        return []
    last = total_pages if total_pages is not None else max(nar)
    return [nar.get(i, "") for i in range(1, last + 1)]


# 短页型（情绪/封面/落幕/转场）讲解本就短，豁免展开度/时长审核
_SHORT_PT = {"情绪slogan", "封面", "落幕", "转场"}


def check_narration(line: dict, narration: str) -> list[dict]:
    """讲解词机检审核（makedeck SKILL 阶段5 可机检项）：展开度 / 时长 / 口语。warn 喂人审。"""
    out = []
    claim = (line.get("claim", "") or "").strip()
    pt = line.get("page_type", "数据论断")
    n = len(narration)
    if pt not in _SHORT_PT:
        if n <= len(claim) + 4:
            out.append({"rule": "narration_not_expanded", "sev": "warn",
                        "note": "讲解词≈复述 claim·未展开（页面浓缩、讲解要讲透）"})
        elif n < 30:
            out.append({"rule": "narration_too_short", "sev": "warn", "note": f"讲解词 {n} 字偏短·没展开"})
    if n > 220:
        out.append({"rule": "narration_too_long", "sev": "warn", "note": f"讲解词 {n} 字偏长·啰嗦"})
    for sym in ("→", "±", "≥", "≤"):
        if sym in narration:
            out.append({"rule": "narration_unspeakable", "sev": "warn", "hit": sym})
    return out


def check_narration_aligned(page_text: str, narration: str) -> list[dict]:
    """页面 ↔ 讲解对齐机检：讲解念的数字应都在页面上——讲解有、页面无 = 不合格（用户验收教训）。"""
    nums_nar = set(re.findall(r"\d+%?", narration))
    nums_page = set(re.findall(r"\d+%?", page_text))
    missing = nums_nar - nums_page
    if missing:
        return [{"rule": "narration_page_misaligned", "sev": "warn",
                 "note": f"讲解念了页面没有的数据：{sorted(missing)}（页面要展示讲解念的整组数据）"}]
    return []
