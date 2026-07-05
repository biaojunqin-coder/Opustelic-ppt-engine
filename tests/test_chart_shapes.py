"""高 stakes 图表几何引擎测试——waterfall/Gantt/Mekko 坐标必须手算验证过，不能只测"不崩"。"""

from __future__ import annotations

import re

import pytest

from engine.chart_shapes import gantt_chart, mekko_chart, mekko_intervals, waterfall_chart, waterfall_intervals
from reinforce.deck_rules.svg_compat import check_svg_compat


def _rects(svg: str) -> list[dict]:
    """从 SVG 片段抽所有 rect 的几何属性（回归测试共用）。"""
    out = []
    for m in re.finditer(r'<rect x="([-\d.]+)" y="([-\d.]+)" width="([-\d.]+)" height="([-\d.]+)"', svg):
        out.append({"x": float(m.group(1)), "y": float(m.group(2)),
                    "w": float(m.group(3)), "h": float(m.group(4))})
    return out

WATERFALL_ITEMS = [
    {"label": "Q1收入", "value": 100, "measure": "total"},
    {"label": "新客增量", "value": 30, "measure": "relative"},
    {"label": "流失", "value": -15, "measure": "relative"},
    {"label": "Q2收入", "value": 115, "measure": "total"},
]


def test_waterfall_intervals_hand_verified():
    seq = waterfall_intervals(WATERFALL_ITEMS)
    # item0 total=100：base=0,top=100，累计level=100
    assert seq[0]["base"] == 0 and seq[0]["top"] == 100 and seq[0]["kind"] == "total" and seq[0]["level"] == 100
    # item1 +30：从累计100起浮空到130
    assert seq[1]["base"] == 100 and seq[1]["top"] == 130 and seq[1]["kind"] == "up" and seq[1]["level"] == 130
    # item2 -15：从130降到115，区间取min/max后 base=115,top=130
    assert seq[2]["base"] == 115 and seq[2]["top"] == 130 and seq[2]["kind"] == "down" and seq[2]["level"] == 115
    # item3 total=115：重置到 base=0,top=115
    assert seq[3]["base"] == 0 and seq[3]["top"] == 115 and seq[3]["kind"] == "total" and seq[3]["level"] == 115


def test_waterfall_intervals_all_relative_never_goes_negative_base_incorrectly():
    items = [{"label": "起点", "value": 50, "measure": "total"},
             {"label": "大跌", "value": -80, "measure": "relative"}]
    seq = waterfall_intervals(items)
    # 50 - 80 = -30，区间应为 base=-30, top=50（min/max 正确处理负值穿零）
    assert seq[1]["base"] == -30 and seq[1]["top"] == 50 and seq[1]["kind"] == "down"


def test_waterfall_chart_bar_count_and_colors():
    svg = waterfall_chart(0, 0, 400, 200, WATERFALL_ITEMS)
    assert svg.count("<rect") == 4  # 4 项各一根柱
    assert "#10B981" in svg  # 默认涨色
    assert "#F43F5E" in svg  # 默认跌色
    assert "#1E293B" in svg  # 默认总计色
    assert svg.count("stroke-dasharray") == 3  # n-1 条桥接虚线


def test_waterfall_chart_custom_colors_override_defaults():
    svg = waterfall_chart(0, 0, 400, 200, WATERFALL_ITEMS, colors={"up": "#FF0000"})
    assert "#FF0000" in svg
    assert "#10B981" not in svg  # 默认涨色被覆盖，不该再出现


def test_waterfall_chart_empty_items_no_crash():
    assert waterfall_chart(0, 0, 400, 200, []) == "<g/>"


def test_waterfall_chart_passes_svg_compat_gate():
    svg = f'<svg viewBox="0 0 400 200">{waterfall_chart(0, 0, 400, 200, WATERFALL_ITEMS)}</svg>'
    issues = check_svg_compat(svg)
    assert not any(i["sev"] == "error" for i in issues)


