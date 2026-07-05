"""deck_memory（⑤Memory）独立单测——已交付只读锁 + 交接卡。"""

from __future__ import annotations

import json
import pathlib

import pytest

from reinforce import deck_memory as M


def test_published_roundtrip(tmp_path):
    p = tmp_path / "published.json"
    assert M.load_published(p) == set()
    M.mark_published("deckA", p)
    assert M.is_published("deckA", p)
    assert "deckA" in M.load_published(p)


def test_assert_editable_blocks_published(tmp_path):
    p = tmp_path / "published.json"
    M.mark_published("deckA", p)
    with pytest.raises(PermissionError):
        M.assert_editable("deckA", p)
    M.assert_editable("deckB", p)  # 未交付·可改·不抛


def test_handoff_roundtrip(tmp_path):
    c = M.new_handoff("某 deck", 5, todos=["补数据页"], next_steps=["做第6页"])
    M.save_handoff(c, tmp_path / "h.json")
    loaded = M.load_handoff(tmp_path / "h.json")
    assert loaded["current_page"] == 5 and loaded["todos"] == ["补数据页"]


def test_save_handoff_takes_lock(tmp_path):
    """批④：save_handoff 补 _locked（对齐同文件 mark_published 的写点纪律）——
    <文件>.lock 真被创建即证临界区走了锁路径；内容照常完整落盘。"""
    p = tmp_path / "h.json"
    M.save_handoff(M.new_handoff("deckA", 3), p)
    assert (tmp_path / "h.json.lock").exists()   # _locked 的锁文件（锁它不锁数据文件本身）
    assert M.load_handoff(p)["current_page"] == 3
    assert not (tmp_path / "h.json.tmp").exists()  # 原子写不留半截


def test_atomic_write_no_tmp_leftover(tmp_path):
    """原子写（temp+rename）：写完不留 .tmp 残骸，内容完整。"""
    p = tmp_path / "published.json"
    M.mark_published("deckA", p)
    M.mark_published("deckB", p)
    assert not list(tmp_path.glob("*.tmp"))            # rename 干净·无半截文件
    assert M.load_published(p) == {"deckA", "deckB"}   # 两次写都完整落盘


# ── D16 修复批（2026-07-02）──────────────────────────────────────────
def _mark_one(args):
    deck_id, path = args
    from reinforce import deck_memory as DM
    DM.mark_published(deck_id, path)


def test_concurrent_mark_published_no_lost_update(tmp_path):
    """D16 🟡①：并发 read-modify-write 加 flock 后无丢更新（evolution.py 计数器同款病·
    那边实测无锁丢失率 98%）。20 进程并发各登记一个 deck，20 个必须全在。"""
    import multiprocessing as mp
    p = tmp_path / "published.json"
    ids = [f"deck{i:02d}" for i in range(20)]
    with mp.Pool(10) as pool:
        pool.map(_mark_one, [(i, str(p)) for i in ids])
    assert M.load_published(p) == set(ids)


def test_corrupt_ledger_raises_not_empty(tmp_path):
    """D16 追加发现：账本损坏必须 raise（fail-closed）——若照 Novel 版'损坏→空集'，
    只读锁会全体失效（fail-open 方向）。文件不存在仍是正常初始态（空集）。"""
    p = tmp_path / "published.json"
    assert M.load_published(p) == set()                # 不存在 = 正常初始态
    p.write_text("{半截损坏", encoding="utf-8")
    with pytest.raises(ValueError, match="登记表损坏"):
        M.load_published(p)
    with pytest.raises(ValueError):                     # assert_editable 同样拒绝按空账放行
        M.assert_editable("deckA", p)


def test_mark_published_records_checksum(tmp_path):
    """D16 🟢①：登记时可带交付物 sha256 指纹（npm integrity 同款机制）。"""
    p = tmp_path / "published.json"
    M.mark_published("deckA", p, checksum="abc123")
    M.mark_published("deckB", p)                       # 不带指纹的老路径兼容
    assert M.load_checksums(p) == {"deckA": "abc123"}
    assert M.load_published(p) == {"deckA", "deckB"}


def test_file_sha256_stable(tmp_path):
    a, b = tmp_path / "a.bin", tmp_path / "b.bin"
    a.write_bytes(b"hello deck")
    b.write_bytes(b"hello deck TAMPERED")
    assert M.file_sha256(a) == M.file_sha256(a)        # 同文件同指纹
    assert M.file_sha256(a) != M.file_sha256(b)        # 内容变指纹必变


def test_schema_version_in_outputs(tmp_path):
    """D16 🟢③：落盘 JSON 带 schema_version。"""
    p = tmp_path / "published.json"
    M.mark_published("deckA", p)
    assert json.loads(p.read_text(encoding="utf-8"))["schema_version"] == 1
    assert M.new_handoff("x", 1)["schema_version"] == 1


# ── 2026-07-02 saopan扫盘修复回归（账本 fail-closed 加固）──────────────
def test_ledger_type_corruption_raises_not_fail_open(tmp_path):
    """🟡：delivered 被手改成字符串曾被 list() 拆成单字符 → 只读锁静默失效——类型坏同语法坏，raise。"""
    import json
    import pytest
    from reinforce.deck_memory import is_published, load_published
    p = tmp_path / "_published.json"
    p.write_text(json.dumps({"schema_version": 1, "delivered": "deckC", "checksums": {}}), encoding="utf-8")
    with pytest.raises(ValueError, match="类型坏"):
        is_published("deckC", p)
    p.write_text(json.dumps({"schema_version": 1, "delivered": ["a"], "checksums": []}), encoding="utf-8")
    with pytest.raises(ValueError, match="checksums"):
        load_published(p)
    p.write_text(json.dumps(["not", "a", "dict"]), encoding="utf-8")
    with pytest.raises(ValueError, match="顶层不是对象"):
        load_published(p)


def test_ledger_newer_schema_rejected(tmp_path):
    """🟡：schema_version 只写不读曾形同虚设——新版本账本被旧代码读改写会剥字段，拒读。"""
    import json
    import pytest
    from reinforce.deck_memory import load_published
    p = tmp_path / "_published.json"
    p.write_text(json.dumps({"schema_version": 99, "delivered": [], "checksums": {}}), encoding="utf-8")
    with pytest.raises(ValueError, match="schema_version=99"):
        load_published(p)


def test_mark_published_exclusive_rejects_in_lock(tmp_path):
    # D26 二轮扫盘🔴：并发 TOCTOU 闭环——锁内裁决拒重复登记（外层预检只是友好报错）
    import pytest

    from reinforce.deck_memory import mark_published
    p = tmp_path / "led.json"
    mark_published("d1", p, checksum="aaa", exclusive=True)
    with pytest.raises(PermissionError, match="锁内裁决"):
        mark_published("d1", p, checksum="bbb", exclusive=True)
    from reinforce.deck_memory import load_checksums
    assert load_checksums(p)["d1"] == "aaa"     # 首次登记的指纹未被覆盖
    mark_published("d1", p, checksum="ccc")     # 非 exclusive 旧语义不变（幂等更新）
