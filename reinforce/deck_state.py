"""deck 状态 State（⑦）—— deck_outline 的 schema 校验 + 读写。

对应 Novel numbers.json/story_graph.json：结构化建模"当前 deck 进行到哪、各页什么状态"。
fail-closed：缺必填/页号重复/坏依赖 → error，save 前必校验通过才写。独立可测。
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

SCHEMA_VERSION = 1
REQUIRED_DECK = ["title", "doc_type", "intent", "domain"]
REQUIRED_PAGE = ["n", "page_function", "claim"]
PAGE_STATUS = {"planned", "drafted", "gated", "done"}
# 页状态生命周期主向流转：planned →(生成SVG) drafted →(硬门全过) gated →(导出) done。
# 2026-07-02 补：PAGE_STATUS 四态早就定义，但 pipeline 此前从不写 status（每页永远停在 planned），
# 状态 schema 是摆设、「非法跳变能被规则引擎逮住」的准入判据也无从兑现——现在 build_deck 逐页
# 真实流转 + 本表硬门校验。
# 2026-07-02 saopan扫盘揪出：resume 复用页硬门重跑失败后状态停在 gated/done 不降级，收尾循环
# 还把 gated 无条件升 done——落盘的 outline.json 变成假绿（门败只活在被丢弃的返回值里，跨会话
# 被遗忘）。此前"不设 revert 机制"针对的是人审毙掉的罕见人工路径；resume 重检失败是**机器路径**
# （规则升级后旧页重检必然发生），必须有机器降级通道 → 补 gated/done→drafted 返工边，仅供
# build_deck 在 resume 门败时调用。人工改 JSON 的介入口照旧存在。
STATUS_FLOW = {"planned": {"drafted"}, "drafted": {"gated"},
               "gated": {"done", "drafted"}, "done": {"drafted"}}


def new_outline(title: str, doc_type: str, intent, domain, audience=None,
                brand_terms=None) -> dict:
    """建空 deck_outline 骨架（facets 在 deck 级）。

    brand_terms（D19 FR5.1）：品牌名豁免表——品牌名含数字（"059"）曾被 check_source 当
    统计数字 error 误报（第二轮实测复现）。命中豁免词的数字串不当统计数字；strategy 交棒
    时 to_outline 从 storyline.brand 自动带下，用户可补别名（["059", "059某品牌精酿公社"]）。
    """
    return {
        "schema_version": SCHEMA_VERSION,
        "title": title, "doc_type": doc_type,
        "intent": intent if isinstance(intent, list) else [intent],
        "domain": domain if isinstance(domain, list) else [domain],
        "audience": audience or [], "brand_terms": list(brand_terms or []), "pages": [],
    }


def add_page(outline: dict, n: int, page_function: str, claim: str,
             card_ref: str | None = None, depends_on=None, facets=None) -> dict:
    """加一页（claim=action title 论断·card_ref=用的页型卡 id·depends_on=前序页号）。"""
    outline.setdefault("pages", []).append({
        "n": n, "page_function": page_function, "claim": claim,
        "card_ref": card_ref, "depends_on": depends_on or [],
        "facets": facets or {}, "status": "planned",
    })
    return outline


def validate_outline(d: dict) -> dict:
    """校验结构 → {issues, valid}。非法跳变/缺字段/坏依赖被逮（fail-closed）。"""
    issues = []
    for k in REQUIRED_DECK:
        if k not in d or d.get(k) in (None, "", []):
            issues.append({"sev": "error", "msg": f"deck 缺必填 {k}"})
    # 2026-07-02 saopan扫盘揪出：pages=None（合法 JSON 手改场景）在此崩 TypeError——第一道
    # 结构门自己被崩溃击穿，与 check_page_count_consistency 当年同因；全文件 .get(k, 默认)
    # 对"键在但值为 None"不设防，统一 or 兜底（fail-loud 要 loud 在 issues 里，不是崩栈）。
    pages = d.get("pages") or []
    all_n = [p.get("n") for p in pages]
    seen = set()
    for p in pages:
        for k in REQUIRED_PAGE:
            if k not in p or p.get(k) in (None, ""):
                issues.append({"sev": "error", "msg": f"页 {p.get('n','?')} 缺 {k}"})
        n = p.get("n")
        if n in seen:
            issues.append({"sev": "error", "msg": f"页号重复 {n}"})
        seen.add(n)
        st = p.get("status")
        if st and st not in PAGE_STATUS:
            issues.append({"sev": "warn", "msg": f"未知 status '{st}' @p{n}"})
        for dep in p.get("depends_on") or []:
            if dep not in all_n:
                issues.append({"sev": "error", "msg": f"p{n} 依赖不存在的 p{dep}"})
    ns = sorted(x for x in seen if isinstance(x, int))
    if ns and ns != list(range(ns[0], ns[0] + len(ns))):
        issues.append({"sev": "warn", "msg": "页号不连续"})
    return {"issues": issues, "valid": not any(i["sev"] == "error" for i in issues)}


def check_status_transition(old: str, new: str) -> list[dict]:
    """页状态跳变校验：主向流转 + 返工降级边，跳级/未知态 → error（非法跳变被规则引擎逮住）。

    同状态重放（drafted→drafted）不算跳变——断点续做重跑同一页是合法幂等操作。
    合法边见 STATUS_FLOW：主向 planned→drafted→gated→done；降级 gated/done→drafted
    仅一种语义——硬门重跑未过·返工（resume 场景 build_deck 机器调用）。
    """
    issues = []
    if old not in PAGE_STATUS:
        issues.append({"sev": "error", "msg": f"未知源状态 '{old}'"})
    if new not in PAGE_STATUS:
        issues.append({"sev": "error", "msg": f"未知目标状态 '{new}'"})
    if issues:
        return issues
    if old != new and new not in STATUS_FLOW[old]:
        issues.append({"sev": "error",
                       "msg": f"非法跳变 {old}→{new}（主向 planned→drafted→gated→done·"
                              f"降级仅允许 gated/done→drafted 返工）"})
    return issues


def page_input_fingerprint(page: dict, spec_lock: dict | None = None) -> str:
    """页的「直接输入」指纹（sha256）——Bazel action key 思路（复用判定该看输入摘要，
    不该只看产物文件还在不在·D16 🟡②）：claim/page_function/facets 等产出本页 SVG 的
    直接输入 + spec_lock，canonical JSON 后取哈希。status / input_fingerprint 自身除外
    （生命周期不是输入）。

    诚实边界：只算**本页直接输入**——依赖页（depends_on 指向的页）的 claim 变了会影响
    prompt 里的承接语境但不进本指纹（否则前页改一个字全 deck 指纹连锁失效，过敏）；
    这类跨页漂移留给硬门重跑 + 人审，不假装指纹全知。
    """
    src = {k: v for k, v in page.items() if k not in ("status", "input_fingerprint")}
    blob = json.dumps({"page": src, "spec_lock": spec_lock or {}},
                      ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def set_page_status(outline: dict, n: int, new_status: str) -> dict:
    """改第 n 页状态（fail-closed：页不存在 / 非法跳变 → 抛拒改）。"""
    page = next((p for p in outline.get("pages", []) if p.get("n") == n), None)
    if page is None:
        raise ValueError(f"页 {n} 不存在·拒改状态")
    issues = check_status_transition(page.get("status", "planned"), new_status)
    if issues:
        raise ValueError(f"页 {n} 状态跳变非法·拒改：{issues}")
    page["status"] = new_status
    return outline


def load_outline(path: str | Path) -> dict:
    """读 outline（fail-closed：schema_version 比本代码新 → 拒读，防旧代码剥掉新版字段）。

    2026-07-02 saopan扫盘揪出：schema_version 此前只写不读——未来版本的数据被 v1 代码
    读改写一轮字段就丢了，版本号形同虚设。低/缺版本照常读（v1 起点·无历史包袱）。
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    ver = data.get("schema_version", SCHEMA_VERSION)
    if isinstance(ver, int) and ver > SCHEMA_VERSION:
        raise ValueError(f"outline schema_version={ver} 比本代码支持的 {SCHEMA_VERSION} 新·"
                         f"拒读（防旧代码静默剥掉新版字段）：{path}")
    return data


def save_outline(outline: dict, path: str | Path) -> dict:
    """校验通过才写（fail-closed·非法拒写）。

    2026-07-02 saopan扫盘揪出：outline.json 是写得最频繁的活文件（build_deck 每页回写）、
    又是断点续做唯一入口，此前裸 write_text——「防中断丢进度」的机制自身可被中断打成半截
    JSON。改 tmp+rename 原子写（同 deck_memory._atomic_write 一个道理：同目录保证同文件系统）。
    """
    r = validate_outline(outline)
    if not r["valid"]:
        raise ValueError(f"deck_outline 非法·拒写：{r['issues']}")
    p = Path(path)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(outline, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)
    return r