# ── B2-1 回归（2026-07-02 saopan扫盘）：负值瀑布旧版只用 max 归一，柱子画出画布（y=556/height=540）──
NEGATIVE_WATERFALL = [
    {"label": "A", "value": 100, "measure": "relative"},
    {"label": "B", "value": -180, "measure": "relative"},
    {"label": "合计", "value": -80, "measure": "total"},
]


def test_waterfall_negative_values_all_rects_inside_canvas():
    # 值域 [-80,100]·h=300：A 柱 [0,100]→y=0,h=166.7；B 柱 [-80,100]→y=0,h=300；合计 [-80,0]→y=166.7,h=133.3
    svg = waterfall_chart(0, 0, 400, 300, NEGATIVE_WATERFALL)
    rects = _rects(svg)
    assert len(rects) == 3
    for r in rects:
        assert r["y"] >= -0.5, f"柱顶画出画布上沿：{r}"
        assert r["y"] + r["h"] <= 300 + 0.5, f"柱底画出画布下沿：{r}"
    # 手算锁两根：B 柱满高 300；合计柱 y=300*100/180≈166.7、h≈133.3
    assert any(abs(r["h"] - 300) < 0.5 for r in rects)
    assert any(abs(r["y"] - 166.7) < 0.5 and abs(r["h"] - 133.3) < 0.5 for r in rects)


def test_waterfall_negative_values_draw_zero_axis_dashline():
    svg = waterfall_chart(0, 0, 400, 300, NEGATIVE_WATERFALL)
    # 零轴虚线（2,2）+ 桥接虚线（3,3）×2 —— 零轴在 py(0)=300*(100-0)/180≈166.7
    assert 'stroke-dasharray="2,2"' in svg
    assert 'y1="166.7"' in svg


def test_waterfall_negative_total_label_sits_by_bar_not_zero_axis():
    """2026-07-03 二轮扫盘批D：负值 total 的标签此前按 top_px-8 定位——top 是零轴，标签飘在
    零轴上方、离柱体值端一整根柱子远。修后贴柱底（对照 down 柱行为：bot_px+16）。"""
    svg = waterfall_chart(0, 0, 400, 300, NEGATIVE_WATERFALL)
    # 合计柱（total=-80·display 缺省=str(value)）：柱体 y∈[166.7, 300]（见上方负值画布测试手算）
    m = re.search(r'<text x="\d+" y="(-?\d+)"[^>]*font-weight="bold"[^>]*>-80<', svg)
    assert m, "找不到合计柱的数值标签"
    label_y = float(m.group(1))
    # 旧行为 label_y=158（零轴 166.7 上方·柱顶）；新行为=316（柱底 300 下方 16px·柱体旁）
    assert 300 <= label_y <= 320, f"负 total 标签应贴柱底（约316），实际 {label_y}"


def test_waterfall_positive_total_label_still_above_bar_top():
    """负 total 修复不动正 total 行为：标签仍在柱顶上方 8px。"""
    svg = waterfall_chart(0, 0, 400, 200, WATERFALL_ITEMS)
    # Q1收入 total=100·值域 vmax=130：柱顶 py(100)=200*30/130≈46.2 → 标签 y=46.2-8≈38
    m = re.search(r'<text x="\d+" y="(-?\d+)"[^>]*font-weight="bold"[^>]*>100<', svg)
    assert m, "找不到 Q1 total 柱的数值标签"
    assert 36 <= float(m.group(1)) <= 40


def test_waterfall_pure_positive_geometry_identical_to_legacy_formula():
    # 纯正值时 vmin=0，py(v)=y+h*(vmax-v)/vmax ≡ 旧式 y+h*(1-v/vmax)——语义零变化、不画零轴线
    svg = waterfall_chart(0, 0, 400, 200, WATERFALL_ITEMS)
    assert 'stroke-dasharray="2,2"' not in svg
    rects = _rects(svg)
    # item1 区间 [100,130]·vmax=130：top_px=200*(130-130)/130=0，h=200*30/130≈46.2（旧公式同值）
    assert any(abs(r["y"] - 0.0) < 0.05 and abs(r["h"] - 46.2) < 0.1 for r in rects)


