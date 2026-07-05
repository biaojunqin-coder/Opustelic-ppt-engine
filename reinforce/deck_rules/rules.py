"""deck 确定性硬门：能机检判死的质量项。error=拦·warn=喂人审。

来源：01 雷区7(数字带source)/共因1(标题论断) + 02 char_budget。

2026-07-01 用户拍板移除"AI 味"检查（原 01 雷区10：禁用词五连/m-dash/打太极）：PPT 是商业文档不是
小说创作，不需要刻意避免"听起来像 AI 写的"——原禁用词（leverage/synergy 等）恰是真实咨询语域
常见词，该雷区出处标"[toolkit] 跨门"（非 storyline/critic 真实拆样本来源），属继承通用工具箱惯例、
未针对 PPT 场景独立验证的一类，同 L2"LLM 打分"原则审计揭出的同一种问题，审视后判定不适用即移除，
不是漏做。历史考虑见 specs/PPT方法论/01_顶级deck共因与翻车雷区.md 雷区表第10行标注。
"""

from __future__ import annotations

import re

# 02 layout-matrix·char_budget（超 = 结构性 error）
PAGE_BUDGET = {"donut": 6, "pie": 6, "four_column": 4, "process_chevron": 5,
               "timeline_label": 6, "grouped_bar_cat": 6}

# 02 设计系统·合法字号 8 级（pt）
FONT_GRID = {44, 28, 24, 22, 18, 16, 14, 9}


def check_title(title: str) -> list[dict]:
    """标题硬门：过长(warn) + 疑似主题式非论断(warn·人审)。共因1。"""
    issues = []
    t = title.strip()
    cjk = sum(1 for ch in t if "一" <= ch <= "鿿")
    length = cjk if cjk else len(t.split())
    if (cjk and cjk > 20) or (not cjk and length > 15):
        issues.append({"rule": "title_too_long", "sev": "warn", "note": "标题应 ≤15词/20字"})
    elif cjk:
        # 2026-07-02 saopan扫盘揪出：中英混排长标题两分支都躲过——少量汉字(≤20)不触发中文分支，
        # cjk非零又进不了英文分支，3个汉字+30个英文词照样放行。补加权等效长度判：20字/15词的
        # 既有上限折算成 1词=4/3字当量，整数化(×3)避免浮点边界误差——cjk*3+词数*4>60 即超限，
        # 纯中文(>20字)/纯英文(>15词)边界行为跟原两分支完全一致，这里只兜混排的漏网。
        non_cjk_words = sum(1 for w in re.sub(r"[一-鿿]", " ", t).split()
                            if any(c.isalnum() for c in w))
        if cjk * 3 + non_cjk_words * 4 > 60:
            issues.append({"rule": "title_too_long", "sev": "warn",
                           "note": "标题应 ≤15词/20字(中英混排按加权折算)"})
    if length <= 4 and not any(ch.isdigit() for ch in t):
        issues.append({"rule": "title_maybe_topic", "sev": "warn",
                       "note": "疑似主题式标题(非论断)·人审是否 claim-shaped"})
    return issues


# 页码/分页标注（"第4页"/"共10页"/"4/10页"）——结构性装饰数字，不是需要溯源的证据数字，
# 2026-07-01 saopan扫盘揪出这类会被误判"含数字无source"而拦截，先从待扫描文本里挖掉再判定。
_PAGE_LABEL_RE = re.compile(r"第\s*\d+\s*(?:[/／]\s*\d+\s*)?页|共\s*\d+\s*页|\d+\s*[/／]\s*\d+\s*页")


