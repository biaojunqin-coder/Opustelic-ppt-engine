"""数据色板——图表多系列/图例配色资产（2026-07-01·open-color 价值评估🟢采纳·D6 决策记录）。

来源：`exemplars/数据色板.json`（open-color v1.9.1 裁剪·剔 cyan+留 index3-8 共 6 档，详见该文件 `_来源`）。
补的是这个真实空缺——`reinforce/spec_lock.py` 的 `palette` 字段此前只有 schema 占位符
（`{bg, ink, accent, grey}` 键名），没有任何具体色值：图表多系列配色（如 Mekko 3+ 列/ waterfall 图例）
之前完全靠临场发挥。这里只管"给一组好看且跨色相区分度够的候选色"，不管"这份 deck 该不该用这些色"——
主色/语义/纪律仍走麦肯锡规范（NAVY 主色 + 强调四色 + 一个高亮其余灰），正式 deck 生成时数据色仍需
按当次 spec_lock 锁定色板确认（"模板供结构不供皮肤"同一条纪律，这里的默认值只是候选，不是成品）。
"""

from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(os.environ.get("PPT_DIR", str(Path(__file__).resolve().parent.parent)))
PALETTE_FILE = ROOT / "exemplars" / "数据色板.json"


def load_data_palette(path: str | Path | None = None) -> dict:
    """读数据色板.json 的 families 字典（缺/坏 → {}·fail-closed 不崩调用方）。"""
    p = Path(path) if path else PALETTE_FILE
    if not p.is_file():
        return {}
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return d.get("families", {}) if isinstance(d, dict) else {}


def suggest_series_colors(n: int, *, families: list[str] | None = None, shade_index: int = 2) -> list[str]:
    """给 n 个图表系列建议候选色——优先跨色相取（每系列不同色相，区分度最好），
    n 超过可用色相数时才在同色相内换深浅档继续补（每轮 shade_index 往深处挪 2 档，封顶最深档 index5）。

    families：限定只用哪些色相（如已知这份 deck 忌某色相），缺省用 `数据色板.json` 里全部 11 个色相。
    shade_index：起始档位(0-5·对应 index3-8)，缺省 2(约"600"档·饱和但不过分刺眼，一般场景够用)。
    n<=0 或色板文件缺失/无可用色相 → 返回 []。
    """
    if n <= 0:
        return []
    data = load_data_palette()
    fam_list = [f for f in (families or list(data.keys())) if f in data]
    if not fam_list:
        return []
    out: list[str] = []
    round_idx = 0
    while len(out) < n and round_idx <= 6:  # 防御性熔断·正常情况每轮必产出 len(fam_list) 个不会触顶
        shade = min(shade_index + round_idx * 2, 5)
        for fam in fam_list:
            if len(out) >= n:
                break
            out.append(data[fam][shade])
        round_idx += 1
    return out
