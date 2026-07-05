"""evolution 包内共享的「锁 + 原子写」基础件（2026-07-02 saopan扫盘揪出：methodology.py /
knowledge_ingest.py / versioning.py 三处账本类文件全是裸 read-modify-write——无锁并发互相覆盖
（同 evolution.py 计数器当年实测 98% 丢失率的同款病根），且普通 write_text 进程中途死掉会留半截
JSON，下次 fail-open 读直接按空账重建 = 静默清空承重墙数据。

实现照抄 reinforce/deck_memory.py 的 _locked / _atomic_write（复制同款而非 import——deck_memory
是⑤记忆层业务模块，evolution 包 import 它属奇怪的跨层耦合；三个兄弟文件各自内联三份又会漂移，
故收进本包私有基础件一处）：

- 锁**独立 .lock 文件**而非数据文件本身：数据文件用 temp+rename 原子写，rename 会换 inode、
  锁在旧 inode 上会失效；锁一个永不 rename 的 .lock 文件语义干净，两个防护都保住。
- ⚠️ fcntl.flock 在 NFS/网络盘语义不可靠（POSIX 已知限制）——当前单机 Mac 场景无碍。
"""

from __future__ import annotations

import contextlib
import fcntl
import json
from pathlib import Path


@contextlib.contextmanager
def locked(path: str | Path):
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


def atomic_write_json(data: dict, path: str | Path) -> None:
    """temp+rename 原子写：进程中途死掉不会留半截 JSON（半截 JSON + fail-closed 读 = 台账
    彻底锁死只能人工修，半截 + fail-open 读 = 静默清空，都不可接受，从写入侧根治）。"""
    f = Path(path)
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_suffix(f.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(f)
