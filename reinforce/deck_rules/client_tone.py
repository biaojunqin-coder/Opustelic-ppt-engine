"""对客文案门（D18 FR5.2 warn 起步 → D19 FR1.2 部分升 error）——逮"内部工作语言泄漏到对客页面"。

第一轮实测确诊（某品牌 24 页普查）：页面上直接出现 "brief P3-4" 工作定位符、
"对齐我们对brief的理解，确保方向不跑偏" 流程自述、"GD领先GX待追赶" 内部区域缩写；
第二轮实测（059）再确诊"说明书感"：framing 字段被直译上页——"立场：""依据：""反方会怎么看"
"聚焦判断：""开场判断："至少 8 页命中，用户判定"像说明书不像方案"且 warn 全程被忽略。
语域分工（FR5.3）：工作推演进 speaker_notes 与工作档案，页面只呈现对客语域文案。

D19 FR1.2 分级原则（用户拍板升 error·白名单控误拦）：
  **error（strict 拦导出）**——形态上不可能是正当对客表达的：①brief 页码定位符
  ②字段标签冒号形态（"立场：/依据：/聚焦判断："——只拦"标签+冒号"，不拦自然句"我们的
  立场是与消费者站在一起"）③"反方会怎么看"短语（字段语义直译·对客句不会这么说）。
  **warn（喂人审）**——自然句误拦风险高的：流程自述句式/白名单外缩写/工作口语。

⚠️ 坏例子清单靠飞轮从每单实测积累——每单新逮到的泄漏形态往清单追加并配回归测试。
"""

from __future__ import annotations

import re

# 白名单：营销/商业通用缩写——客户方评审日常使用、无需解释的词（需求 FR5.2 列举 + 营销
# 行业常用合理扩展 + 本单 brief 客户自用术语 BPS/UTC/AIPL/RFM/TTL）。**建常量可扩**：
# 新单遇到客户自己 brief 里用的缩写，加进来即可（客户自己的词不算内部语言）。
# 注意 GD/GX（区域内部代号）刻意不在名单里——正是第一轮实测的坏例子。
ACRONYM_WHITELIST = frozenset({
    # 需求 FR5.2 明文列举
    "KPI", "ROI", "GMV", "CNY", "KV", "KOL", "KOC", "IP", "AI", "PPT", "SOW",
    "TA", "CTA", "UGC", "PGC", "SKU", "DAU", "MAU",
    # 营销/媒介常用（4A 对客语域通行）
    "SEO", "SEM", "PR", "IMC", "CRM", "SCRM", "DTC", "MCN", "TVC", "EDM",
    "ATL", "BTL", "TTL", "CPM", "CPC", "CPA", "CPS", "CPT", "CTR", "ROAS",
    "GRP", "TGI", "UV", "PV", "WAU", "LTV", "NPS", "POSM", "VI", "CI",
    "FAQ", "VIP", "APP", "LOGO", "URL", "IPO", "GT", "MT", "KA", "OK",
    # 本单 brief 客户自用术语（客户自己的词不算内部语言）
    "BPS", "UTC", "AIPL", "RFM",
})

# 连续 2-4 个大写字母、前后不挨字母（"KOLs" 复数形态整体不命中；中文夹缩写"GD领先GX"命中）
_ACRONYM_RE = re.compile(r"(?<![A-Za-z])[A-Z]{2,4}(?![A-Za-z])")

# 工作定位符：brief 页码引用（"brief P3-4"/"Brief P24"）——工作档案里的溯源坐标，
# 对客页面该改成对客说法（外部数据→页脚"来源：名称(日期)"；客户资料→页面不标，FR5.1）
_BRIEF_LOCATOR_RE = re.compile(r"brief\s*[Pp]\d")

# 流程自述句式：说给项目组自己听的话（推演过程），不是说给客户听的结论
_NARRATION_PHRASES = ["对齐我们对", "确保方向不跑偏", "我们的理解"]

# 工作口语：Engine 内部工位黑话，任何语境都不该上对客页面
_WORK_JARGON = ["填肉", "埋点位"]

# D19 FR1.2：字段标签冒号形态（error）——storyline 工作字段被直译上页的签名形态。
# 只拦「标签+冒号」（"立场：xxx"），不拦自然句（"我们的立场是…"无冒号紧随不命中）；
# 标签前允许行首/空白/标点/标签闭合（">"），防止把长句里的正常词误当标签。
_FIELD_LABELS = ["立场", "依据", "反方", "聚焦判断", "开场判断", "回顾判断", "判断理由"]
# 前缀允许集含中文标点（2026-07-03 saopan批②：「结论已明。立场：坚定站位」句中标签跟在
# 。，、；— 后此前漏拦——标签形态跟行首完全一样，只是前面多了个句读）
_FIELD_LABEL_RE = re.compile(
    r"(?:^|[\s>›»（(【\[|·。，、；—])(" + "|".join(_FIELD_LABELS) + r")\s*[:：]")
