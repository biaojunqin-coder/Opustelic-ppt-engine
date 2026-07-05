"""deck 工作目录 Workspace（④数据产物层）——「每份 deck 一套自洽产物」的家。

对应 Novel「单本书一个目录一套产物」（book.json/story_graph.json/numbers.json/manuscript/台账）。
此前状态文件散落：CFO demo 只落 storyline 在 examples/out/、Descente 只落 spec_lock 在
out_descente_v2/，没有一份 deck 有完整产物套装，data/state·data/memory 只有 .示例.json——
铁律 L3「数据是命根子」要的可落盘+可观测+可回滚，先得有个统一的「家」。

本模块只管「东西该放哪」（路径约定 + 建目录 + 交付收尾），schema 校验各归各模块
（deck_state/storyline_state/planning_team/spec_lock/asset_ledger）——纯路径层，不重写它们。

约定 data/decks/<deck_id>/：
  team_state.json    策略内部多角色交接（planning_team.save_team 的落盘点）
  storyline.json     策略定稿（storyline_state.save_storyline 的落盘点）
  handoff.json       策略→制作交接卡（handoff_to_production(path=...) 的落盘点）
  spec_lock.json     设计锁定（阶段1.5 定稿落盘）
  outline.json       制作大纲+页状态流转（活文件·build_deck 逐页回写 status·断点续做入口）
  asset_ledger.json  素材/证据溯源台账（asset_ledger.build_asset_ledger 自动汇集）
  handoff_card.json  制作中断续做交接卡（deck_memory.save_handoff 的落盘点）
  pages/             逐页 SVG/PNG（build_deck 的 out_dir 指到这）
  deck.pptx          成品
全局 data/decks/_published.json：已交付登记表（deck_memory 只读锁的真相源）。

幂等：new_workspace 只建目录、不覆盖任何已有文件（同 scaffold 纪律）。
fail-closed：deck_id 空/含路径分隔符或 ".." → 拒（防路径穿越把状态写到家外面）。

🔻 立此存照（D16 收窄·防反复）：Novel 的 numbers.json（进度指标曲线）/story_graph.json
（实体关系图谱）**不移植**——20 来页的 deck 用不上 360 章小说的追踪装置，页间依赖
outline.depends_on 已覆盖。再议触发条件：出现 50 页+多版本长期迭代的超长 deck 项目。
"""

from __future__ import annotations

from pathlib import Path

from reinforce.deck_memory import (file_sha256, is_published, load_checksums, load_published,
                                   mark_published, save_handoff)

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DECKS_ROOT = REPO_ROOT / "data" / "decks"
PUBLISHED_LEDGER_NAME = "_published.json"

# 产物名 → workspace 内相对路径（键即 workspace dict 的键·pipeline 等调用方按键取用）
ARTIFACTS = {
    "team_state": "team_state.json",
    "storyline": "storyline.json",
    "handoff": "handoff.json",
    "spec_lock": "spec_lock.json",
    "outline": "outline.json",
    "asset_ledger": "asset_ledger.json",
    "handoff_card": "handoff_card.json",
    "review": "review.json",   # 三道人审清单落盘点（reinforce.review.new_review 结构·D18 FR6.1 人审闸读它）
    "images": "images",  # 图像获取落点（acquire_image 的 out_dir·D18 FR7.4）
    "brand_assets": "brand_assets",  # D22b 品牌素材收集点（VI/logo/字体/历史deck·leader 开场提示用户投放·制作层 list_brand_assets 扫描消费）
    "pages": "pages",
    "pptx": "deck.pptx",
}

# 品牌素材收集点的引导说明（首次建家时落一份·已存在不覆盖——scaffold 幂等纪律）
_BRAND_ASSETS_README = """# 品牌素材收集点（有就放·没有也不影响做 deck）

把品牌相关素材直接丢进本文件夹（命名随意·子文件夹也行），制作层会自动扫描按品牌资产锚定视觉：

- **VI / 品牌手册**：PDF、PPT 都行 → 色板/字体规范按手册提取（视觉锚定最高优先级）
- **Logo / KV / 产品图 / 官网截图**：png、jpg、svg → 读图提取品牌主色+辅色
- **品牌字体文件**：ttf、otf、woff → 通过可嵌入性检查后锁进标题/正文字体
- **历史 deck**：pptx、pdf → 沿用既有视觉基因

没放素材时的兜底：联网查证品牌官方色（带来源出处）；再查不到用中性色板并如实标注。
"""


