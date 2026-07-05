"""spec_lock（deck 级设计规范锁定·对应 ppt-master spec_lock.md 机制）测试。"""

from __future__ import annotations

from reinforce.spec_lock import check_against_spec, new_spec_lock, spec_lock_brief, validate_spec_lock


def _spec():
    return new_spec_lock({"bg": "#FFFFFF", "ink": "#111111", "accent": "#E2231A"}, "Arial")


def test_new_spec_lock_defaults_font_grid():
    s = new_spec_lock({"bg": "#FFFFFF"}, "Arial")
    assert s["font_grid"] == [44, 28, 24, 22, 18, 16, 14, 9]
    assert s["hero_size"] == 130  # 焦点数字专用字号也锁死(防早期177px超界漂移重演)


def test_hero_size_overridable():
    assert new_spec_lock({"bg": "#fff"}, "Arial", hero_size=110)["hero_size"] == 110


def test_validate_requires_palette_and_font():
    assert validate_spec_lock(_spec())["valid"]
    assert not validate_spec_lock({"font_family": "Arial"})["valid"]  # 缺 palette
    assert not validate_spec_lock({"palette": {"bg": "#fff"}})["valid"]  # 缺 font_family


def test_spec_lock_brief_contains_palette_and_font():
    brief = spec_lock_brief(_spec())
    assert "#E2231A" in brief and "Arial" in brief and "spec_lock" in brief


def test_check_against_spec_passes_when_colors_match():
    svg = '<svg><rect fill="#FFFFFF"/><text fill="#111111">x</text></svg>'
    assert check_against_spec(svg, _spec()) == []


def test_check_against_spec_catches_rogue_color():
    svg = '<svg><rect fill="#00FF00"/></svg>'  # 不在锁定色板里
    out = check_against_spec(svg, _spec())
    assert any(i["rule"] == "off_spec_color" for i in out)
    assert "#00FF00" in out[0]["note"]


# ── zones / per_page（借鉴 ppt-master executor-base.md·2026-07-01 补，per_page 统一重构·2026-07-01 补）──
def test_zones_default_empty_and_overridable():
    assert new_spec_lock({"bg": "#fff"}, "Arial")["zones"] == {}
    s = new_spec_lock({"bg": "#fff"}, "Arial", zones={"content": {"y": 160, "h": 480}})
    assert s["zones"]["content"]["h"] == 480


def test_spec_lock_brief_includes_zones_when_present():
    s = new_spec_lock({"bg": "#fff"}, "Arial", zones={"header": {"y": 0, "h": 90}})
    assert "header" in spec_lock_brief(s)


def test_spec_lock_brief_without_page_n_omits_page_specific_items():
    s = new_spec_lock({"bg": "#fff"}, "Arial",
                       per_page={1: {"chart": "waterfall_chart", "rhythm": "anchor"}})
    brief = spec_lock_brief(s)  # 不传 page_n
    assert "waterfall_chart" not in brief and "anchor" not in brief


def test_spec_lock_brief_with_page_n_surfaces_chart_and_rhythm():
    s = new_spec_lock({"bg": "#fff"}, "Arial",
                       per_page={1: {"chart": "waterfall_chart", "rhythm": "dense"}})
    brief = spec_lock_brief(s, page_n=1)
    assert "waterfall_chart" in brief and "dense" in brief
    assert "模板供结构不供皮肤" in brief
    assert spec_lock_brief(s, page_n=2) == spec_lock_brief(new_spec_lock({"bg": "#fff"}, "Arial"), page_n=2)


def test_validate_rejects_unknown_rhythm_state():
    s = new_spec_lock({"bg": "#fff"}, "Arial", per_page={1: {"rhythm": "chaotic"}})  # 不在三态枚举内
    v = validate_spec_lock(s)
    assert not v["valid"] and any("rhythm" in i["msg"] for i in v["issues"])


def test_validate_accepts_known_rhythm_states():
    s = new_spec_lock({"bg": "#fff"}, "Arial",
                       per_page={1: {"rhythm": "anchor"}, 2: {"rhythm": "dense"}, 3: {"rhythm": "breathing"}})
    assert validate_spec_lock(s)["valid"]


