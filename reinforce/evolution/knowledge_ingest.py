"""知识库摄入 —— 分析框架库/行业知识库的客户回灌飞轮摄入管线（D5/D5.1 决策落地）。

两条摄入路径分工不同：
- **框架候选**：从 issue_tree/storyline 结构指纹里找跨客户复用的结构（纯代码可判·不碰内容语义），
  ≥2 份撞到才进候选池（复用 evolution.converge 证据门槛），候选池仍需人/LLM 二次抽象命名才能变成
  exemplars/分析框架库.json 里的正式卡片——本模块只产候选，不自动写正式库（承重墙·铁律7）。
- **事实候选**：从 review.extract_numeric_facts 摘出的 dim/data 起步，强制脱敏（domain 由调用方
  显式传入已泛化的类目；claim 原句不进候选池，只留数字），强制打时效性提醒戳。
- **结构性文案候选（D20 FR3.2）**：从 deck 工作区 storyline.json 的结构件行（转场/章小结/决策/目录）
  提取结构性文案句，按行类型映射六槽位（COPY_SLOTS），排进第三池 `_文案候选池.json`——人审加工成
  槽位卡（含 slot/formula/demo/anti_pattern）后 promote 进 exemplars/表达手法卡.json。语料随使用
  自我生长（第三轮实测拍板的产品方向：真提案文案语料全网不存在现成库，只能自己攒）。

品牌库分流（D5.1·2026-07-01 用户拍板）：事实按 **brand（品牌/客户方）建库**，不再把品牌身份泛化
掉——收集到的事实先落各品牌自己的库(`_品牌知识库.json`)，公开/隐私两条口径分流：
- **公开数据**（有可独立核查的第三方信源，如 Ipsos/巨量算数/BEA/官方报告）：默认可被同步进
  跨客户共享池 `_行业知识库.json`，供其他客户的 deck 检索引用。
- **隐私数据**（客户自己内部数据/deck 内未标信源）：默认只收集、不外放——留在该品牌自己的库里，
  除非该品牌方明确同意分享（`sharing_override=True`，产品层未来的开关，本模块只留接口不做 UI）。

隐私口径（D3/D3.1/D5/D5.1·2026-07-01 用户拍板）：不做逐条 opt-out，配置阶段一次性向客户说清楚会
被用于知识库沉淀；脱敏/公私分流是产品质量/避免误摄入具体客户机密的技术兜底，跟"要不要问客户同意"
是两件事——本模块只管后者，不代替法务/同意流程。

原始素材备份（2026-07-01 用户拍板）：候选池/共享知识库刻意脱敏（claim 原句不进候选/框架只留结构
指纹）是正确的隐私设计，不推翻；但用户要求"蒸馏进知识库之外，尽量保留原始素材留作备用"——
`archive_raw_fact_context`/`archive_raw_framework_source` 额外把脱敏时丢掉的完整原始内容存进
两份独立的归档文件，按品牌/指纹隔离、不参与检索、不经 `sync_public_facts_to_shared_pool` 外流，
纯粹是"以后想回头看原始上下文"的内部备份，不是新增一份对外资产。
"""

from __future__ import annotations

import json
import os
import re
from collections import defaultdict
from pathlib import Path

from reinforce.evolution._locked_io import atomic_write_json, locked
from reinforce.review import extract_numeric_facts

ROOT = Path(os.environ.get("PPT_DIR", str(Path(__file__).resolve().parent.parent.parent)))
FRAMEWORK_POOL = ROOT / "reinforce" / "evolution" / "_框架候选池.json"
FACT_POOL = ROOT / "reinforce" / "evolution" / "_知识候选池.json"
COPY_POOL = ROOT / "reinforce" / "evolution" / "_文案候选池.json"  # D20 FR3.2·结构性文案候选（gitignore 同款运行期产物）
FEEDBACK_POOL = ROOT / "reinforce" / "evolution" / "_反馈池.json"  # D24·用户对话反馈/想法（收集范围第5条·gitignore 同款）
FRAMEWORK_LIB = ROOT / "exemplars" / "分析框架库.json"
FACT_LIB = ROOT / "research_lib" / "真实样本" / "_行业知识库.json"
COPY_LIB = ROOT / "exemplars" / "表达手法卡.json"  # D20 FR3.2·copy 池 promote 目标=槽位卡并入表达手法卡库
BRAND_LIB = ROOT / "research_lib" / "真实样本" / "_品牌知识库.json"
RAW_FACT_ARCHIVE = ROOT / "reinforce" / "evolution" / "_事实原始归档.json"
RAW_FRAMEWORK_ARCHIVE = ROOT / "reinforce" / "evolution" / "_框架原始归档.json"

MIN_SUPPORT = 2  # 复用 evolution.py 证据门槛：单份不采纳（防单客户偏样本污染）
MAX_DOMAIN_LEN = 20  # domain 短语长度上限，超过大概率是塞了句子/具体名而非类目标签

