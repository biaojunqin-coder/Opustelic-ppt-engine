"""deck_workspace（④数据产物层）独立单测——「每份 deck 一套自洽产物」路径约定 + 交付收尾。"""

from __future__ import annotations

import pytest

from reinforce import deck_workspace as W
from reinforce.deck_memory import is_published, load_handoff



def _drop_passed_review(ws):
    """D18 FR6.1 适配：publish 前落盘一份全勾完的三道人审清单（这些测试测的是
    checksum/handoff/只读锁机制，不是人审闸——闸有自己的专门测试）。"""
    import json as _json
    from reinforce.review import new_review as _nr
    r = _nr()
    for section in r.values():
        for k in section:
            section[k] = True
    ws["review"].write_text(_json.dumps(r, ensure_ascii=False), encoding="utf-8")


def test_new_workspace_creates_dirs_and_paths(tmp_path):
    ws = W.new_workspace("deckA", root=tmp_path)
    assert ws["dir"].is_dir() and ws["pages"].is_dir()
    assert ws["deck_id"] == "deckA"
    # 全套产物路径映射齐全，都落在 deck 自己的家里
    for key in ("team_state", "storyline", "handoff", "spec_lock", "outline",
                "asset_ledger", "handoff_card", "pptx"):
        assert ws[key].parent == ws["dir"]
    # 已交付登记表是全局一本账（decks 根下·不在单 deck 目录里）
    assert ws["published_ledger"].parent == tmp_path


def test_new_workspace_idempotent_keeps_existing_files(tmp_path):
    ws = W.new_workspace("deckA", root=tmp_path)
    ws["outline"].write_text('{"title": "已填的肉"}', encoding="utf-8")
    ws2 = W.new_workspace("deckA", root=tmp_path)     # 再建·幂等
    assert ws2["outline"].read_text(encoding="utf-8") == '{"title": "已填的肉"}'  # 不毁已填的肉


@pytest.mark.parametrize("bad", ["", "  ", "a/b", "a\\b", "../escape", "x/../y"])
def test_deck_id_traversal_rejected(tmp_path, bad):
    with pytest.raises(ValueError):
        W.new_workspace(bad, root=tmp_path)


def test_workspace_dir_pure_path(tmp_path):
    d = W.workspace_dir("deckA", root=tmp_path)
    assert d == tmp_path / "deckA" and not d.exists()  # 纯计算·不建目录


def test_publish_deck_marks_readonly_and_writes_handoff(tmp_path):
    _drop_passed_review(W.new_workspace("deckA", root=tmp_path))   # D18 FR6.1 人审闸前置
    r = W.publish_deck("deckA", root=tmp_path,
                       handoff_card={"deck": "deckA", "current_page": 21, "todos": []})
    assert "deckA" in r["published"]
    ledger = W.published_ledger_path(tmp_path)
    assert is_published("deckA", ledger)               # 只读锁真相源已登记
    assert load_handoff(r["handoff_path"])["current_page"] == 21


def test_publish_deck_without_handoff(tmp_path):
    _drop_passed_review(W.new_workspace("deckB", root=tmp_path))
    r = W.publish_deck("deckB", root=tmp_path)
    assert r["handoff_path"] is None
    assert is_published("deckB", W.published_ledger_path(tmp_path))


# ── D16 修复批（2026-07-02）──────────────────────────────────────────
def test_publish_deck_records_pptx_checksum(tmp_path):
    """D16 🟢①：交付时自动算 deck.pptx 的 sha256 记入登记表。"""
    ws = W.new_workspace("deckC", root=tmp_path)
    ws["pptx"].write_bytes(b"fake pptx bytes")
    _drop_passed_review(ws)
    r = W.publish_deck("deckC", root=tmp_path)
    assert r["checksum"] and len(r["checksum"]) == 64  # sha256 hex


def test_publish_deck_no_pptx_checksum_none(tmp_path):
    """pptx 还没生成就交付（异常流程）：checksum=None 如实标出，不假装有指纹。"""
    _drop_passed_review(W.new_workspace("deckD", root=tmp_path))
    assert W.publish_deck("deckD", root=tmp_path)["checksum"] is None


