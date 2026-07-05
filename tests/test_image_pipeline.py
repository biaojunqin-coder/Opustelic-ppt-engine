"""image_pipeline（D18 FR7.4/FR4.2/FR4.3）单测——六源分发/BYO key/降级/风格词段/实测尺寸。

网络纪律：单测绝不真联网——web 路径 monkeypatch vendor 的 search_and_download，
ai 路径 monkeypatch _http_post_json/_http_get_bytes 两个 seam。四库真调验证是
开发期一次性人工动作（结果记在开发实录/交付报告），不进测试。
"""

from __future__ import annotations

import base64
import json
import types

import pytest

from engine import image_pipeline as ip

# load_image_api_keys 的全部 env 候选——测试逐个清干净，防开发机真实 key 污染断言
_ALL_KEY_ENVS = ("IMAGE_GEN_API_KEY", "IMAGE_GEN_BASE_URL", "OPENROUTER_API_KEY",
                 "GEMINI_API_KEY", "VOLCENGINE_API_KEY", "ARK_API_KEY", "BFL_API_KEY")


def _clear_key_envs(monkeypatch):
    for name in _ALL_KEY_ENVS:
        monkeypatch.delenv(name, raising=False)


def _row(**over) -> dict:
    base = {"filename": "hero.png", "purpose": "beer festival atmosphere",
            "pattern_id": "#38", "acquire_via": "web"}
    base.update(over)
    return base


# ═══════════════ 主分发：坏行 fail-closed / 四个轻量源 ═══════════════

def test_acquire_missing_filename_raises(tmp_path):
    with pytest.raises(ValueError, match="filename"):
        ip.acquire_image({"acquire_via": "web"}, tmp_path)


def test_acquire_unknown_via_raises(tmp_path):
    with pytest.raises(ValueError, match="acquire_via"):
        ip.acquire_image(_row(acquire_via="magic"), tmp_path)


def test_acquire_user_pending(tmp_path):
    r = ip.acquire_image(_row(acquire_via="user"), tmp_path)
    assert r["status"] == "pending_user" and r["path"] is None
    assert "hero.png" in r["note"]                      # 标注要指名道姓·人一眼知道缺哪张


def test_acquire_placeholder_ok_without_path(tmp_path):
    """placeholder 的获取诉求就是"画占位框"——status=ok 但 path=None 是正常形态（注释锁定）。"""
    r = ip.acquire_image(_row(acquire_via="placeholder"), tmp_path)
    assert r["status"] == "ok" and r["path"] is None and "占位" in r["note"]


@pytest.mark.parametrize("via", ["formula", "slice"])
def test_acquire_formula_slice_not_implemented(tmp_path, via):
    """二期源诚实标注 not_implemented（铁律 2 防假绿：没做就说没做）。"""
    r = ip.acquire_image(_row(acquire_via=via), tmp_path)
    assert r["status"] == "not_implemented" and via in r["note"]


def test_all_statuses_in_contract(tmp_path):
    """返回 status 必须落在统一契约枚举内（下游按枚举分流）。"""
    for via in ("user", "placeholder", "formula", "slice"):
        assert ip.acquire_image(_row(acquire_via=via), tmp_path)["status"] in ip.ACQUIRE_STATUSES


# ═══════════════ FR4.2：BYO key 配置读取 ═══════════════

def test_load_keys_none_when_unconfigured(tmp_path, monkeypatch):
    """无 env 无文件 → None（=用户未开启生图·合法状态·FR4.2 默认不依赖生图）。"""
    _clear_key_envs(monkeypatch)
    assert ip.load_image_api_keys(tmp_path) is None


def test_load_keys_aggregator_env_first(tmp_path, monkeypatch):
    _clear_key_envs(monkeypatch)
    monkeypatch.setenv("IMAGE_GEN_API_KEY", "sk-agg")
    monkeypatch.setenv("IMAGE_GEN_BASE_URL", "https://agg.example/v1")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or")   # 通用 key 必须压过 provider 专属
    keys = ip.load_image_api_keys(tmp_path)
    assert keys == {"api_key": "sk-agg", "base_url": "https://agg.example/v1",
                    "models": {}, "source": "env:IMAGE_GEN_API_KEY"}