def _check_deck_id(deck_id: str) -> None:
    """deck_id 合法性（fail-closed）：拒空/纯空格/路径分隔符/'..'/纯点——它是目录名，穿越即写到家外。"""
    if not deck_id or not deck_id.strip():
        raise ValueError("deck_id 不能为空")
    if "/" in deck_id or "\\" in deck_id or ".." in deck_id:
        raise ValueError(f"deck_id 含路径分隔符或 '..'·拒（防路径穿越）：{deck_id!r}")
    # 2026-07-02 saopan扫盘揪出："." 不含上面任何子串却直指 decks 根目录——产物会跟全局
    # _published.json 混放，「一份 deck 一个家」布局破坏。纯点串一律拒。
    if set(deck_id.strip()) == {"."}:
        raise ValueError(f"deck_id 是纯点串·拒（'.' 会把产物写到 decks 根目录）：{deck_id!r}")


def workspace_dir(deck_id: str, root: str | Path | None = None) -> Path:
    """该 deck 的工作目录路径（不建目录·纯计算）。"""
    _check_deck_id(deck_id)
    return (Path(root) if root else DEFAULT_DECKS_ROOT) / deck_id


def published_ledger_path(root: str | Path | None = None) -> Path:
    """全局已交付登记表路径（所有 deck 共用一本账·deck_memory 只读锁的真相源）。"""
    return (Path(root) if root else DEFAULT_DECKS_ROOT) / PUBLISHED_LEDGER_NAME


def new_workspace(deck_id: str, root: str | Path | None = None) -> dict:
    """建（或幂等复用）deck 工作目录，返回全套产物路径映射。

    返回 dict：{deck_id, dir, published_ledger, team_state, storyline, handoff, spec_lock,
    outline, asset_ledger, handoff_card, pages, pptx}——值全是 Path（pptx/pages 等尚未生成
    也先给出约定位置）。pipeline.build_deck(workspace=...) 按键消费，不 import 本模块（依赖注入，
    同 svg_provider 一条纪律）。root 缺省 data/decks/（测试注入 tmp_path）。
    """
    _check_deck_id(deck_id)
    base = Path(root) if root else DEFAULT_DECKS_ROOT
    d = base / deck_id
    (d / "pages").mkdir(parents=True, exist_ok=True)  # 幂等·已有文件一概不动
    # D22b 品牌素材收集点：建目录+首次落引导说明（已存在不覆盖·用户改过的说明是用户的）
    ba = d / ARTIFACTS["brand_assets"]
    ba.mkdir(parents=True, exist_ok=True)
    readme = ba / "_放什么.md"
    if not readme.exists():
        readme.write_text(_BRAND_ASSETS_README, encoding="utf-8")
    ws: dict = {"deck_id": deck_id, "dir": d, "published_ledger": base / PUBLISHED_LEDGER_NAME}
    for key, rel in ARTIFACTS.items():
        ws[key] = d / rel
    return ws


# 品牌素材扫描的类型分组口径（发现素材是机械活·识别内容[读图提色/提取VI]是制作会话的智能活——分工同图像获取）
_BRAND_FONT_EXTS = {".ttf", ".otf", ".woff", ".woff2"}
_BRAND_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".svg", ".webp"}
_BRAND_DOC_EXTS = {".pdf", ".pptx", ".ppt", ".key"}


def list_brand_assets(ws: dict) -> dict:
    """扫品牌素材收集点 → {fonts, images, docs, others}（各为 Path 列表·递归含子目录·D22b）。

    只做"发现"不做"识别"：色板提取/VI 解读/字体登记是制作会话的智能活（读图识色、docling 提
    手册），本函数只负责把用户丢进来的东西按类型分好组。`_放什么.md` 引导说明不算素材。
    全空 dict 的判断口径：`any(list_brand_assets(ws).values())` 为 False = 没素材 → 品牌锚定
    走 web_verified 联网查证链（制作 SKILL 阶段 1.5）。
    """
    ba = ws.get("brand_assets")
    out: dict = {"fonts": [], "images": [], "docs": [], "others": []}
    if not ba or not Path(ba).is_dir():
        return out
    for f in sorted(Path(ba).rglob("*")):
        if not f.is_file() or f.name == "_放什么.md" or f.name.startswith("."):
            continue
        ext = f.suffix.lower()
        if ext in _BRAND_FONT_EXTS:
            out["fonts"].append(f)
        elif ext in _BRAND_IMAGE_EXTS:
            out["images"].append(f)
        elif ext in _BRAND_DOC_EXTS:
            out["docs"].append(f)
        else:
            out["others"].append(f)
    return out


