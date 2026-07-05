"""范本库版本追踪 —— exemplars/*.json 三库（页型卡库/表达手法卡/分析框架库）的 version/change_log
门禁（承重墙·铁律7）。

缺口对照：范本卡库此前谁都能直接改 JSON、无版本号、无修改留痕，跟"承重墙改写须证据门槛+人确认+
版本化"名实不符（reinforce/data/conformance.json L7 记录的缺口·2026-07-01 补此机制）。

不是给每张卡单独加版本（101+127+88 张卡逐条版本化过重），是给库文件本身的顶层 version + change_log
两个字段——每次改动（chaideck 入库/人工改卡）记一笔：谁改的、改了什么、为什么。日期不由本函数生成
（核心不碰系统时钟·同 run_storyline_gate 的 current_year 原则），要留痕就把日期写进 reviewer/description
文本里，同 _可信值台账.json 的既有惯例。
"""

from __future__ import annotations

import json
from pathlib import Path

from reinforce.evolution._locked_io import atomic_write_json, locked


def record_library_change(path: str | Path, description: str, reviewer: str,
                           *, card_count: int | None = None) -> dict:
    """给一个范本库 JSON 文件的顶层 version 加一、追加一条 change_log。返回新增的这条记录。

    承重墙：reviewer 必填（人审才落地·铁律7）。调用时机：chaideck Step3 入库/回填后，
    或任何手动改动 cards 数组之后——不调用就没有版本痕迹，等于白加了这个字段。
    """
    if not reviewer or not reviewer.strip():
        raise ValueError("record_library_change 拒写：reviewer 不能为空（承重墙·铁律7·人审才落地）")
    f = Path(path)
    # 2026-07-02 saopan扫盘揪出：自身也是裸 read-modify-write——两个并发调用各读到同一 version，
    # 后写者覆盖前写者的 change_log 条目（留痕机制自己丢留痕）。锁包临界区 + 原子写落盘。
    with locked(f):
        if not f.is_file():
            raise ValueError(f"record_library_change 拒写：范本库文件不存在（{f}）——"
                              f"要记录改动的库文件本身得先存在，不是本函数负责新建")
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise ValueError(f"record_library_change 拒写：范本库文件 JSON 损坏无法解析（{f}）——{e}") from e
        new_version = int(data.get("version", 0)) + 1
        entry = {"version": new_version, "reviewer": reviewer, "change": description}
        if card_count is not None:
            entry["card_count"] = card_count
        data.setdefault("change_log", []).append(entry)
        data["version"] = new_version
        atomic_write_json(data, f)
    return entry


def current_version(path: str | Path) -> int:
    """读一个范本库 JSON 文件当前的 version（无此字段 → 0，说明还没经过 record_library_change）。"""
    f = Path(path)
    if not f.is_file():
        return 0
    try:
        return int(json.loads(f.read_text(encoding="utf-8")).get("version", 0))
    except Exception:
        return 0


def cards_changed_without_version_bump(old_data: dict, new_data: dict,
                                        *, content_key: str = "cards") -> bool:
    """给 git pre-commit 钩子用的纯判断逻辑（无 I/O·独立可测·同 .githooks/pre-commit 配套）：
    内容主体变了但 version 没跟着涨 → True（该拦，说明绕开了 record_library_change 直接改文件）。
    内容没变、或 version 有跟着涨，都放行。这道函数只判"有没有留痕"，不判"改得对不对"——
    改没改对是内容审查的事，这里只管"改了必须留痕"这一条机械规则。

    content_key（2026-07-02 saopan扫盘 B3-3 泛化）：数据色板的内容主体是 "families"、行业知识库
    是 "facts"，硬编码 "cards" 会让这两个库的留痕校验永远比不出差异。钩子按文件名传对应键。
    ⚠️ 本函数只查 version 数字，是**不完整**的留痕校验——完整校验（含 change_log 必须同步追加）
    用下面 library_change_violations()，钩子已换用后者；本函数保留作兼容与最小判断原语。
    """
    if new_data.get(content_key) == old_data.get(content_key):
        return False
    return new_data.get("version", 0) <= old_data.get("version", 0)


def library_change_violations(old_data: dict, new_data: dict,
                               *, content_key: str = "cards") -> list[str]:
    """完整版留痕校验（纯函数·无 I/O·pre-commit 钩子的核心判断）——返回违规问题列表，空=放行。

    2026-07-02 saopan扫盘揪出：旧钩子只验 version 数字，手改内容 + 手动 version+1（不追加
    change_log 条目）即可放行，"留痕"名存实亡。内容主体（content_key 指向的数组/字典）变了时，
    三件必须同时成立：
      ① version 比旧值涨；
      ② change_log 有新增条目（且旧条目原样保留——历史台账是史实，只可追加不可篡改，
         防"删旧条目再补新条目"伪装成有留痕）；
      ③ 新增条目里最新一条的 version 字段 == 新 version（change_log 条目结构含 version 字段，
         见 record_library_change 写入的 entry——数字对不上说明 log 是手编的不是走函数记的）。
    内容主体没变（如只改 _schema 说明文字）→ 不管，放行。
    """
    if new_data.get(content_key) == old_data.get(content_key):
        return []
    problems: list[str] = []
    old_v, new_v = old_data.get("version", 0), new_data.get("version", 0)
    if new_v <= old_v:
        problems.append(f"{content_key} 内容变了但 version 没跟着涨（{old_v}→{new_v}）")
    old_log = old_data.get("change_log") or []
    new_log = new_data.get("change_log") or []
    if len(new_log) <= len(old_log):
        problems.append(f"{content_key} 内容变了但 change_log 没有新增条目"
                        f"（{len(old_log)}→{len(new_log)} 条）——留痕不能只改 version 数字")
    elif new_log[:len(old_log)] != old_log:
        problems.append("change_log 旧条目被改动/删除——历史台账是史实，只可追加不可篡改")
    else:
        latest = new_log[-1]
        if latest.get("version") != new_v:
            problems.append(f"change_log 最新条目的 version={latest.get('version')!r} "
                            f"与库顶层 version={new_v!r} 不一致——疑似手编 log 而非走 record_library_change")
    return problems
