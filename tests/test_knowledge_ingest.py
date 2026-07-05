"""知识库摄入（D5/D5.1）独立单测——框架结构指纹/事实脱敏/品牌库公私分流/候选池/人审 promote 承重墙。"""

from __future__ import annotations

import pytest

from reinforce.evolution import knowledge_ingest as K


# ---------- 框架候选 ----------

def test_fingerprint_ignores_content_only_shape():
    t1 = {"mode": "假设树", "branches": [
        {"key": "a", "claim": "客户A的具体主张", "confidence": "高"},
        {"key": "b", "claim": "完全不同的另一句话", "confidence": "中"},
    ]}
    t2 = {"mode": "假设树", "branches": [
        {"key": "x", "claim": "另一个客户的另一套说法", "confidence": "高"},
        {"key": "y", "claim": "内容完全不同", "confidence": "中"},
    ]}
    assert K.fingerprint_issue_tree(t1) == K.fingerprint_issue_tree(t2)  # 形状一样·内容不同


def test_fingerprint_confidence_none_not_crash():
    # 批③🟢：confidence 显式 None（分支未评级）曾在 [:1] 上崩 TypeError——or 兜底按"中"处理
    t_none = {"mode": "假设树", "branches": [{"key": "a", "confidence": None},
                                             {"key": "b", "confidence": "高"}]}
    t_mid = {"mode": "假设树", "branches": [{"key": "a", "confidence": "中"},
                                            {"key": "b", "confidence": "高"}]}
    assert K.fingerprint_issue_tree(t_none) == K.fingerprint_issue_tree(t_mid)


def test_framework_candidates_evidence_threshold():
    same_shape = {"mode": "议题树", "branches": [{"key": "a", "confidence": "高"}] * 3}
    unique_shape = {"mode": "假设树", "branches": [{"key": "z", "confidence": "低"}]}
    trees = [same_shape, same_shape, unique_shape]  # same_shape 撞2次·unique只1次
    cands = K.framework_candidates(trees)
    assert len(cands) == 1
    assert cands[0]["support"] == 2
    assert cands[0]["deck_indexes"] == [0, 1]


def test_framework_candidates_single_not_qualified():
    trees = [{"mode": "议题树", "branches": [{"key": "a"}]},
             {"mode": "假设树", "branches": [{"key": "b"}, {"key": "c"}]}]
    assert K.framework_candidates(trees) == []  # 各自单份·不采纳


# ---------- 事实候选 ----------

def test_desensitize_fact_drops_claim_keeps_numbers():
    entries = [{"n": 3, "data": "10053亿元", "claim": "客户机密表述A"},
               {"n": 5, "data": "1万亿", "claim": "客户机密表述B"}]
    cand = K.desensitize_fact("市场规模", entries, ["精酿啤酒行业"], "某品牌",
                               source_hint="Ipsos调研报告2024")
    assert cand["raw_points"] == [{"n": 3, "data": "10053亿元"}, {"n": 5, "data": "1万亿"}]
    assert "claim" not in str(cand)  # claim 原句必须不进候选
    assert cand["domain"] == ["精酿啤酒行业"]
    assert cand["brand"] == "某品牌"
    assert "未核实" in cand["timeliness"]


def test_desensitize_fact_rejects_empty_domain():
    with pytest.raises(ValueError, match="domain"):
        K.desensitize_fact("市场规模", [{"n": 1, "data": "1"}], [], "某品牌")


def test_desensitize_fact_rejects_long_domain_as_sentence():
    long_domain = ["这看起来像是一整句话而不是一个类目标签所以应该被拒绝"]
    with pytest.raises(ValueError, match="泛化"):
        K.desensitize_fact("市场规模", [{"n": 1, "data": "1"}], long_domain, "某品牌")


def test_desensitize_fact_rejects_empty_brand():
    with pytest.raises(ValueError, match="brand"):
        K.desensitize_fact("市场规模", [{"n": 1, "data": "1"}], ["精酿啤酒行业"], "")


def test_fact_candidates_from_storyline_extracts_all_numeric_dims():
    # 2026-07-02 D18 回灌首跑（某品牌 42条证据提取0候选）证伪旧口径——"只留跨页重复维度"是
    # 一致性人审的口径不是回灌的口径；现在单次出现的数字维度也进候选，同 dim 多条聚合计 support。
    storyline = {"lines": [
        {"n": 1, "claim": "市场很大", "evidence": [{"dim": "市场规模", "data": "100亿"}]},
        {"n": 2, "claim": "持续增长", "evidence": [{"dim": "市场规模", "data": "120亿"}]},
        {"n": 3, "claim": "无关维度", "evidence": [{"dim": "单次维度", "data": "50%"}]},
    ]}
    cands = K.fact_candidates_from_storyline(storyline, ["消费品"], "某快消品牌")
    assert len(cands) == 2                                  # 单次维度也提取
    by_dim = {c["dim"]: c for c in cands}
    assert by_dim["市场规模"]["support"] == 2               # 跨页聚合如实计数
    assert cands[0]["dim"] == "市场规模"
    assert cands[0]["support"] == 2
    assert cands[0]["brand"] == "某快消品牌"


# ---------- 公私分流：visibility 判定 ----------

def test_classify_visibility_public_when_third_party_source():
    assert K.classify_visibility("Ipsos重庆精酿白啤发展机会点调研，24年6月") == "public"
    assert K.classify_visibility("巨量算数，统计截止2020.7-2020.8") == "public"


def test_classify_visibility_private_when_no_independent_source():
    assert K.classify_visibility("") == "private"
    assert K.classify_visibility("客户输入·未标注独立信源") == "private"
    assert K.classify_visibility("deck内部整理，未标注来源") == "private"
    assert K.classify_visibility("品牌方自述数据") == "private"


