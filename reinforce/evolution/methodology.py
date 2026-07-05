"""方法论可信值台账 —— 规律的 support/refute 计数累积 + confidence。

对应 Novel reinforce/methodology.py。拆 deck 印证(support)/打脸(refute)规律 → 可信值变化。
承重墙：accumulate 必带 reviewer（人审拍板才落地·铁律7），绝不 LLM 自动改方法论。
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from reinforce.evolution._locked_io import atomic_write_json, locked

ROOT = Path(os.environ.get("PPT_DIR", str(Path(__file__).resolve().parent.parent.parent)))
LEDGER = ROOT / "specs" / "PPT方法论" / "_可信值台账.json"


def load_ledger(path: str | Path | None = None) -> dict:
    """读可信值台账。文件不存在=正常初始态（空账）；**存在但解析失败必须 raise**——
    2026-07-02 saopan扫盘揪出：此前损坏 JSON 被吞成空默认，下一次 accumulate 就以空账重建、
    静默清空全部 support/refute 计数（承重墙数据·方法论从「强候选」升「铁律」的证据链）。
    deck_memory.py 自己立的纪律（账本读坏必 raise 绝不按空账）当时没推行到这里。"""
    f = Path(path) if path else LEDGER
    if not f.is_file():
        return {}
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except ValueError as e:
        raise ValueError(f"可信值台账损坏·拒按空账处理（fail-closed·承重墙）：{f} — {e}") from e
    # 2026-07-03 二轮扫盘批D：语法坏兜住了，**类型**坏仍 fail-open——顶层被手改成列表/字符串，
    # accumulate 的 `k not in led`/`led[k]` 要么 TypeError 要么静默错位（同包 knowledge_ingest.
    # _load_json 的 D25 口径：顶层不是对象必 raise）。
    if not isinstance(data, dict):
        raise ValueError(f"可信值台账顶层不是对象（JSON object）·拒按空账处理"
                         f"（fail-closed·承重墙·同包 _load_json 口径）：{f}")
    return data


def confidence(rule: dict) -> float:
    """support/(support+refute)·无证据=0。"""
    s, r = rule.get("support", 0), rule.get("refute", 0)
    return round(s / (s + r), 3) if (s + r) else 0.0


def accumulate(evidence: dict, path: str | Path | None = None, reviewer: str = "人审") -> dict:
    """evidence={rule_key:{support,refute,rule_text}} → 累积台账。返回 {new,promoted,demoted}。
    承重墙：reviewer 必填（人审才落地）。"""
    if not reviewer or not reviewer.strip():
        raise ValueError("accumulate 拒写：reviewer 不能为空（承重墙·铁律7·人审才落地）")
    f = Path(path) if path else LEDGER
    # 2026-07-02 saopan扫盘揪出：此前裸 read-modify-write 无并发锁（同 evolution.py 计数器
    # 实测 98% 丢失率的同款场景）+ 普通写非原子——锁包住整个临界区、temp+rename 落盘。
    with locked(f):
        led = load_ledger(f)
        rep = {"new": [], "promoted": [], "demoted": []}
        for k, ev in evidence.items():
            if k not in led:
                led[k] = {"support": 0, "refute": 0, "rule_text": ev.get("rule_text", ""), "reviewer": reviewer}
                rep["new"].append(k)
            led[k]["support"] += ev.get("support", 0)
            led[k]["refute"] += ev.get("refute", 0)
            led[k]["confidence"] = confidence(led[k])
            if ev.get("refute", 0) > ev.get("support", 0):
                rep["demoted"].append(k)
            elif ev.get("support", 0):
                rep["promoted"].append(k)
        atomic_write_json(led, f)
    return rep