def test_validate_rejects_incomplete_hero_page():
    s = new_spec_lock({"bg": "#fff"}, "Arial", per_page={1: {"hero": {"hook": "只填了钩子"}}})  # 缺 composition
    v = validate_spec_lock(s)
    assert not v["valid"] and any("hero" in i["msg"] for i in v["issues"])


def test_validate_accepts_complete_hero_page():
    s = new_spec_lock({"bg": "#fff"}, "Arial",
                       per_page={1: {"hero": {"hook": "重返新疆秘境", "composition": "色块分割·左品牌色右留白"}}})
    assert validate_spec_lock(s)["valid"]


def test_spec_lock_brief_with_page_n_surfaces_hero_page():
    s = new_spec_lock({"bg": "#fff"}, "Arial",
                       per_page={1: {"hero": {"hook": "重返新疆秘境", "composition": "色块分割"}}})
    brief = spec_lock_brief(s, page_n=1)
    assert "重返新疆秘境" in brief and "色块分割" in brief and "默认" in brief


# ── 2026-07-02 saopan扫盘修复回归 ─────────────────────────────────────
def test_per_page_survives_json_roundtrip():
    """③🔴4：per_page int 键落盘回读变 str 后逐页锁定曾静默全丢——源头 str 化+查询兼容。"""
    import json
    from reinforce.spec_lock import new_spec_lock, spec_lock_brief, validate_spec_lock
    spec = new_spec_lock(palette={"bg": "#FFFFFF", "ink": "#111111"}, font_family="Arial",
                         per_page={1: {"chart": "waterfall"}})
    spec2 = json.loads(json.dumps(spec))
    assert "waterfall" in spec_lock_brief(spec2, page_n=1)   # 回读后逐页项不丢
    assert validate_spec_lock(spec2)["valid"]
    legacy = {"palette": {"bg": "#FFFFFF"}, "font_family": "Arial",
              "per_page": {2: {"chart": "mekko"}}}           # 修复前落盘的旧 int 键数据
    assert "mekko" in spec_lock_brief(legacy, page_n=2)


def test_check_against_spec_expands_3digit_hex():
    """③🟡：palette 写 #fff 时 6 位用色曾全被误报越板——统一展开成 6 位再比。"""
    from reinforce.spec_lock import check_against_spec
    spec = {"palette": {"bg": "#fff", "ink": "#111"}}
    assert check_against_spec('<rect fill="#FFFFFF"/><text fill="#111111">x</text>', spec) == []
    assert check_against_spec('<rect fill="#abc"/>', {"palette": {"bg": "#AABBCC"}}) == []
    assert check_against_spec('<rect fill="#E2231A"/>', spec)   # 真越板仍报


def test_validate_spec_lock_none_per_page_no_crash():
    from reinforce.spec_lock import validate_spec_lock
    r = validate_spec_lock({"palette": {"bg": "#FFFFFF"}, "font_family": "Arial", "per_page": None})
    assert r["valid"]


# ── D18 FR7.2/7.6 设计契约扩容 ─────────────────────────────────────────
def test_spec_lock_design_contract_fields():
    from reinforce.spec_lock import new_spec_lock, validate_spec_lock, spec_lock_brief
    spec = new_spec_lock(
        palette={"bg": "#FFFFFF", "ink": "#111111", "accent": "#E2231A"}, font_family="Arial",
        visual_style="memphis",
        typography={"body": 16, "title": 32, "footnote": 9, "title_font": "Archivo Black"},
        icons={"library": "lucide", "inventory": ["arrow-right", "target", "users"]},
        images=[{"filename": "kv_mood.png", "purpose": "第9页大Idea氛围", "pattern_id": "#40",
                 "acquire_via": "ai"}],
        image_rendering="flat-illustration", image_palette="warm-pop",
        per_page={9: {"visual_concept": {"core_message": "一句话让董事会记住big idea",
                                          "layout": "图像当画布+标注卡"},
                      "layout": "chapter_divider"}})
    r = validate_spec_lock(spec)
    assert r["valid"], r["issues"]
    b = spec_lock_brief(spec, page_n=9)
    assert "memphis" in b and "title=32" in b and "arrow-right" in b
    assert "凭什么存在" in b and "chapter_divider" in b