def check_source(text: str, exempt_terms=()) -> list[dict]:
    """数字溯源硬门：含数字/百分比但无 source 标记 → error（01 雷区7）。

    2026-07-01 用户拍板从 warn 升级为 error："数据必须能够溯源，这是100%的"——编造/无据数字
    是咨询 deck 的真红线，比原先被移除的"AI 味"更该是能拦截的硬伤而非提醒。这道升级同时补上了
    移除 check_deslop 后 run_text_gate 失去的 error 判据（此前唯一的 error 来源就是 AI 味检查）。

    exempt_terms（D19 FR5.1+FR1.3 豁免机制·两类合流）：
      ① 品牌词（outline.brand_terms）——"059 用一杯精酿把福建讲给你听"里的品牌名曾被当
        统计数字 error 误报（第二轮实测复现）：命中豁免词的文本段整体从扫描文本里挖掉；
      ② client_provided 数字值（pipeline 逐页从该页 evidence 提取）——客户自己的资料数字
        页面不标来源（内部台账已溯源·D18 FR5.1 用户拍板），数字 token 与豁免值相等即挖掉。
      挖掉后剩余文本照旧判定——外部数字/编造数字一个不放。

    ⚠️ 已知局限（saopan扫盘留证据·未过度设计强行"修完"）：判定单位是整页拼接文本，不是逐个数字——
    只要页面任意角落出现过一次"来源"字样，本页所有数字都算"已溯源"，哪怕这个来源跟其中几个数字毫无
    关系（假阴性）；年份类数字（"2026年战略"这种标题/装饰用法）目前仍会被判定"需要来源"（假阳性）——
    没有一并排除，是因为年份紧跟在数字后（如"预计2026年营收10亿"）时，这类数字可能正是需要溯源的
    真实证据，规则层面分不清"纯装饰的年份"和"证据里带年份"，贸然排除年份风险是引入假阴性（漏检真正
    该拦的编造数据），比现在偶尔多提醒一次更不可接受——只排除"页码"这种100%不可能是证据数字的模式。
    """
    scan_text = _PAGE_LABEL_RE.sub("", text)
    for term in exempt_terms or ():
        t = str(term).strip()
        if t:
            # 2026-07-03 saopan批②揪出：此前 scan_text.replace(t,"") 是全文子串删除——
            # 豁免"3"会把"3%消费者"的 3 挖走（3% 是另一个数字断言·fail-open 放行编造数据）、
            # 把"35%"肢解成"5%"；豁免"5%"反过来让"35%"漏检。改成**数字 token 边界匹配**：
            # 只挖"独立完整"的豁免值——左边不能是数字/小数点/千分位逗号（防豁免"200"命中
            # "1,200"的尾段），右边不能是数字延续（[.,]后接数字=同一个数的一部分，如 3.5 /
            # 1,200）或 %（豁免"20"不得豁免"20%"；豁免"20%"本身则整体命中——% 在 t 里时
            # 模式以 % 结尾，lookahead 看的是 % 之后的字符，天然放行）。
            scan_text = re.sub(
                r"(?<![\d.,])" + re.escape(t) + r"(?!(?:[.,]?\d)|%)", "", scan_text)
    # 2026-07-02 saopan扫盘揪出：\d{2,} 放行一位数金额——"亏损5亿元"这种 error 级红线上的
    # fail-open。不能直接放宽成 \d（"3个方案"这类非数据数字会被拉进来，\d{2,} 本来就是防这个），
    # 改为追加"一位数+计量单位"模式：单个数字只有紧跟 亿/万/成/倍/% 等计量单位才算证据数字。
    has_num = bool(re.search(
        r"\d+%|[$￥]\d|\d{2,}|\d(?:\.\d+)?\s*(?:万亿|千万|百万|亿|万|成|倍|%|个百分点)", scan_text))
    has_src = any(k in text.lower() for k in ["source:", "source ", "来源", "数据来源"])
    if has_num and not has_src:
        return [{"rule": "number_no_source", "sev": "error", "note": "含数字无 source"}]
    return []


def check_page_budget(page_type: str, count: int) -> list[dict]:
    """页型容量硬门：超 char_budget → error（02）。"""
    cap = PAGE_BUDGET.get(page_type)
    if cap is not None and count > cap:
        return [{"rule": "over_budget", "sev": "error", "page_type": page_type,
                 "cap": cap, "got": count}]
    return []


def check_field_budget(field_name: str, text: str, cap: int) -> list[dict]:
    """字段级字符长度契约通用版（2026-07-01 yanjiu研究驱动评估🟢采纳，出处：
    research_lib/开源拆解/01应用/presenton.md L27/56/64「每个 string 字段带 .max(30)……
    服务端按 schema 校验，超 maxLength 返回 saved:false + validation_errors 让 LLM
    缩短重试」）：泛化 check_page_budget 的"超上限→error"模式成通用原语，替代此前
    "只有标题(check_title)和6种图表条目数(check_page_budget)两个孤立特例"的局面——
    以后任何字段要接类似的长度硬门，不用再重新写一遍判断逻辑。

    ⚠️ cap 必须由调用方显式传入，本函数不内置任何字段的默认阈值：Presenton 的 .max(30)
    是它自己给每个具体字段各自标定的数字（不同字段各有不同的 max，不是一个通用值），
    不能照搬成本项目 subtitle/sowhat/evidence.data 这类字段的上限——按本项目"标尺来自
    真实样本非模型常识"的一贯纪律（同 check_aspect_ratio 页数区间/语言两支的搁置理由），
    这些新字段的上限要不要机检、定多少，须先拆真实 deck 校准，现在不编数字。校准出来后
    接一行 `check_field_budget("subtitle", text, N)` 即可，机制已就绪。
    """
    n = len(text or "")
    if n > cap:
        return [{"rule": "field_over_budget", "sev": "error", "field": field_name,
                 "cap": cap, "got": n}]
    return []


def check_font(size_pt: int) -> list[dict]:
    """字号硬门：不在 8 级网格 → warn（02 设计系统）。"""
    if size_pt not in FONT_GRID:
        return [{"rule": "font_off_grid", "sev": "warn", "got": size_pt,
                 "grid": sorted(FONT_GRID, reverse=True)}]
    return []


def run_text_gate(text: str, title: str | None = None, exempt_terms=()) -> dict:
    """文案级综合硬门：source(+title)。有 error → passed=False（fail-closed）。

    exempt_terms 透传 check_source（D19 FR5.1/FR1.3：品牌词+client_provided 数字豁免·
    pipeline 逐页组装传入）。"""
    issues = check_source(text, exempt_terms=exempt_terms)
    if title:
        issues += check_title(title)
    return {"issues": issues, "passed": not any(i["sev"] == "error" for i in issues)}