GANTT_TASKS = [
    {"label": "调研", "start": "2026-01-01", "end": "2026-01-11", "progress": 1.0},
    {"label": "开发", "start": "2026-01-11", "end": "2026-01-21", "progress": 0.5},
    {"label": "上线", "start": "2026-01-21", "end": "2026-01-21"},  # start==end → 里程碑
]


def test_gantt_chart_positions_hand_verified():
    # 全局区间 2026-01-01 ~ 2026-01-21，共20天；w=200 → col_width=10px/天
    svg = gantt_chart(0, 0, 200, 300, GANTT_TASKS, header_height=0, row_gap=0, bar_height=20)
    # 任务0 从第0天开始 → x=0；任务1 从第10天开始 → x=100
    assert 'x="0.0"' in svg
    assert 'x="100.0"' in svg
    # 任务0 工期10天×10px=100px 宽
    assert 'width="100.0"' in svg


def test_gantt_chart_milestone_is_diamond_not_rect():
    svg = gantt_chart(0, 0, 200, 300, GANTT_TASKS)
    assert "<polygon" in svg  # 里程碑用菱形，不是矩形


def test_gantt_chart_dependencies_produce_marker_and_arrow():
    svg = gantt_chart(0, 0, 200, 300, GANTT_TASKS, dependencies=[{"from": 0, "to": 1}, {"from": 1, "to": 2}])
    assert "<marker" in svg and "marker-end" in svg
    assert svg.count("marker-end=") == 2  # 两条依赖各一条折线箭头（<path 计数会多算marker内部的箭头三角形）


def test_gantt_chart_no_dependencies_omits_marker_defs():
    svg = gantt_chart(0, 0, 200, 300, GANTT_TASKS)
    assert "<defs" not in svg and "<marker" not in svg


def test_gantt_chart_today_line():
    svg = gantt_chart(0, 0, 200, 300, GANTT_TASKS, today="2026-01-11")
    assert svg.count("stroke-dasharray") >= 1


def test_gantt_chart_passes_svg_compat_gate():
    svg = f'<svg viewBox="0 0 400 300">{gantt_chart(0, 0, 400, 300, GANTT_TASKS, dependencies=[{"from": 0, "to": 1}])}</svg>'
    issues = check_svg_compat(svg)
    assert not any(i["sev"] == "error" for i in issues)


# ── B2-3 回归（2026-07-02 saopan扫盘）：旧版收了 h 却通篇不用，任务一多静默画出画布底 ──
def _many_tasks(n: int) -> list[dict]:
    return [{"label": f"任务{i}", "start": f"2026-01-{i + 1:02d}", "end": f"2026-01-{i + 2:02d}"}
            for i in range(n)]


def test_gantt_too_many_tasks_for_canvas_raises_not_overflows():
    # 10 行任务塞 h=200（默认表头24）需把标签字号缩穿 9px 可读下限 → fail-closed 明确 raise
    with pytest.raises(ValueError, match="画布高度不够"):
        gantt_chart(0, 0, 400, 200, _many_tasks(10))


def test_gantt_moderate_overflow_shrinks_rows_to_fit():
    # 5 行任务·h=204·表头24 → 可用180/行距需求200 → shrink=0.9：条高25.2、字号10，全部元素≤画布底
    svg = gantt_chart(0, 0, 400, 204, _many_tasks(5), today="2026-01-03")
    for r in _rects(svg):
        assert r["y"] + r["h"] <= 204 + 0.5, f"任务条溢出画布：{r}"
    for m in re.finditer(r'<line [^>]*y2="([\d.]+)"', svg):
        assert float(m.group(1)) <= 204 + 0.5  # TODAY 竖线也不越底
    assert 'font-size="10"' in svg  # 字号按 shrink 同缩（11×0.9≈10）·不是硬写 11


def test_gantt_geometry_unchanged_when_space_is_enough():
    # 空间足够时 shrink=1·行距/条高/字号跟旧版逐像素一致（bar_height+row_gap=20·第2行 y=20）
    svg = gantt_chart(0, 0, 200, 300, GANTT_TASKS, header_height=0, row_gap=0, bar_height=20)
    assert 'y="20.0"' in svg and 'font-size="11"' in svg


