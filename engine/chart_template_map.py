"""D18 FR3.1 chart→资产映射表 + FR3.5 Part 级视觉配额（warn）。

第一轮实测（某品牌 24 页）确诊：storyline 声明了 20 种 chart facet，制作层兑现 0 张——
71 张结构模板（engine/ppt_master/templates/charts/）和 3 个确定性几何引擎（chart_shapes.py）
全程零注入，逐页 prompt 里只有 chart 的英文名，Executor 只能凭空想象结构。本表把"策略层
技术词汇（chart facet）"→"制作层资产（模板文件/几何引擎）"这条断线接上：
`build_deck_prompt` 按当页 chart 查表，把对口模板的 SVG 源码拼进 prompt（延续 spec_lock
「模板供结构不供皮肤」纪律——布局照学、颜色字体必须换成锁定色板）。

映射键 = 实测出现过的 chart facet 名（storyline lines[].chart / spec_lock per_page[].chart），
值 schema：{"template": templates/charts/ 下文件名 or None, "engine": chart_shapes 引擎名 or None,
"hint": 一句结构要点}。template=None 且 engine=None 的条目 = 纯排版页型（引言/洞察陈述这类），
hint 仍会进 prompt，但不算 FR3.5 的"强视觉页"。
"""

from __future__ import annotations

import re
from pathlib import Path

# 71 张结构模板所在目录（真实资产·charts_index.json 有全量索引）
TEMPLATES_DIR = Path(__file__).resolve().parent / "ppt_master" / "templates" / "charts"