def test_desensitize_fact_auto_classifies_visibility():
    entries = [{"n": 1, "data": "1"}, {"n": 2, "data": "2"}]
    public_cand = K.desensitize_fact("d", entries, ["消费品"], "某品牌", source_hint="Ipsos 2024年调研")
    private_cand = K.desensitize_fact("d", entries, ["消费品"], "某品牌", source_hint="deck未标注来源")
    assert public_cand["visibility"] == "public"
    assert private_cand["visibility"] == "private"


def test_desensitize_fact_visibility_override():
    entries = [{"n": 1, "data": "1"}]
    cand = K.desensitize_fact("d", entries, ["消费品"], "某品牌",
                               source_hint="Ipsos 2024年调研", visibility="private")
    assert cand["visibility"] == "private"  # 显式覆盖优先于自动判定


def test_classify_visibility_platform_brand_defaults_public_even_without_citation():
    # 平台自身聚合数据(brand=抖音)即便 source_citation 空/模糊也默认公开——平台数据本来就广泛分发
    assert K.classify_visibility("", brand="抖音") == "public"
    assert K.classify_visibility("数据截至2020年8月", brand="抖音") == "public"


def test_classify_visibility_advertiser_brand_in_platform_deck_stays_private():
    # 同一份抖音销售deck里的广告主案例(brand=京东家电)不因为平台白名单被误放行——
    # 平台规则只对 brand 本身是平台的情况生效，不对"deck来自哪个平台"生效
    assert K.classify_visibility("数据来源：《京东家电#你拍广告我给钱结案》2020年3月",
                                  brand="京东家电") == "private"


def test_desensitize_fact_platform_brand_auto_public():
    entries = [{"n": 1, "data": "6亿"}, {"n": 2, "data": "4亿"}]
    cand = K.desensitize_fact("DAU", entries, ["短视频行业"], "抖音", source_hint="数据截至2020年8月")
    assert cand["visibility"] == "public"


# ---------- 候选池落盘 + 人审 promote ----------

def test_queue_candidates_appends_and_persists(tmp_path):
    p = tmp_path / "pool.json"
    r1 = K.queue_candidates([{"fingerprint": "a"}], pool="framework", path=p)
    # D25 起返回值多 skipped_dup 键（入池去重）——断言改超集兼容
    assert r1 == {"pool": "framework", "queued": 1, "skipped_dup": 0, "total_pending": 1}
    r2 = K.queue_candidates([{"fingerprint": "b"}], pool="framework", path=p)
    assert r2["total_pending"] == 2


def test_queue_candidates_rejects_bad_pool():
    with pytest.raises(ValueError, match="pool"):
        K.queue_candidates([], pool="nope")


def test_promote_requires_reviewer(tmp_path):
    lib_path = tmp_path / "lib.json"
    with pytest.raises(ValueError, match="reviewer"):
        K.promote({"id": "fw1"}, pool="framework", reviewer="", lib_path=lib_path)
    with pytest.raises(ValueError, match="reviewer"):  # 2026-07-01 saopan扫盘：纯空格此前能绕过
        K.promote({"id": "fw1"}, pool="framework", reviewer="   ", lib_path=lib_path)


def test_promote_appends_with_reviewer_to_framework_lib(tmp_path):
    lib_path = tmp_path / "lib.json"
    r = K.promote({"id": "fw1", "framework_name": "测试框架"}, pool="framework",
                   reviewer="人审", lib_path=lib_path)
    assert r == {"pool": "framework", "promoted_id": "fw1", "reviewer": "人审"}
    saved = K._load_json(lib_path, {})
    assert saved["cards"][0]["id"] == "fw1"
    assert saved["cards"][0]["reviewer"] == "人审"


def test_promote_appends_to_fact_lib_uses_facts_key(tmp_path):
    lib_path = tmp_path / "lib.json"
    K.promote({"id": "fact1"}, pool="fact", reviewer="人审", lib_path=lib_path)
    saved = K._load_json(lib_path, {})
    assert "facts" in saved and saved["facts"][0]["id"] == "fact1"


# ---------- 原始素材归档（2026-07-01·用户拍板：蒸馏之外尽量保留原始素材备用）----------

def test_archive_raw_fact_context_keeps_claim_that_desensitize_drops(tmp_path):
    p = tmp_path / "raw_facts.json"
    entries = [{"n": 1, "data": "100亿", "claim": "客户机密表述·蒸馏时会被丢掉"}]
    r = K.archive_raw_fact_context("市场规模", entries, "某品牌", archive_path=p)
    assert r == {"brand": "某品牌", "dim": "市场规模", "archived_count": 1}
    saved = K._load_json(p, {})
    assert saved["brands"]["某品牌"]["entries"][0]["raw_entries"][0]["claim"] == "客户机密表述·蒸馏时会被丢掉"


def test_archive_raw_fact_context_rejects_empty_brand(tmp_path):
    with pytest.raises(ValueError, match="brand"):
        K.archive_raw_fact_context("d", [{"n": 1, "data": "1"}], "", archive_path=tmp_path / "x.json")


def test_archive_raw_fact_context_accumulates_across_calls(tmp_path):
    p = tmp_path / "raw_facts.json"
    K.archive_raw_fact_context("市场规模", [{"n": 1, "data": "100亿"}], "某品牌", archive_path=p)
    K.archive_raw_fact_context("增速", [{"n": 2, "data": "25%"}], "某品牌", archive_path=p)
    saved = K._load_json(p, {})
    assert len(saved["brands"]["某品牌"]["entries"]) == 2