def test_gantt_zero_available_height_raises():
    with pytest.raises(ValueError, match="无剩余空间"):
        gantt_chart(0, 0, 400, 24, GANTT_TASKS, header_height=24)


# ── D19 FR5.2 回归（第二轮实测·059 p35）：首行任务从 day0 附近开始时，D18 的"放不下退回
# 图表左缘"= 标签正好压在自己的色条上（「福州(试点)」(96,231) 落在 rect(80,214,208x28) 内）──

def _texts(svg: str) -> list[dict]:
    """从 SVG 片段抽所有 text 的锚点与内容（FR5.2 遮挡断言共用）。"""
    out = []
    for m in re.finditer(r'<text x="(-?[\d.]+)" y="(-?[\d.]+)"[^>]*>([^<]*)</text>', svg):
        out.append({"x": float(m.group(1)), "y": float(m.group(2)), "s": m.group(3)})
    return out


# 059 p35 真实形态还原：五城巡演甘特·首行「福州(试点)」从全局最早日开工（左侧净空 0）
P35_TASKS = [
    {"label": "福州(试点)", "start": "2026-03-01", "end": "2026-03-27", "progress": 0.0},
    {"label": "厦门", "start": "2026-03-29", "end": "2026-04-24"},
    {"label": "莆田", "start": "2026-04-26", "end": "2026-05-22"},
    {"label": "泉州", "start": "2026-05-24", "end": "2026-06-19"},
    {"label": "有福市集", "start": "2026-06-21", "end": "2026-06-21"},  # 收官里程碑
]


def test_gantt_p35_first_row_label_anchor_not_inside_any_bar():
    # 059 p35 同款调用形态（x=80·表头默认24·首行 day0 开工）——文字锚点不得落进任何色条 rect
    svg = gantt_chart(80, 190, 1120, 300, P35_TASKS)
    rects = _rects(svg)
    assert rects, "至少该有 4 根任务条"
    for t in _texts(svg):
        for r in rects:
            inside = (r["x"] <= t["x"] <= r["x"] + r["w"]
                      and r["y"] <= t["y"] <= r["y"] + r["h"])
            assert not inside, f"标签「{t['s']}」锚点 ({t['x']},{t['y']}) 落在色条 {r} 内（D19 FR5.2 回归）"


def test_gantt_p35_first_row_label_goes_above_bar_column_aligned():
    svg = gantt_chart(80, 190, 1120, 300, P35_TASKS)
    label = next(t for t in _texts(svg) if "福州" in t["s"])
    # 首行条顶 = 190+24(默认表头) = 214 → 基线在条顶上方 4px = 210；x 同列对齐条左缘 80
    assert abs(label["y"] - 210) <= 1, f"标签基线应在条顶上方 4px：{label}"
    assert abs(label["x"] - 80) <= 1, f"标签应与色条左缘同列对齐：{label}"


def test_gantt_p35_later_rows_keep_d18_left_of_bar_behavior():
    # 非首行（左侧净空够）照旧 D18 行为：anchor=end 紧贴色条左缘·基线垂直居中
    svg = gantt_chart(80, 190, 1120, 300, P35_TASKS)
    xiamen = next(t for t in _texts(svg) if t["s"] == "厦门")
    row1_top = 190 + 24 + 1 * 40  # 第二行条顶（bar 28 + gap 12）
    assert abs(xiamen["y"] - (row1_top + 14 + 11 * 0.35 - 0.5)) <= 1.5  # 垂直居中(int截断±1)
    assert 'text-anchor="end"' in svg


def test_gantt_thin_header_fallback_label_inside_bar_inverse():
    # 极薄表头（header_height=0 < 字高11+4）·首行 day0：上方放不下 → 条内左端反白兜底
    tasks = [{"label": "调研", "start": "2026-01-01", "end": "2026-01-11"},
             {"label": "开发", "start": "2026-01-11", "end": "2026-01-21"}]
    svg = gantt_chart(0, 0, 200, 300, tasks, header_height=0, row_gap=0, bar_height=20)
    label = next(t for t in _texts(svg) if t["s"] == "调研")
    assert label["x"] == 8 and 0 <= label["y"] <= 20        # 条内左端·垂直居中（不越画布顶）
    assert 'fill="#FFFFFF"' in svg                           # 反白（默认 label_on_bar）