# ── D18 FR3.1 映射表：chart facet → {template, engine, hint} ─────────────────
# 键覆盖：chart_shapes 引擎 3 种 + 第一轮实测 deck 声明过的全部 chart facet（23 种·
# 2026-07-02 从 data/decks/*/storyline.json + spec_lock per_page 全量统计）+ 常用模板直名 2 种。
# template 文件名逐一对照 templates/charts/ 真实存在（有单测锁定，防映射到不存在的资产）。
CHART_TEMPLATE_MAP: dict[str, dict] = {
    # ── chart_shapes.py 确定性几何引擎三种（坐标必须调引擎算·模板另供视觉结构参考）──
    "waterfall": {"template": "waterfall_chart.svg", "engine": "waterfall",
                  "hint": "浮空柱区间=前值滚动累加，升/降/合计三色区分，柱间桥接虚线"},
    "gantt": {"template": "gantt_chart.svg", "engine": "gantt",
              "hint": "时间轴线性铺满画布宽，任务条+里程碑菱形+依赖箭头，行标签紧贴色条"},
    "mekko": {"template": None, "engine": "mekko",
              "hint": "列宽=各列权重占比，列内 100% 堆叠（份额自动归一），双维占比一图讲清"},
    # ── 数据图表类 ──
    "line_compare": {"template": "line_chart.svg", "engine": None,
                     "hint": "多系列折线同轴对比，拐点/结论区间显式标注，系列名标线尾不塞图例"},
    "trend_shift": {"template": "line_chart.svg", "engine": None,
                    "hint": "折线突出趋势换挡：拐点前后分段着色/标注，结论写在拐点旁"},
    "bar_callout": {"template": "bar_chart.svg", "engine": None,
                    "hint": "柱状图+关键柱高亮（其余柱降灰），callout 大数字指向被强调柱"},
    "donut": {"template": "donut_chart.svg", "engine": None,
              "hint": "环形占比，中心放大数字/结论，扇区从 12 点顺时针按大小排"},
    "metric_callout": {"template": "kpi_cards.svg", "engine": None,
                       "hint": "大数字 KPI 卡并列（数字为主体·标签为辅），3-4 卡一行"},
    "media_mix": {"template": "stacked_bar_chart.svg", "engine": None,
                  "hint": "渠道×占比堆叠条（预算/声量配比），段内标百分比，图例按堆叠序"},
    "aipl_funnel": {"template": "funnel_chart.svg", "engine": None,
                    "hint": "漏斗逐层收窄（A-I-P-L 链路），层间标转化率，层内标人群量级"},
    # ── 框架/结构图类 ──
    "kol_pyramid": {"template": "pyramid_chart.svg", "engine": None,
                    "hint": "金字塔分层（头部→腰部→素人），每层标量级+角色定位，宽度示意声量"},
    "expansion_map": {"template": "hub_spoke.svg", "engine": None,
                      "hint": "中心辐射式扩张结构（大本营居中→扩张点放射），辐射线标先后波次"},
    "hub_spoke": {"template": "hub_spoke.svg", "engine": None,
                  "hint": "中心枢纽+辐射节点，中心放核心概念，节点等距环布"},
    "wave_timeline": {"template": "timeline.svg", "engine": None,
                      "hint": "时间轴分波段（Teaser/Launch/Sustain 三段式），波段间标节奏切换点"},
    "content_pillars": {"template": "vertical_pillars.svg", "engine": None,
                        "hint": "3-4 根内容支柱并列，柱头=支柱名，柱身=内容方向要点"},
    "mechanism_diagram": {"template": "process_flow.svg", "engine": None,
                          "hint": "节点+箭头机制链路，环节名短词，箭头上标传导逻辑"},
    "design_logic": {"template": "chevron_process.svg", "engine": None,
                     "hint": "推导链条逐步递进（洞察→策略→设计），箭头段首尾呼应"},
    "video_concept": {"template": "journey_map.svg", "engine": None,
                      "hint": "横向分格叙事（分镜：画面示意+旁白/字幕逐格），格间有时序感"},
    # ── 表格类 ──
    "checklist_table": {"template": "basic_table.svg", "engine": None,
                        "hint": "清单表格（事项×状态/说明列），行少列窄，勾选列视觉统一"},
    "budget_table": {"template": "consulting_table.svg", "engine": None,
                     "hint": "预算表（项目行×金额/占比列）+合计行加重，大数右对齐"},
    # ── 论断/文字主体类（无对口图表模板·纯排版，hint 仍进 prompt）──
    "risk_statement": {"template": "pros_cons_chart.svg", "engine": None,
                       "hint": "风险×应对双栏对照，一行风险配一行缓释动作，别只列风险不给解法"},
    "brief_recap": {"template": "vertical_list.svg", "engine": None,
                    "hint": "任务要求逐条列点+我方理解并置，条目短句化，出处标注 brief 页码进备注"},
    "decision_box": {"template": "labeled_card.svg", "engine": None,
                     "hint": "决策请求放显眼强调框：选项+我方建议+需拍板点，一页只请一个决策"},
    "quote_callout": {"template": None, "engine": None,
                      "hint": "纯排版：大引号+引言主体（放大）+出处署名（缩小），留白撑气场"},
    "consumer_insight": {"template": None, "engine": None,
                         "hint": "洞察陈述：张力句为页面主体，支撑证据小字随注，不堆卡片网格"},
    "text_highlight": {"template": None, "engine": None,
                       "hint": "纯排版：关键词放大高亮+其余文字降噪（灰/小），一页一个强调焦点"},
    "creative_concept": {"template": None, "engine": None,
                         "hint": "创意概念主视觉页：概念名大字+一句阐述+视觉示意，别套数据图表"},
    "cover": {"template": None, "engine": None,
              "hint": "封面走版式骨架（spec_lock per_page.layout 路由 templates/layouts/），不套图表模板"},
}

# 惰性缓存：templates/charts/ 全部模板文件词根（模糊匹配②用·71 张）
_STEMS_CACHE: list[str] | None = None


def _template_stems() -> list[str]:
    """列出 templates/charts/ 下全部模板文件名词根（去 .svg·排序保确定性）。目录缺失 → []。"""
    global _STEMS_CACHE
    if _STEMS_CACHE is None:
        try:
            _STEMS_CACHE = sorted(p.stem for p in TEMPLATES_DIR.glob("*.svg"))
        except OSError:
            _STEMS_CACHE = []
    return _STEMS_CACHE