def test_archive_raw_fact_context_does_not_touch_shared_pool_or_brand_lib(tmp_path):
    # 归档是独立文件，跟共享知识库/品牌库物理隔离——不应该出现在另外两份文件里
    shared_p, brand_p, archive_p = tmp_path / "shared.json", tmp_path / "brand.json", tmp_path / "raw.json"
    K.archive_raw_fact_context("市场规模", [{"n": 1, "data": "100亿", "claim": "机密"}], "某品牌",
                                archive_path=archive_p)
    assert K._load_json(shared_p, {}) == {}
    assert K._load_json(brand_p, {}) == {}
    assert "机密" in str(K._load_json(archive_p, {}))


def test_archive_raw_framework_source_keeps_full_tree_content(tmp_path):
    p = tmp_path / "raw_frameworks.json"
    tree = {"mode": "假设树", "branches": [{"key": "a", "claim": "客户具体主张", "confidence": "高"}]}
    r = K.archive_raw_framework_source("假设树|n=1|conf=高", [tree], archive_path=p)
    assert r == {"fingerprint": "假设树|n=1|conf=高", "archived_count": 1}
    saved = K._load_json(p, {})
    stored_tree = saved["fingerprints"]["假设树|n=1|conf=高"]["trees"][0]
    assert stored_tree["branches"][0]["claim"] == "客户具体主张"  # fingerprint 本身丢的内容，归档留住了


def test_archive_raw_framework_source_rejects_empty_fingerprint(tmp_path):
    with pytest.raises(ValueError, match="fingerprint"):
        K.archive_raw_framework_source("", [{}], archive_path=tmp_path / "x.json")


def test_archive_raw_framework_source_groups_multiple_brands_under_same_fingerprint(tmp_path):
    # 同一结构指纹可能是不同品牌各自独立撞到的——按指纹分组不按品牌，不丢失"这是几份独立案例"
    p = tmp_path / "raw_frameworks.json"
    tree_a = {"mode": "假设树", "branches": [{"key": "a", "claim": "品牌A的主张"}]}
    tree_b = {"mode": "假设树", "branches": [{"key": "a", "claim": "品牌B的主张"}]}
    K.archive_raw_framework_source("fp1", [tree_a], archive_path=p)
    K.archive_raw_framework_source("fp1", [tree_b], archive_path=p)
    saved = K._load_json(p, {})
    assert len(saved["fingerprints"]["fp1"]["trees"]) == 2


# ---------- 品牌库：公私分流 ----------

def test_file_to_brand_library_requires_reviewer_and_brand(tmp_path):
    p = tmp_path / "brand.json"
    with pytest.raises(ValueError, match="reviewer"):
        K.file_to_brand_library({"brand": "某品牌", "visibility": "public"}, reviewer="", brand_lib_path=p)
    with pytest.raises(ValueError, match="reviewer"):  # 2026-07-01 saopan扫盘：纯空格此前能绕过
        K.file_to_brand_library({"brand": "某品牌", "visibility": "public"}, reviewer="   ", brand_lib_path=p)
    with pytest.raises(ValueError, match="brand"):
        K.file_to_brand_library({"visibility": "public"}, reviewer="人审", brand_lib_path=p)
    with pytest.raises(ValueError, match="visibility"):
        K.file_to_brand_library({"brand": "某品牌", "visibility": "??"}, reviewer="人审", brand_lib_path=p)


def test_file_to_brand_library_groups_by_brand(tmp_path):
    p = tmp_path / "brand.json"
    K.file_to_brand_library({"id": "f1", "brand": "某品牌", "visibility": "public"}, reviewer="人审", brand_lib_path=p)
    K.file_to_brand_library({"id": "f2", "brand": "某品牌", "visibility": "private"}, reviewer="人审", brand_lib_path=p)
    K.file_to_brand_library({"id": "f3", "brand": "MTA", "visibility": "public"}, reviewer="人审", brand_lib_path=p)
    saved = K._load_json(p, {})
    assert len(saved["brands"]["某品牌"]["facts"]) == 2
    assert len(saved["brands"]["MTA"]["facts"]) == 1


def test_visible_facts_for_brand_hides_private_by_default(tmp_path):
    p = tmp_path / "brand.json"
    K.file_to_brand_library({"id": "f1", "brand": "某品牌", "visibility": "public"}, reviewer="人审", brand_lib_path=p)
    K.file_to_brand_library({"id": "f2", "brand": "某品牌", "visibility": "private"}, reviewer="人审", brand_lib_path=p)
    visible = K.visible_facts_for_brand("某品牌", brand_lib_path=p)
    assert [f["id"] for f in visible] == ["f1"]  # 私有数据默认不放出


def test_visible_facts_for_brand_honors_sharing_override(tmp_path):
    p = tmp_path / "brand.json"
    facts_lib = {"brands": {"某品牌": {"facts": [
        {"id": "f1", "visibility": "private"},
        {"id": "f2", "visibility": "private", "sharing_override": True},
    ]}}}
    K._save_json(p, facts_lib)
    visible = K.visible_facts_for_brand("某品牌", brand_lib_path=p)
    assert [f["id"] for f in visible] == ["f2"]  # 品牌方明确 override 才放行


def test_sync_public_facts_to_shared_pool_only_moves_visible(tmp_path):
    bp, sp = tmp_path / "brand.json", tmp_path / "shared.json"
    K.file_to_brand_library({"id": "f1", "brand": "某品牌", "visibility": "public"}, reviewer="人审", brand_lib_path=bp)
    K.file_to_brand_library({"id": "f2", "brand": "某品牌", "visibility": "private"}, reviewer="人审", brand_lib_path=bp)
    r = K.sync_public_facts_to_shared_pool(reviewer="人审", brand_lib_path=bp, shared_lib_path=sp)
    assert r["synced_ids"] == ["f1"]
    saved = K._load_json(sp, {})
    ids = [f["id"] for f in saved["facts"]]
    assert ids == ["f1"]  # f2(private) 永不进共享池