def test_load_keys_provider_env_with_default_url(tmp_path, monkeypatch):
    _clear_key_envs(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or")
    keys = ip.load_image_api_keys(tmp_path)
    assert keys["api_key"] == "sk-or" and keys["source"] == "env:OPENROUTER_API_KEY"
    assert keys["base_url"] == "https://openrouter.ai/api/v1"   # OpenRouter 自带默认地址


def test_load_keys_from_project_file(tmp_path, monkeypatch):
    _clear_key_envs(monkeypatch)
    (tmp_path / ip.KEY_FILE_NAME).write_text(json.dumps(
        {"api_key": "sk-file", "base_url": "https://proxy.cn/v1",
         "models": {"default": "google/gemini-3-pro-image-preview"}}), encoding="utf-8")
    keys = ip.load_image_api_keys(tmp_path)
    assert keys["api_key"] == "sk-file" and keys["source"] == f"file:{ip.KEY_FILE_NAME}"
    assert keys["models"]["default"] == "google/gemini-3-pro-image-preview"


def test_load_keys_broken_file_fails_closed(tmp_path, monkeypatch):
    """key 文件存在但坏 JSON → raise（想配但配坏了≠没配·静默 None 会假降级）。"""
    _clear_key_envs(monkeypatch)
    (tmp_path / ip.KEY_FILE_NAME).write_text("{broken", encoding="utf-8")
    with pytest.raises(ValueError, match="JSON"):
        ip.load_image_api_keys(tmp_path)


def test_key_file_is_gitignored():
    """FR4.2 承重墙：.image_keys.json 必须在 .gitignore 里——key 绝不入库。"""
    gi = (ip._PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ip.KEY_FILE_NAME in gi.splitlines()


# ═══════════════ FR4.3：模型路由 / prompt 分层拼装 / 风格词段 ═══════════════

def test_select_model_default_nano_banana():
    assert ip.select_gen_model(_row(intent="craft beer glass close-up")) == ip.GEN_MODEL_DEFAULT


def test_select_model_cjk_routes_seedream():
    assert ip.select_gen_model(_row(intent="春节庙会热闹氛围")) == ip.GEN_MODEL_CJK


def test_select_model_brand_hex_routes_flux():
    # intent 出现 hex 色值 = 品牌色严苛场景（hex 直出）
    assert ip.select_gen_model(_row(intent="brand pattern in #00563F")) == ip.GEN_MODEL_BRAND_HEX
    # 显式行级开关同样生效
    assert ip.select_gen_model(_row(intent="pattern", brand_color_strict=True)) == ip.GEN_MODEL_BRAND_HEX


def test_select_model_override_wins():
    got = ip.select_gen_model(_row(intent="x"), models_override={"default": "vendor/custom-id"})
    assert got == "vendor/custom-id"


def test_load_rendering_prompt_flat():
    """真文件读取（不 mock——references 是仓库内静态资产）。"""
    seg = ip.load_rendering_prompt("flat")
    assert "flat design" in seg.lower() and len(seg) > 100   # §1 Style paragraph 抽出来了
    assert not seg.startswith("#")                            # 不是整个 md 文件


def test_load_palette_prompt_cool_corporate():
    seg = ip.load_palette_prompt("cool-corporate")
    assert "color behavior" in seg.lower()                    # 抽的是色彩行为词段
    assert "[..." not in seg                                  # fewshot 占位符清干净


def test_load_style_unknown_name_lists_available():
    with pytest.raises(ValueError, match="vector-illustration"):
        ip.load_rendering_prompt("no-such-style")
    with pytest.raises(ValueError, match="mono-ink"):
        ip.load_palette_prompt("no-such-palette")
    with pytest.raises(ValueError, match="不合法"):
        ip.load_rendering_prompt("../escape")                 # 路径穿越拦死


def test_build_prompt_layers_and_no_text_clause():
    """分层拼装：行级主体 + rendering 段 + palette 段 + 无字铁律（顺序即层次）。"""
    p = ip.build_image_prompt(_row(intent="beer festival crowd, warm light"),
                              rendering="flat", palette="cool-corporate")
    i_subject = p.index("beer festival crowd")
    i_render = p.lower().index("flat design")
    i_palette = p.lower().index("color behavior")
    i_notext = p.index("NO text")
    assert i_subject < i_render < i_palette < i_notext
    assert "NO logos" in p and "NO watermarks" in p           # FR4.3 无字底图工程铁律


def test_build_prompt_without_subject_raises():
    with pytest.raises(ValueError, match="intent/purpose"):
        ip.build_image_prompt({"filename": "x.png", "intent": "", "purpose": ""})


# ═══════════════ FR4.2/§六：ai 路径降级（绝不 raise） ═══════════════

def test_acquire_ai_without_key_handoff(tmp_path):
    """无 key → 真人接管标注，不 raise（FR4.2 用户做主 + §六不阻塞）。"""
    r = ip.acquire_image(_row(acquire_via="ai", intent="beer glass"), tmp_path, api_keys=None)
    assert r["status"] == "handoff_to_human" and r["path"] is None
    assert "真人接管" in r["note"] and "key" in r["note"]


def _keys():
    return {"api_key": "sk-test", "base_url": "https://agg.example/v1", "models": {}}


def test_acquire_ai_with_key_generates(tmp_path, monkeypatch):
    png = b"\x89PNG fakebytes"
    seen = {}

    def fake_post(url, headers, payload, timeout=300):
        seen.update(url=url, payload=payload, auth=headers.get("Authorization"))
        return {"data": [{"b64_json": base64.b64encode(png).decode()}],
                "usage": {"cost": 0.134}}

    monkeypatch.setattr(ip, "_http_post_json", fake_post)
    r = ip.acquire_image(_row(acquire_via="ai", intent="beer glass close-up", size="1536x1024"),
                         tmp_path, api_keys=_keys(), rendering="flat")
    assert r["status"] == "ok"
    assert (tmp_path / "hero.png").read_bytes() == png                 # 真落盘
    assert seen["url"] == "https://agg.example/v1/images/generations"  # OpenAI 兼容端点
    assert seen["auth"] == "Bearer sk-test"
    assert seen["payload"]["size"] == "1536x1024"
    assert "NO text" in seen["payload"]["prompt"]                      # 无字铁律真进了 prompt
    assert r["model"] == ip.GEN_MODEL_DEFAULT
    assert r["cost_estimate"] == 0.134                                 # §六成本可见·直喂台账


def test_acquire_ai_url_response_branch(tmp_path, monkeypatch):
    monkeypatch.setattr(ip, "_http_post_json",
                        lambda *a, **k: {"data": [{"url": "https://cdn.example/i.png"}]})
    monkeypatch.setattr(ip, "_http_get_bytes", lambda url, timeout=300: b"imgbytes")
    r = ip.acquire_image(_row(acquire_via="ai", intent="glass"), tmp_path, api_keys=_keys())
    assert r["status"] == "ok" and (tmp_path / "hero.png").read_bytes() == b"imgbytes"
    assert r["cost_estimate"] is None            # 平台没回成本→如实 None·台账记 unknown


def test_acquire_ai_api_failure_degrades(tmp_path, monkeypatch):
    """§六：生图 API 炸了 → 降级真人接管，不 raise 不阻塞 deck 产出。"""
    def boom(*a, **k):
        raise RuntimeError("HTTP 429 quota exceeded")
    monkeypatch.setattr(ip, "_http_post_json", boom)
    r = ip.acquire_image(_row(acquire_via="ai", intent="glass"), tmp_path, api_keys=_keys())
    assert r["status"] == "handoff_to_human"
    assert "429" in r["note"] and "真人接管" in r["note"]    # 失败原因如实摊给人


def test_acquire_ai_missing_base_url_degrades(tmp_path):
    """配置残缺（有 key 无 base_url）也走降级——配置错误不该把 deck 卡死。"""
    r = ip.acquire_image(_row(acquire_via="ai", intent="glass"), tmp_path,
                         api_keys={"api_key": "sk", "base_url": None, "models": {}})
    assert r["status"] == "handoff_to_human" and "base_url" in r["note"]


# ═══════════════ FR7.4：web 路径（mock vendor·不联网） ═══════════════

def _fake_candidate(**over):
    base = dict(provider="openverse", title="Beer festival crowd", author="Alice",
                source_page_url="https://src.example/p", download_url="https://src.example/i.jpg",
                license_name="CC0", license_url="", license_tier="no-attribution",
                width=1600, height=900)
    base.update(over)
    return types.SimpleNamespace(**base)


def _patch_vendor_search(monkeypatch, result_candidate, provider="openverse"):
    """在真 vendor 模块上只换 search_and_download（接缝最小·参数拼装走真代码）。"""
    m = ip._vendor_image_search()
    seen = {}

    def fake(providers, request, *, output_path, strict_no_attribution, **kw):
        seen.update(providers=list(providers), query=request.query,
                    orientation=request.orientation,
                    min_width=request.min_width, min_height=request.min_height)
        if result_candidate is None:
            return None, None, None
        output_path.write_bytes(b"fakejpeg")
        return result_candidate, provider, "all"

    monkeypatch.setattr(m, "search_and_download", fake)
    return seen


def test_acquire_web_ok(tmp_path, monkeypatch):
    seen = _patch_vendor_search(monkeypatch, _fake_candidate())
    r = ip.acquire_image(_row(intent="beer festival", size="1200x800"), tmp_path)
    assert r["status"] == "ok" and (tmp_path / "hero.png").exists()
    assert r["provider"] == "openverse" and "web:openverse" in r["note"]
    assert seen["query"] == "beer festival"                 # intent 优先当检索词
    assert seen["orientation"] == "landscape"               # size 推方向
    assert (seen["min_width"], seen["min_height"]) == (1200, 800)
    # 溯源 manifest 落盘（与 vendor image_sources.json 同名同义）
    manifest = json.loads((tmp_path / "image_sources.json").read_text(encoding="utf-8"))
    item = manifest["items"][0]
    assert item["filename"] == "hero.png" and item["provider"] == "openverse"
    assert item["license_tier"] == "no-attribution" and item["status"] == "sourced"
    assert "generated_at" not in manifest                   # 引擎不碰系统时钟（项目纪律）


def test_acquire_web_attribution_required_flagged(tmp_path, monkeypatch):
    """CC BY 图必须把署名义务摊到 note/返回值——对客交付合规面不能静默。"""
    _patch_vendor_search(monkeypatch, _fake_candidate(
        license_name="CC BY 4.0", license_tier="attribution-required"), provider="wikimedia")
    r = ip.acquire_image(_row(intent="beer festival"), tmp_path)
    assert r["attribution_required"] is True
    assert "署名" in r["note"] and r["attribution_text"]    # attribution 文本给到 Executor


def test_acquire_web_no_candidate_handoff(tmp_path, monkeypatch):
    """四库全空 → 降级真人接管（web 失败与生图失败同一条 §六 哲学·不阻塞）。"""
    _patch_vendor_search(monkeypatch, None)
    r = ip.acquire_image(_row(intent="qqzzxx nonsense query"), tmp_path)
    assert r["status"] == "handoff_to_human" and "真人接管" in r["note"]


def test_acquire_web_without_query_handoff(tmp_path):
    """行级 intent/purpose 都空 → 没词可搜，降级（这条不碰 vendor·先于 import 返回）。"""
    r = ip.acquire_image(_row(intent="", purpose=""), tmp_path)
    assert r["status"] == "handoff_to_human" and "查询词" in r["note"]


# ═══════════════ D19 FR6.1：keyed 图库 key 缺失可见化 ═══════════════

def _mute_env_file(monkeypatch):
    """屏蔽 vendor 共享 .env 加载——测试断言只看进程 env，不受开发机磁盘 .env 干扰。"""
    m = ip._vendor_image_search()
    monkeypatch.setattr(m, "_load_search_env_file", lambda: None)
    return m


def test_acquire_web_reports_skipped_keyed_providers(tmp_path, monkeypatch):
    """缺 key 不再静默跳过：skipped_providers 带 provider+理由（含注册指引·FR6.1）。"""
    _mute_env_file(monkeypatch)
    monkeypatch.delenv("PEXELS_API_KEY", raising=False)
    monkeypatch.delenv("PIXABAY_API_KEY", raising=False)
    _patch_vendor_search(monkeypatch, _fake_candidate())
    r = ip.acquire_image(_row(intent="fujian tulou"), tmp_path)
    assert r["status"] == "ok"
    skipped = {s["provider"]: s["reason"] for s in r["skipped_providers"]}
    assert set(skipped) == {"pexels", "pixabay"}
    assert "PEXELS_API_KEY" in skipped["pexels"] and "4.7K" in skipped["pexels"]  # 理由带实测数据
    assert "pexels.com/api" in skipped["pexels"]                                  # 理由带注册指引
    assert "缺 key 被跳过" in r["note"]        # 成功路径 note 也提示——"四库只跑两库"必须可见


def test_acquire_web_handoff_also_reports_skipped(tmp_path, monkeypatch):
    """失败路径（无结果降级）同样带 skipped_providers——正是误诊高发场景（FR6.1）。"""
    _mute_env_file(monkeypatch)
    monkeypatch.delenv("PEXELS_API_KEY", raising=False)
    monkeypatch.delenv("PIXABAY_API_KEY", raising=False)
    _patch_vendor_search(monkeypatch, None)
    r = ip.acquire_image(_row(intent="qqzzxx nonsense"), tmp_path)
    assert r["status"] == "handoff_to_human"
    assert {s["provider"] for s in r["skipped_providers"]} == {"pexels", "pixabay"}
    assert "缺 key 被跳过" in r["note"]


def test_acquire_web_with_keys_no_skip_and_keyed_first(tmp_path, monkeypatch):
    """key 齐配 → skipped_providers 空、note 无 warn、keyed 库排链首（vendor 链序不回归）。"""
    m = _mute_env_file(monkeypatch)
    monkeypatch.setenv("PEXELS_API_KEY", "k1")
    monkeypatch.setenv("PIXABAY_API_KEY", "k2")
    seen = _patch_vendor_search(monkeypatch, _fake_candidate())
    r = ip.acquire_image(_row(intent="fujian tulou"), tmp_path)
    assert r["skipped_providers"] == [] and "缺 key 被跳过" not in r["note"]
    assert seen["providers"][:2] == ["pexels", "pixabay"]
    assert m.KEYED_PROVIDERS == ("pexels", "pixabay")   # 跳过检测依赖的 vendor 常量语义锁定


def test_dotenv_is_gitignored():
    """FR6.1 承重墙：.env 必须整行进 .gitignore——图库 key 绝不入库（现查此前未忽略）。"""
    gi = (ip._PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".env" in [line.strip() for line in gi.splitlines()]


# ═══════════════ D19 FR6.3：中国地名消歧（防上海福州路混入） ═══════════════

def test_disambiguate_cn_place_appends_province():
    assert ip.disambiguate_cn_place("Fuzhou street") == "Fuzhou street Fujian"
    assert ip.disambiguate_cn_place("Wuyishan tea mountain") == "Wuyishan tea mountain Fujian"


def test_disambiguate_cn_place_idempotent_and_scoped():
    assert ip.disambiguate_cn_place("Fuzhou Fujian old town") == "Fuzhou Fujian old town"  # 已带省不重复
    assert ip.disambiguate_cn_place("Paris street") == "Paris street"                      # 非中国地名不动
    assert ip.disambiguate_cn_place("福州 街景") == "福州 街景"   # 中文查询不消歧（FR6.2 通路覆盖）


def test_acquire_web_query_gets_province_qualifier(tmp_path, monkeypatch):
    """行级 intent 含英文中国城市名 → 真实传给 vendor 的 query 已带省级限定（FR6.3 接线）。"""
    _mute_env_file(monkeypatch)
    seen = _patch_vendor_search(monkeypatch, _fake_candidate())
    ip.acquire_image(_row(intent="Fuzhou historic street"), tmp_path)
    assert seen["query"] == "Fuzhou historic street Fujian"


# ═══════════════ FR7.4：analyze_acquired 实测尺寸喂布局 ═══════════════

def test_analyze_acquired_measures_real_pixels(tmp_path):
    from PIL import Image
    Image.new("RGB", (200, 100), "#123456").save(tmp_path / "wide.png")
    Image.new("RGB", (100, 300), "#654321").save(tmp_path / "tall.png")
    out = ip.analyze_acquired([tmp_path / "wide.png", tmp_path / "tall.png"])
    wide, tall = out[0], out[1]
    assert (wide["width"], wide["height"]) == (200, 100)
    assert wide["aspect_ratio"] == 2.0 and wide["layout_hint"] == "Wide landscape"
    assert tall["layout_hint"] == "Portrait" and tall["filesize_kb"] > 0


def test_analyze_acquired_reports_unreadable(tmp_path):
    bad = tmp_path / "corrupt.png"
    bad.write_bytes(b"not an image")
    rec = ip.analyze_acquired([bad])[0]
    assert "error" in rec and rec["filename"] == "corrupt.png"   # 如实摊出·不静默跳过
