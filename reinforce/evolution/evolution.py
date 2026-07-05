"""盲拆收敛 + 护城河进化 —— 攒够 N 份拆 deck → 跨 deck 收敛 → 提案 → 人审。

对应 Novel reinforce/evolution.py。只产 pending 提案，人审拍板才落地（承重墙·铁律7）。
证据门槛：单份撞到不采纳（≥2 份才提案·防偏样本污染）。

decks_since 计数落盘于 COUNTER（2026-07-01 接入）：此前 evolution_due 是纯函数，decks_since 靠人读
research_lib/真实样本/README.md 台账手数，chaideck 从未真调用过这套函数——现在给它配一个真计数器，
chaideck 每拆完一份调 record_deck_torn_down()，Step0 查护城河调 load_decks_since() 喂 evolution_due()。
"""

from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path

from reinforce.evolution._locked_io import atomic_write_json, locked

ROOT = Path(os.environ.get("PPT_DIR", str(Path(__file__).resolve().parent.parent.parent)))
COUNTER = ROOT / "specs" / "PPT方法论" / "_护城河计数.json"

N_TRIGGER = 30  # 攒够 N 份 deck 跑一轮护城河优化（D2：N 未来主要来自客户产出回灌）


def evolution_due(decks_since: int) -> dict:
    """查护城河优化是否到期。"""
    return {"due": decks_since >= N_TRIGGER, "decks_since": decks_since,
            "n_trigger": N_TRIGGER, "remaining": max(0, N_TRIGGER - decks_since)}


def load_decks_since(path: str | Path | None = None) -> int:
    """读当前计数（自上次护城河收敛以来拆了几份）。文件不存在 → 0（还没拆过/刚收敛完）。"""
    f = Path(path) if path else COUNTER
    if not f.is_file():
        return 0
    try:
        return int(json.loads(f.read_text(encoding="utf-8")).get("decks_since", 0))
    except Exception:
        return 0


def record_deck_torn_down(path: str | Path | None = None) -> int:
    """chaideck 每拆完一份 deck（Step3 入库时）调用一次：计数 +1、落盘，返回新值。

    并发锁 + 原子写走同包 `_locked_io`（2026-07-03 二轮扫盘批D：此前自带一套"锁数据文件本身+
    原地 truncate 写"——锁语义解决了 2026-07-01 实测 98% 丢失，但写非原子：进程写到一半死掉留
    半截 JSON；且与 methodology/versioning/knowledge_ingest 三兄弟的 locked+atomic_write_json
    模式漂移成两套。统一改造：锁 .lock 旁文件包住读-改-写临界区，temp+rename 原子落盘）。
    """
    f = Path(path) if path else COUNTER
    with locked(f):
        n = load_decks_since(f) + 1
        atomic_write_json({"decks_since": n}, f)
    return n


def reset_decks_since(path: str | Path | None = None) -> None:
    """护城河收敛（Step4）人审通过、真落地后清零，供下一轮重新计数。同一把锁写，
    保证"清零"和"计数+1"两类写操作互相串行，不会撞车覆盖。
    """
    f = Path(path) if path else COUNTER
    with locked(f):
        atomic_write_json({"decks_since": 0}, f)


def converge(findings: list[dict], baseline: set, n_decks: int) -> dict:
    """跨 deck 收敛：findings=[{rule_key, polarity}]。≥2 份撞到才提案（证据门槛）。
    返回 confirmed/added/refuted（全 pending·人审拍板才落地）。"""
    sup, ref = Counter(), Counter()
    for f in findings:
        (sup if f.get("polarity", "support") == "support" else ref)[f["rule_key"]] += 1
    confirmed, added, refuted = [], [], []
    for k, c in sup.items():
        if c < 2:
            continue  # 单份不采纳
        (confirmed if k in baseline else added).append({"rule_key": k, "support": c})
    for k, c in ref.items():
        if c >= 2:
            refuted.append({"rule_key": k, "refute": c})
    return {"confirmed": confirmed, "added": added, "refuted": refuted,
            "n_decks": n_decks, "status": "pending_人审"}
