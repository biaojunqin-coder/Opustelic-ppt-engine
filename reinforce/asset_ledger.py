"""素材/证据溯源台账（④数据产物层）——「这份 deck 每个数字/素材从哪来」的 deck 级汇总。

data/state/_说明.md fill 承诺的 asset_ledger.json 的落点。**不是新硬门**：数字必须溯源的
逐条硬拦在 deck_rules/storyline.py::check_evidence_source（error 级·handoff 拒交接），本台账
是 deck 级汇总视图——从 outline 各页 facets.evidence 自动汇集（evidence 由 to_outline() 从
storyline 带下来；简版 source 字符串 + 完整引用五件套 source_title/outlet/date/quote/url 由
engine/research.py::attach_citation 生成），交付时一键回答「每个数字从哪来」，给客户答疑/
法务复核/项目复盘用。

图像素材段（D16 🟢②·2026-07-02）：台账字面职责是「素材」不只是「数据」——SVG 里
<image href> 引用的图片/logo 的版权来源是咨询/4A 交付的真实合规面（deck_rules 的 H8 只查
href 破损、不管来源合规）。传 svgs 时自动抽 image href 进 images 段，license_note 留空
**供人补**（版权判断是人的事，台账只保证「用了哪些图」这个清单不漏）。

AI 生成记录段（D18 FR4.4·2026-07-02）：images 段除 SVG 引用行外，追加 kind="generation"
的生成过程行（prompt/模型/迭代次数/参考图/成本/时间）——中国 2025-09 判例（北互）下
AI 生成物维权要举证生成过程，这些字段就是客户维权证据链；与本台账既有 evidence 溯源
条目同构（「每个数字从哪来」→「每张 AI 图怎么生成的」）。deck 级 image_cost_summary
汇总生图成本（需求 §六 成本可见）。⚠️ 投放物料记得"AI 生成"标识义务（2025-09-01 施行）
——台账记录是证据链，页面标识是另一件事，别混。

🔻 立此存照（D16 收窄·防反复）：**不搬 W3C PROV 全模型**——Entity-Activity-Agent 三元组
+ wasGeneratedBy/wasAttributedTo 关系链 + RDF 序列化是跨系统互操作/学术工作流的规格；单机
deck 工作流用扁平 entries+citation 已覆盖 PROV 的核心目标（唯一标识/可追溯/可引用）。
将来看到 PROV"高大上"想引入时先读本条。

自动生成为主：pipeline.build_deck 收尾传 workspace 时自动落盘，不需要人另填一遍
（早期 Descente demo 踩过"制作脚本里按页号另开一张硬编码引用表"的反模式——声明式：
evidence 里有引用字段就自动进台账）。无 evidence 的页、无 source 的条目照实列出
（pages_without_evidence / unsourced_count），摊在台账上供人扫，不代判（铁律2）。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

SCHEMA_VERSION = 1
CITATION_KEYS = ("source_title", "source_outlet", "source_date", "source_quote", "source_url")
# <image href="..."> / <image xlink:href="...">（SVG 1.1 用 xlink:href，SVG 2 用裸 href）
# 2026-07-02 saopan扫盘揪出：旧正则只认双引号（href='logo.png' 整条漏抽·台账"用了哪些图"
# 的清单出现盲区），且无前缀防护（data-href="x.png" 这类自定义属性被误抽进台账）。
# 修法：["'] 单双引号都认 + (?<![\w-]) 负向后顾拦住 data-/自定义前缀，只认真正的 (xlink:)href。
_IMAGE_HREF_RE = re.compile(r'<image\b[^>]*?(?<![\w-])(?:xlink:)?href\s*=\s*["\']([^"\']+)["\']', re.I)


def _image_entries(page_n, svg_text: str) -> list[dict]:
    """抽一页 SVG 里全部 <image> 引用。data URI 只记媒体类型不存 base64 全文（台账要可读）。"""
    out = []
    for href in _IMAGE_HREF_RE.findall(svg_text or ""):
        if href.startswith("data:"):
            href = href.split(",", 1)[0] + ",<内嵌 base64·原文见 SVG>"
        out.append({"page": page_n, "href": href, "license_note": ""})
    return out


def merge_generation_records(new_ledger: dict, old_ledger: dict | None) -> dict:
    """把旧台账里的 AI 生图记录（kind="generation"·D18 FR4.4 维权证据链）并进新台账（D26 二轮扫盘🔴）。

    病根：pipeline 每次收尾（含续做/重跑）都用 outline+svgs **从头重建**台账再落盘——
    record_image_generation 记下的生成证据（filename/prompt/model/timestamp·维权举证材料）
    被静默清零（实测：记 1 条→模拟收尾重建→0 条）。生成记录不是 outline 的派生物，
    重建时必须从旧台账搬运保留。去重按 (filename, timestamp)。原地改并返回 new_ledger。
    """
    if not old_ledger:
        return new_ledger
    new_imgs = new_ledger.setdefault("images", [])
    seen = {(r.get("filename"), r.get("timestamp"))
            for r in new_imgs if r.get("kind") == "generation"}
    for r in old_ledger.get("images") or []:
        if r.get("kind") == "generation" and (r.get("filename"), r.get("timestamp")) not in seen:
            new_imgs.append(r)
            seen.add((r.get("filename"), r.get("timestamp")))
    return new_ledger


def build_asset_ledger(outline: dict, svgs: dict | None = None) -> dict:
    """从 outline 各页 facets.evidence（+ 可选 svgs={页号: svg文本} 的图像引用）汇集溯源台账。
    纯函数·不 IO。⚠️ 重建语义：本函数不知道旧台账里的生成记录——落盘前必须
    merge_generation_records 保留 AI 生图维权证据（D26），pipeline 收尾已接线。"""
    entries: list[dict] = []
    images: list[dict] = []
    pages_without: list = []
    svgs = svgs or {}
    for p in outline.get("pages", []):
        n = p.get("n")
        if n in svgs:
            images.extend(_image_entries(n, svgs[n]))
        evs = (p.get("facets") or {}).get("evidence") or []
        if not evs:
            pages_without.append(n)
            continue
        for ev in evs:
            citation = {k: ev[k] for k in CITATION_KEYS if ev.get(k)}
            entries.append({
                "page": n, "claim": p.get("claim", ""),
                "dim": ev.get("dim", ""), "data": ev.get("data", ""),
                "source": ev.get("source", ""), "citation": citation,
                "sourced": bool(ev.get("source") or citation),
            })
    unsourced = sum(1 for e in entries if not e["sourced"])
    return {
        "schema_version": SCHEMA_VERSION,
        "deck_title": outline.get("title", ""),
        "entries": entries,
        "total": len(entries),
        "unsourced_count": unsourced,
        "pages_without_evidence": pages_without,
        "images": images,
    }


# ── D18 FR4.4 AI 生成台账 ────────────────────────────────────────────────────
# 维权证据链必填四件（缺一条证据链就断）：filename（对应哪张图）/ prompt（生成指令）/
# model（用的什么模型）/ timestamp（何时生成·由调用方传入——引擎核心不碰系统时钟，
# 项目既有纪律，同 deck_memory 的 mark_published 一个道理）。
_GENERATION_REQUIRED = ("filename", "prompt", "model", "timestamp")


def record_image_generation(ledger: dict, *, filename: str, prompt: str, model: str,
                            iterations: int = 1, ref_images=None,
                            cost_estimate: float | None = None,
                            timestamp: str = "") -> dict:
    """把一次 AI 生图过程记进台账 images 段（D18 FR4.4·维权证据链）。

    行标 kind="generation" 与 SVG 引用行（{page, href, license_note}·无 kind）共存
    互不干扰——引用行答"页面用了哪些图"，生成行答"这张 AI 图怎么来的"。
    cost_estimate 允许 None（聚合平台不回成本时如实记 unknown·§六成本可见≠编造成本）。
    ref_images 记参考图路径/URL 列表（品牌手册参考图是 Nano Banana Pro 主路径的输入，
    也是判例下"独创性投入"的举证材料）。

    ⚠️ 调用顺序：build_asset_ledger 是从 outline 重建台账（会得到全新 dict），
    生成记录要在 build 之后 record 进同一个 dict 再 save——先 record 后 build 会丢。
    """
    missing = [k for k in _GENERATION_REQUIRED
               if not {"filename": filename, "prompt": prompt,
                       "model": model, "timestamp": timestamp}[k]]
    if missing:
        raise ValueError(f"生成台账缺必填 {missing}（维权证据链四件：文件名/prompt/模型/时间·"
                         f"timestamp 由调用方传入，引擎不碰系统时钟）")
    entry = {
        "kind": "generation",
        "filename": filename,
        "prompt": prompt,
        "model": model,
        "iterations": int(iterations),
        "ref_images": list(ref_images or []),
        "cost_estimate": cost_estimate,
        "timestamp": timestamp,
    }
    ledger.setdefault("images", []).append(entry)
    return entry


def image_cost_summary(ledger: dict) -> dict:
    """deck 级生图成本汇总（D18 FR4.4·需求 §六「生图成本可见」）。

    只汇总 kind="generation" 行（SVG 引用行没有成本概念）。成本未知的行如实计入
    unknown_cost_count 摊出来，不猜不编（铁律 2）——total_cost_estimate 是
    「已知成本之和」，unknown>0 时它是下界不是全额。
    """
    gens = [i for i in (ledger.get("images") or []) if i.get("kind") == "generation"]
    by_model: dict[str, dict] = {}
    known_total = 0.0
    unknown = 0
    for g in gens:
        m = str(g.get("model") or "unknown")
        slot = by_model.setdefault(m, {"count": 0, "cost": 0.0, "unknown_cost_count": 0})
        slot["count"] += 1
        c = g.get("cost_estimate")
        if isinstance(c, (int, float)):
            slot["cost"] = round(slot["cost"] + float(c), 6)
            known_total += float(c)
        else:
            slot["unknown_cost_count"] += 1
            unknown += 1
    return {"generation_count": len(gens),
            "total_cost_estimate": round(known_total, 6),
            "unknown_cost_count": unknown,
            "by_model": by_model}


def save_asset_ledger(ledger: dict, path: str | Path) -> None:
    """台账落盘。普通写即可：台账由 outline 重建（可回滚产物），不是 published 那种不可重建真相源。"""
    Path(path).write_text(json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8")


def load_asset_ledger(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))