def test_gantt_thin_header_milestone_fallback_right_of_diamond():
    # 极薄表头·首行 day0 是里程碑：菱形中心盛不下字 → 放右尖外侧（不反白·右侧是空白区）
    tasks = [{"label": "启动", "start": "2026-01-01", "end": "2026-01-01"},
             {"label": "开发", "start": "2026-01-01", "end": "2026-01-21"}]
    svg = gantt_chart(0, 0, 200, 300, tasks, header_height=0, row_gap=0, bar_height=20)
    label = next(t for t in _texts(svg) if t["s"] == "启动")
    assert label["x"] == 18                                  # bx(0)+菱形半宽(10)+间距(8)
    assert label["x"] > 10                                   # 在菱形右尖(x=10)之外


def test_gantt_p35_shape_passes_svg_compat_gate():
    svg = f'<svg viewBox="0 0 1280 720">{gantt_chart(80, 190, 1120, 300, P35_TASKS)}</svg>'
    issues = check_svg_compat(svg)
    assert not any(i["sev"] == "error" for i in issues)


MEKKO_COLUMNS = [
    {"label": "华东", "weight": 60, "segments": [{"label": "品牌A", "share": 0.6}, {"label": "品牌B", "share": 0.4}]},
    {"label": "华南", "weight": 40, "segments": [{"label": "品牌A", "share": 0.3}, {"label": "品牌B", "share": 0.7}]},
]


def test_mekko_intervals_column_width_proportional_to_weight():
    seq = mekko_intervals(MEKKO_COLUMNS)
    # weight 60/40 → 列宽占比 0.6/0.4
    assert seq[0]["left"] == 0 and abs(seq[0]["width"] - 0.6) < 1e-9
    assert abs(seq[1]["left"] - 0.6) < 1e-9 and abs(seq[1]["width"] - 0.4) < 1e-9


def test_mekko_intervals_segments_stack_to_full_column():
    seq = mekko_intervals(MEKKO_COLUMNS)
    segs = seq[0]["segments"]
    assert segs[0]["base"] == 0 and abs(segs[0]["top"] - 0.6) < 1e-9
    assert abs(segs[1]["base"] - 0.6) < 1e-9 and abs(segs[1]["top"] - 1.0) < 1e-9


def test_mekko_chart_rect_widths_reflect_weight_ratio():
    svg = mekko_chart(0, 0, 1000, 400, MEKKO_COLUMNS)
    widths = [float(w) for w in re.findall(r'width="([\d.]+)"', svg)]
    # 华东两段矩形宽度应等于华南两段（同列同宽），且华东列宽(≈600-gap)明显大于华南列(≈400-gap)
    assert widths[0] == widths[1]  # 华东列内两段同宽
    assert widths[2] == widths[3]  # 华南列内两段同宽
    assert widths[0] > widths[2]  # 华东weight更大，列更宽


def test_mekko_chart_passes_svg_compat_gate():
    svg = f'<svg viewBox="0 0 1000 400">{mekko_chart(0, 0, 1000, 400, MEKKO_COLUMNS)}</svg>'
    issues = check_svg_compat(svg)
    assert not any(i["sev"] == "error" for i in issues)


# ── B2-2 回归（2026-07-02 saopan扫盘）：share 不归一化，传百分数（60/40）rect y 算到 -29700 ──
def _mekko_cols_with_shares(a: float, b: float) -> list[dict]:
    return [{"label": "华东", "weight": 60,
             "segments": [{"label": "品牌A", "share": a}, {"label": "品牌B", "share": b}]},
            {"label": "华南", "weight": 40,
             "segments": [{"label": "品牌A", "share": a / 2}, {"label": "品牌B", "share": b / 2}]}]