def _check_review_complete(review_path: Path) -> None:
    """D18 FR6.1 人审完成度闸：三道人审清单没勾完 → 拒交付（fail-closed）。

    第一轮实测确诊：review_v1.json 视觉 9 项全 null、rate 0.0，deck 照样 publish 了——
    "呼吸页不堆卡片网格"这条清单项就躺在没人勾的 9 项里，恰是用户抱怨的病。
    边界（铁律2）：机器只拦"没做"（存在未评项/文件缺失），不代判"好坏"——全勾完但有
    不通过项（人明知有红项仍交付）是人的决策权，这里放行；判定"能不能交"的方法论标准
    （三道≥90%+Critic非Red）由 SKILL 工序指引人执行。
    """
    import json

    from reinforce.review import REVIEWS, score_review

    if not review_path.is_file():
        raise ValueError(
            f"三道人审清单未落盘（{review_path} 不存在）·拒交付——没做人审就 publish 是"
            f"第一轮实测确诊的闸洞（D18 FR6.1）；用 reinforce.review.new_review 建清单、"
            f"人工勾完落盘到 workspace['review'] 再交付；紧急场景 publish_deck(force=True) 留痕绕行")
    review = json.loads(review_path.read_text(encoding="utf-8"))
    score = score_review(review)
    unrated = {r: s["unrated"] for r, s in score.items()
               if isinstance(s, dict) and s.get("unrated")}
    # D25 扫盘🔴：完成度基准 = **现行 REVIEWS 清单**，不是"review 文件自己写了几项"——
    # 清单 D19/D20 真实长过两次，旧 schema 落盘文件的新项永远没人评过却 unrated=0 照样过闸；
    # 极端形态 {"action_title": {}, ...}（三角色空 dict·一项没勾）rate=0.0 也能 publish——
    # 正是 D18 要根治的"9 项全 null 照样交付"原病的复发路径。缺项=未评，同一条防假绿纪律。
    missing = {}
    for role, ref_items in REVIEWS.items():
        have = review.get(role) if isinstance(review.get(role), dict) else {}
        lack = [i for i in ref_items if i not in have]
        if lack:
            missing[role] = lack
    if unrated or missing:
        detail = []
        if unrated:
            detail.append(f"未评项 {unrated}")
        if missing:
            detail.append(f"缺现行清单项 {{{ '; '.join(f'{r}: {len(v)}项' for r, v in missing.items()) }}}"
                          f"（review 文件早于清单扩容·用 new_review() 重建补评）")
        raise ValueError(
            f"三道人审清单不完整·拒交付（{'；'.join(detail)}——未评/缺项=没做完人审，"
            f"不是通过·防假绿）；勾完再 publish，或 force=True 留痕绕行（D18 FR6.1·D25 补基准比对）")