def test_spec_lock_contract_validation_catches_half_filled():
    from reinforce.spec_lock import new_spec_lock, validate_spec_lock
    bad = new_spec_lock(palette={"bg": "#FFF"}, font_family="Arial",
                        visual_style="不存在的风格",
                        typography={"title": 32},                      # 缺 body 锚点
                        icons={"library": "lucide", "inventory": []},  # 空清单
                        images=[{"filename": "a.png"}],                # 缺 pattern_id/purpose/acquire_via
                        per_page={2: {"visual_concept": {"layout": "x"}}})  # 缺 core_message
    msgs = " ".join(i["msg"] for i in validate_spec_lock(bad)["issues"])
    assert "不在 18 风格" in msgs and "body 锚点" in msgs and "inventory 为空" in msgs
    assert "pattern_id" in msgs and "core_message" in msgs


def test_spec_lock_old_calls_unbroken():
    from reinforce.spec_lock import new_spec_lock, validate_spec_lock
    spec = new_spec_lock(palette={"bg": "#FFFFFF", "ink": "#111111"}, font_family="Arial")
    assert validate_spec_lock(spec)["valid"]          # 旧调用（不带新参数）零破坏
    assert spec["visual_style"] is None and spec["images"] == []


def test_seed_per_page_from_outline():
    """D18 FR3.4：策略声明的 chart 自动播种进 per_page——已有人工声明不覆盖。"""
    from reinforce.spec_lock import new_spec_lock, seed_per_page_from_outline
    spec = new_spec_lock(palette={"bg": "#FFFFFF", "ink": "#111111"}, font_family="Arial",
                         per_page={2: {"chart": "人工指定的mekko"}})
    outline = {"pages": [{"n": 1, "facets": {"chart": "waterfall"}},
                         {"n": 2, "facets": {"chart": "line_compare"}},
                         {"n": 3, "facets": {}}]}
    seed_per_page_from_outline(spec, outline)
    assert spec["per_page"]["1"]["chart"] == "waterfall"          # 播种
    assert spec["per_page"]["2"]["chart"] == "人工指定的mekko"     # 人工优先不覆盖
    assert "3" not in spec["per_page"]                             # 无 chart 不建空条目


# ---------- D22 视觉配置舱：richness 档 + palette_source 品牌锚定留痕 ----------

def test_richness_and_palette_source_roundtrip():
    from reinforce.spec_lock import new_spec_lock, validate_spec_lock
    s = new_spec_lock({"bg": "#fff", "ink": "#111", "accent": "#00843D"}, "Arial",
                      richness="浓郁",
                      palette_source={"kind": "web_verified", "brand": "某品牌",
                                      "evidence": "https://某品牌.com/brand"})
    assert s["richness"] == "浓郁" and s["palette_source"]["kind"] == "web_verified"
    assert validate_spec_lock(s)["valid"]


def test_richness_bad_value_rejected():
    from reinforce.spec_lock import new_spec_lock, validate_spec_lock
    s = new_spec_lock({"bg": "#fff"}, "Arial", richness="超级花")
    r = validate_spec_lock(s)
    assert not r["valid"] and any("richness" in i["msg"] for i in r["issues"])


def test_palette_source_without_evidence_rejected():
    # 联网查证的品牌色必须带 URL 溯源——无溯源=常识幻觉风险（'某品牌 绿记成蓝'）·D22 fail-closed
    from reinforce.spec_lock import new_spec_lock, validate_spec_lock
    s = new_spec_lock({"bg": "#fff"}, "Arial",
                      palette_source={"kind": "web_verified", "brand": "某品牌"})
    r = validate_spec_lock(s)
    assert not r["valid"] and any("evidence" in i["msg"] for i in r["issues"])


def test_palette_source_neutral_needs_no_evidence():
    from reinforce.spec_lock import new_spec_lock, validate_spec_lock
    s = new_spec_lock({"bg": "#fff"}, "Arial", palette_source={"kind": "neutral"})
    assert validate_spec_lock(s)["valid"]