# 白名单制：默认 private，只有命中已知的"确有可查证第三方信源"特征才判 public。
# ⚠️ 2026-07-01 用 61 条真实抽取事实回测过两轮：
#   v1 黑名单制(不命中负面词就默认public) → 误判率超过一半，改白名单制默认 private。
#   v2 白名单里原本裸用"《"当信号 → 又把"《京东家电#你拍广告我给钱结案》"这种内部campaign结案
#      文档误判成public(结案报告≠独立第三方报告，书名号格式不能代表信源独立性)。改成要求书名号内
#      同时出现"报告/白皮书/研究"这类真报告特征词，"结案/效果统计"这类内部文档词不够格。
# 这份清单不追求穷尽，未来遇到新的真实第三方信源模式再补，漏判(该public判private)只是少放不是
# 安全问题；调用方也可用 visibility 参数显式覆盖，见 desensitize_fact。
_PUBLIC_SIGNAL_MARKERS = (
    "Ipsos", "巨量算数", "Nielsen", "尼尔森", "Bureau of", "National Transit Database",
    "NTD", "BLS", "BEA", "Tribune", "Herald", "Database", "统计局", "研究院",
    "Rapid Transit", "Metro", "Open Data", "Pitch Deck", "Sequoia", ".gov",
    # D28：".com" 已移除——"客户内部BI后台 admin.mostbrand.com 导出"被判 public 是
    # private→public 方向性误判（隐私外流），与本清单"漏判只是少放不是安全问题"的
    # 设计自述相悖。.gov 保留（政府域名可信）；真公开的 .com 信源降 private 只是少放，
    # 人审 promote 时可显式改判（宁私勿公）。
)
_REPORT_TITLE_KEYWORDS = ("报告", "白皮书", "研究")  # 书名号内须命中其一，才算真报告而非内部文档


def _has_real_report_title(text: str) -> bool:
    """粗略检测"《...》"里是否像一份真报告(含报告/白皮书/研究)，排除"结案/效果统计"这类内部文档。"""
    for seg in re.findall(r"《([^》]*)》", text):
        if any(k in seg for k in _REPORT_TITLE_KEYWORDS):
            return True
    return False


# 平台自身聚合数据（DAU/生态规模/产品报告）默认公开——平台本来就靠广泛分发这类数据拉新客户，
# 不是某个具体客户的私有效果数据。⚠️ 用真实数据回测发现：这条规则必须绑定"fact 的 brand 本身
# 就是平台"，不能只看"这条事实出现在哪份销售deck里"——同一份抖音销售deck里混了两种事实：
# ①抖音自己的DAU/生态规模(brand=抖音·平台数据·该公开) ②京东家电/宝马某次具体campaign的
# 效果数据(brand=京东家电/宝马·广告主的私有campaign数据·哪怕被平台当案例展示也不该公开)。
# 调用方必须把 brand 精确标成"这条事实描述的是谁"，不是"从哪份deck抽出来的"，本清单才有意义。
_PLATFORM_BRANDS = {"抖音", "巨量算数", "巨量引擎", "懂球帝", "小红书", "微信", "微博", "B站", "快手"}


def classify_visibility(source_citation: str, brand: str = "") -> str:
    """brand 命中平台白名单 → 直接判 "public"（平台自身聚合数据·默认公开分发）。
    否则 source_citation 命中已知第三方信源特征、或书名号里像份真报告 → "public"；
    都不命中 → 默认 "private"（宁可少放不多放）。
    """
    if brand in _PLATFORM_BRANDS:
        return "public"
    if not source_citation:
        return "private"
    if any(m in source_citation for m in _PUBLIC_SIGNAL_MARKERS):
        return "public"
    return "public" if _has_real_report_title(source_citation) else "private"


# ---------- 框架候选：issue_tree 结构指纹 ----------

def fingerprint_issue_tree(tree: dict) -> str:
    """议题树结构指纹——只取形状(mode/分支数/信心分布)，不碰 claim/test 具体文字内容(防泄露客户内容)。"""
    branches = tree.get("branches", [])
    # 批③🟢：confidence 显式 None（分支未评级的合法形态）时 .get(k, 默认) 不兜底——or 才兜住，按"中"处理
    conf_pattern = "".join(sorted((b.get("confidence") or "中")[:1] for b in branches))
    return f"{tree.get('mode', '?')}|n={len(branches)}|conf={conf_pattern}"


def framework_candidates(trees: list[dict], *, min_support: int = MIN_SUPPORT) -> list[dict]:
    """跨 deck 撞到同一结构指纹 → 候选（≥min_support 份独立撞到才收）。**批量/内存版**——
    trees 要一次性备齐才能跑，适合已经攒了一批 tree 在手上的场景（如离线批量回填）。

    只产"这个结构反复出现"的信号，不产框架名/mechanism/pick_when 这类需要抽象归纳的字段——
    那一步机器判不准，必须走 LLM/人工二次加工后再 promote() 落正式库（同 evolution.converge）。

    ⚠️ 这版按"第几份"计支持度，不按"哪个客户"——如果传入的多份 tree 其实来自同一个客户
    （比如同一品牌反复做类似分析），会被误算成多份"独立"撞到，违背 MIN_SUPPORT"防单客户偏样本
    污染"的原始用意。批量场景下由调用方自行保证传入的 trees 已经是跨客户去重过的；真正跨会话、
    跨真实客户场景请用下面 `record_issue_tree_fingerprint`/`due_framework_candidates`（按品牌去重）。
    """
    grouped: dict[str, list[int]] = defaultdict(list)
    for i, tree in enumerate(trees):
        grouped[fingerprint_issue_tree(tree)].append(i)
    return [{"fingerprint": fp, "support": len(idxs), "deck_indexes": idxs}
            for fp, idxs in grouped.items() if len(idxs) >= min_support]