def test_sync_public_facts_to_shared_pool_is_idempotent(tmp_path):
    bp, sp = tmp_path / "brand.json", tmp_path / "shared.json"
    K.file_to_brand_library({"id": "f1", "brand": "某品牌", "visibility": "public"}, reviewer="人审", brand_lib_path=bp)
    K.sync_public_facts_to_shared_pool(reviewer="人审", brand_lib_path=bp, shared_lib_path=sp)
    r2 = K.sync_public_facts_to_shared_pool(reviewer="人审", brand_lib_path=bp, shared_lib_path=sp)
    assert r2["synced_ids"] == []  # 已同步过的 id 不重复写入
    saved = K._load_json(sp, {})
    assert len(saved["facts"]) == 1


def test_sync_public_facts_to_shared_pool_requires_reviewer(tmp_path):
    with pytest.raises(ValueError, match="reviewer"):
        K.sync_public_facts_to_shared_pool(reviewer="", brand_lib_path=tmp_path / "b.json",
                                            shared_lib_path=tmp_path / "s.json")
    with pytest.raises(ValueError, match="reviewer"):  # 2026-07-01 saopan扫盘：纯空格此前能绕过
        K.sync_public_facts_to_shared_pool(reviewer="   ", brand_lib_path=tmp_path / "b.json",
                                            shared_lib_path=tmp_path / "s.json")


# ---------- sharing_override 操作留痕 ----------

def test_set_sharing_override_requires_actor_and_reason(tmp_path):
    p = tmp_path / "brand.json"
    K.file_to_brand_library({"id": "f1", "brand": "某品牌", "visibility": "private"}, reviewer="人审", brand_lib_path=p)
    with pytest.raises(ValueError, match="actor"):
        K.set_sharing_override("某品牌", "f1", True, actor="", reason="品牌方同意分享", brand_lib_path=p)
    with pytest.raises(ValueError, match="reason"):
        K.set_sharing_override("某品牌", "f1", True, actor="产品经理张三", reason="", brand_lib_path=p)
    with pytest.raises(ValueError, match="actor"):  # 2026-07-01 saopan扫盘：纯空格此前能绕过
        K.set_sharing_override("某品牌", "f1", True, actor="   ", reason="品牌方同意分享", brand_lib_path=p)
    with pytest.raises(ValueError, match="reason"):
        K.set_sharing_override("某品牌", "f1", True, actor="产品经理张三", reason="\t\n", brand_lib_path=p)


def test_set_sharing_override_rejects_unknown_brand_or_fact(tmp_path):
    p = tmp_path / "brand.json"
    K.file_to_brand_library({"id": "f1", "brand": "某品牌", "visibility": "private"}, reviewer="人审", brand_lib_path=p)
    with pytest.raises(ValueError, match="brand"):
        K.set_sharing_override("不存在的品牌", "f1", True, actor="a", reason="r", brand_lib_path=p)
    with pytest.raises(ValueError, match="id=f999"):
        K.set_sharing_override("某品牌", "f999", True, actor="a", reason="r", brand_lib_path=p)


def test_set_sharing_override_updates_fact_and_writes_audit_log(tmp_path):
    p = tmp_path / "brand.json"
    K.file_to_brand_library({"id": "f1", "brand": "某品牌", "visibility": "private"}, reviewer="人审", brand_lib_path=p)
    r = K.set_sharing_override("某品牌", "f1", True, actor="产品经理张三",
                                reason="品牌方书面同意开放该数据", brand_lib_path=p)
    assert r == {"brand": "某品牌", "fact_id": "f1", "old_value": None, "new_value": True,
                 "actor": "产品经理张三", "reason": "品牌方书面同意开放该数据"}
    saved = K._load_json(p, {})
    fact = saved["brands"]["某品牌"]["facts"][0]
    assert fact["sharing_override"] is True
    assert len(saved["audit_log"]) == 1
    assert saved["audit_log"][0]["actor"] == "产品经理张三"
    # override 后该事实应该能被 visible_facts_for_brand 检索到
    visible = K.visible_facts_for_brand("某品牌", brand_lib_path=p)
    assert [f["id"] for f in visible] == ["f1"]


def test_set_sharing_override_can_revoke(tmp_path):
    p = tmp_path / "brand.json"
    K.file_to_brand_library({"id": "f1", "brand": "某品牌", "visibility": "private"}, reviewer="人审", brand_lib_path=p)
    K.set_sharing_override("某品牌", "f1", True, actor="a", reason="开放", brand_lib_path=p)
    K.set_sharing_override("某品牌", "f1", False, actor="b", reason="品牌方撤回同意", brand_lib_path=p)
    saved = K._load_json(p, {})
    assert len(saved["audit_log"]) == 2  # 两次操作都留痕，不覆盖历史
    assert K.visible_facts_for_brand("某品牌", brand_lib_path=p) == []


# ── 跨客户结构复用侦测持久化池（2026-07-01）──
_TREE_3H = {"mode": "假设树", "branches": [{"confidence": "高"}, {"confidence": "中"}, {"confidence": "低"}]}


def test_record_fingerprint_requires_brand(tmp_path):
    with pytest.raises(ValueError, match="brand"):
        K.record_issue_tree_fingerprint(_TREE_3H, "", path=tmp_path / "p.json")


def test_record_fingerprint_same_brand_not_double_counted(tmp_path):
    p = tmp_path / "pool.json"
    K.record_issue_tree_fingerprint(_TREE_3H, "BrandA", path=p)
    r = K.record_issue_tree_fingerprint(_TREE_3H, "BrandA", path=p)  # 同品牌重复撞
    assert r["distinct_brands"] == 1


