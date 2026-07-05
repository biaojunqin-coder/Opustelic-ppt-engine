"""高 stakes 图表几何引擎——waterfall / Gantt / Mekko 的坐标计算 + SVG 矩形拼装。

来源：`specs/PPT方法论/06_高stakes难图实现.md`（d3/echarts/plotly/highcharts/frappe-gantt 四源互证的
算法，带出处行号）。这三种图表没有任何库能原生产可编辑 pptx——是"咨询级 vs 通用 PPT"的护城河。
但坐标本身是纯算术（区间/累加/占比），跟 svg_layout.py 的字号缩放算法同一类：必须写成确定性函数，
不能让 LLM 逐页手算再自己肉眼查（制作工作流 SKILL 旧纪律"图表几何手算…易出几何 bug，生成后
render 自检"——这层就是把那道手算风险摘掉，改成调用算对的函数）。

跟 svg_layout.py 同一层级：函数只画图表本体（一个 `<g>`），标题/action title/来源引用由调用页自己拼。
颜色默认值取自 `engine/ppt_master/templates/charts/{waterfall_chart,gantt_chart}.svg` 真实模板，
可传 colors 覆盖——按 spec_lock「模板供结构不供皮肤」纪律，正式生成时必须传当次锁定色板，
不能把这里的默认色当成成品颜色直接出。
"""

from __future__ import annotations

from datetime import date

from engine.svg_layout import text_block
from reinforce.data_palette import suggest_series_colors

_WATERFALL_DEFAULT_COLORS = {"up": "#10B981", "down": "#F43F5E", "total": "#1E293B"}
_GANTT_DEFAULT_COLORS = {"bar": "#1E293B", "progress": "#10B981", "milestone": "#F43F5E",
                          "today": "#94A3B8", "grid": "#E2E8F0",
                          # D18 FR3.6：行标签色入 colors dict（默认=修复前的硬编码值）——
                          # 正式 deck 按 spec_lock 色板传 "label" 覆盖，跟其余键同一纪律
                          "label": "#374151",
                          # D19 FR5.2：极薄表头兜底分支的条内反白标签色（正式 deck 按
                          # spec_lock 色板传 "label_on_bar" 覆盖·须与 bar 色对比度够）
                          "label_on_bar": "#FFFFFF"}
# Mekko 默认多系列色取自 reinforce/data_palette.py（open-color 裁剪·跨色相区分度好），
# 色板资产缺失时兜底一组硬编码色（fail-closed·图表不能因为配色资产没读到就直接崩）。
_MEKKO_FALLBACK_PALETTE = ["#1E293B", "#10B981", "#F43F5E", "#3B82F6", "#F59E0B", "#8B5CF6"]
_MEKKO_DEFAULT_PALETTE = suggest_series_colors(8) or _MEKKO_FALLBACK_PALETTE


# ============================== Waterfall 瀑布图 ==============================

def waterfall_intervals(items: list[dict]) -> list[dict]:
    """瀑布区间计算（纯算术·无 SVG）。

    出处【plotly calc.js:42-99】：measure 数组（"relative"增量 / "total"或"absolute"总计）+
    滚动 previousSum 累加——调用方只填每段增量/总计，这里自动算出每根柱子的浮空区间。

    items: [{"label": str, "value": float, "measure": "relative"|"total"|"absolute", "display": str?}]
    返回每项附加 base/top（值域区间·base<=top）、kind（up/down/total，供上色）、
    level（本项处理完后的累计值·画桥接线用）。
    """
    out = []
    running = 0.0
    for it in items:
        measure = it.get("measure", "relative")
        value = it["value"]
        if measure in ("total", "absolute"):
            base, top = 0.0, value
            kind = "total"
            running = value
        else:
            base = running
            top = running + value
            kind = "up" if value >= 0 else "down"
            running = top
        out.append({**it, "base": min(base, top), "top": max(base, top), "kind": kind, "level": running})
    return out