# ---------- 跨客户结构复用侦测（持久化版·2026-07-01 补）----------
# 问题：framework_candidates() 是纯内存函数，真实客户项目一个一个隔会话/隔时间发生，没有地方
# 攒历史指纹——这里补一个真计数器（同 evolution.py 的 decks_since 计数器是同一类缺口/同一种补法）。

FRAMEWORK_FINGERPRINT_POOL = ROOT / "reinforce" / "evolution" / "_框架指纹池.json"


def record_issue_tree_fingerprint(tree: dict, brand: str, *, path: str | Path | None = None) -> dict:
    """真实客户项目阶段2假设树定稿后调用一次：把结构指纹计入跨客户复用侦测池（只存指纹+品牌名，
    不存 claim/test 具体内容，同 fingerprint_issue_tree 的隐私克制——两个完全不同客户的 deck 若
    问题分解形状一样，才是这个函数要抓的信号）。

    同一品牌多次撞到同一指纹只算 1 次独立支持（防单客户偏样本污染，MIN_SUPPORT 门槛的原始用意——
    framework_candidates() 批量版没做这层去重，这个持久化版补上）。
    """
    if not brand:
        raise ValueError("record_issue_tree_fingerprint 不能匿名——需要 brand 才能判断'独立'撞到")
    fp = fingerprint_issue_tree(tree)
    p = path or FRAMEWORK_FINGERPRINT_POOL
    # 2026-07-02 saopan扫盘揪出：本模块 8 个落盘函数全是裸 read-modify-write（同 evolution.py
    # 计数器实测 98% 丢失率的同款病根）——统一 locked() 包临界区，下同不逐处重复注释。
    with locked(p):
        data = _load_json(p, {"fingerprints": {}})
        entry = data["fingerprints"].setdefault(fp, {"brands": []})
        if brand not in entry["brands"]:
            entry["brands"].append(brand)
        _save_json(p, data)
    return {"fingerprint": fp, "distinct_brands": len(entry["brands"])}


def due_framework_candidates(*, min_support: int = MIN_SUPPORT, path: str | Path | None = None) -> list[dict]:
    """扫指纹池，找出已被 ≥min_support 个『不同』品牌独立撞到的结构——候选清单，不自动入库。
    命中的候选接下来查 `_框架原始归档.json`（`archive_raw_framework_source` 存的完整原始树）
    回看真实内容，供人二次抽象命名成正式框架卡后 `promote(pool="framework", ...)`。
    """
    p = path or FRAMEWORK_FINGERPRINT_POOL
    data = _load_json(p, {"fingerprints": {}})
    return [{"fingerprint": fp, "support": len(entry["brands"]), "brands": entry["brands"]}
            for fp, entry in data.get("fingerprints", {}).items() if len(entry["brands"]) >= min_support]


# ---------- 事实候选：storyline 数字证据脱敏 ----------

