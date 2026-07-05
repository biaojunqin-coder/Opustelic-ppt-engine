"""数据色板测试（open-color 裁剪资产·2026-07-01·D6 决策记录🟢采纳）。"""

from __future__ import annotations

from reinforce.data_palette import load_data_palette, suggest_series_colors


def test_load_data_palette_has_eleven_families_six_shades_each():
    data = load_data_palette()
    assert len(data) == 11
    assert "cyan" not in data  # 麦肯锡明令废弃·裁剪时剔掉
    assert "gray" not in data and "white" not in data and "black" not in data  # 那是 ink/bg 管的·不是数据色
    for fam, shades in data.items():
        assert len(shades) == 6, f"{fam} 应有6档"
        assert all(s.startswith("#") and len(s) == 7 for s in shades)


def test_load_data_palette_missing_file_returns_empty(tmp_path):
    assert load_data_palette(tmp_path / "不存在.json") == {}


def test_suggest_series_colors_returns_n_distinct_hues():
    colors = suggest_series_colors(5)
    assert len(colors) == 5 and len(set(colors)) == 5  # 5个系列5个不同色·跨色相取区分度最好


def test_suggest_series_colors_zero_or_negative_returns_empty():
    assert suggest_series_colors(0) == [] and suggest_series_colors(-1) == []


def test_suggest_series_colors_respects_families_filter():
    colors = suggest_series_colors(2, families=["blue", "orange"])
    data = load_data_palette()
    assert colors == [data["blue"][2], data["orange"][2]]


def test_suggest_series_colors_more_than_families_cycles_deeper_shade():
    # 只给1个色相·要7个系列 → 第2轮同色相换更深档(不是简单重复同一个颜色)
    colors = suggest_series_colors(7, families=["blue"])
    assert len(colors) == 7
    assert colors[0] != colors[6]  # 第1个跟第7个用不同深浅档·不是硬重复


def test_suggest_series_colors_unknown_family_ignored():
    colors = suggest_series_colors(1, families=["不存在的色相", "blue"])
    data = load_data_palette()
    assert colors == [data["blue"][2]]