def publish_deck(deck_id: str, root: str | Path | None = None,
                 handoff_card: dict | None = None, *, force: bool = False,
                 direct_through_waiver: str = "") -> dict:
    """交付收尾一步到位：登记只读锁（+ 交付物 sha256 指纹）+ 可选写交接卡（铁律4·制作工作流
    阶段4的代码落点）。

    此前 SKILL.md 阶段4 让人分别手调 mark_published / save_handoff，两步都靠自觉——
    漏掉 mark_published 则 assert_editable 永远拦不住回改（只读锁形同虚设）。收成一个函数后
    SKILL 只指一个入口。交付判断本身仍是人拍板（铁律0/2：机器不代判「可以交付」）。

    checksum（D16 🟢①）：workspace 里 deck.pptx 存在则自动算 sha256 记入登记表——只读锁
    从"拦 API"（assert_editable）升级到"文件系统篡改可发现"（verify_published 巡检比对，
    npm integrity / Maven checksum 同款机制）。pptx 还没生成就交付属异常，记 checksum=None
    并在返回值里如实标出。

    人审闸（D18 FR6.1）：交付前校验 workspace['review']（三道人审清单落盘）存在且零未评项
    ——第一轮实测视觉 9 项全 null 也交付了，"没做完人审就出货"从此走不通。force=True 紧急
    绕行（返回值 review_gate_forced=True 留痕）；机器只拦"没做"，不代判"好坏"（铁律2）。

    direct_through_waiver（D21 直通档）：传用户开场亲选直通档的**根授权原话**则豁免人审闸——
    与 force 是两种语义：force=事中紧急绕行（异常态），waiver=用户开场就预授权"字面直通、
    问完直接到成品"（2026-07-03 用户拍板）。诚实留痕而非伪造勾选：不假装人审做过了，返回值
    review_waiver 如实记"这份 deck 未经人审、依据哪句授权发布"，事后可回放可对质。
    空串/纯空白串=不豁免（批③🟡：" " 这类空白串不是授权原话，strip 后按未传处理）。

    审计链落盘（D21 批③·🔴6）：waiver/force 非常规交付除进返回值外还写进全局登记表的
    review_gates（mark_published(review_gate=...) 透传）——返回值没人存就丢了，账本才是
    可巡检的真相源。正常人审交付不写：**台账语义=有记录即非常规路径**。
    """
    ws = new_workspace(deck_id, root)
    # 2026-07-02 saopan扫盘揪出：重复 publish 会用**当前**文件重算 sha256 覆盖登记指纹——
    # 已交付产物被篡改后再跑一次 publish_deck，verify_published 的 mismatch 证据就被洗白。
    # 交付是一次性动作：已登记即拒重登（同 assert_editable 一个精神，发新版走新 deck_id）。
    if is_published(deck_id, ws["published_ledger"]):
        raise PermissionError(
            f"deck '{deck_id}' 已登记交付·拒重复 publish（重登会用当前文件覆盖登记指纹，"
            f"篡改证据即被洗白·铁律4）；确要发新版请用新 deck_id")
    # 批③🟡：纯空白 waiver 视为未传——" " 若混过下面的真值判断等于白拿豁免（空白串不是授权原话）
    waiver = (direct_through_waiver or "").strip()
    forced = False
    if force:
        forced = True   # 逃生门·留痕（进返回值与交接卡由调用方带走）——绕的是人审闸不是只读锁
    elif waiver:
        pass            # D21 直通档预授权豁免——waiver 原话进返回值留痕，不伪造"人审已勾完"
    else:
        _check_review_complete(ws["review"])   # D18 FR6.1：人审没勾完拒交付
    checksum = file_sha256(ws["pptx"]) if ws["pptx"].is_file() else None
    # 批③🔴6 审计链落盘：waiver/force 非常规路径写进台账 review_gates；正常人审交付不传
    # （台账语义：有记录=非常规路径），mark_published 对 None 不写任何条目。
    review_gate = {"waiver": waiver or None, "forced": forced} if (forced or waiver) else None
    published = mark_published(deck_id, ws["published_ledger"], checksum=checksum,
                               review_gate=review_gate, exclusive=True)  # 锁内裁决·D26 并发 TOCTOU 闭环
    handoff_path = None
    if handoff_card is not None:
        save_handoff(handoff_card, ws["handoff_card"])
        handoff_path = str(ws["handoff_card"])
    return {"deck_id": deck_id, "published": sorted(published),
            "checksum": checksum, "handoff_path": handoff_path, "review_gate_forced": forced,
            "review_waiver": waiver or None}


def verify_published(root: str | Path | None = None) -> list[dict]:
    """巡检已交付产物的完整性：逐个 deck 重算 deck.pptx 的 sha256 与登记指纹比对（只读·
    仪表盘 / saopan 可调）。返回 [{deck_id, status, note}]，status ∈：
      ok            指纹一致（本地副本未被动过）
      mismatch      指纹不一致——已交付产物被绕过 API 直接改了（铁律4被文件系统路径击穿）
      missing_file  登记为已交付但 deck.pptx 不在（产物丢失/被删）
      no_checksum   登记时没记指纹（老账/交付时 pptx 未生成），无从验证

    🧭 能力边界（D16·诚实标注）：只验证**本地 git 工作区里的副本**——交付出去的文件在
    客户手里的修改超出系统边界，不可知也不假装可知。
    """
    base = Path(root) if root else DEFAULT_DECKS_ROOT
    ledger = published_ledger_path(root)
    checksums = load_checksums(ledger)
    out = []
    for deck_id in sorted(load_published(ledger)):
        expected = checksums.get(deck_id)
        pptx = base / deck_id / ARTIFACTS["pptx"]
        if expected is None:
            out.append({"deck_id": deck_id, "status": "no_checksum",
                        "note": "登记时未记指纹·无从验证（老账或交付时 pptx 未生成）"})
        elif not pptx.is_file():
            out.append({"deck_id": deck_id, "status": "missing_file",
                        "note": f"登记为已交付但产物不在：{pptx}"})
        elif file_sha256(pptx) == expected:
            out.append({"deck_id": deck_id, "status": "ok", "note": ""})
        else:
            out.append({"deck_id": deck_id, "status": "mismatch",
                        "note": "sha256 与登记指纹不一致——已交付产物被绕过只读锁直接改动（铁律4）"})
    return out