def test_verify_published_four_states(tmp_path):
    """D16 🟢①：巡检四态——ok / mismatch（绕过 API 直接改文件被逮）/ missing_file / no_checksum。"""
    for d in ("ok_deck", "tampered", "vanished"):
        ws = W.new_workspace(d, root=tmp_path)
        ws["pptx"].write_bytes(f"content of {d}".encode())
        _drop_passed_review(ws)
        W.publish_deck(d, root=tmp_path)
    _drop_passed_review(W.new_workspace("old_deck", root=tmp_path))
    W.publish_deck("old_deck", root=tmp_path)          # 无 pptx → no_checksum

    W.new_workspace("tampered", root=tmp_path)["pptx"].write_bytes(b"HACKED")  # 绕 API 改文件
    W.new_workspace("vanished", root=tmp_path)["pptx"].unlink()                # 产物被删

    by_id = {r["deck_id"]: r["status"] for r in W.verify_published(tmp_path)}
    assert by_id == {"ok_deck": "ok", "tampered": "mismatch",
                     "vanished": "missing_file", "old_deck": "no_checksum"}


# ── 2026-07-02 saopan扫盘修复回归 ─────────────────────────────────────
def test_deck_id_pure_dots_rejected():
    """🟡：deck_id="." 曾穿过校验直指 decks 根目录（与全局账本混放）——纯点串拒。"""
    import pytest
    from reinforce.deck_workspace import workspace_dir
    for bad in (".", "..", "...", " . "):
        with pytest.raises(ValueError):
            workspace_dir(bad)


# ── D18 FR6.1 人审完成度闸 ─────────────────────────────────────────────
def _passed_review():
    from reinforce.review import new_review
    r = new_review()
    for section in r.values():
        for k in section:
            section[k] = True
    return r


def test_publish_blocked_without_review_file(tmp_path):
    import pytest
    from reinforce.deck_workspace import new_workspace, publish_deck
    ws = new_workspace("t_gate_nofile", root=tmp_path)
    ws["pptx"].write_bytes(b"pptx")
    with pytest.raises(ValueError, match="人审清单未落盘"):
        publish_deck("t_gate_nofile", root=tmp_path)


def test_publish_blocked_with_unrated_items(tmp_path):
    import json
    import pytest
    from reinforce.deck_workspace import new_workspace, publish_deck
    from reinforce.review import new_review
    ws = new_workspace("t_gate_unrated", root=tmp_path)
    ws["pptx"].write_bytes(b"pptx")
    ws["review"].write_text(json.dumps(new_review(), ensure_ascii=False), encoding="utf-8")  # 全 None
    with pytest.raises(ValueError, match="未评项"):
        publish_deck("t_gate_unrated", root=tmp_path)


def test_publish_passes_with_complete_review_and_force_leaves_trace(tmp_path):
    import json
    from reinforce.deck_workspace import new_workspace, publish_deck
    ws = new_workspace("t_gate_ok", root=tmp_path)
    ws["pptx"].write_bytes(b"pptx")
    ws["review"].write_text(json.dumps(_passed_review(), ensure_ascii=False), encoding="utf-8")
    r = publish_deck("t_gate_ok", root=tmp_path)
    assert r["review_gate_forced"] is False and r["checksum"]
    ws2 = new_workspace("t_gate_forced", root=tmp_path)
    ws2["pptx"].write_bytes(b"pptx")
    r2 = publish_deck("t_gate_forced", root=tmp_path, force=True)   # 紧急绕行·留痕
    assert r2["review_gate_forced"] is True


def test_publish_direct_through_waiver_skips_review_and_leaves_trace(tmp_path):
    # D21 直通档：无人审清单也可 publish，但 waiver 原话必须进返回值留痕——
    # 不伪造"人审已勾完"，如实记"未经人审·依据哪句根授权发布"
    from reinforce.deck_workspace import new_workspace, publish_deck
    ws = new_workspace("t_gate_waiver", root=tmp_path)
    ws["pptx"].write_bytes(b"pptx")
    quote = "直通档就是字面上的直通，问完直接到出成品"
    r = publish_deck("t_gate_waiver", root=tmp_path, direct_through_waiver=quote)
    assert r["review_waiver"] == quote and r["review_gate_forced"] is False


