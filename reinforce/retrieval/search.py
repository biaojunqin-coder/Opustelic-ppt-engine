"""检索：按 facets 评分召回，对应 Novel exemplars.search_exemplars。跨六库统一评分口径。

评分：主键 facet 精确 +4 / 模糊 +2 · domain 交集 ×2 · 其余 facet 交集 ×1。
无任何 facet → 全返回，按 rating 降序（兜底浏览）。纯读·确定性·独立可测。

四库检索函数（页型卡/表达手法卡/分析框架库/行业知识库）+ 时效性巡检 + 跨库同源索引。
"""

from __future__ import annotations

import json
import os
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(os.environ.get("PPT_DIR", str(Path(__file__).resolve().parent.parent.parent)))
CARDS_FILE = ROOT / "exemplars" / "页型卡库.json"
EXPRESSION_FILE = ROOT / "exemplars" / "表达手法卡.json"
FRAMEWORK_FILE = ROOT / "exemplars" / "分析框架库.json"
FACT_FILE = ROOT / "research_lib" / "真实样本" / "_行业知识库.json"

STALE_THRESHOLD_YEARS = 2  # timeliness 里标的年份距今超过这个阈值 → 巡检标记待复核

# ── D18 FR3.3 页型词表同义映射 ──────────────────────────────────────────────
# 病根（第一轮实测确诊·22 页喂错卡）：storyline 的 9 个 PAGE_TYPES（reinforce/storyline_state.py·
# 节奏角色词）跟页型卡库 exemplars/页型卡库.json 的真实 page_function 词表是两套词——
# 如 search(page_function='数据论断') 对卡库的"数据呈现"既不相等也非互为子串 → 主键 0 分，
# 检索全靠 domain 撑，错卡上位。2026-07-02 全量 distinct 抽卡库词表后，把 9 个 PAGE_TYPES
# 逐个对到卡库真实词建此映射（值必须是卡库真实存在的词或其可靠前缀——子串模糊靠它接上）。
# 映射双向生效（查"数据呈现"也能扩出"数据论断"），同义词与主词同权重参与精确/模糊匹配。
# 注：封面/转场/情绪slogan/高潮/落幕五词靠子串模糊本就能命中（如"高潮"⊂"高潮页"），
# 仍显式建条目——把"词表已对齐"变成看得见的清单，卡库词表将来漂了有单测逮。
PAGE_FUNCTION_SYNONYMS: dict[str, list[str]] = {
    "封面": ["封面/章节", "封面钩子页"],
    "目录": ["议程"],                                # 卡库无"目录"字样·目录页手法卡叫"议程"
    "转场": ["转场页", "过渡页"],
    "数据论断": ["数据呈现", "数据callout页", "效果预估", "案例数据仪表盘页"],
    "情绪slogan": ["情绪slogan页", "宣言页", "品牌宣言"],
    "高潮": ["高潮页"],
    "落幕": ["落幕页"],
    "决策": ["多方案并列选优页", "并列对比选择", "二选一"],  # 决策页=选项收敛拍板·卡库对应"选优/对比选择"族
    "创意展示": ["创意"],                            # 卡库创意类卡全带"创意"字样·子串族收
}


def _expand_page_function(q: str | None) -> tuple[str, ...]:
    """q 的同义词组（不含 q 本身）——双向查：q 是映射键取其值；q 落在某键的值里则把
    该键与同组词全收进来。无同义 → ()。"""
    if not q:
        return ()
    terms: set[str] = set(PAGE_FUNCTION_SYNONYMS.get(q, ()))
    for k, vs in PAGE_FUNCTION_SYNONYMS.items():
        if q == k or q in vs:
            terms.add(k)
            terms.update(vs)
    terms.discard(q)
    return tuple(sorted(terms))


def _load(path: Path, list_key: str) -> list[dict]:
    if not path.is_file():
        return []
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if isinstance(d, dict):
        return d.get(list_key, [])
    return d if isinstance(d, list) else []


def load_cards(path: str | Path | None = None) -> list[dict]:
    """读页型卡库.json 的 cards 列表（缺/坏 → []）。"""
    return _load(Path(path) if path else CARDS_FILE, "cards")


def load_expression_cards(path: str | Path | None = None) -> list[dict]:
    """读表达手法卡.json 的 cards 列表（缺/坏 → []）。"""
    return _load(Path(path) if path else EXPRESSION_FILE, "cards")


def load_frameworks(path: str | Path | None = None) -> list[dict]:
    """读分析框架库.json 的 cards 列表（缺/坏 → []）。"""
    return _load(Path(path) if path else FRAMEWORK_FILE, "cards")


def load_facts(path: str | Path | None = None) -> list[dict]:
    """读 _行业知识库.json 的 facts 列表（缺/坏 → []）。"""
    return _load(Path(path) if path else FACT_FILE, "facts")