def _is_contiguous_subseq(needle: tuple, hay: tuple) -> bool:
    """needle 是否为 hay 的连续子序列（按 token 边界比，防 pie↔pipeline 这类子串假配）。"""
    n = len(needle)
    return n > 0 and any(hay[i:i + n] == needle for i in range(len(hay) - n + 1))


def template_for_chart(chart: str | None) -> dict | None:
    """D18 FR3.1：按 chart facet 名查映射 → {template, engine, hint, matched, match} 或 None。

    三级匹配（全部大小写不敏感）：
    ① exact：映射键精确命中；
    ② fuzzy_key：与某映射键互为子串（如 line_compare_yoy → line_compare），取最长键；
    ③ fuzzy_template：chart 名的 token 里含某模板词根（kol_pyramid → pyramid_chart.svg，
       词根=模板名去 _chart 后缀·按 token 连续子序列匹配），取词根最长者。
    全不中 → None（调用方决定怎么兜底，本函数不编造映射）。
    """
    if not chart or not str(chart).strip():
        return None
    key = str(chart).strip().lower()
    if key in CHART_TEMPLATE_MAP:
        return {"chart": key, "matched": key, "match": "exact", **CHART_TEMPLATE_MAP[key]}
    # 模糊①：与映射键互为子串——取最长键（防 "bar" 这类短键抢走更具体的命中）。
    # len(key)>=3 才进（2026-07-03 saopan批②）：单字/双字输入是任意映射键的子串
    # （'e' in "mechanism_diagram" 恒真），短垃圾输入必然假配——太短没资格谈"互为子串"
    if len(key) >= 3:
        subs = [k for k in CHART_TEMPLATE_MAP if k in key or key in k]
        if subs:
            best = max(subs, key=len)
            return {"chart": key, "matched": best, "match": "fuzzy_key", **CHART_TEMPLATE_MAP[best]}
    # 模糊②：token 词根对 71 张模板文件名
    tokens = tuple(t for t in re.split(r"[^a-z0-9]+", key) if t)
    best_stem, best_root = None, ()
    for stem in _template_stems():
        root = stem[:-len("_chart")] if stem.endswith("_chart") else stem
        rtok = tuple(t for t in root.split("_") if t)
        if _is_contiguous_subseq(rtok, tokens) and (len(rtok), len(root)) > (len(best_root), len("_".join(best_root))):
            best_stem, best_root = stem, rtok
    if best_stem:
        return {"chart": key, "matched": best_stem, "match": "fuzzy_template",
                "template": f"{best_stem}.svg", "engine": None,
                "hint": f"结构对口模板 {best_stem}，布局照模板、皮肤换 spec_lock 色板"}
    return None


"""D22 视觉丰富度：类型智能默认 + 图像配额分级执法（第五轮实测"总推荐特别素"三层病根之三）。"""

# deck 类型关键词 → 默认丰富度档（用户可改·推荐时须说明为什么是这档）
_RICHNESS_RICH_KEYS = ("比稿", "创意", "营销", "campaign", "品牌", "imc", "kv", "发布会", "推广")
_RICHNESS_PLAIN_KEYS = ("尽调", "董事会", "财务", "估值", "审计", "投委会", "法务")


def default_richness_for(purpose: str) -> tuple[str, str]:
    """按 deck 目的/类型给丰富度默认档 → (档, 一句为什么)——"素"从此是被选择的，不是被默认的。

    比稿/创意/营销类默认浓郁（客户买的是感染力），尽调/董事会类默认素雅（决策场合克制专业），
    其余标准。只做推荐默认：普通档在设计定稿轮摊给用户拍板，直通档进开场配置舱。
    """
    p = (purpose or "").lower()
    for k in _RICHNESS_RICH_KEYS:
        if k in p:
            return "浓郁", f"目的含「{k}」——比稿/创意/营销类客户买的是感染力，默认图像与设计浓度拉满"
    for k in _RICHNESS_PLAIN_KEYS:
        if k in p:
            return "素雅", f"目的含「{k}」——决策/尽调场合克制专业，数据与留白主导"
    return "标准", "非典型创意/决策场景，图文均衡起步（可随时改档）"


