"""长任务记忆 Memory（⑤）—— 已交付只读锁 published + 交接卡。

对应 Novel publish_status.py + 交接卡(出口=入口的圆)。守铁律4(产出真相源只读)：
已交付 deck 绝不回改，动它前先 assert_editable。独立可测。

并发正确性（D16 🟡①·2026-07-02）：mark_published 是账本类 read-modify-write，与
evolution.py 计数器同款场景（那边实测并发丢失率 98% 后加 fcntl 锁）——这里锁**独立
.lock 文件**而非数据文件本身：数据文件用 temp+rename 原子写（防半截），rename 会换
inode、锁在旧 inode 上会失效，锁一个永不 rename 的 .lock 文件则语义干净，两个防护
都保住。⚠️ fcntl.flock 在 NFS/网络盘语义不可靠（POSIX 已知限制·D16 🧭②）——当前
单机 Mac 场景无碍，workspace 挪上共享盘需换锁方案。

fail-closed 读账本（D16 修复时追加发现）：published.json 存在但解析失败必须 raise
——若照 Novel 版"损坏→空集"，账本读坏等于所有 deck 突然"未交付"、只读锁全体失效，
方向是 fail-open；文件不存在才是正常初始态（空集）。
"""

from __future__ import annotations

import contextlib
import fcntl
import hashlib
import json
from pathlib import Path

SCHEMA_VERSION = 1