# "反方会怎么看"：无冒号也拦——它本身就是 framing.counter_read 的语义直译短语，
# 正当对客表达不会用这个句式（会写成"有人可能质疑…而我们的答案是…"）。
_FIELD_PHRASES = ["反方会怎么看"]

# ── D20 FR2.1 元叙述组合检测（第三轮实测确诊·比逐词清单泛化一级）──────────────
# 第三轮 8 句坏文案 0 命中旧清单——形态从"字段直译"变异成"元叙述"（deck 谈论自己）。
# 判定原语升级为**组合**：文档部件词（谈论 deck 结构的名词）× 过程时态词（工序完成/推进
# 动词）同现 = error（"三条线诊断完毕，下一步…"）；文档部件词单独出现 = warn（"这份提案
# 想说清楚三件事"——已经够坏但单维误拦风险稍高，warn 喂人审）。
# 真提案对照（零误拦回归的白名单依据）：内容实体词承接（"该如何占据暑期社交场？"）、
# 口语主持词（"LET'S QUICKLY RECAP"）、升维宣言——都不含文档部件词，天然不命中。
_DOC_PART_WORDS = ["这份提案", "本提案", "这一页", "本页", "后面每一页", "前面几页",
                   "上一部分", "下一部分", "第一个判断",
                   "这套判断", "接下来是", "接下来我们"]
# 2026-07-03 saopan批②：「这一部分」「这个判断」从部件词筐摘出——它们是高频内容语义
# （"这一部分消费者的需求…"=人群细分、"这个判断落到渠道层面"=策略判断的业务承接），
# 留在筐里跟 _PROCESS_RE 组合必 error 误伤。真元叙述形态（"这一部分我们讲品牌资产"）
# 用更强共现条件单独兜：部分词 + 我们 + 讲述类动词 = 主持人语态，业务句不这么说。
_PART_PRESENTER_RE = re.compile(
    r"这一?(?:个)?部分[，,、]?\s*(?:里|中)?我们(?:先|来|将|想|要)?"
    r"(?:讲|说|聊|谈|看|回顾|展开|论证|拆|分析|铺垫|收口)")
_PROCESS_TENSE_WORDS = ["完毕", "锁定", "定案", "收口", "落到", "落进", "进入下一",
                        "下一步", "先诊断", "再给方向", "证明它", "说清楚"]
_DOC_PART_RE = re.compile("|".join(_DOC_PART_WORDS) +
                          r"|[一二三四五六七八九十\d]+条(?:表述|线|主线)")  # "三条线诊断完毕"式自指
_PROCESS_RE = re.compile("|".join(_PROCESS_TENSE_WORDS))
# 结构预告句式（论文导语腔·"先诊断，再给方向，最后落到…"·某品牌 p2 实测坏例）
_STRUCTURE_PREVIEW_RE = re.compile(r"先[^，。]{1,8}，再[^，。]{1,8}，(?:最后|然后)")
# 2026-07-03 saopan批②：三段式本身是常见业务句式（"先试点，再推广，最后全国铺开"=
# 正当的分阶段打法文案），单靠句式必误伤。组合判定：三段式命中后，句中还含"谈论 deck
# 自身"的工序词才是论文导语式结构预告 → error；纯业务动词的三段式不报。
_DECK_PROCESS_HINT_RE = re.compile(r"诊断|判断|方向|章节|论证|展开|收口|铺垫|结论")
# 祈使请求句上页（ask 页的请求动作留给口头·页面走 SOW/机制表·真样本范式）。
# 左边界（saopan批②）：句首或标点/空白后才算祈使开头——"邀请媒体到场确认排期"的
# "请"长在"邀请"里，不是请求句；"恳请/敬请"敬语前缀同算句首祈使。用单字符负向
# lookbehind（"前一个字符不是非边界字符"·串首天然通过）保 group(0) 不带边界符。
_IMPERATIVE_ASK_RE = re.compile(
    r"(?<![^，。；！？：、,.;!?:\s])(?:恳|敬)?请[^，。]{1,10}(?:批准|拍板|确认|通过)")