def test_record_fingerprint_different_brands_counted_independently(tmp_path):
    p = tmp_path / "pool.json"
    K.record_issue_tree_fingerprint(_TREE_3H, "BrandA", path=p)
    r = K.record_issue_tree_fingerprint(_TREE_3H, "BrandB", path=p)
    assert r["distinct_brands"] == 2


def test_due_framework_candidates_respects_min_support(tmp_path):
    p = tmp_path / "pool.json"
    K.record_issue_tree_fingerprint(_TREE_3H, "BrandA", path=p)
    assert K.due_framework_candidates(min_support=2, path=p) == []  # 只 1 个品牌·不够
    K.record_issue_tree_fingerprint(_TREE_3H, "BrandB", path=p)
    out = K.due_framework_candidates(min_support=2, path=p)
    assert len(out) == 1 and set(out[0]["brands"]) == {"BrandA", "BrandB"}


# ── 路径参数接受字符串（2026-07-01·saopan扫盘：类型标注跟姊妹模块不一致，
#    传字符串此前会 AttributeError('str' object has no attribute 'is_file')）──
def test_promote_accepts_string_path(tmp_path):
    p_str = str(tmp_path / "lib.json")
    rep = K.promote({"id": "fw1"}, pool="framework", reviewer="人审", lib_path=p_str)
    assert rep["promoted_id"] == "fw1"


def test_record_issue_tree_fingerprint_accepts_string_path(tmp_path):
    p_str = str(tmp_path / "pool.json")
    r = K.record_issue_tree_fingerprint(_TREE_3H, "BrandA", path=p_str)
    assert r["distinct_brands"] == 1


# ── fail-closed 读 / 原子写 / 并发锁（2026-07-02 saopan扫盘揪出：_load_json 把损坏 JSON 吞成
#    default→下次落盘以 default 重建=静默清空（含 audit_log 审计日志）；_save_json 非原子；
#    全部落盘函数裸 read-modify-write 无锁）──
def test_load_json_corrupted_raises_not_default(tmp_path):
    p = tmp_path / "broken.json"
    p.write_text("{半截损坏", encoding="utf-8")
    with pytest.raises(ValueError, match="fail-closed"):
        K._load_json(p, {"pending": []})


def test_load_json_top_level_non_dict_raises_not_default(tmp_path):
    """批④：顶层被手改成列表/字符串的**合法 JSON** 同样是"读不懂"——旧版直接返回，
    下游 data["fingerprints"]/setdefault 要么 TypeError 要么静默按空重建（同 deck_memory
    "delivered 类型坏必 raise"一条纪律），补 fail-closed。"""
    p = tmp_path / "wrong_shape.json"
    p.write_text('["a", "b"]', encoding="utf-8")
    with pytest.raises(ValueError, match="顶层不是对象"):
        K._load_json(p, {"pending": []})
    assert p.read_text(encoding="utf-8") == '["a", "b"]'  # 原文件不动·人工修复的唯一依据


def test_queue_candidates_on_corrupted_pool_raises_and_keeps_file(tmp_path):
    """损坏候选池上写入必须 raise 且绝不覆盖原文件（原文件是人工修复的唯一依据）。"""
    p = tmp_path / "pool.json"
    p.write_text("{半截损坏", encoding="utf-8")
    with pytest.raises(ValueError, match="fail-closed"):
        K.queue_candidates([{"fingerprint": "a"}], pool="framework", path=p)
    assert p.read_text(encoding="utf-8") == "{半截损坏"


def test_set_sharing_override_on_corrupted_brand_lib_keeps_audit_trail_file(tmp_path):
    """audit_log 所在的品牌库损坏时 set_sharing_override 必须 raise——旧版会按空默认重建，
    审计日志被静默清空=操作留痕机制名存实亡。"""
    p = tmp_path / "brand.json"
    p.write_text("{半截损坏", encoding="utf-8")
    with pytest.raises(ValueError, match="fail-closed"):
        K.set_sharing_override("某品牌", "f1", True, actor="张三", reason="测试", brand_lib_path=p)
    assert p.read_text(encoding="utf-8") == "{半截损坏"


def test_save_json_atomic_no_tmp_leftover(tmp_path):
    p = tmp_path / "pool.json"
    K.queue_candidates([{"fingerprint": "a"}], pool="framework", path=p)
    assert not (tmp_path / "pool.json.tmp").exists()  # temp+rename·不留半截临时文件


def test_record_fingerprint_concurrent_brands_dont_lose(tmp_path):
    """并发回归：8线程各记不同品牌同一指纹，锁住后 distinct_brands 一个不丢。"""
    import threading
    p = tmp_path / "pool.json"

    def worker(i):
        K.record_issue_tree_fingerprint(_TREE_3H, f"Brand{i}", path=p)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    out = K.due_framework_candidates(min_support=8, path=p)
    assert len(out) == 1 and len(out[0]["brands"]) == 8


# ── D18 FR6.2 回灌首跑修复回归（某品牌 补跑揪出的口径错配）───────────
def test_fact_candidates_extracts_single_occurrence_dims():
    """旧版只留跨页重复维度——真实 storyline 42 条证据提取 0 候选；现在逐条提取。"""
    from reinforce.evolution.knowledge_ingest import fact_candidates_from_storyline
    sl = {"lines": [
        {"n": 4, "evidence": [{"dim": "市场规模", "data": "1342亿元·增速23.6%", "source": "报告大厅"}]},
        {"n": 7, "evidence": [{"dim": "男性消费力", "data": "2025年突破6万亿", "source": "知乎"},
                              {"dim": "无数字维度", "data": "纯定性描述", "source": "访谈"}]},
    ]}
    cands = fact_candidates_from_storyline(sl, domain=["啤酒行业"], brand="某品牌")
    dims = {c["dim"] for c in cands}
    assert dims == {"市场规模", "男性消费力"}          # 单次出现也提取·无数字的不进
    assert all(c["support"] == 1 for c in cands)