def test_publish_without_waiver_still_gated(tmp_path):
    # 空 waiver（默认值）不豁免——人审闸行为对存量调用零变化
    import pytest
    from reinforce.deck_workspace import new_workspace, publish_deck
    ws = new_workspace("t_gate_nowaiver", root=tmp_path)
    ws["pptx"].write_bytes(b"pptx")
    with pytest.raises(ValueError, match="人审清单未落盘"):
        publish_deck("t_gate_nowaiver", root=tmp_path, direct_through_waiver="")


# ── 批③ 直通档审计链：waiver/force 留痕落盘（🔴6）+ 空白 waiver（🟡）──────────
def _ledger_json(tmp_path):
    import json
    return json.loads(W.published_ledger_path(tmp_path).read_text(encoding="utf-8"))


def test_publish_waiver_lands_in_ledger_review_gates(tmp_path):
    # 🔴6：waiver 交付后根授权原话必须落进台账——只进返回值的留痕没人存就丢了
    ws = W.new_workspace("t_led_waiver", root=tmp_path)
    ws["pptx"].write_bytes(b"pptx")
    quote = "直通档就是字面上的直通，问完直接到出成品"
    W.publish_deck("t_led_waiver", root=tmp_path, direct_through_waiver=quote)
    assert _ledger_json(tmp_path)["review_gates"]["t_led_waiver"] == {
        "waiver": quote, "forced": False}


def test_publish_force_lands_in_ledger_review_gates(tmp_path):
    # 🔴6：force 紧急绕行同样进台账（forced=True·waiver=None）
    ws = W.new_workspace("t_led_forced", root=tmp_path)
    ws["pptx"].write_bytes(b"pptx")
    W.publish_deck("t_led_forced", root=tmp_path, force=True)
    assert _ledger_json(tmp_path)["review_gates"]["t_led_forced"] == {
        "waiver": None, "forced": True}


def test_publish_normal_review_writes_no_review_gate_entry(tmp_path):
    # 🔴6 台账语义：有记录=非常规路径——正常人审交付不写 review_gates 条目
    ws = W.new_workspace("t_led_normal", root=tmp_path)
    ws["pptx"].write_bytes(b"pptx")
    _drop_passed_review(ws)
    W.publish_deck("t_led_normal", root=tmp_path)
    assert "t_led_normal" not in _ledger_json(tmp_path).get("review_gates", {})


def test_old_ledger_without_review_gates_key_still_loads(tmp_path):
    # 🔴6 兼容：旧账本（无 review_gates 键）load 不炸，且能继续登记新的非常规交付
    import json
    from reinforce.deck_memory import load_published, mark_published
    p = W.published_ledger_path(tmp_path)
    p.write_text(json.dumps({"schema_version": 1, "delivered": ["old_deck"], "checksums": {}}),
                 encoding="utf-8")
    assert load_published(p) == {"old_deck"}                     # 旧结构读取不炸
    mark_published("new_deck", p, review_gate={"waiver": "原话", "forced": False})
    led = json.loads(p.read_text(encoding="utf-8"))
    assert led["review_gates"] == {"new_deck": {"waiver": "原话", "forced": False}}
    assert led["delivered"] == ["new_deck", "old_deck"]          # 旧账条目不丢


def test_publish_blank_waiver_still_gated(tmp_path):
    # 🟡：纯空白串不是授权原话——strip 后按未传处理，人审闸照拦
    ws = W.new_workspace("t_led_blank", root=tmp_path)
    ws["pptx"].write_bytes(b"pptx")
    with pytest.raises(ValueError, match="人审清单未落盘"):
        W.publish_deck("t_led_blank", root=tmp_path, direct_through_waiver="   ")


# ---------- D22b 品牌素材收集点：建家自带 + 扫描分组 ----------

def test_workspace_creates_brand_assets_with_readme(tmp_path):
    from reinforce.deck_workspace import new_workspace
    ws = new_workspace("t_brand_home", root=tmp_path)
    assert ws["brand_assets"].is_dir()
    readme = ws["brand_assets"] / "_放什么.md"
    assert readme.is_file() and "品牌素材收集点" in readme.read_text(encoding="utf-8")