# 2026-07-03 二轮扫盘：元叙述组合判定加**邻近约束**——旧版部件词/工序词各自全文 search，
# 两词哪怕隔半句话、语义毫无关联也判 error（"这份提案的核心创意是价格要落到消费者能接受的
# 区间"："这份提案"是主语定语、"落到"在谓语深处讲价格带，误判 error）。真元叙述里工序词
# 直接谓述部件词，两词紧邻（"三条线诊断完毕"间距2、"后面每一页都在证明它"间距2、"这份提案
# 先诊断"间距0）。约束=同一子句（，。；切分）内共现 **且** 字符间距≤_META_PAIR_MAX_GAP——
# 光靠子句切分兜不住无标点长句（上述误报句整句无标点、间距9）。不满足邻近的降回
# doc 部件词单维 warn（仍喂人审·不静默放行）。
_CLAUSE_SPLIT_RE = re.compile(r"[，。；]")
_META_PAIR_MAX_GAP = 6  # 已知真坏句间距 0-2、误报句间距 9——取 6 留双侧余量


def _proximate_doc_proc_pair(text: str):
    """在同一子句内找间距≤_META_PAIR_MAX_GAP 的（部件词, 工序词）匹配对；无则 None。"""
    for clause in _CLAUSE_SPLIT_RE.split(text):
        for d in _DOC_PART_RE.finditer(clause):
            for p in _PROCESS_RE.finditer(clause):
                if max(p.start() - d.end(), d.start() - p.end()) <= _META_PAIR_MAX_GAP:
                    return d, p
    return None


def check_client_facing_tone(text: str) -> list[dict]:
    """单条文案的对客语域检查（D18 FR5.2 → D19 FR1.2 分级）。六类已知坏模式：
    error——①brief 页码定位符 ②字段标签冒号形态 ③"反方会怎么看"直译短语；
    warn——④流程自述句式 ⑤白名单外的 2-4 位大写缩写 ⑥内部工作口语。
    note 里给改写方向。error 的判定边界见模块 docstring（只拦形态上不可能正当的）。
    """
    if not text:
        return []
    out = []
    m = _BRIEF_LOCATOR_RE.search(text)
    if m:
        out.append({"rule": "internal_locator", "sev": "error", "hit": m.group(0),
                    "note": f"「{m.group(0)}」是工作定位符，永不上对客页面——外部数据改页脚"
                            f"'来源：名称(日期)'，客户内部资料页面不标(溯源进内部台账·FR5.1)"
                            f"（D19 升 error：第二轮实测 warn 被忽略仍上页）"})
    for m in _FIELD_LABEL_RE.finditer(text):
        out.append({"rule": "field_label_leak", "sev": "error", "hit": m.group(1),
                    "note": f"「{m.group(1)}：」是工作字段标签直译上页（说明书感的签名形态·"
                            f"D19 FR1.2）——删标签、把内容消化成对客陈述句；该字段本身的价值"
                            f"应体现在你如何组织与措辞，不是当小标题印出来"})
    for phrase in _FIELD_PHRASES:
        if phrase in text:
            out.append({"rule": "field_label_leak", "sev": "error", "hit": phrase,
                        "note": f"「{phrase}」是 framing 字段语义直译——对客表达应写成"
                                f"'有人可能质疑…而答案是…'的自然论证，不是印字段名"})
    # D20 FR2.1 元叙述组合检测（deck 谈论自己=说明书感的第三形态）
    if text.strip() in _FIELD_LABELS:
        # 孤立标签形态：整条 <text> 只有"立场"两个字=版式块标签（某品牌 实测坏例）
        out.append({"rule": "field_label_leak", "sev": "error", "hit": text.strip(),
                    "note": f"「{text.strip()}」孤立成块=工作字段当版式标签——删块，内容消化进对客陈述句（D20）"})
    m = _STRUCTURE_PREVIEW_RE.search(text)
    if m and _DECK_PROCESS_HINT_RE.search(text):
        # 组合判定（saopan批②）：三段式 × deck 工序词才 error——"先试点，再推广，最后
        # 全国铺开"这类纯业务三步走是正当文案，零报；"先诊断，再给方向，最后落到执行"照拦
        out.append({"rule": "meta_narration", "sev": "error", "hit": m.group(0),
                    "note": f"「{m.group(0)}…」是论文导语式结构预告——真提案的目录用统一句式给各章"
                            f"命名（'立形象/现场景/步酒局'式），不预告论证机制（D20）"})
    m = _PART_PRESENTER_RE.search(text)
    if m:
        # 「这一部分」摘出部件词筐后的强共现兜底（saopan批②）：部分词+我们+讲述动词=
        # 主持人语态元叙述（"这一部分我们讲品牌资产"），业务句（"这一部分消费者…"）不命中
        out.append({"rule": "meta_narration", "sev": "error", "hit": m.group(0),
                    "note": f"「{m.group(0)}」是主持人语态元叙述（deck 在预告自己讲什么）——"
                            f"直接给该部分的论断本身，别播报'我们接下来讲什么'（D20）"})
    m = _IMPERATIVE_ASK_RE.search(text)
    if m:
        out.append({"rule": "imperative_ask", "sev": "warn", "hit": m.group(0),
                    "note": f"「{m.group(0)}」祈使请求句写上了页面——真提案的 ask 页放 SOW 交付清单/"
                            f"合作机制表，'请批准'这个动作留给现场嘴说（D20·真样本范式）"})
    doc_m = _DOC_PART_RE.search(text)
    proc_m = _PROCESS_RE.search(text)
    # 组合 error 须过邻近约束（2026-07-03 二轮扫盘·机制见 _proximate_doc_proc_pair 上方注释）：
    # 同子句紧邻才是"工序词谓述部件词"的真元叙述；跨子句/远距共现降回 doc 单维 warn
    pair = _proximate_doc_proc_pair(text) if (doc_m and proc_m) else None
    if pair:
        d, pr = pair
        out.append({"rule": "meta_narration", "sev": "error",
                    "hit": f"{d.group(0)}×{pr.group(0)}",
                    "note": f"元叙述（deck 在谈论自己而非客户的生意·「{d.group(0)}」+"
                            f"「{pr.group(0)}」同子句紧邻组合）——改写方向：承接用内容实体词或内容"
                            f"设问（'该如何占据暑期社交场？'式），结构信息走版式组件不写成句子"
                            f"（D20·第三轮实测确诊）"})
    elif doc_m:
        out.append({"rule": "meta_narration", "sev": "warn", "hit": doc_m.group(0),
                    "note": f"「{doc_m.group(0)}」是文档部件词（deck 自指）——真提案不谈论"
                            f"自己的结构，确认这句在讲客户的生意还是在讲这份 deck"})
    elif proc_m and proc_m.group(0) in ("完毕", "锁定", "定案", "收口"):
        out.append({"rule": "meta_narration", "sev": "warn", "hit": proc_m.group(0),
                    "note": f"「{proc_m.group(0)}」是工序完成时态词——真提案的诊断一步给判断"
                            f"（对比定位/设问自答），不播报流程状态（D20）"})
    for phrase in _NARRATION_PHRASES:
        if phrase in text:
            out.append({"rule": "process_narration", "sev": "warn", "hit": phrase,
                        "note": f"「{phrase}」是流程自述(说给项目组听的推演话术)——对客改写方向："
                                f"直接给结论/主张，推演过程挪进 speaker_notes(语域分工·FR5.3)"})
    # D20 修正：缩写检测的设计意图是"中文文本里夹的内部代号"（GD领先GX）——纯英文文本
    # （真提案的全大写英文标题是常态·"LET'S QUICKLY RECAP THE EVENT"）跳过，否则 LET/THE
    # 全中招（真样本零误拦回归揪出）。
    _has_cjk = re.search(r"[一-鿿]", text)
    for m in (_ACRONYM_RE.finditer(text) if _has_cjk else ()):
        token = m.group(0)
        if token not in ACRONYM_WHITELIST:
            out.append({"rule": "internal_acronym", "sev": "warn", "hit": token,
                        "note": f"缩写「{token}」不在营销常用白名单——内部代号(GD/GX类)请全称化"
                                f"或换客户能懂的说法；若是客户 brief 自用术语，把它加进"
                                f"ACRONYM_WHITELIST(客户自己的词不算内部语言)"})
    for jargon in _WORK_JARGON:
        if jargon in text:
            out.append({"rule": "work_jargon", "sev": "warn", "hit": jargon,
                        "note": f"「{jargon}」是内部工位口语，任何语境都不该上对客页面——"
                                f"改成客户视角的正式表达"})
    return out