def desensitize_fact(dim: str, entries: list[dict], domain: list[str], brand: str,
                      *, source_hint: str = "客户输入·未标注独立信源",
                      visibility: str | None = None) -> dict:
    """把 extract_numeric_facts() 摘出的一组 (n/data/claim) 转成待审事实候选。

    脱敏责任划分：domain 必须由调用方显式传入已泛化的类目标签(如["精酿啤酒行业"])——这管的是
    "事实归到哪个行业类目"，不影响 brand 字段（brand 就是品牌/客户方本名，D5.1 起不再抹掉，
    因为事实要按品牌建库）。候选池只留数字(n/data)，claim 原句不进候选（客户具体表述不原样摄入）。
    visibility 未显式传入时按 classify_visibility(source_hint, brand) 自动判——brand 命中平台
    白名单(抖音/巨量算数等)默认 public，否则无独立第三方信源默认判 private（宁可少放，不多放）。
    """
    if not domain:
        raise ValueError("domain 不能为空——脱敏事实必须显式标类目，不接受未分类内容")
    if any(len(d) > MAX_DOMAIN_LEN for d in domain):
        raise ValueError(f"domain 单项超过 {MAX_DOMAIN_LEN} 字·疑似塞了长句/具体客户名，需先泛化成类目短语")
    if not brand:
        raise ValueError("brand 不能为空——事实必须归到具体品牌库，不接受匿名事实")
    points = [{"n": e["n"], "data": e["data"]} for e in entries]
    # D25 扫盘🔴：候选自带内容稳定 id——此前标准链 desensitize→file_to_brand_library→sync 全程
    # 无 id，而 sync 的幂等去重只按 id，无 id 的 public 事实每跑一次 sync 就往共享库重复追加一遍。
    # id=内容 hash（brand+dim+数据点），同一事实重新提取得到同一 id，sync 幂等从根上成立。
    import hashlib
    _sig = hashlib.sha256(
        json.dumps({"brand": brand, "dim": dim, "points": points},
                   ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:12]
    return {
        "id": f"fact_{_sig}",
        "dim": dim,
        "domain": list(domain),
        "brand": brand,
        "visibility": visibility or classify_visibility(source_hint, brand),
        "raw_points": points,
        "source_citation": source_hint,
        "timeliness": "客户产出回灌候选·未核实具体年份来源，人审 promote 前必须补全或明确标注不确定",
        "support": len(entries),
    }


# D28 提取噪音过滤：deck 版式元数据不是客户知识——第七轮某品牌单 38 条候选混入 10 条
# （期号/目录编号/X轴标签/卡片编号/章节标注），26% 噪音率拖垮人审。dim 命中即跳过。
_LAYOUT_META_DIM_RE = re.compile(
    r"期号|编号|标注|标签|轴|卡片|口径|目录|章节|页码|序号|version|period")


def fact_candidates_from_storyline(storyline: dict, domain: list[str], brand: str,
                                    *, source_hint: str = "客户输入·未标注独立信源") -> list[dict]:
    """storyline → 逐条数字 evidence → 按品牌打好标的脱敏候选列表。

    2026-07-02 D18 回灌首跑（某品牌 补跑·FR6.2）揪出两处口径错配：
    ① 旧版复用 extract_numeric_facts——那是"跨页事实一致性人审"口径（只留出现 ≥2 次的维度，
      单次出现没有'跨页'可言），但真实 storyline 的 evidence 维度几乎都只出现一次 →
      42 条真实证据提取出 0 候选。回灌要的是"每条带数字的证据都值得进候选池"，改逐条提取
      （同 dim 多条仍聚合·support 如实计数）。
    ② 旧版把统一 source_hint 传给全部候选——evidence 自带真实 source（虎嗅/36氪/报告大厅 vs
      brief PX）时，公开报道也会被 classify_visibility 按"无独立信源"误判 private。现在优先
      用 evidence 自己的 source 参与公私分流，没有才落回 source_hint（宁可少放的兜底不变）。
    """
    by_dim: dict[str, list] = defaultdict(list)
    src_by_dim: dict[str, str] = {}
    for ln in storyline.get("lines") or []:
        for e in ln.get("evidence") or []:
            dim, data = e.get("dim"), e.get("data")
            if dim and _LAYOUT_META_DIM_RE.search(str(dim)):
                continue  # D28 版式元数据不是客户知识（期号/编号/轴标签…）·26% 噪音率的解
            if not dim or not re.search(r"\d", str(data or "")):
                continue  # 无维度名/无数字的证据不成事实候选（回灌只收数字事实·同 desensitize 口径）
            by_dim[dim].append({"n": ln.get("n"), "data": data})
            src_by_dim.setdefault(dim, str(e.get("source") or e.get("source_citation") or source_hint))
    return [desensitize_fact(dim, entries, domain, brand, source_hint=src_by_dim[dim])
            for dim, entries in by_dim.items()]


# ---------- 结构性文案候选（D20 FR3.2）：storyline 结构件文案 → 槽位语料飞轮 ----------

# 六槽位枚举（同 exemplars/表达手法卡.json 槽位卡的 slot 字段口径·FR1.2）
COPY_SLOTS = ("目录命名", "章间桥", "章小结", "诊断收束", "ask收尾", "落幕")


def copy_candidates_from_deck(deck_dir: str | Path, *, source_hint: str = "") -> list[dict]:
    """从一个 deck 工作区提取「结构性文案」候选——第三轮实测（某品牌）确诊说明书感 12 页命中
    全部集中在结构性文案槽位（目录/转场/章小结/决策 ask），而真提案文案语料全网不存在现成库
    （github 全是模板骗星），用户拍板的产品方向是**语料随使用自我生长**：每单收尾把本单结构件
    文案排进候选池，人审加工成槽位卡后 promote 进表达手法卡库（好句成卡范式/坏句进 anti_pattern
    禁形态对照）。

    扫 <deck_dir>/storyline.json 四类行，按行类型映射槽位（六槽位见 COPY_SLOTS）：
    - 转场行（page_type="转场"）：claim 与 bridge_from 非空各出一条 → slot="章间桥"；
    - 章小结行（role="章小结" 或 page_function 含"小结"·同 deck_rules 的 check_part_structure
      判定口径，别只认一个字段）：claim → slot="章小结"；
    - 决策行（page_type="决策"）：claim → slot="ask收尾"；
    - 目录行（page_type="目录"）：toc_items 逐项 → slot="目录命名"。
    「诊断收束/落幕」两槽位没有确定性的行类型可映射（诊断长在普通数据论断行里、落幕页型不固定），
    不从这条管线自动提取——人审时从 deck 里手挑，不硬造映射。

    kind 一律 "good_candidate"：回灌跑在 handoff/publish 成功之后，句子来自人审通过的 deck——
    但"好"的最终判定仍在人审 promote（候选 ≠ 范式）。**坏句侧（文案门拦截记录+人审否决的文案）
    本期不在此函数**：拦截记录现状不落盘——outline.json 只存页 status 不存 gate 明细，strict 模式
    拦截即中断返工、改完重跑后拦截痕迹随之消失——等文案门留痕机制落地后再扩坏句提取，
    这里不硬造数据源（宁缺毋假）。

    source_hint 非空时写进每条候选（如 "某品牌 40页 IMC·已publish"·供人审辨来源）。
    storyline.json 不存在 → 拒（回灌跑在策略定稿落盘之后，找不到=传错目录）；损坏 → _load_json
    fail-closed 抛错，同全模块纪律。
    """
    sp = Path(deck_dir) / "storyline.json"
    if not sp.is_file():
        raise ValueError(f"copy_candidates_from_deck 找不到 {sp}——deck 工作区必须已有策略定稿落盘"
                         f"（save_storyline），确认 deck_dir 传的是 data/decks/<deck_id> 一级目录")
    sl = _load_json(sp, {})
    if "lines" not in sl:
        # 批④补可见警告：storyline.json 在但没有 lines 键（落盘形态异常/字段名不对）——
        # 此前静默返回 []，跟"真提取了 0 条"分不清。返回形态是 list（多调用方按候选清单消费），
        # 不动契约，print 一条可见信号（同 backup/scaffold 的播报口径）。
        print(f"⚠️ copy_candidates_from_deck：{sp} 缺 'lines' 键（storyline 尚未写行或落盘形态异常）"
              f"——提取 0 条候选；确认 deck_dir 指向策略定稿（save_storyline）后的工作区")
    deck_id = Path(deck_dir).name

    def _cand(text: str, slot: str, n) -> dict:
        c = {"text": text, "slot": slot, "deck": deck_id, "n": n, "kind": "good_candidate"}
        if source_hint:
            c["source_hint"] = source_hint
        return c

    out: list[dict] = []
    for ln in sl.get("lines") or []:
        n = ln.get("n")
        page_type = str(ln.get("page_type") or "")
        claim = str(ln.get("claim") or "").strip()
        if page_type == "转场":
            bridge = str(ln.get("bridge_from") or "").strip()
            if claim:
                out.append(_cand(claim, "章间桥", n))
            if bridge:  # 首个 Part 的转场豁免 bridge_from（D18 FR2）——空就是没有，不算漏
                out.append(_cand(bridge, "章间桥", n))
        if ln.get("role") == "章小结" or "小结" in str(ln.get("page_function") or ""):
            if claim:
                out.append(_cand(claim, "章小结", n))
        if page_type == "决策" and claim:
            out.append(_cand(claim, "ask收尾", n))
        if page_type == "目录":
            for item in ln.get("toc_items") or []:
                item = str(item).strip()
                if item:
                    out.append(_cand(item, "目录命名", n))
    return out


# ---------- 候选池落盘 + 人审 promote ----------

def _load_json(path: str | Path, default: dict) -> dict:
    """2026-07-01 saopan扫盘揪出：本模块公开函数的路径参数标注是 Path|None，跟姊妹模块
    evolution.py/methodology.py 统一用的 str|Path|None 不一致——传字符串路径会在这里
    AttributeError('str' object has no attribute 'is_file')。这里补 Path() 归一化，
    是本文件所有落盘函数共同的入口，修一处即覆盖全部 10 个调用点。

    2026-07-02 saopan扫盘揪出：此前「存在但解析失败」也被吞成 default（fail-open）——本模块
    落盘的是品牌知识库/审计日志(audit_log)/候选池/原始归档这类账本数据，坏一次读、下一次写就
    以 default 重建 = 静默清空（audit_log 被清 = 操作留痕机制名存实亡）。改成同 deck_memory /
    methodology 的纪律：文件不存在才是正常初始态，损坏必 raise（fail-closed）。"""
    path = Path(path)
    if not path.is_file():
        return dict(default)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as e:
        raise ValueError(f"知识库落盘文件损坏·拒按空默认处理（fail-closed·含audit_log等留痕数据）："
                         f"{path} — {e}") from e
    # 批④补：语法坏兜住了，**类型**坏还是 fail-open——顶层被手改成列表/字符串，下游
    # data["fingerprints"]/data.setdefault(...) 要么 TypeError 要么静默按空重建（同
    # deck_memory._load_ledger 2026-07-02 补的"delivered 类型坏必 raise"一条纪律）。
    if not isinstance(data, dict):
        raise ValueError(f"知识库落盘文件顶层不是对象（JSON object）·拒按空默认处理"
                         f"（fail-closed·同 deck_memory 口径）：{path}")
    return data


def _save_json(path: str | Path, data: dict) -> None:
    """2026-07-02 saopan扫盘揪出：此前普通 write_text 非原子——进程半途死掉留半截 JSON，
    正好喂给上面 fail-closed 读变成台账锁死。改 temp+rename 原子写（同 deck_memory._atomic_write）。
    set_sharing_override 等所有落盘路径都走这里，修一处覆盖全部。"""
    atomic_write_json(data, Path(path))


_POOL_FILES = {"framework": FRAMEWORK_POOL, "fact": FACT_POOL, "copy": COPY_POOL,
               "feedback": FEEDBACK_POOL}


def queue_candidates(candidates: list[dict], *, pool: str, path: str | Path | None = None) -> dict:
    """候选写入待审池(不动正式库)。pool='framework'|'fact'|'copy'|'feedback' 选目标池文件
    （copy=结构性文案候选池 `_文案候选池.json`·D20 FR3.2；feedback=用户反馈池·D24 收集范围
    第5条——同前几池一样是 gitignore 内的运行期产物，人审 promote 前不会被任何检索读到）。
    ⚠️ feedback 没有 promote 入库路径（_POOL_LIBS 故意不含它）：反馈的"内化"=转需求种子/工作
    偏好/实录素材，是人审+会话的动作不是库 append——池只负责"用户说的话一句不丢"。"""
    if pool not in _POOL_FILES:
        raise ValueError("pool 必须是 'framework'、'fact'、'copy' 或 'feedback'")
    p = path or _POOL_FILES[pool]
    with locked(p):
        data = _load_json(p, {"pending": []})
        pending = data.setdefault("pending", [])
        # D25 扫盘🟡：入池去重（按内容签名）——收尾工序"每单必跑"遇断点重来/重复执行，
        # 同一批候选曾整批翻倍（对比：指纹池按 brand 去重、sync 按 id 去重，唯独四池入口裸奔）。
        # 签名=整条候选的规范化 JSON（无 id 的候选也能去重）；跨批次重复同样拦（池内已有即跳过）。
        def _sig(c: dict) -> str:
            return json.dumps(c, ensure_ascii=False, sort_keys=True)
        seen = {_sig(c) for c in pending}
        added = 0
        for c in candidates:
            s = _sig(c)
            if s in seen:
                continue
            pending.append(c)
            seen.add(s)
            added += 1
        _save_json(p, data)
    return {"pool": pool, "queued": added, "skipped_dup": len(candidates) - added,
            "total_pending": len(data["pending"])}


def queue_feedback(quote: str, *, context: str = "", deck_id: str = "", category: str = "反馈",
                   date: str = "", path: str | Path | None = None) -> dict:
    """用户反馈/想法一句入池（D24 收集范围第5条·飞轮宪法 specs/进化飞轮收集范围.md）。

    quote=用户**逐字原话**（必填·fail-closed 空拒——转述不是留痕，同 record_user_ack 一条纪律）；
    context=什么场景说的（哪一轮实测/讨论什么时）；category ∈ 建议值{反馈, 需求种子, 偏好, 表扬, 纠偏}
    （自由串·不闸）；date 由调用会话显式传（引擎核心不碰系统时钟·同 run_storyline_gate 的
    current_year 一条纪律）。

    为什么值得单独一个函数：第六轮确诊"用户在实测会话说的金子级反馈（'只诊断不解决'）没有任何
    回传通道，全靠人肉搬运到开发会话"——收集范围第5条的缺口实例。会话在对话中听到反馈/想法/
    纠偏，随手调这个，一句不丢。
    """
    if not quote or not quote.strip():
        raise ValueError("queue_feedback 拒收空 quote——必须是用户逐字原话，转述/概括不算（D24 第5条）")
    entry = {"quote": quote, "context": context, "deck_id": deck_id,
             "category": category, "date": date}
    return queue_candidates([entry], pool="feedback", path=path)


_POOL_LIBS = {"framework": FRAMEWORK_LIB, "fact": FACT_LIB, "copy": COPY_LIB}
_POOL_LIB_KEYS = {"framework": "cards", "fact": "facts", "copy": "cards"}


def promote(card: dict, *, pool: str, reviewer: str, lib_path: str | Path | None = None) -> dict:
    """人审拍板：把一条(已由人/LLM二次加工补全字段的)候选正式写入
    exemplars/分析框架库.json、research_lib/真实样本/_行业知识库.json
    或 exemplars/表达手法卡.json（pool="copy"·D20 FR3.2）。
    承重墙：reviewer 必填（人审拍板才落地·铁律7·同 methodology.accumulate）。

    pool="copy" 的额外契约：目标库=表达手法卡库，要求卡**已加工成表达卡 schema**——
    slot ∈ COPY_SLOTS 六槽位，且 formula（句式公式）/demo（真实 demo 带出处）非空（FR1.2 卡三要素
    的前两件·加工过的确定性证据）。⚠️ 只查 slot 拦不住裸句：copy_candidates_from_deck 产的候选
    本身就带 slot（端到端真跑揪出的假门），裸句与成卡的确定性分界是 formula/demo——候选只有
    text，没有句式抽象。第三要素 anti_pattern（禁形态对照）应有，但坏句侧语料本期不全，不硬卡，
    齐不齐是人审责任（同 framework 池"候选→正式卡要二次抽象"一个道理）。
    ⚠️ 留痕提醒：exemplars/ 卡库在 git 钩子监控内（L7 铁律），promote 后必须另行
    `evolution.versioning.record_library_change(库路径, description, reviewer)` 留痕，否则
    pre-commit 拒提交——本函数不代跑（promote 与版本留痕是两个人工动作，framework 池同此现状）。
    """
    if pool not in _POOL_LIBS:
        raise ValueError("pool 必须是 'framework'、'fact' 或 'copy'")
    if not reviewer or not reviewer.strip():
        raise ValueError("promote 必须带 reviewer（人审拍板才落地·铁律7）")
    if pool == "copy":
        if card.get("slot") not in COPY_SLOTS:
            raise ValueError(f"copy 池 promote 要求 slot ∈ {COPY_SLOTS}（表达卡 schema·D20 FR3.2）")
        if not str(card.get("formula") or "").strip() or not str(card.get("demo") or "").strip():
            raise ValueError("copy 池 promote 要求卡已加工成槽位卡：formula（句式公式）与 demo"
                             "（真实 demo 带出处）都不能空——候选池的裸句(text)不能直接入库，"
                             "先按 FR1.2 三要素（句式公式+真实demo+禁形态）加工再来（D20 FR3.2）")
    if pool == "fact" and card.get("visibility") not in (None, "public"):
        # D25 扫盘🟡：行业知识库=跨客户共享池——private 事实从这条热路径直写共享库等于隐私外流，
        # "隐私默认不放出"此前只硬编码在 visible_facts_for_brand/sync 链上，promote 直路没门。
        # visibility=None 的历史/手工卡放行（老口径卡无此字段·由人审负责），显式 private/其他值拒。
        raise ValueError(
            f"fact 池 promote 拒收 visibility={card.get('visibility')!r}——行业知识库是跨客户"
            f"共享池，非 public 事实该走 file_to_brand_library 进品牌库（隐私默认不外放·D5.1/D25）")
    lp = lib_path or _POOL_LIBS[pool]
    key = _POOL_LIB_KEYS[pool]
    with locked(lp):
        lib = _load_json(lp, {key: []})
        lib.setdefault(key, []).append({**card, "reviewer": reviewer})
        _save_json(lp, lib)
    return {"pool": pool, "promoted_id": card.get("id"), "reviewer": reviewer}


# ---------- 品牌库（D5.1）：事实按品牌分流·公开可放行/隐私默认扣住 ----------

def file_to_brand_library(fact: dict, *, reviewer: str, brand_lib_path: str | Path | None = None) -> dict:
    """把一条已审事实(须含 brand+visibility)归档进品牌库——公开/隐私都进，只是后续能不能被
    其他客户检索到取决于 visibility(见 visible_facts_for_brand)。承重墙：reviewer 必填。
    """
    if not reviewer or not reviewer.strip():
        raise ValueError("file_to_brand_library 必须带 reviewer（人审拍板才落地·铁律7）")
    brand = fact.get("brand")
    if not brand:
        raise ValueError("fact 缺 brand 字段——不能归档匿名事实")
    if fact.get("visibility") not in ("public", "private"):
        raise ValueError("fact.visibility 必须是 'public' 或 'private'")
    p = brand_lib_path or BRAND_LIB
    with locked(p):
        lib = _load_json(p, {"brands": {}})
        # D27b 防键名分裂：'某品牌'/'Goose Island'/'某品牌(Goose Island)'曾分裂成三个互不可见的库
        # （检索按键隔离）——新键与既有键互为子串时可见警告，提醒对齐既有键名（不拦：改名是人审动作）
        _similar = [k for k in lib.get("brands", {})
                    if k != brand and (k in brand or brand in k)]
        if _similar:
            print(f"⚠️ 品牌键疑似分裂：新键 {brand!r} 与既有 {_similar} 相似——同一品牌请用同一键名"
                  f"（检索按键隔离·分裂即互不可见·D27b 某品牌三键教训）")
        lib.setdefault("brands", {}).setdefault(brand, {"facts": []})
        lib["brands"][brand]["facts"].append({**fact, "reviewer": reviewer})
        _save_json(p, lib)
    return {"brand": brand, "visibility": fact["visibility"], "reviewer": reviewer}


def visible_facts_for_brand(brand: str, *, brand_lib_path: str | Path | None = None) -> list[dict]:
    """给客户端"能不能把这条事实给客户看"用：只返回该品牌下 visibility=public 或
    sharing_override=True 的事实——private 且未被品牌方明确 override 的事实永不从这里返回
    （"隐私数据默认只收集不放出"，硬编码在这个函数里，不是配置项）。
    """
    p = brand_lib_path or BRAND_LIB
    lib = _load_json(p, {"brands": {}})
    facts = lib.get("brands", {}).get(brand, {}).get("facts", [])
    return [f for f in facts if f.get("visibility") == "public" or f.get("sharing_override") is True]


def set_sharing_override(brand: str, fact_id: str, value: bool, *, actor: str, reason: str,
                          brand_lib_path: str | Path | None = None) -> dict:
    """品牌方主动开放/收回某条私有事实的对外可见性——**必须带操作留痕，不能是裸改 JSON 字段**
    （D5.1 待办：谁、为什么把某条 private 事实标成了可分享，此前完全没有审计机制）。
    actor(谁做的)/reason(为什么) 必填，写入该品牌库的 audit_log 数组，可追溯不可静默改。
    不内置时间戳（保持函数纯/可测），需要时间线索的场景由调用方在 reason 里自带或外部系统记录。
    """
    if not actor or not actor.strip():
        raise ValueError("set_sharing_override 必须带 actor（谁做的这个决定·操作留痕）")
    if not reason or not reason.strip():
        raise ValueError("set_sharing_override 必须带 reason（为什么·操作留痕）")
    p = brand_lib_path or BRAND_LIB
    with locked(p):
        lib = _load_json(p, {"brands": {}})
        brand_entry = lib.get("brands", {}).get(brand)
        if not brand_entry:
            raise ValueError(f"品牌库里没有 brand={brand}")
        fact = next((f for f in brand_entry["facts"] if f.get("id") == fact_id), None)
        if not fact:
            raise ValueError(f"品牌 {brand} 下没有 id={fact_id} 的事实")
        old_value = fact.get("sharing_override")
        fact["sharing_override"] = value
        lib.setdefault("audit_log", []).append({
            "brand": brand, "fact_id": fact_id, "old_value": old_value, "new_value": value,
            "actor": actor, "reason": reason,
        })
        _save_json(p, lib)
    return {"brand": brand, "fact_id": fact_id, "old_value": old_value, "new_value": value,
            "actor": actor, "reason": reason}


def archive_raw_fact_context(dim: str, entries: list[dict], brand: str,
                              *, archive_path: str | Path | None = None) -> dict:
    """把 desensitize_fact() 出于隐私脱敏而丢掉的 claim 原句+完整 entries，存进按品牌隔离的
    原始归档（2026-07-01 用户拍板：蒸馏进知识库之外，尽量保留原始素材留作备用）。

    跟事实候选池/共享知识库/品牌库是三份完全独立的文件——这份归档**不参与 search.py 检索、不经
    `sync_public_facts_to_shared_pool` 外流、`visible_facts_for_brand` 也读不到它**，纯粹是给
    未来人工回看"这条数字当初的完整上下文/原话是什么"用的内部备份，不是新增一份对外可见的资产。
    不做 public/private 分流判断——既然是内部备份，统一按品牌隔离私有存放，不需要那层复杂度。
    """
    if not brand:
        raise ValueError("brand 不能为空——原始归档必须归到具体品牌，不接受匿名归档")
    p = archive_path or RAW_FACT_ARCHIVE
    with locked(p):
        data = _load_json(p, {"brands": {}})
        data.setdefault("brands", {}).setdefault(brand, {"entries": []})
        data["brands"][brand]["entries"].append({"dim": dim, "raw_entries": entries})
        _save_json(p, data)
    return {"brand": brand, "dim": dim, "archived_count": len(entries)}


def archive_raw_framework_source(fingerprint: str, trees: list[dict],
                                  *, archive_path: str | Path | None = None) -> dict:
    """把 framework_candidates() 只留下结构指纹背后、撞出这个指纹的完整原始 issue_tree(s) 存进
    归档——供人工做"候选→正式框架卡"的二次抽象命名那一步时，能回看真实原始结构（claim/test 具体
    文字），不用只凭一个抽象指纹瞎猜"当初客户到底是怎么想的"。同 `archive_raw_fact_context` 一样
    不参与检索/不外流，纯内部备份。按 fingerprint 分组（不按品牌——同一结构可能是不同品牌各自
    独立撞到的，归档时不丢失"这是好几份独立案例"这个事实）。
    """
    if not fingerprint:
        raise ValueError("fingerprint 不能为空")
    p = archive_path or RAW_FRAMEWORK_ARCHIVE
    with locked(p):
        data = _load_json(p, {"fingerprints": {}})
        data.setdefault("fingerprints", {}).setdefault(fingerprint, {"trees": []})
        data["fingerprints"][fingerprint]["trees"].extend(trees)
        _save_json(p, data)
    return {"fingerprint": fingerprint, "archived_count": len(trees)}


def sync_public_facts_to_shared_pool(*, reviewer: str, brand_lib_path: str | Path | None = None,
                                      shared_lib_path: str | Path | None = None) -> dict:
    """把所有品牌库里"能给客户看"的事实(同 visible_facts_for_brand 口径)同步进跨客户共享池
    (exemplars/../_行业知识库.json)，供其他客户 deck 检索。私有数据永不经这条路径外流。
    承重墙：reviewer 必填；已同步过的事实(按 id)不重复写入。

    D25 扫盘🔴修复：无 id 条目**跳过并警告**，绝不写入——此前无 id 条目绕过按 id 去重，
    每跑一次 sync 就往承重墙共享库重复追加一遍（且是缺 fact 文本的残缺 schema）。正路：
    desensitize_fact 起候选就自带内容 hash id（同批修复），历史无 id 条目先补 id 再 sync。
    """
    if not reviewer or not reviewer.strip():
        raise ValueError("sync_public_facts_to_shared_pool 必须带 reviewer（人审拍板才落地·铁律7）")
    bp = brand_lib_path or BRAND_LIB
    sp = shared_lib_path or FACT_LIB
    brand_lib = _load_json(bp, {"brands": {}})  # 品牌库只读快照·锁的是写目标共享池
    with locked(sp):
        shared = _load_json(sp, {"facts": []})
        existing_ids = {f.get("id") for f in shared.get("facts", [])}
        synced = []
        skipped_no_id = []
        for brand, entry in brand_lib.get("brands", {}).items():
            for f in visible_facts_for_brand(brand, brand_lib_path=bp):
                if not f.get("id"):
                    skipped_no_id.append(f"{brand}/{f.get('dim') or '?'}")
                    continue  # 无 id 无幂等键·拒同步（fail-closed·防重复注入共享库）
                if f["id"] in existing_ids:
                    continue
                shared.setdefault("facts", []).append({**f, "reviewer": reviewer})
                existing_ids.add(f["id"])
                synced.append(f["id"])
        _save_json(sp, shared)
    if skipped_no_id:
        print(f"⚠️ sync 跳过 {len(skipped_no_id)} 条无 id 的 public 事实（无幂等键不敢写共享库）："
              f"{skipped_no_id[:5]}——先给品牌库条目补内容 id 再重跑")
    return {"synced_count": len(synced), "synced_ids": synced,
            "skipped_no_id": skipped_no_id, "reviewer": reviewer}