def test_brand_assets_readme_not_overwritten(tmp_path):
    # scaffold 幂等纪律：用户改过的引导说明是用户的，重复建家不覆盖
    from reinforce.deck_workspace import new_workspace
    ws = new_workspace("t_brand_keep", root=tmp_path)
    readme = ws["brand_assets"] / "_放什么.md"
    readme.write_text("用户自己的备注", encoding="utf-8")
    new_workspace("t_brand_keep", root=tmp_path)
    assert readme.read_text(encoding="utf-8") == "用户自己的备注"


def test_list_brand_assets_groups_by_type(tmp_path):
    from reinforce.deck_workspace import list_brand_assets, new_workspace
    ws = new_workspace("t_brand_scan", root=tmp_path)
    ba = ws["brand_assets"]
    (ba / "brand.ttf").write_bytes(b"f")
    (ba / "logo.PNG").write_bytes(b"i")          # 大小写扩展名也认
    (ba / "vi_manual.pdf").write_bytes(b"d")
    sub = ba / "旧年份"
    sub.mkdir()
    (sub / "y24_deck.pptx").write_bytes(b"d")    # 子目录递归
    (ba / "notes.txt").write_bytes(b"o")
    got = list_brand_assets(ws)
    assert [p.name for p in got["fonts"]] == ["brand.ttf"]
    assert [p.name for p in got["images"]] == ["logo.PNG"]
    assert sorted(p.name for p in got["docs"]) == ["vi_manual.pdf", "y24_deck.pptx"]
    assert [p.name for p in got["others"]] == ["notes.txt"]


def test_list_brand_assets_empty_means_no_material(tmp_path):
    # 只有引导说明=没素材（any(values)=False → 制作层走 web_verified 联网查证链）
    from reinforce.deck_workspace import list_brand_assets, new_workspace
    ws = new_workspace("t_brand_empty", root=tmp_path)
    assert not any(list_brand_assets(ws).values())


# ---------- D25 🔴 人审闸 schema 漂移穿闸的修复 ----------

def test_publish_blocked_with_empty_role_dicts(tmp_path):
    # 三角色全空 dict（一项没勾·rate=0.0·unrated=0）曾能穿闸——原病"9项全null照样publish"复发路径
    import json

    import pytest

    from reinforce.deck_workspace import new_workspace, publish_deck
    ws = new_workspace("t_gate_empty_roles", root=tmp_path)
    ws["pptx"].write_bytes(b"pptx")
    ws["review"].write_text(json.dumps({"action_title": {}, "storyline": {}, "slide_content": {}},
                                       ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="缺现行清单项"):
        publish_deck("t_gate_empty_roles", root=tmp_path)


def test_publish_blocked_with_stale_schema_review(tmp_path):
    # 旧 schema：文件里有的项全勾了，但现行 REVIEWS 后来长出的新项它根本没有——缺项=未评拒
    import json

    import pytest

    from reinforce.deck_workspace import new_workspace, publish_deck
    from reinforce.review import REVIEWS
    stale = {role: {items[0]: True} for role, items in REVIEWS.items()}  # 每道只有第一项且勾了
    ws = new_workspace("t_gate_stale", root=tmp_path)
    ws["pptx"].write_bytes(b"pptx")
    ws["review"].write_text(json.dumps(stale, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="缺现行清单项"):
        publish_deck("t_gate_stale", root=tmp_path)


def test_publish_passes_with_current_full_review(tmp_path):
    # 按现行 new_review() 建的清单全评完 → 照常放行（含评了 False 的项——机器只拦"没做"不代判好坏）
    import json

    from reinforce.deck_workspace import new_workspace, publish_deck
    from reinforce.review import new_review
    review = new_review()
    for role, items in review.items():
        for k in items:
            items[k] = True
    ws = new_workspace("t_gate_current", root=tmp_path)
    ws["pptx"].write_bytes(b"pptx")
    ws["review"].write_text(json.dumps(review, ensure_ascii=False), encoding="utf-8")
    r = publish_deck("t_gate_current", root=tmp_path)
    assert r["review_gate_forced"] is False