def test_fact_candidates_use_real_evidence_source_for_visibility():
    """evidence 自带 source 参与公私分流——公开报道不再被统一 hint 误判 private。"""
    from reinforce.evolution.knowledge_ingest import fact_candidates_from_storyline
    sl = {"lines": [{"n": 3, "evidence": [
        {"dim": "品牌健康度", "data": "41升至49", "source": "brief P9"}]}]}
    cands = fact_candidates_from_storyline(sl, domain=["啤酒行业"], brand="某品牌")
    assert cands[0]["source_citation"] == "brief P9"   # 真实来源进候选·分流按它判


# ── D20 FR3.2 结构性文案候选管线（语料飞轮·第三轮实测拍板"语料随使用自我生长"）───────────

import json as _json


def _write_deck_storyline(tmp_path, lines):
    """造一个最小 deck 工作区：<dir>/storyline.json 只需 lines 字段（提取器只读它）。"""
    deck_dir = tmp_path / "某品牌_brand_equity"
    deck_dir.mkdir()
    (deck_dir / "storyline.json").write_text(
        _json.dumps({"lines": lines}, ensure_ascii=False), encoding="utf-8")
    return deck_dir


def test_copy_candidates_maps_four_line_types_to_slots(tmp_path):
    """四类结构件行按类型映射槽位：转场→章间桥(claim+bridge_from 各一条)、章小结→章小结、
    决策→ask收尾、目录→目录命名(toc_items 逐项)。字段口径对齐 某品牌 真实 storyline。"""
    deck_dir = _write_deck_storyline(tmp_path, [
        {"n": 2, "page_type": "目录", "claim": "这份提案想说清楚三件事",
         "toc_items": ["先看清我们要打的是一场什么仗", "解法：出拳，才算数"]},
        {"n": 3, "page_type": "转场", "claim": "先看清我们要打的是一场什么仗",
         "bridge_from": None},                                     # 首 Part 转场豁免 bridge_from
        {"n": 8, "page_type": "转场", "claim": "解法：出拳，才算数",
         "bridge_from": "认知模糊是真病根——该拿什么把三条线连起来？"},
        {"n": 13, "page_type": "落幕", "role": "章小结",
         "claim": "三条线诊断完毕：认知模糊是真病根"},              # 真实坏例也进候选·好坏判定在人审
        {"n": 20, "page_type": "数据论断", "claim": "普通行不提取", "role": ""},
        {"n": 40, "page_type": "决策", "claim": "请某品牌批准，由我们担任代理"},
    ])
    cands = K.copy_candidates_from_deck(deck_dir)
    by_slot = {}
    for c in cands:
        by_slot.setdefault(c["slot"], []).append(c["text"])
    assert by_slot["目录命名"] == ["先看清我们要打的是一场什么仗", "解法：出拳，才算数"]
    # 目录行的 claim 不进候选（目录槽位语料=章命名本身，不是目录页标题）
    assert "这份提案想说清楚三件事" not in by_slot["目录命名"]
    assert by_slot["章间桥"] == ["先看清我们要打的是一场什么仗",          # p3 claim(bridge 空只出一条)
                                  "解法：出拳，才算数",                    # p8 claim
                                  "认知模糊是真病根——该拿什么把三条线连起来？"]  # p8 bridge_from
    assert by_slot["章小结"] == ["三条线诊断完毕：认知模糊是真病根"]
    assert by_slot["ask收尾"] == ["请某品牌批准，由我们担任代理"]
    assert "普通行不提取" not in str(cands)


def test_copy_candidates_carry_deck_n_kind_and_source_hint(tmp_path):
    deck_dir = _write_deck_storyline(tmp_path, [
        {"n": 40, "page_type": "决策", "claim": "SOW三栏交付"}])
    cands = K.copy_candidates_from_deck(deck_dir, source_hint="40页IMC·已publish")
    assert cands == [{"text": "SOW三栏交付", "slot": "ask收尾", "deck": "某品牌_brand_equity",
                      "n": 40, "kind": "good_candidate", "source_hint": "40页IMC·已publish"}]
    # 不传 source_hint 时不带该键（别写空字符串占位）
    assert "source_hint" not in K.copy_candidates_from_deck(deck_dir)[0]


def test_copy_candidates_page_function_xiaojie_also_counts(tmp_path):
    """章小结判定同 check_part_structure 口径：role="章小结" 或 page_function 含"小结"。"""
    deck_dir = _write_deck_storyline(tmp_path, [
        {"n": 12, "page_type": "数据论断", "page_function": "阶段小结页", "claim": "认知模糊是真病根"}])
    cands = K.copy_candidates_from_deck(deck_dir)
    assert [(c["slot"], c["text"]) for c in cands] == [("章小结", "认知模糊是真病根")]


def test_copy_candidates_missing_storyline_raises(tmp_path):
    empty_dir = tmp_path / "not_a_deck"
    empty_dir.mkdir()
    with pytest.raises(ValueError, match="storyline"):
        K.copy_candidates_from_deck(empty_dir)


def test_copy_candidates_corrupted_storyline_fail_closed(tmp_path):
    deck_dir = tmp_path / "deck"
    deck_dir.mkdir()
    (deck_dir / "storyline.json").write_text("{半截损坏", encoding="utf-8")
    with pytest.raises(ValueError, match="fail-closed"):
        K.copy_candidates_from_deck(deck_dir)