def waterfall_chart(x: float, y: float, w: float, h: float, items: list[dict], *,
                     colors: dict | None = None, bar_gap_ratio: float = 0.02) -> str:
    """瀑布图 SVG 片段（矩形拼 + 桥接虚线）。items 同 `waterfall_intervals`。

    x/y/w/h = 图表本体画布区（不含标题/来源，那些调用页自己拼）。
    colors：{"up":.., "down":.., "total":..}，缺省用真实模板同款；正式 deck 必须按 spec_lock 传入
    当次锁定色板（模板供结构不供皮肤）。
    """
    colors = {**_WATERFALL_DEFAULT_COLORS, **(colors or {})}
    seq = waterfall_intervals(items)
    n = len(seq)
    if n == 0:
        return "<g/>"
    # 2026-07-02 saopan扫盘揪出：旧版只用 max 归一（py=y+h*(1-v/vmax)），负值区间（base/top<0）
    # 会算出 y>画布底、height 超画布——plotly calc.js 原版本身处理负值，移植时把值域下界截掉了。
    # 修法：值域取 [vmin, vmax]（各自向 0 收口，保证零轴一定在值域内），py 按双端线性映射。
    vmin = min(0.0, min(it["base"] for it in seq))
    vmax = max(0.0, max(it["top"] for it in seq))
    if vmax == vmin:  # 全零数据防除零（每根柱子靠 bh 的 1px 下限兜底仍可见）
        vmax = vmin + 1.0
    gap = w * bar_gap_ratio if n > 1 else 0.0
    bar_w = (w - gap * (n - 1)) / n

    def py(v: float) -> float:
        return y + h * (vmax - v) / (vmax - vmin)

    parts = []
    if vmin < 0:  # 有负值时零轴基线落在画布内部——画条浅色虚线当参照（纯正值时零轴=底边，不画）
        zero_y = py(0.0)
        parts.append(f'<line x1="{x:.1f}" y1="{zero_y:.1f}" x2="{x + w:.1f}" y2="{zero_y:.1f}" '
                      f'stroke="#94A3B8" stroke-width="1" stroke-dasharray="2,2"/>')
    for i, it in enumerate(seq):
        bx = x + i * (bar_w + gap)
        top_px, bot_px = py(it["top"]), py(it["base"])
        bh = max(bot_px - top_px, 1.0)
        color = colors[it["kind"]]
        parts.append(f'<rect x="{bx:.1f}" y="{top_px:.1f}" width="{bar_w:.1f}" height="{bh:.1f}" fill="{color}"/>')
        label = it.get("display", str(it["value"]))
        # 2026-07-03 二轮扫盘批D：负值 total（base<0·top==0）此前按"非 down"走 top_px-8——top 是零轴，
        # 标签飘在零轴上方、离柱体值端（柱底）整根柱子远。标签应贴柱体的**值端**：正 total 值端=顶
        # （零轴上方·top_px-8 不变），负 total 值端=底（对照 down 柱行为·bot_px+16）。
        below = it["kind"] == "down" or (it["kind"] == "total" and it["base"] < 0)
        label_y = (bot_px + 16) if below else (top_px - 8)
        parts.append(text_block(int(bx), int(label_y), label, 12, max(int(bar_w // 7), 6), fill=color, weight="bold"))
        parts.append(text_block(int(bx), int(y + h + 16), it["label"], 11, max(int(bar_w // 6), 6), fill="#6B7280"))
    for i in range(n - 1):
        conn_y = py(seq[i]["level"])
        x1 = x + i * (bar_w + gap) + bar_w
        x2 = x1 + gap
        parts.append(f'<line x1="{x1:.1f}" y1="{conn_y:.1f}" x2="{x2:.1f}" y2="{conn_y:.1f}" '
                      f'stroke="#CBD5E1" stroke-width="1" stroke-dasharray="3,3"/>')
    return f'<g>{"".join(parts)}</g>'


# ============================== Gantt 甘特图 ==============================

def _to_date(d) -> date:
    return d if isinstance(d, date) else date.fromisoformat(str(d))


def gantt_chart(x: float, y: float, w: float, h: float, tasks: list[dict], *,
                 colors: dict | None = None, bar_height: float = 28, row_gap: float = 12,
                 header_height: float = 24, today=None, dependencies: list[dict] | None = None) -> str:
    """甘特图 SVG 片段（任务条 + 里程碑菱形 + 可选依赖箭头 + 可选 TODAY 虚线）。

    出处【frappe-gantt bar.js:592-596,72,622-627】：
    X = (任务start − 全局最早start)/每格天数×每格宽；宽 = 工期格数×每格宽；
    Y = 表头高 + 行号×(条高+行距)。这里把"每格天数"简化成"整个时间轴按总天数线性铺满 w"
    （比 frappe-gantt 固定格宽更适配"图表本体宽度已由 spec_lock zones 定好"的场景）。

    ⚠️ 里程碑菱形（start==end）+ 依赖箭头，frappe-gantt 本身**没有**，是这里的差异化补全——
    正是把 Gantt 做成"咨询级"的差异点（见 06 号方法论文档）。

    tasks: [{"label": str, "start": date|"YYYY-MM-DD", "end": date|"YYYY-MM-DD", "progress": float(0..1)?}]
    dependencies: [{"from": task_idx, "to": task_idx}]（可选·画直角弯箭头，箭头会转成原生 DrawingML 线端，
        非位图）。today: date|"YYYY-MM-DD"（可选·画 TODAY 虚线）。

    bar_height/row_gap 语义：**期望值上限**——任务数少、画布够高时按原值画（跟旧版逐像素一致）；
    塞不下时整体按比例缩（行距/条高/字号同缩），缩到标签字号低于 9px 可读下限则 raise（fail-closed，
    绝不静默溢出/静默缩没）。

    行标签定位（D18 FR3.6 + D19 FR5.2）三级策略：① 色条左侧放得下 → 紧贴左缘右对齐；
    ② 放不下（色条起点在图表左缘附近·059 p35 首行遮挡实锤）→ **色条上方**同列左对齐
    （选"上方"不选"条内反白"：反白在短条/里程碑上不成立且锚点仍压条，上方可几何自证零遮挡）；
    ③ 表头薄到上方也放不下（默认表头 24px 不触发）→ 条内左端反白（colors["label_on_bar"]）/
    里程碑放右尖外侧。详见函数体 D19 FR5.2 注释。
    """
    colors = {**_GANTT_DEFAULT_COLORS, **(colors or {})}
    parsed = [{"label": t["label"], "start": _to_date(t["start"]), "end": _to_date(t["end"]),
               "progress": t.get("progress")} for t in tasks]
    n = len(parsed)
    if n == 0:
        return "<g/>"
    # 2026-07-02 saopan扫盘揪出：旧版收了 h 参数但通篇没用它——行距恒等于 bar_height+row_gap，
    # 任务一多就静默画出画布底（调用方按 spec_lock zones 给的 h 完全形同虚设）。
    # 修法：行距取 min(期望行距, (h-header_height)/n)，超出时条高/字号按同比例缩；
    # 字号缩穿 9px 可读下限直接 raise（宁 raise 也不出一张没人看得清的废图）。
    if h - header_height <= 0:
        raise ValueError(f"gantt_chart 画布高度 h={h} 扣除表头 {header_height} 后无剩余空间——调大 h 或减小 header_height")
    requested_stride = bar_height + row_gap
    shrink = min(1.0, ((h - header_height) / n) / requested_stride)
    stride = requested_stride * shrink
    bar_h = bar_height * shrink
    label_size = 11 if shrink >= 1.0 else int(11 * shrink + 0.5)
    if label_size < 9:
        raise ValueError(
            f"gantt_chart 画布高度不够：{n} 个任务塞进 h={h}（表头 {header_height}）需把标签字号缩到 "
            f"{label_size}px（<9px 可读下限）——请调大画布高度、减少任务数或减小 bar_height/row_gap")
    global_start = min(t["start"] for t in parsed)
    global_end = max(t["end"] for t in parsed)
    total_days = max((global_end - global_start).days, 1)
    col_width = w / total_days

    def px(d: date) -> float:
        return x + (d - global_start).days * col_width

    parts = [f'<line x1="{x:.1f}" y1="{y + header_height:.1f}" x2="{x + w:.1f}" y2="{y + header_height:.1f}" '
             f'stroke="{colors["grid"]}" stroke-width="1"/>']
    bar_positions = []  # (x_start_px, x_end_px, row_y, bar_height) —— 依赖箭头锚点用
    label_gap = 8.0  # D18 FR3.6：标签紧贴色条左侧的固定水平间距
    for i, t in enumerate(parsed):
        row_y = y + header_height + i * stride
        bx = px(t["start"])
        # ── D18 FR3.6 行标签定位修复：旧版恒画在图表左缘 x 上方（row_y-6）——实测病：色条起点
        # 在时间轴中后段（x=400+）时标签跟自己的色条水平脱节；且首行 row_y-6 会画出画布顶。
        # 修法：y 垂直居中跟随本行色条；x 优先紧贴色条左侧（text-anchor=end 右对齐·右缘距条
        # 视觉左缘恒 =label_gap·里程碑菱形左尖比 bx 多伸出半个条高，一并计入）。
        # 宽度估算口径：CJK 全宽≈字号、其余≈0.62 字号（只用于"放得下吗"的分支判断，非精排）。
        #
        # ── D19 FR5.2 首行遮挡修复：D18 的"放不下退回图表左缘"在色条起点就在左缘附近时，
        # 标签正好压在自己的色条上（059 p35 实锤：「福州(试点)」(96,231) 落在 rect(80,214,
        # 208x28) 内·首行任务从 day0 开始 → 左侧净空 0）。修法选「色条上方」而非「条内左端
        # 反白」：反白在短条上放不下、对里程碑菱形无"条内"可言，且锚点仍落在色条 rect 内没法
        # 几何自证零遮挡；上方放置（x 同列对齐色条左缘·基线 y=条顶-4）锚点必然在条外。
        # 默认表头 24px ≥ 字高 11+4 的净空需求，首行放上方即落在表头区、不越画布顶；
        # 极薄表头（header_height < label_size+4·默认参数不触发）放不上去时兜底：
        # rect 条→条内左端反白（colors["label_on_bar"]·059 手工补救同款），
        # 里程碑→菱形右尖外侧（菱形中心盛不下字·右侧是空白时间轴区）。──
        label_y = int(row_y + bar_h / 2 + label_size * 0.35)  # 基线近似垂直居中
        left_edge = bx - bar_h / 2 if t["start"] == t["end"] else bx  # 色条/菱形的视觉左缘
        est_w = label_size * sum(1.0 if ord(ch) > 0x2E7F else 0.62 for ch in t["label"])
        if left_edge - x >= est_w + label_gap:
            parts.append(text_block(int(left_edge - label_gap), label_y, t["label"], label_size, 28,
                                     fill=colors["label"], anchor="end"))
        elif row_y - y >= label_size + 4:
            # D19 FR5.2 主修复：色条上方·同列左对齐（里程碑左尖越出图表左缘时夹回 x）
            parts.append(text_block(max(int(left_edge), int(x)), int(row_y - 4), t["label"],
                                     label_size, 28, fill=colors["label"]))
        elif t["start"] == t["end"]:
            # D19 FR5.2 兜底（极薄表头·里程碑）：菱形右尖外侧
            parts.append(text_block(int(bx + bar_h / 2 + label_gap), label_y, t["label"],
                                     label_size, 28, fill=colors["label"]))
        else:
            # D19 FR5.2 兜底（极薄表头·任务条）：条内左端反白
            parts.append(text_block(int(bx + label_gap), label_y, t["label"], label_size, 28,
                                     fill=colors["label_on_bar"], weight="bold"))
        if t["start"] == t["end"]:
            cx, cy, r = bx, row_y + bar_h / 2, bar_h / 2
            pts = f"{cx:.1f},{cy - r:.1f} {cx + r:.1f},{cy:.1f} {cx:.1f},{cy + r:.1f} {cx - r:.1f},{cy:.1f}"
            parts.append(f'<polygon points="{pts}" fill="{colors["milestone"]}"/>')
            bar_positions.append((bx, bx, row_y, bar_h))
        else:
            bw = max((t["end"] - t["start"]).days * col_width, 4.0)
            parts.append(f'<rect x="{bx:.1f}" y="{row_y:.1f}" width="{bw:.1f}" height="{bar_h:.1f}" '
                          f'rx="4" fill="{colors["bar"]}"/>')
            if t["progress"] is not None:
                pw = bw * max(0.0, min(1.0, t["progress"]))
                parts.append(f'<rect x="{bx:.1f}" y="{row_y:.1f}" width="{pw:.1f}" height="{bar_h:.1f}" '
                              f'rx="4" fill="{colors["progress"]}"/>')
            bar_positions.append((bx, bx + bw, row_y, bar_h))
    if today is not None:
        tx = px(_to_date(today))
        bottom = y + header_height + n * stride
        parts.append(f'<line x1="{tx:.1f}" y1="{y:.1f}" x2="{tx:.1f}" y2="{bottom:.1f}" '
                      f'stroke="{colors["today"]}" stroke-width="1.5" stroke-dasharray="4,3"/>')
    marker_def = ""
    if dependencies:
        marker_def = ('<defs><marker id="ganttDepArrow" markerWidth="8" markerHeight="8" refX="6" refY="3" '
                       'orient="auto" markerUnits="userSpaceOnUse"><path d="M0,0 L6,3 L0,6 Z" fill="#94A3B8"/>'
                       '</marker></defs>')
        for k, dep in enumerate(dependencies):
            i, j = dep["from"], dep["to"]
            # 2026-07-03 二轮扫盘揪出：索引越界此前裸抛 IndexError（负索引还会被 Python 负下标
            # 静默绕回到末尾任务·画出一条指错对象的箭头）——改成带可读信息的 ValueError。
            if not (0 <= i < n) or not (0 <= j < n):
                raise ValueError(f"gantt_chart dependencies[{k}]=({i},{j}) 越界·任务共{n}个"
                                 f"（合法索引 0..{n - 1}，负索引不接受），请检查依赖数据")
            x1, y1c = bar_positions[i][1], bar_positions[i][2] + bar_positions[i][3] / 2
            x2, y2c = bar_positions[j][0], bar_positions[j][2] + bar_positions[j][3] / 2
            midx = (x1 + x2) / 2
            parts.append(f'<path d="M{x1:.1f},{y1c:.1f} L{midx:.1f},{y1c:.1f} L{midx:.1f},{y2c:.1f} '
                          f'L{x2:.1f},{y2c:.1f}" fill="none" stroke="#94A3B8" stroke-width="1.5" '
                          f'marker-end="url(#ganttDepArrow)"/>')
    return f'<g>{marker_def}{"".join(parts)}</g>'


# ============================== Mekko / Marimekko ==============================

def mekko_intervals(columns: list[dict]) -> list[dict]:
    """Mekko 区间计算（纯算术·无 SVG）。

    出处【highcharts variwide】：列宽 = relZ[i]/totalZ×轴长（按各列 weight 占比铺满整轴）；
    列内再按 share 占比堆叠（出处【d3 stackOffsetExpand】100% 堆叠——它的机制就是按列总和归一化，
    输入是 0.6/0.4、60/40 还是绝对值都天然正确）。
    columns: [{"label": str, "weight": float, "segments": [{"label": str, "share": float, "color": str?}]}]
    返回每列附加 left/width（0..1 相对坐标），每 segment 附加 base/top（0..1 相对坐标）。
    """
    # 2026-07-03 二轮扫盘揪出：负 weight 无校验——列宽=weight/总和，负值让 col_w/left 变负，
    # 负宽度/负坐标矩形直接画出画布（与"百分数 Mekko 坐标爆炸"同根因、换了个字段）。
    # 变宽柱的列宽在 Mekko 语义里不能为负，对照下方负 share 校验同风格直接拒。
    for c in columns:
        if c["weight"] < 0:
            raise ValueError(f"Mekko 列「{c.get('label')}」存在负 weight——列宽按 weight 占比铺满轴，不能为负，请检查数据")
    total_w = sum(c["weight"] for c in columns) or 1.0
    out = []
    left = 0.0
    for c in columns:
        # 2026-07-02 saopan扫盘揪出：旧版直接拿 share 当 0..1 累加、不归一不校验——share 传百分数
        # （60/40）时 top 累到 100，rect y 算到画布外几万 px。docstring 引的 d3 stackOffsetExpand
        # 机制本来就是"按列总和归一化"，移植时把归一那步丢了。负 share 在 100% 堆叠里无意义，直接拒。
        shares = [seg["share"] for seg in c["segments"]]
        if any(s < 0 for s in shares):
            raise ValueError(f"Mekko 列「{c.get('label')}」存在负 share——100% 堆叠图的份额不能为负，请检查数据")
        share_sum = sum(shares)
        if share_sum <= 0:
            raise ValueError(f"Mekko 列「{c.get('label')}」share 总和为 0——无法按占比堆叠，请检查该列 segments 数据")
        col_w = c["weight"] / total_w
        top = 0.0
        seg_out = []
        for seg in c["segments"]:
            base = top
            top = top + seg["share"] / share_sum
            seg_out.append({**seg, "base": base, "top": top})
        out.append({"label": c["label"], "left": left, "width": col_w, "segments": seg_out})
        left += col_w
    return out


def mekko_chart(x: float, y: float, w: float, h: float, columns: list[dict], *,
                 colors: list[str] | None = None, col_gap_ratio: float = 0.015) -> str:
    """Mekko 图 SVG 片段（变宽堆叠柱）。columns 同 `mekko_intervals`。

    三大高 stakes 图表里唯一连模板起点都没有的（71 张 ppt-master 图表模板 grep 零命中）——
    这是纯自研，没有第二个选项（见 06 号方法论文档）。colors：按 segment 顺序循环取色的调色板，
    单个 segment 可传 "color" 字段覆盖；正式 deck 必须按 spec_lock 锁定色板传入。
    """
    palette = colors or _MEKKO_DEFAULT_PALETTE
    seq = mekko_intervals(columns)
    gap = w * col_gap_ratio
    parts = []
    for col in seq:
        cx = x + col["left"] * w
        cw = max(col["width"] * w - gap, 1.0)
        for i, seg in enumerate(col["segments"]):
            seg_top_px = y + h * (1 - seg["top"])
            seg_bot_px = y + h * (1 - seg["base"])
            sh = max(seg_bot_px - seg_top_px, 1.0)
            color = seg.get("color") or palette[i % len(palette)]
            parts.append(f'<rect x="{cx:.1f}" y="{seg_top_px:.1f}" width="{cw:.1f}" height="{sh:.1f}" fill="{color}"/>')
            if seg.get("label") and sh > 16:
                parts.append(text_block(int(cx + 4), int(seg_top_px + sh / 2 + 4), seg["label"], 10,
                                         max(int(cw // 7), 6), fill="#FFFFFF"))
        parts.append(text_block(int(cx), int(y + h + 16), col["label"], 11, max(int(cw // 6), 6), fill="#6B7280"))
    return f'<g>{"".join(parts)}</g>'