def test_mekko_percent_shares_output_identical_to_fraction_shares():
    # d3 stackOffsetExpand 的机制就是按列总和归一——60/40、0.6/0.4、绝对值 600/400 三种写法必须同图
    svg_frac = mekko_chart(0, 0, 1000, 400, _mekko_cols_with_shares(0.6, 0.4))
    svg_pct = mekko_chart(0, 0, 1000, 400, _mekko_cols_with_shares(60, 40))
    svg_abs = mekko_chart(0, 0, 1000, 400, _mekko_cols_with_shares(600, 400))
    assert svg_frac == svg_pct == svg_abs


def test_mekko_percent_shares_all_rects_inside_canvas():
    svg = mekko_chart(0, 0, 1000, 400, _mekko_cols_with_shares(60, 40))
    rects = _rects(svg)
    assert rects, "至少该有 4 段矩形"
    for r in rects:
        assert r["y"] >= -0.5 and r["y"] + r["h"] <= 400 + 0.5, f"段矩形画出画布：{r}"


def test_mekko_zero_share_sum_raises_business_error():
    cols = [{"label": "空列", "weight": 50, "segments": [{"label": "x", "share": 0}, {"label": "y", "share": 0}]}]
    with pytest.raises(ValueError, match="share 总和为 0"):
        mekko_intervals(cols)


def test_mekko_negative_share_raises():
    cols = [{"label": "怪列", "weight": 50, "segments": [{"label": "x", "share": -0.2}, {"label": "y", "share": 1.2}]}]
    with pytest.raises(ValueError, match="负 share"):
        mekko_intervals(cols)


# ── 2026-07-03 二轮扫盘批B回归 ──────────────────────────────────────────────
def test_mekko_negative_weight_raises_not_draws_off_canvas():
    """批B-1：负 weight 此前无校验——列宽/left 变负、矩形画出画布（与"百分数 Mekko 坐标爆炸"
    同根因换字段）。对照负 share 校验同风格直接拒。"""
    cols = [{"label": "怪列", "weight": -20,
             "segments": [{"label": "x", "share": 0.6}, {"label": "y", "share": 0.4}]},
            {"label": "正常列", "weight": 60,
             "segments": [{"label": "x", "share": 0.5}, {"label": "y", "share": 0.5}]}]
    with pytest.raises(ValueError, match="负 weight"):
        mekko_intervals(cols)
    with pytest.raises(ValueError, match="负 weight"):
        mekko_chart(0, 0, 1000, 400, cols)


def test_mekko_positive_weights_not_regressed_by_weight_guard():
    """批B-1 护栏：正数 weight 走原路径，几何输出与既有手算基线一致。"""
    seq = mekko_intervals(MEKKO_COLUMNS)
    assert seq[0]["left"] == 0 and abs(seq[0]["width"] - 0.6) < 1e-9
    assert abs(seq[1]["left"] - 0.6) < 1e-9 and abs(seq[1]["width"] - 0.4) < 1e-9


def test_gantt_dependency_index_out_of_range_raises_readable_valueerror():
    """批B-2：dependencies 索引越界此前裸抛 IndexError（负索引还被 Python 负下标静默绕回
    末尾任务·画出指错对象的箭头）——改为带任务数/合法区间的可读 ValueError。"""
    with pytest.raises(ValueError, match=r"dependencies\[0\]=\(0,99\) 越界·任务共3个"):
        gantt_chart(0, 0, 200, 300, GANTT_TASKS, dependencies=[{"from": 0, "to": 99}])
    with pytest.raises(ValueError, match=r"dependencies\[1\]=\(-1,1\) 越界"):
        gantt_chart(0, 0, 200, 300, GANTT_TASKS,
                    dependencies=[{"from": 0, "to": 1}, {"from": -1, "to": 1}])


def test_gantt_valid_dependencies_not_regressed_by_bounds_guard():
    """批B-2 护栏：合法索引（含首尾边界 0 与 n-1）照常画箭头。"""
    svg = gantt_chart(0, 0, 200, 300, GANTT_TASKS, dependencies=[{"from": 0, "to": 2}])
    assert "marker-end" in svg