def test_copy_candidates_no_lines_key_prints_visible_warning(tmp_path, capsys):
    """批④：storyline.json 在但缺 lines 键（落盘形态异常）——此前静默返回 []，与
    "真提取了 0 条"分不清；现在 print 一条可见警告，返回形态不动（仍是候选 list）。"""
    deck_dir = tmp_path / "deck"
    deck_dir.mkdir()
    (deck_dir / "storyline.json").write_text('{"governing_thought": "x"}', encoding="utf-8")
    assert K.copy_candidates_from_deck(deck_dir) == []
    assert "缺 'lines' 键" in capsys.readouterr().out
    # lines 键在但为空列表=正常形态（策略刚起步还没写行），不该刷警告
    (deck_dir / "storyline.json").write_text('{"lines": []}', encoding="utf-8")
    assert K.copy_candidates_from_deck(deck_dir) == []
    assert "缺 'lines' 键" not in capsys.readouterr().out


def test_queue_candidates_copy_pool(tmp_path):
    p = tmp_path / "copy_pool.json"
    r = K.queue_candidates([{"text": "回见！", "slot": "落幕"}], pool="copy", path=p)
    assert r == {"pool": "copy", "queued": 1, "skipped_dup": 0, "total_pending": 1}
    saved = K._load_json(p, {})
    assert saved["pending"][0]["text"] == "回见！"


def test_queue_candidates_copy_pool_default_path_constant():
    """copy 池缺省路径 = _文案候选池.json（不误写进 framework/fact 池文件）。"""
    assert K._POOL_FILES["copy"].name == "_文案候选池.json"
    assert K.COPY_LIB.name == "表达手法卡.json"


def test_promote_copy_pool_requires_slot(tmp_path):
    lib_path = tmp_path / "lib.json"
    with pytest.raises(ValueError, match="slot"):     # 无 slot 拒
        K.promote({"text": "回见！", "deck": "d", "n": 32}, pool="copy",
                  reviewer="人审", lib_path=lib_path)
    with pytest.raises(ValueError, match="slot"):     # slot 非法值同样拒
        K.promote({"slot": "不存在的槽位", "formula": "x", "demo": "y"}, pool="copy",
                  reviewer="人审", lib_path=lib_path)


def test_promote_copy_pool_rejects_raw_candidate_even_with_valid_slot(tmp_path):
    """端到端真跑揪出的假门回归：copy_candidates_from_deck 产的候选本身带合法 slot——只查 slot
    拦不住裸句直接入库；裸句与成卡的确定性分界是 formula/demo（FR1.2 卡三要素前两件）。"""
    deck_dir = _write_deck_storyline(tmp_path, [
        {"n": 40, "page_type": "决策", "claim": "请某品牌批准，由我们担任代理"}])
    raw = K.copy_candidates_from_deck(deck_dir)[0]
    assert raw["slot"] in K.COPY_SLOTS                 # 前提成立：裸候选自带合法 slot
    with pytest.raises(ValueError, match="formula"):
        K.promote(raw, pool="copy", reviewer="人审", lib_path=tmp_path / "lib.json")
    with pytest.raises(ValueError, match="formula"):   # formula 有但 demo 空同样拒
        K.promote({**raw, "formula": "[栏×交付物]"}, pool="copy",
                  reviewer="人审", lib_path=tmp_path / "lib.json")


def test_promote_copy_pool_appends_to_cards_key(tmp_path):
    lib_path = tmp_path / "lib.json"
    card = {"id": "slot_ending_x", "slot": "落幕", "expression_type": "落幕-人格化告别",
            "formula": "[超短口语告别·带品牌人格]", "demo": "某品牌 8x8结案 p32「回见！」",
            "anti_pattern": "❌「以上就是我们的完整方案」"}
    r = K.promote(card, pool="copy", reviewer="人审", lib_path=lib_path)
    assert r == {"pool": "copy", "promoted_id": "slot_ending_x", "reviewer": "人审"}
    saved = K._load_json(lib_path, {})
    assert saved["cards"][0]["slot"] == "落幕"        # 表达手法卡库顶层键是 cards（非 facts）
    assert saved["cards"][0]["reviewer"] == "人审"


def test_promote_still_rejects_unknown_pool():
    with pytest.raises(ValueError, match="pool"):
        K.promote({"slot": "落幕"}, pool="nope", reviewer="人审")


# ---------- D24 反馈池（收集范围宪法第5条）----------

def test_queue_feedback_rejects_empty_quote(tmp_path):
    import pytest
    from reinforce.evolution.knowledge_ingest import queue_feedback
    with pytest.raises(ValueError, match="逐字原话"):
        queue_feedback("  ", path=tmp_path / "fb.json")


def test_queue_feedback_stores_verbatim(tmp_path):
    import json
    from reinforce.evolution.knowledge_ingest import queue_feedback
    p = tmp_path / "fb.json"
    r = queue_feedback("明明发现了问题为什么没有解决方案？", context="第六轮实测",
                       deck_id="d1", category="需求种子", date="2026-07-03", path=p)
    assert r["pool"] == "feedback" and r["queued"] == 1
    data = json.loads(p.read_text(encoding="utf-8"))
    e = data["pending"][0]
    assert e["quote"] == "明明发现了问题为什么没有解决方案？"
    assert e["category"] == "需求种子" and e["date"] == "2026-07-03"


def test_feedback_pool_has_no_promote_path():
    # 宪法设计：反馈内化=人审转需求/偏好，不是库 append——_POOL_LIBS 故意不含 feedback
    import pytest
    from reinforce.evolution.knowledge_ingest import _POOL_LIBS, promote
    assert "feedback" not in _POOL_LIBS
    with pytest.raises(ValueError):
        promote({"quote": "x"}, pool="feedback", reviewer="r")


