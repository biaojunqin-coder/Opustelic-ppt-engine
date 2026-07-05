"""自进化（⑧）独立单测——可信值台账 + 盲拆收敛证据门槛 + 承重墙。"""

from __future__ import annotations

from reinforce.evolution import evolution as E
from reinforce.evolution import methodology as M


def test_confidence():
    assert M.confidence({"support": 3, "refute": 1}) == 0.75
    assert M.confidence({}) == 0.0


def test_accumulate_new_and_promote(tmp_path):
    p = tmp_path / "l.json"
    rep = M.accumulate({"action_title_claim": {"support": 3, "rule_text": "标题论断"}}, path=p)
    assert "action_title_claim" in rep["new"] and "action_title_claim" in rep["promoted"]
    assert M.load_ledger(p)["action_title_claim"]["confidence"] == 1.0


def test_accumulate_demote_on_refute(tmp_path):
    p = tmp_path / "l.json"
    M.accumulate({"r": {"support": 2, "rule_text": "x"}}, path=p)
    rep = M.accumulate({"r": {"refute": 3}}, path=p)
    assert "r" in rep["demoted"]
    assert M.load_ledger(p)["r"]["confidence"] < 0.5


def test_evolution_due_threshold():
    assert E.evolution_due(30)["due"] is True
    d = E.evolution_due(10)
    assert d["due"] is False and d["remaining"] == 20


def test_converge_evidence_threshold():
    findings = [{"rule_key": "newrule", "polarity": "support"},
                {"rule_key": "newrule", "polarity": "support"},
                {"rule_key": "single", "polarity": "support"}]  # single 只 1 份
    r = E.converge(findings, baseline={"known"}, n_decks=2)
    keys = [a["rule_key"] for a in r["added"]]
    assert "newrule" in keys and "single" not in keys  # 单份不采纳
    assert r["status"] == "pending_人审"  # 承重墙·不自动落地


def test_converge_confirmed_vs_added():
    findings = [{"rule_key": "known", "polarity": "support"}] * 2
    r = E.converge(findings, baseline={"known"}, n_decks=2)
    assert any(c["rule_key"] == "known" for c in r["confirmed"])
    assert not r["added"]


# ── decks_since 计数器（2026-07-01 接入·此前 evolution_due 无真实数据源）──
def test_load_decks_since_missing_file_is_zero(tmp_path):
    assert E.load_decks_since(tmp_path / "nope.json") == 0


def test_record_deck_torn_down_increments_and_persists(tmp_path):
    p = tmp_path / "c.json"
    assert E.record_deck_torn_down(p) == 1
    assert E.record_deck_torn_down(p) == 2
    assert E.load_decks_since(p) == 2


def test_reset_decks_since_zeroes(tmp_path):
    p = tmp_path / "c.json"
    E.record_deck_torn_down(p); E.record_deck_torn_down(p)
    E.reset_decks_since(p)
    assert E.load_decks_since(p) == 0


def test_record_deck_torn_down_atomic_write_no_tmp_residue(tmp_path):
    """2026-07-03 二轮扫盘批D：计数器改用同包 _locked_io（locked+atomic_write_json）——
    temp+rename 原子落盘，不留 .tmp 残件；读回值正确。"""
    p = tmp_path / "c.json"
    E.record_deck_torn_down(p)
    E.reset_decks_since(p)
    E.record_deck_torn_down(p)
    assert not (tmp_path / "c.json.tmp").exists()  # 原子写不留半截临时文件
    assert (tmp_path / "c.json.lock").exists()      # 锁走 .lock 旁文件（_locked_io 模式）
    assert E.load_decks_since(p) == 1


def test_accumulate_refuses_whitespace_only_reviewer(tmp_path):
    """2026-07-01 saopan扫盘揪出：纯空格此前能绕过校验且真的写盘。"""
    import pytest
    p = tmp_path / "l.json"
    with pytest.raises(ValueError, match="reviewer"):
        M.accumulate({"r": {"support": 1, "rule_text": "x"}}, path=p, reviewer="   ")
    assert not p.exists()  # 拒绝时不该有任何写盘痕迹


