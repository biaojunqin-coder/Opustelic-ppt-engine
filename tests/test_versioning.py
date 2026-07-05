"""范本库版本追踪测试（reinforce/evolution/versioning.py·补 L7 铁律"无版本无留痕"缺口）。"""

from __future__ import annotations

import json

import pytest

from reinforce.evolution.versioning import (
    cards_changed_without_version_bump,
    current_version,
    library_change_violations,
    record_library_change,
)


def _lib(tmp_path, cards=None):
    p = tmp_path / "lib.json"
    p.write_text(json.dumps({"cards": cards or []}, ensure_ascii=False), encoding="utf-8")
    return p


def test_current_version_missing_file_is_zero(tmp_path):
    assert current_version(tmp_path / "nope.json") == 0


def test_current_version_no_field_is_zero(tmp_path):
    p = _lib(tmp_path)
    assert current_version(p) == 0


def test_record_library_change_bumps_version_and_appends_log(tmp_path):
    p = _lib(tmp_path, cards=[{"id": "a"}])
    entry = record_library_change(p, "新增1张卡", reviewer="人审(测试)", card_count=1)
    assert entry["version"] == 1
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["version"] == 1
    assert data["change_log"] == [entry]
    assert data["cards"] == [{"id": "a"}]  # 不动 cards 本体


def test_record_library_change_accumulates_across_calls(tmp_path):
    p = _lib(tmp_path)
    record_library_change(p, "第一次改动", reviewer="人审A")
    record_library_change(p, "第二次改动", reviewer="人审B")
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["version"] == 2
    assert [e["change"] for e in data["change_log"]] == ["第一次改动", "第二次改动"]
    assert current_version(p) == 2


def test_record_library_change_refuses_empty_reviewer(tmp_path):
    p = _lib(tmp_path)
    with pytest.raises(ValueError, match="reviewer"):
        record_library_change(p, "改动", reviewer="")


def test_record_library_change_refuses_whitespace_only_reviewer(tmp_path):
    """2026-07-01 saopan扫盘揪出：纯空格此前能绕过校验。"""
    p = _lib(tmp_path)
    with pytest.raises(ValueError, match="reviewer"):
        record_library_change(p, "改动", reviewer="   ")


# ── pre-commit 钩子核心判断逻辑（2026-07-01·补 L7"绕过代码直接改文件"最后一环）──
def test_cards_unchanged_passes():
    old = {"cards": [{"id": "a"}], "version": 1}
    new = {"cards": [{"id": "a"}], "version": 1}
    assert cards_changed_without_version_bump(old, new) is False


def test_cards_changed_with_version_bump_passes():
    old = {"cards": [{"id": "a"}], "version": 1}
    new = {"cards": [{"id": "a"}, {"id": "b"}], "version": 2}
    assert cards_changed_without_version_bump(old, new) is False


def test_cards_changed_without_version_bump_blocked():
    old = {"cards": [{"id": "a"}], "version": 1}
    new = {"cards": [{"id": "a"}, {"id": "b"}], "version": 1}  # 卡加了·版本没动
    assert cards_changed_without_version_bump(old, new) is True


def test_new_file_with_cards_but_version_zero_blocked():
    old = {"cards": [], "version": 0}  # 视同全新文件
    new = {"cards": [{"id": "a"}], "version": 0}  # 有卡了但没走 record_library_change
    assert cards_changed_without_version_bump(old, new) is True


# ── 文件不存在/JSON损坏时的错误处理（2026-07-01·saopan扫盘：此前抛裸FileNotFoundError/
#    JSONDecodeError，跟同文件current_version()的优雅降级不一致）──
def test_record_library_change_refuses_missing_file(tmp_path):
    with pytest.raises(ValueError, match="不存在"):
        record_library_change(tmp_path / "不存在.json", "改动", reviewer="人审")


def test_record_library_change_refuses_corrupted_json(tmp_path):
    p = tmp_path / "corrupted.json"
    p.write_text("{这不是合法json!!!", encoding="utf-8")
    with pytest.raises(ValueError, match="JSON 损坏"):
        record_library_change(p, "改动", reviewer="人审")


# ── library_change_violations 完整留痕校验（2026-07-02 saopan扫盘揪出：旧钩子只验 version
#    数字，手改 cards + 手动 version+1 不追加 change_log 即可放行，"留痕"名存实亡）──
_OLD = {"cards": [{"id": "a"}], "version": 1,
        "change_log": [{"version": 1, "reviewer": "人审", "change": "初始"}]}


def _new(cards=None, version=2, log_extra=None):
    """基于 _OLD 派生一个"新暂存区版本"。log_extra=None 表示 change_log 原封不动。"""
    log = list(_OLD["change_log"]) + (log_extra or [])
    return {"cards": cards if cards is not None else [{"id": "a"}, {"id": "b"}],
            "version": version, "change_log": log}