def _overlap(query, field) -> int:
    """query(str|list) 与 card 字段(str|list) 的交集大小。"""
    if not query or not field:
        return 0
    sq = {query} if isinstance(query, str) else set(query)
    sf = {field} if isinstance(field, str) else set(field)
    return len(sq & sf)


def _score_by_key(items: list[dict], key_field: str, key_query: str | None, *,
                   domain=None, extra: dict | None = None,
                   key_synonyms: tuple[str, ...] = ()) -> list[tuple[dict, int]]:
    """通用打分器：key_field 精确+4/模糊+2 · domain 交集×2 · extra(字段名→query) 交集×1。

    key_synonyms（D18 FR3.3）：主键查询词的同义词组，与主词同权重参与精确/模糊匹配，
    主键得分取所有词中的最高（不叠加——同义词是"换个叫法"不是"多个证据"）。
    """
    extra = extra or {}
    no_facet = not any([key_query, domain, *extra.values()])
    scored: list[tuple[dict, int]] = []
    for it in items:
        if no_facet:
            scored.append((it, it.get("rating", 0)))
            continue
        s = 0
        if key_query:
            kv = it.get(key_field, "")
            best = 0
            for q in (key_query, *key_synonyms):
                if q == kv:
                    best = max(best, 4)
                elif kv and (q in kv or kv in q):
                    # kv and（2026-07-03 saopan批②）：主键空串的卡此前 "" in q 恒真——
                    # 白得 2 分混进任意查询的结果；空键=没这个 facet，就该 0 分
                    best = max(best, 2)
            s += best
        s += 2 * _overlap(domain, it.get("domain"))
        for field, q in extra.items():
            s += 1 * _overlap(q, it.get(field))
        if s > 0:
            scored.append((it, s))
    scored.sort(key=lambda x: (x[1], x[0].get("rating", 0)), reverse=True)
    return scored


def search_deck_cards(page_function: str | None = None, domain=None, intent=None,
                      doc_type=None, cards: list[dict] | None = None, top: int | None = None):
    """按 facets 检索页型卡·返回 [(card, score)] 降序。对应 Novel search_exemplars(题材, 桥段)。

    D18 FR3.3：page_function 走同义映射扩词（storyline PAGE_TYPES ↔ 卡库词表两套词对齐，
    见 PAGE_FUNCTION_SYNONYMS）——只有页型卡这条检索路径吃同义词，其余三库词表没有错位病。
    """
    cards = cards if cards is not None else load_cards()
    scored = _score_by_key(cards, "page_function", page_function, domain=domain,
                            extra={"intent": intent, "doc_type_seen": doc_type},
                            key_synonyms=_expand_page_function(page_function))
    return scored[:top] if top else scored


def search_expression_cards(expression_type: str | None = None, domain=None,
                             cards: list[dict] | None = None, top: int | None = None,
                             slot: str | None = None):
    """按 facets 检索表达手法卡（文案/修辞公式）·返回 [(card, score)] 降序。

    slot（D20 FR1.3·结构性文案槽位精确路由）：六槽位之一（目录命名/章间桥/章小结/
    诊断收束/ask收尾/落幕）——传入则**只在带该 slot 的卡里检索**（槽位卡是"页面位置"
    驱动的正向范式，与"内容手法"驱动的 expression_type 检索正交）；转场页生成给章间桥、
    决策页给 ask 收尾——防说明书感的正向弹药按位置精确送达（第三轮实测确诊元叙述全长在
    结构性文案位置）。
    """
    cards = cards if cards is not None else load_expression_cards()
    if slot:
        cards = [c for c in cards if c.get("slot") == slot]
    scored = _score_by_key(cards, "expression_type", expression_type, domain=domain)
    return scored[:top] if top else scored


def search_frameworks(framework_type: str | None = None, domain=None,
                       cards: list[dict] | None = None, top: int | None = None):
    """按 facets 检索分析框架库（可复用策略思考工具）·返回 [(card, score)] 降序。"""
    cards = cards if cards is not None else load_frameworks()
    scored = _score_by_key(cards, "framework_type", framework_type, domain=domain)
    return scored[:top] if top else scored


def search_facts(fact_type: str | None = None, domain=None,
                  facts: list[dict] | None = None, top: int | None = None):
    """按 facets 检索行业知识库（真实行业事实）·带 facet 时按相关性 [(fact, score)] 降序。

    ⚠️ **无 facet 时不按"重要性"排序，只按入库原始顺序返回**——`_score_by_key` 的兜底逻辑是
    "按 rating 降序"，但行业知识库(facts) schema 里**没有 rating 字段**(chaideck 轨6设计时，
    事实类内容本来就没有"打分"这个概念，跟框架/手法这类判断性内容不一样)，`it.get("rating", 0)`
    全部退化成 0，等价于稳定排序=原始插入顺序，**不是真的按重要性排的**——如实告知，不假装排了序。
    页型卡/表达手法卡/分析框架库三个库都有 rating 字段，兜底排序对它们是有意义的，只有 facts 例外。
    ⚠️ 不做时效性过滤——用哪条自己判断，过期与否见 flag_stale_facts，本函数只管相关性排序。
    """
    facts = facts if facts is not None else load_facts()
    scored = _score_by_key(facts, "fact_type", fact_type, domain=domain)
    return scored[:top] if top else scored