def test_accumulate_refuses_empty_reviewer(tmp_path):
    import pytest
    p = tmp_path / "l.json"
    with pytest.raises(ValueError, match="reviewer"):
        M.accumulate({"r": {"support": 1, "rule_text": "x"}}, path=p, reviewer="")


def test_record_deck_torn_down_concurrent_calls_dont_lose_count(tmp_path):
    """2026-07-01 saopan扫盘揪出：读-改-写无锁，8线程×20次并发实测丢失率98%。
    加 fcntl.flock 独占锁(+释放前flush/fsync)后应该0丢失。"""
    import threading
    p = tmp_path / "counter.json"

    def worker():
        for _ in range(20):
            E.record_deck_torn_down(p)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert E.load_decks_since(p) == 8 * 20


# ── 可信值台账 fail-closed 读 + 并发锁（2026-07-02 saopan扫盘揪出：load_ledger 把损坏 JSON
#    吞成空默认→下次 accumulate 以空账重建=静默清空承重墙数据；accumulate 裸 read-modify-write
#    无锁。deck_memory 立的"账本读坏必 raise 绝不按空账"纪律当时没推行到这里）──
def test_load_ledger_corrupted_json_raises_not_empty(tmp_path):
    import pytest
    p = tmp_path / "l.json"
    p.write_text("{这不是合法json!!!", encoding="utf-8")
    with pytest.raises(ValueError, match="拒按空账"):
        M.load_ledger(p)


def test_load_ledger_missing_file_is_still_empty(tmp_path):
    assert M.load_ledger(tmp_path / "nope.json") == {}  # 不存在=正常初始态·不误伤


def test_load_ledger_top_level_not_dict_raises(tmp_path):
    """2026-07-03 二轮扫盘批D：顶层被改成列表/字符串（语法合法·类型坏）此前直接放行——
    对照同包 knowledge_ingest._load_json 的 D25 口径补 fail-closed。"""
    import pytest
    for bad in ('["不是对象"]', '"一串字符串"', "42"):
        p = tmp_path / "l.json"
        p.write_text(bad, encoding="utf-8")
        with pytest.raises(ValueError, match="不是对象"):
            M.load_ledger(p)


def test_accumulate_on_corrupted_ledger_raises_and_keeps_file(tmp_path):
    """损坏台账上 accumulate 必须 raise 且绝不覆盖原文件——原文件是人工修复的唯一依据。"""
    import pytest
    p = tmp_path / "l.json"
    p.write_text("{半截损坏", encoding="utf-8")
    with pytest.raises(ValueError, match="拒按空账"):
        M.accumulate({"r": {"support": 1, "rule_text": "x"}}, path=p)
    assert p.read_text(encoding="utf-8") == "{半截损坏"  # 一字未动


def test_accumulate_normal_growth_never_resets(tmp_path):
    """正常累积不回退：两轮 accumulate 后计数是累加的，不是第二轮按空账重来。"""
    p = tmp_path / "l.json"
    M.accumulate({"r": {"support": 2, "rule_text": "x"}}, path=p)
    M.accumulate({"r": {"support": 3}}, path=p)
    led = M.load_ledger(p)
    assert led["r"]["support"] == 5
    assert not (tmp_path / "l.json.tmp").exists()  # 原子写·不留半截临时文件


def test_accumulate_concurrent_calls_dont_lose_counts(tmp_path):
    """同 record_deck_torn_down 的并发场景：8线程×10次各 +1 support，锁住后一次不丢。"""
    import threading
    p = tmp_path / "l.json"

    def worker():
        for _ in range(10):
            M.accumulate({"r": {"support": 1, "rule_text": "x"}}, path=p)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert M.load_ledger(p)["r"]["support"] == 80