def check_image_quota(outline: dict, spec_lock: dict | None = None) -> list[dict]:
    """D22 图像配额分级执法——图像与图表分开计数（旧 Part 配额里图表也算强视觉，
    全 deck 零照片/插画照样过，是"素"的机检洞）。

    计数口径：spec_lock.images 清单行数（六源含 placeholder 都算——真人接管也是设计过的
    视觉位；没设计才是问题）。分级：
      浓郁：下限 max(3, 页数//8)，不足 → **error**（用户亲选/类型默认了浓郁就必须兑现——
            直通档下 warn 整批架空[人审已 waiver]，必须有 error 层兜底·fail-closed）；
      标准：一张图像位都没有 → warn；
      素雅 / richness 未锁：不查（评估不了就不评估，旧 deck 零破坏）。
    """
    spec = spec_lock or {}
    rich = spec.get("richness")
    if rich not in ("标准", "浓郁"):
        return []
    pages = (outline or {}).get("pages") or []
    n_images = len(spec.get("images") or [])
    if rich == "浓郁":
        floor = max(3, len(pages) // 8)
        if n_images < floor:
            return [{"sev": "error", "msg":
                     f"丰富度=浓郁 但 images 清单仅 {n_images} 张（{len(pages)} 页下限 {floor}）"
                     f"——浓郁档是用户拍板的承诺，图像位不达标拒做；回设计定稿补足 images 清单"
                     f"（六源获取·免费图库搜不到可标 placeholder 真人接管，但位置必须设计出来）"}]
        return []
    if n_images == 0:
        return [{"sev": "warn", "msg":
                 f"丰富度=标准 但 images 清单为空（{len(pages)} 页零图像位）——图文均衡档"
                 f"建议至少给封面/高潮页设计图像位，全 deck 纯图表容易'素'"}]
    return []


def check_part_visual_quota(outline: dict, spec_lock: dict | None = None) -> list[dict]:
    """D18 FR3.5：Part 级视觉配额机检（warn·不拦）——真样本节奏是每章 1-2 页强视觉页。

    按 outline pages 的 facets.part 分组；"强视觉页"判定（任一命中即算）：
    ① facets.chart 经 template_for_chart 命中且有 template 或 engine（真图表/框架图）；
    ② spec_lock.per_page[n] 声明了 layout（版式骨架页）或 hero（巨字/门面页）。
    某 Part 全组 0 强视觉页 → 一条 warn。没标 part 的页不参与（老 deck 无 part 字段时
    不误报——评估不了就不评估，不假装评估过）。返回 issues 列表，pipeline 接线由调用方做。
    """
    pages = (outline or {}).get("pages") or []
    per_page = (spec_lock or {}).get("per_page") or {}
    groups: dict[str, list[dict]] = {}
    for p in pages:
        part = (p.get("facets") or {}).get("part")
        if part in (None, ""):
            continue
        groups.setdefault(str(part), []).append(p)
    issues = []
    for part, ps in groups.items():
        strong = []
        for p in ps:
            n = p.get("n")
            # per_page str 键为正·int 键兼容旧落盘数据（同 spec_lock_brief 的查询口径）
            lock = per_page.get(str(n)) or per_page.get(n) or {}
            m = template_for_chart((p.get("facets") or {}).get("chart"))
            hits_asset = bool(m and (m.get("template") or m.get("engine")))
            if hits_asset or lock.get("layout") or lock.get("hero"):
                strong.append(n)
        if not strong:
            issues.append({"sev": "warn", "part": part,
                           "pages": [p.get("n") for p in ps],
                           "msg": f"Part「{part}」全组 {len(ps)} 页无强视觉页（真图表/框架图/版式骨架/巨字页"
                                  f"全缺）——真样本节奏是每章 1-2 页强视觉，建议给其中 1 页升级 chart/layout/hero"})
    return issues