def search(**kw) -> list[dict]:
    """便捷：只返回页型卡列表（不带 score）。"""
    return [c for c, _ in search_deck_cards(**kw)]


# ---------- 时效性巡检 ----------

_YEAR_RE = re.compile(r"(20\d{2})年")


def flag_stale_facts(facts: list[dict] | None = None, *, current_year: int,
                      threshold_years: int = STALE_THRESHOLD_YEARS) -> list[dict]:
    """扫 timeliness 字段里的年份，距 current_year 超过 threshold_years → 标记待复核。

    只做"抽年份+算距今几年"的确定性活，不判断"是不是真的过期"（同 review.py 的
    extract_numeric_facts 分工原则：机器摘录，语义判断留给人）。timeliness 里没标年份的
    (如"无具体年份标注")不参与判断——不编造年份，如实跳过。
    """
    facts = facts if facts is not None else load_facts()
    flagged = []
    for f in facts:
        years = [int(y) for y in _YEAR_RE.findall(f.get("timeliness", ""))]
        if not years:
            continue
        latest = max(years)
        age = current_year - latest
        if age >= threshold_years:
            flagged.append({"id": f.get("id"), "latest_year": latest, "age_years": age,
                             "timeliness": f.get("timeliness")})
    return sorted(flagged, key=lambda x: -x["age_years"])


# ---------- 跨库同源索引 ----------

# 中/英文括号及其内容（不含嵌套层·由 _norm_source 循环剥净）
_PAREN_RE = re.compile(r"[（(][^（()）]*[)）]")


def _norm_source(s: str) -> str:
    """source 键归一化口径（2026-07-02 saopan扫盘揪出：入库时同一份 deck 的 source 标注带各种
    括号备注——如 '某品牌 2025 Social Campaign提案' / '…(47页demo版)' / '…(47页demo版+69页
    完整版共同印证)' 是 3 个不同键，25 份 deck 裂成 123 个键，related_by_source 同源接不上）。

    口径：①剥掉中英文括号（（…）/(…)）及括号内内容，循环剥直到不动（防嵌套/多组括号残留）；
    ②连续空白压成单个空格；③去首尾空白。**只改检索时的匹配逻辑，绝不回写卡库 JSON**——
    改卡库数据要走 record_library_change 留痕，且是数据治理大事，不归检索层管。
    """
    s = s or ""
    prev = None
    while prev != s:
        prev = s
        s = _PAREN_RE.sub("", s)
    return re.sub(r"\s+", " ", s).strip()


def related_by_source(source: str) -> dict:
    """给定 source(deck 文件名/来源标注)，跨四库找同源条目——同一份 deck 抽出的页型卡/表达手法卡/
    分析框架/行业事实彼此现在互相不知道对方存在，这里给个最简单的"按 source 字符串精确/子串匹配"
    索引，不追求语义关联，只解决"这份 deck 我们还挖到过什么"这个最基本的问题。

    匹配前两边都先过 _norm_source 归一化（口径见其 docstring）——传哪个括号变体进来都能接上同源。
    归一后为空（纯括号/空串）→ 全空结果：空串子串匹配恒真，不拦会把整库都"命中"。
    """
    ns = _norm_source(source)

    def _match(items):
        if not ns:
            return []
        out = []
        for it in items:
            nit = _norm_source(it.get("source", ""))
            if nit and (ns in nit or nit in ns):
                out.append(it)
        return out

    return {
        "page_cards": _match(load_cards()),
        "expression_cards": _match(load_expression_cards()),
        "frameworks": _match(load_frameworks()),
        "facts": _match(load_facts()),
    }


def sources_index() -> dict:
    """反向索引：归一化 source → {counts: 各库条目数, raw_sources: [原始 source 键…]}，
    用于一次性扫描"这份deck六轨分别挖到几条"。

    2026-07-02 起按 _norm_source 归一键聚合（此前按原始 source 字符串分桶，同一 deck 的括号
    备注变体各占一桶）；原始写法保留在 raw_sources 里，溯源时能对回卡库里的原样标注。
    """
    idx: dict[str, dict] = defaultdict(lambda: {"counts": {"page_cards": 0, "expression_cards": 0,
                                                             "frameworks": 0, "facts": 0},
                                                  "raw_sources": []})
    for key, loader in (("page_cards", load_cards), ("expression_cards", load_expression_cards),
                        ("frameworks", load_frameworks), ("facts", load_facts)):
        for it in loader():
            src = it.get("source", "")
            if not src:
                continue
            norm = _norm_source(src) or src.strip()  # 归一后为空(纯括号)兜底用原键·信息不丢
            entry = idx[norm]
            entry["counts"][key] += 1
            if src not in entry["raw_sources"]:
                entry["raw_sources"].append(src)
    return dict(idx)