_TEXT_CONTENT_RE = re.compile(r"<text\b[^>]*>(.*?)</text>", re.DOTALL)
_INNER_TAG_RE = re.compile(r"<[^>]+>")


def run_client_tone_gate(svg_text: str) -> list[dict]:
    """整页 SVG 的对客文案门（D18 FR5.2 warn 起步 → D19 FR1.2/D20 FR2.1 分级）：抽全部
    <text> 内容（含 tspan 内文·剥内层标签）逐条跑 check_client_facing_tone。返回 list
    （issue 形态同 run_visual_gate，喂 pipeline gate）。⚠️ D19 起**不再全 warn**——
    brief 定位符/字段标签冒号形态/元叙述组合这类形态上不可能正当的判 error（参与
    gate.passed，strict 模式拦导出）；流程自述/白名单外缩写/工作口语这类误拦风险高的
    仍 warn 喂人审。分级依据见模块 docstring；每条 issue 附命中文案摘要方便定位。"""
    issues = []
    for m in _TEXT_CONTENT_RE.finditer(svg_text):
        content = _INNER_TAG_RE.sub("", m.group(1)).strip()
        if not content:
            continue
        for issue in check_client_facing_tone(content):
            issue["text"] = content[:40]  # 命中文案摘要·人审定位用
            issues.append(issue)
    return issues