def _atomic_write(payload: dict, path: str | Path) -> None:
    """temp+rename 原子写（学 Novel publish_status.py）：进程中途死掉不会留半截 JSON——
    published 登记表是只读锁的真相源，写坏一次 = 所有 deck 的交付状态全部丢失。"""
    f = Path(path)
    tmp = f.with_suffix(f.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(f)


@contextlib.contextmanager
def _locked(path: str | Path):
    """独占锁包住账本 read-modify-write 临界区（锁 <账本>.lock 而非账本本身，理由见模块说明）。"""
    lock = Path(str(path) + ".lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.touch(exist_ok=True)
    with open(lock, "r+", encoding="utf-8") as fh:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)


# ── 已交付只读锁（铁律4）──────────────────────────────────────────────
def _load_ledger(path: str | Path) -> dict:
    """读账本全量 {delivered, checksums, review_gates}。不存在=正常初始态；损坏=raise（fail-closed，
    绝不把'读不懂账本'吞成'账本是空的'——那会让只读锁全体失效）。"""
    f = Path(path)
    if not f.is_file():
        return {"schema_version": SCHEMA_VERSION, "delivered": [], "checksums": {},
                "review_gates": {}}
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except ValueError as e:
        raise ValueError(f"已交付登记表损坏·拒按空账处理（fail-closed·铁律4）：{f} — {e}") from e
    # 2026-07-02 saopan扫盘揪出：上面只兜住 JSON 语法坏，字段**类型**坏是 fail-open——
    # delivered 若被手改成字符串 "deckC"，list() 静默拆成 ['d','e','c','k','C'] →
    # is_published 永远 False → assert_editable 放行已交付 deck。账本在 git 里明文可手编，
    # 类型错和语法错一样都是"读不懂"，同样必须 raise 而不是变形吞掉。
    if not isinstance(data, dict):
        raise ValueError(f"已交付登记表顶层不是对象·拒按空账处理（fail-closed·铁律4）：{f}")
    ver = data.get("schema_version", SCHEMA_VERSION)
    if isinstance(ver, int) and ver > SCHEMA_VERSION:
        raise ValueError(f"登记表 schema_version={ver} 比本代码支持的 {SCHEMA_VERSION} 新·"
                         f"拒读（防旧代码剥掉新版字段·D17 补读侧门）：{f}")
    delivered = data.get("delivered", [])
    checksums = data.get("checksums", {})
    # review_gates（D21 批③·🔴6）：waiver/force 非常规交付的留痕——旧账本无此键=按空处理（兼容，
    # 那时还没有这条审计链）；有键但类型坏与 checksums 同一条 fail-closed 纪律，raise 不吞。
    review_gates = data.get("review_gates", {})
    if not isinstance(delivered, list) or not all(isinstance(x, str) for x in delivered):
        raise ValueError(f"登记表 delivered 字段类型坏（应为字符串列表）·拒按空账处理：{f}")
    if not isinstance(checksums, dict):
        raise ValueError(f"登记表 checksums 字段类型坏（应为对象）·拒按空账处理：{f}")
    if not isinstance(review_gates, dict):
        raise ValueError(f"登记表 review_gates 字段类型坏（应为对象）·拒按空账处理：{f}")
    return {"schema_version": ver, "delivered": list(delivered), "checksums": dict(checksums),
            "review_gates": dict(review_gates)}


def load_published(path: str | Path) -> set:
    return set(_load_ledger(path)["delivered"])


def load_checksums(path: str | Path) -> dict:
    """已交付 deck 的交付物指纹 {deck_id: sha256hex}（登记时未传 checksum 的 deck 不在其中）。"""
    return _load_ledger(path)["checksums"]


def is_published(deck_id: str, path: str | Path) -> bool:
    return deck_id in load_published(path)


def mark_published(deck_id: str, path: str | Path, checksum: str | None = None,
                   review_gate: dict | None = None, *, exclusive: bool = False) -> set:
    """标 deck 已交付（锁为只读真相源）。flock 防并发丢更新 + 原子写防半截。

    checksum：交付物（deck.pptx）的 sha256 指纹，可选——传入则记入账本，供 verify_published
    巡检"文件系统上的已交付产物有没有被绕过 API 直接改"（npm integrity/Maven checksum 同款
    机制·D16 🟢①）。deck_workspace.publish_deck 会自动算并传入，别手拼。

    review_gate（D21 批③·🔴6 审计链落盘）：非常规交付路径的留痕，可选——如
    {"waiver": 直通档根授权原话, "forced": False}。此前 waiver/force 只进 publish_deck 返回值，
    调用方不存返回值留痕就丢了，账本上看不出哪份 deck 没走人审。非 None 才写入：
    **台账语义=review_gates 里有记录即非常规路径**，正常人审交付不写这段。
    deck_workspace.publish_deck 会自动透传，别手拼。

    exclusive（D26 二轮扫盘🔴·并发 TOCTOU 闭环）：True 时**在锁内**检查 deck_id 已登记则
    PermissionError——publish_deck 的"拒重复"预检在锁外，两进程同时 publish 同一 deck_id
    （实测多进程 Barrier 15/15 轮双双"成功"）时后写入者静默覆盖前者的 checksum/审计留痕，
    恰是注释声称要防的"篡改证据被洗白"。锁内检查才是最终裁决，外层预检只管友好报错。
    """
    with _locked(path):
        led = _load_ledger(path)
        if exclusive and deck_id in led["delivered"]:
            raise PermissionError(
                f"deck '{deck_id}' 已登记交付·拒重复登记（锁内裁决·D26 TOCTOU 闭环——"
                f"重登会覆盖登记指纹与审计留痕·铁律4）")
        if deck_id not in led["delivered"]:
            led["delivered"].append(deck_id)
        led["delivered"].sort()
        if checksum:
            led["checksums"][deck_id] = checksum
        if review_gate is not None:
            led.setdefault("review_gates", {})[deck_id] = review_gate
        led["schema_version"] = SCHEMA_VERSION
        _atomic_write(led, path)
        return set(led["delivered"])


def assert_editable(deck_id: str, path: str | Path) -> None:
    """改 deck 前必查：已交付 → 抛 PermissionError（铁律4·防越改越乱）。"""
    if is_published(deck_id, path):
        raise PermissionError(f"deck '{deck_id}' 已交付·只读真相源·拒改（铁律4）")


def file_sha256(path: str | Path) -> str:
    """算文件 sha256（十六进制）。交付物指纹的统一算法。"""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ── 交接卡（长任务记忆·出口=入口的圆）────────────────────────────────
def new_handoff(deck_title: str, current_page: int, todos=None, changes=None, next_steps=None) -> dict:
    return {"schema_version": SCHEMA_VERSION, "deck": deck_title, "current_page": current_page,
            "todos": todos or [], "changes": changes or [], "next_steps": next_steps or []}


def save_handoff(card: dict, path: str | Path) -> None:
    """交接卡落盘。批④补 _locked（对齐同文件 mark_published 的写点纪律）：原子写只防半截，
    不防两个会话同时收尾各写各的交接卡互相覆盖——锁 <文件>.lock 独占临界区，双防护齐。"""
    with _locked(path):
        _atomic_write(card, path)


def load_handoff(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))