def test_queue_candidates_accepts_feedback_pool(tmp_path):
    from reinforce.evolution.knowledge_ingest import queue_candidates
    r = queue_candidates([{"quote": "q"}], pool="feedback", path=tmp_path / "fb.json")
    assert r["total_pending"] == 1


# ---------- D25 扫盘：飞轮四闸 ----------

def test_desensitize_fact_carries_stable_content_id():
    from reinforce.evolution.knowledge_ingest import desensitize_fact
    a = desensitize_fact("市场规模", [{"n": 1, "data": "500亿", "claim": "x"}], ["行业"], "品牌A")
    b = desensitize_fact("市场规模", [{"n": 1, "data": "500亿", "claim": "y"}], ["行业"], "品牌A")
    c = desensitize_fact("市场规模", [{"n": 1, "data": "600亿", "claim": "x"}], ["行业"], "品牌A")
    assert a["id"].startswith("fact_") and a["id"] == b["id"]   # 同内容同 id（claim 不参与·本就不进候选）
    assert a["id"] != c["id"]                                    # 数据不同 id 不同


def test_sync_skips_and_reports_no_id_facts(tmp_path):
    import json
    from reinforce.evolution.knowledge_ingest import (file_to_brand_library,
                                                      sync_public_facts_to_shared_pool)
    bp, sp = tmp_path / "brand.json", tmp_path / "shared.json"
    file_to_brand_library({"dim": "无id公开事实", "brand": "B", "visibility": "public"},
                          reviewer="t", brand_lib_path=bp)
    r1 = sync_public_facts_to_shared_pool(reviewer="t", brand_lib_path=bp, shared_lib_path=sp)
    r2 = sync_public_facts_to_shared_pool(reviewer="t", brand_lib_path=bp, shared_lib_path=sp)
    assert r1["synced_count"] == 0 and r1["skipped_no_id"] == ["B/无id公开事实"]
    shared = json.loads(sp.read_text(encoding="utf-8")) if sp.exists() else {"facts": []}
    assert len(shared.get("facts", [])) == 0    # 跑两次一条都没进——不再重复注入
    # 带 id 的正常同步 + 幂等
    file_to_brand_library({"id": "fact_x1", "dim": "有id", "brand": "B", "visibility": "public"},
                          reviewer="t", brand_lib_path=bp)
    r3 = sync_public_facts_to_shared_pool(reviewer="t", brand_lib_path=bp, shared_lib_path=sp)
    r4 = sync_public_facts_to_shared_pool(reviewer="t", brand_lib_path=bp, shared_lib_path=sp)
    assert r3["synced_count"] == 1 and r4["synced_count"] == 0


def test_promote_fact_rejects_private_visibility(tmp_path):
    import pytest
    from reinforce.evolution.knowledge_ingest import promote
    with pytest.raises(ValueError, match="跨客户"):
        promote({"id": "f1", "visibility": "private"}, pool="fact", reviewer="t",
                lib_path=tmp_path / "lib.json")
    # public 与无 visibility 字段（历史手工卡）照常放行
    promote({"id": "f2", "visibility": "public"}, pool="fact", reviewer="t",
            lib_path=tmp_path / "lib.json")
    promote({"id": "f3"}, pool="fact", reviewer="t", lib_path=tmp_path / "lib.json")


def test_queue_candidates_dedups_within_and_across_batches(tmp_path):
    from reinforce.evolution.knowledge_ingest import queue_candidates
    p = tmp_path / "pool.json"
    c = {"dim": "d", "brand": "b"}
    r1 = queue_candidates([c, dict(c)], pool="fact", path=p)   # 同批内重复
    assert r1["queued"] == 1 and r1["skipped_dup"] == 1
    r2 = queue_candidates([dict(c)], pool="fact", path=p)      # 跨批次重复（断点重跑形态）
    assert r2["queued"] == 0 and r2["total_pending"] == 1


# ---------- D28 C端前收口：.com移出public白名单 + 提取器版式噪音过滤 ----------

def test_internal_dotcom_domain_stays_private():
    # 二轮扫盘🟡(D26漏排·D28补)："客户内部BI后台 admin.xx.com 导出"曾被.com标记判public——
    # private→public 方向性误判=隐私外流；真公开.com信源降private只是少放(宁私勿公·人审可改判)
    from reinforce.evolution.knowledge_ingest import classify_visibility
    assert classify_visibility("客户内部BI后台 admin.mostbrand.com 导出", brand="某品牌") == "private"
    assert classify_visibility("data.gov 公开数据集", brand="某品牌") == "public"   # .gov 保留
    assert classify_visibility("Ipsos 调查", brand="某品牌") == "public"            # 真信源标记不受影响


def test_layout_meta_dims_filtered_from_candidates():
    # D27 记账：某品牌单 38 条候选混入 10 条版式元数据(期号/目录编号/X轴标签/卡片编号)·26%噪音
    from reinforce.evolution.knowledge_ingest import fact_candidates_from_storyline
    sl = {"lines": [
        {"n": 1, "evidence": [{"dim": "4月单篇阅读量", "data": "1331", "source": "客户后台"}]},
        {"n": 2, "evidence": [{"dim": "报告期号", "data": "第4期", "source": "版式"}]},
        {"n": 3, "evidence": [{"dim": "月度曲线X轴标签", "data": "1-12月", "source": "版式"}]},
        {"n": 4, "evidence": [{"dim": "标题占比与卡片编号", "data": "3/9", "source": "版式"}]},
    ]}
    cands = fact_candidates_from_storyline(sl, ["行业"], "品牌A")
    dims = [c["dim"] for c in cands]
    assert dims == ["4月单篇阅读量"]   # 真数据留·三条版式元数据全滤