def test_unlocked_richness_keeps_legacy_behavior():
    # 不填两字段=旧行为零破坏（None 合法·validate 不管"该不该填"）
    from reinforce.spec_lock import new_spec_lock, validate_spec_lock
    s = new_spec_lock({"bg": "#fff"}, "Arial")
    assert s["richness"] is None and s["palette_source"] is None
    assert validate_spec_lock(s)["valid"]


def test_brief_carries_richness_and_brand_anchor():
    # 丰富度档+品牌色板来源必须进每页 prompt 简报——逐页生成时的准绳（强制重读机制）
    from reinforce.spec_lock import new_spec_lock, spec_lock_brief
    s = new_spec_lock({"bg": "#fff", "accent": "#00843D"}, "Arial",
                      richness="浓郁",
                      palette_source={"kind": "web_verified", "brand": "某品牌",
                                      "evidence": "https://某品牌.com/brand"})
    brief = spec_lock_brief(s)
    assert "浓郁" in brief and "禁止退回纯文字卡片" in brief
    assert "某品牌" in brief and "品牌色" in brief


# ── 2026-07-03 saopan批② 校验器免崩三处（fail-closed=记 error issue·不是裸栈）──
def test_validate_non_dict_images_row_is_error_not_crash():
    """🟡4：images 行不是 dict 此前 row.get 裸栈——校验器自己先崩就谈不上拦。"""
    r = validate_spec_lock({"palette": {"bg": "#FFFFFF"}, "font_family": "Arial",
                            "images": ["not-a-dict", {"filename": "a.png", "purpose": "kv",
                                                      "pattern_id": "P1", "acquire_via": "web"}]})
    assert not r["valid"]
    assert any("images[0]" in i["msg"] and i["sev"] == "error" for i in r["issues"])
    # 合法行不受牵连（继续查完其余行·只报坏行）
    assert not any("images[1]" in i["msg"] for i in r["issues"])


def test_validate_non_dict_per_page_value_is_error_not_crash():
    """🟡5：per_page 值不是 dict 此前 p.get 裸栈——记 error issue 继续查其余页。"""
    r = validate_spec_lock({"palette": {"bg": "#FFFFFF"}, "font_family": "Arial",
                            "per_page": {"1": "not-a-dict", "2": {"rhythm": "anchor"}}})
    assert not r["valid"]
    assert any("p1" in i["msg"] and i["sev"] == "error" for i in r["issues"])
    assert not any("p2" in i["msg"] for i in r["issues"])  # 合法页不报


def test_validate_none_palette_value_is_error_not_downstream_crash():
    """🟡6：palette 值 None/非字符串在 validate 就拦——此前能通过校验、滑到 pipeline 的
    check_colorblind_safe 时 _hex_to_rgb(None) 裸栈崩溃。"""
    r = validate_spec_lock({"palette": {"bg": None, "ink": "#111111"}, "font_family": "Arial"})
    assert not r["valid"]
    assert any("palette[bg]" in i["msg"] and i["sev"] == "error" for i in r["issues"])
    r2 = validate_spec_lock({"palette": {"bg": 123}, "font_family": "Arial"})
    assert not r2["valid"]
    # palette 整体不是 dict 也记 error 不崩
    r3 = validate_spec_lock({"palette": "blue", "font_family": "Arial"})
    assert not r3["valid"]
    # 全字符串色值照常通过
    assert validate_spec_lock({"palette": {"bg": "#FFFFFF"}, "font_family": "Arial"})["valid"]


def test_brief_skips_non_dict_zone_and_page_not_crash():
    """🟡5：spec_lock_brief 对 zones 脏值跳过并标注（brief 是拼 prompt 的展示函数，
    不该被脏数据崩掉）；per_page 页值非 dict 容错成无逐页锁定项。"""
    b = spec_lock_brief({"palette": {"bg": "#FFFFFF"}, "font_family": "Arial",
                         "zones": {"header": "oops", "content": {"y": 100, "h": 500}}})
    assert "content(y=100,h=500)" in b          # 合法区照常给
    assert "header" in b and "跳过" in b        # 异常区如实标注
    b2 = spec_lock_brief({"palette": {"bg": "#FFFFFF"}, "font_family": "Arial",
                          "per_page": {"3": "not-a-dict"}}, page_n=3)
    assert "spec_lock 锁定规范" in b2           # 不崩·退化成无逐页锁定项