def test_violations_cards_changed_version_bumped_but_no_new_log_entry_blocked():
    """核心验收：cards 变 + version 涨 + 无新 log 条目 → 拒（旧钩子放行的漏洞场景）。"""
    problems = library_change_violations(_OLD, _new(version=2, log_extra=None))
    assert len(problems) == 1 and "change_log 没有新增条目" in problems[0]


def test_violations_full_trail_passes():
    new = _new(version=2, log_extra=[{"version": 2, "reviewer": "人审", "change": "加一张卡"}])
    assert library_change_violations(_OLD, new) == []


def test_violations_cards_unchanged_passes_whatever():
    """内容主体没变（如只改 _schema 说明文字）→ 不管 version/log，放行。"""
    same = {"cards": [{"id": "a"}], "version": 1, "change_log": []}
    assert library_change_violations(_OLD, same) == []


def test_violations_version_not_bumped_blocked():
    new = _new(version=1, log_extra=[{"version": 1, "reviewer": "人审", "change": "x"}])
    problems = library_change_violations(_OLD, new)
    assert any("version 没跟着涨" in p for p in problems)


def test_violations_old_log_entry_tampered_blocked():
    """防"删旧条目再补新条目"伪装成有留痕——历史台账是史实，只可追加不可篡改。"""
    new = {"cards": [{"id": "a"}, {"id": "b"}], "version": 2,
           "change_log": [{"version": 1, "reviewer": "被篡改", "change": "初始"},
                          {"version": 2, "reviewer": "人审", "change": "加卡"}]}
    problems = library_change_violations(_OLD, new)
    assert any("只可追加不可篡改" in p for p in problems)


def test_violations_new_entry_version_mismatch_blocked():
    """新增条目 version 字段跟库顶层 version 对不上 → 疑似手编 log，拒。"""
    new = _new(version=3, log_extra=[{"version": 2, "reviewer": "人审", "change": "x"}])
    problems = library_change_violations(_OLD, new)
    assert any("不一致" in p for p in problems)


def test_violations_content_key_families_for_palette():
    """B3-3 泛化：数据色板的内容主体键是 families（硬编码 cards 会让它的留痕校验永远失明）。"""
    old = {"families": {"red": ["#f00"]}, "version": 1,
           "change_log": [{"version": 1, "reviewer": "人审", "change": "初始"}]}
    new = {"families": {"red": ["#f00"], "blue": ["#00f"]}, "version": 1,
           "change_log": [{"version": 1, "reviewer": "人审", "change": "初始"}]}
    problems = library_change_violations(old, new, content_key="families")
    assert problems  # families 变了没留痕·必须拦
    assert library_change_violations(old, dict(old), content_key="families") == []


def test_violations_content_key_facts_for_knowledge_base():
    """B3-3 泛化：行业知识库的内容主体键是 facts。"""
    old = {"facts": [{"id": "f1"}], "version": 1,
           "change_log": [{"version": 1, "reviewer": "人审", "change": "初始"}]}
    new = {"facts": [{"id": "f1"}, {"id": "f2"}], "version": 2,
           "change_log": [{"version": 1, "reviewer": "人审", "change": "初始"},
                          {"version": 2, "reviewer": "人审", "change": "加一条"}]}
    assert library_change_violations(old, new, content_key="facts") == []


def test_violations_brand_new_file_requires_trail():
    """全新库文件（HEAD 里没有·钩子用空默认对照）第一次提交也得带上 version+change_log。"""
    old = {"cards": [], "version": 0}
    bare = {"cards": [{"id": "a"}], "version": 0}
    assert library_change_violations(old, bare)  # 裸内容无留痕·拦
    proper = {"cards": [{"id": "a"}], "version": 1,
              "change_log": [{"version": 1, "reviewer": "人审", "change": "建库"}]}
    assert library_change_violations(old, proper) == []


# ── record_library_change 并发与原子写（2026-07-02 saopan扫盘揪出：自身也是裸
#    read-modify-write——留痕机制自己会丢留痕）──
def test_record_library_change_concurrent_calls_dont_lose_entries(tmp_path):
    import threading
    p = _lib(tmp_path, cards=[{"id": "a"}])

    def worker():
        for _ in range(10):
            record_library_change(p, "并发改动", reviewer="人审(并发测试)")

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["version"] == 80                 # 8线程×10次·一次不丢
    assert len(data["change_log"]) == 80         # 每次调用都留了痕
    assert [e["version"] for e in data["change_log"]] == list(range(1, 81))


def test_record_library_change_atomic_write_no_tmp_leftover(tmp_path):
    p = _lib(tmp_path)
    record_library_change(p, "改动", reviewer="人审")
    assert not (tmp_path / "lib.json.tmp").exists()  # temp+rename·不留半截临时文件
