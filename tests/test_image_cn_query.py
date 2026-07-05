"""D19 FR6.2/FR6.4 图像管线中文查询通路测试（vendor provider_common CJK 修复 + locale + OAuth）。

覆盖需求《第二轮实测反馈》FR6.2 两处 CJK 硬伤（simplify_query 的 len>2 过滤删两字中文词 /
_query_tokens 丢弃全部 CJK token）、locale 参数按语言出现（Pexels locale=zh-CN /
Pixabay lang=zh·英文查询不传）、FR6.4 Openverse OAuth 通路（有配置带 token·无配置匿名照跑）。

网络纪律：单测绝不真联网——provider 请求级测试 monkeypatch requests.get/post。
"土楼"免 key 库真调验证是开发期一次性人工动作（结果记交付报告），不进测试。

vendor 模块以顶层名互相 import（config/console_encoding），需先经
image_pipeline._vendor_image_search() 把 scripts 目录接进 sys.path（同薄适配层接缝纪律）。
"""

from __future__ import annotations

import pytest

from engine import image_pipeline as ip

ip._vendor_image_search()  # side effect：sys.path 接线 + console_encoding 垫片

from image_sources import provider_openverse, provider_pexels, provider_pixabay  # noqa: E402
from image_sources.provider_common import (  # noqa: E402
    AssetCandidate,
    ImageSearchRequest,
    _query_tokens,
    cjk_locale_params,
    compute_relevance,
    openverse_auth_headers,
    simplify_query,
)


# ═══════════════ FR6.2 ①：simplify_query 不再删两字中文词 ═══════════════

def test_simplify_query_keeps_two_char_cjk_words():
    """调研点名的两个病例词："福州""土楼" 都是完整高信息名词，绝不能被 len>2 过滤删掉。"""
    assert "福州" in simplify_query("福州 街景 photo")
    assert "土楼" in simplify_query("土楼 建筑 全景")
    assert simplify_query("福州") == "福州"           # 单个两字中文词不落入 fail-open 回退


def test_simplify_query_single_cjk_char_kept():
    assert "楼" in simplify_query("楼 建筑物 特写")    # CJK 词 ≥1 字即保留（字符类感知）


def test_simplify_query_english_behavior_unchanged():
    """英文查询行为零回归：≤2 字符英文词照旧被过滤、噪声词照旧剔除。"""
    assert simplify_query("an offshore wind farm") == "offshore wind farm"
    assert "microsoft" not in simplify_query("microsoft cloud datacenter servers")


# ═══════════════ FR6.2 ②：CJK token 参与相关性打分 ═══════════════

def test_query_tokens_include_cjk():
    toks = _query_tokens("福州 historic street")
    assert "福州" in toks and "historic" in toks and "street" in toks


def test_query_tokens_long_cjk_run_split_to_bigrams():
    """中文无空格分词：长于 2 字的连续段拆 2-gram，专名"福州""街景"都拆得出来。"""
    toks = _query_tokens("福州街景")
    assert "福州" in toks and "街景" in toks


def test_compute_relevance_scores_cjk_metadata():
    hit = AssetCandidate(provider="wikimedia", title="福州 三坊七巷 historic street")
    assert compute_relevance(hit, "福州 街景") > 0.0          # 修复前恒 1.0 中性（信号为零）
    miss = AssetCandidate(provider="wikimedia", title="Shanghai bund skyline")
    assert compute_relevance(miss, "福州") == 0.0             # 不相关的中文查询真能打 0 分了


def test_compute_relevance_pure_cjk_hit_full_score():
    c = AssetCandidate(provider="wikimedia", title="Fujian Tulou 土楼")
    assert compute_relevance(c, "土楼") == 1.0


# ═══════════════ FR6.2 ③：locale 参数按语言出现 ═══════════════

def test_cjk_locale_params_mapping():
    assert cjk_locale_params("pexels", "福州 街景") == {"locale": "zh-CN"}
    assert cjk_locale_params("pixabay", "土楼") == {"lang": "zh"}
    assert cjk_locale_params("pexels", "fuzhou street") == {}     # 英文查询不传（不动既有行为）
    assert cjk_locale_params("wikimedia", "福州") == {}           # 无 locale 参数的库不传


class _FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


_PEXELS_PAYLOAD = {"photos": [{
    "src": {"original": "https://img.example/tulou.jpg"}, "alt": "土楼",
    "id": 1, "url": "https://pexels.example/p/1",
    "width": 2000, "height": 1500, "photographer": "a"}]}

_PIXABAY_PAYLOAD = {"hits": [{
    "largeImageURL": "https://img.example/tulou.jpg", "tags": "土楼, fujian",
    "id": 1, "pageURL": "https://pixabay.example/p/1",
    "imageWidth": 2000, "imageHeight": 1500, "user": "a"}]}


def test_pexels_request_carries_locale_for_cjk_only(monkeypatch):
    monkeypatch.setenv("PEXELS_API_KEY", "test-key")
    seen = []

    def fake_get(url, params=None, headers=None, timeout=None):
        seen.append(dict(params or {}))
        return _FakeResp(_PEXELS_PAYLOAD)

    monkeypatch.setattr("requests.get", fake_get)
    provider_pexels.search(ImageSearchRequest(query="土楼"), license_tier_filter="all")
    assert seen and all(p.get("locale") == "zh-CN" for p in seen)   # CJK 查询全程带 locale

    seen.clear()
    provider_pexels.search(ImageSearchRequest(query="offshore wind farm"), license_tier_filter="all")
    assert seen and all("locale" not in p for p in seen)            # 英文查询一律不带


def test_pixabay_request_carries_lang_for_cjk_only(monkeypatch):
    monkeypatch.setenv("PIXABAY_API_KEY", "test-key")
    seen = []

    def fake_get(url, params=None, headers=None, timeout=None):
        seen.append(dict(params or {}))
        return _FakeResp(_PIXABAY_PAYLOAD)

    monkeypatch.setattr("requests.get", fake_get)
    provider_pixabay.search(ImageSearchRequest(query="土楼"), license_tier_filter="all")
    assert seen and all(p.get("lang") == "zh" for p in seen)

    seen.clear()
    provider_pixabay.search(ImageSearchRequest(query="offshore wind farm"), license_tier_filter="all")
    assert seen and all("lang" not in p for p in seen)


# ═══════════════ FR6.4：Openverse OAuth 通路 ═══════════════

@pytest.fixture()
def _clean_openverse(monkeypatch):
    """清配置 + 清 token 缓存——防开发机真实 key/上一测试的缓存污染断言。"""
    from image_sources import provider_common as pc
    monkeypatch.delenv("OPENVERSE_CLIENT_ID", raising=False)
    monkeypatch.delenv("OPENVERSE_CLIENT_SECRET", raising=False)
    monkeypatch.setattr(pc, "_OPENVERSE_TOKEN_CACHE", {})
    return pc


def test_openverse_headers_anonymous_without_credentials(_clean_openverse):
    assert openverse_auth_headers() == {}    # 无配置 → 匿名照跑（零配置路径不破）


def test_openverse_headers_bearer_with_credentials_and_cache(_clean_openverse, monkeypatch):
    monkeypatch.setenv("OPENVERSE_CLIENT_ID", "cid")
    monkeypatch.setenv("OPENVERSE_CLIENT_SECRET", "sec")
    calls = []

    def fake_post(url, data=None, headers=None, timeout=None):
        calls.append(dict(data or {}))
        return _FakeResp({"access_token": "tok-123", "expires_in": 3600})

    monkeypatch.setattr("requests.post", fake_post)
    assert openverse_auth_headers() == {"Authorization": "Bearer tok-123"}
    assert calls[0]["grant_type"] == "client_credentials"
    assert openverse_auth_headers() == {"Authorization": "Bearer tok-123"}
    assert len(calls) == 1    # 第二次走缓存·不再烧一次 token 请求（匿名限流下 token 也金贵）


def test_openverse_headers_token_failure_degrades_anonymous(_clean_openverse, monkeypatch):
    monkeypatch.setenv("OPENVERSE_CLIENT_ID", "cid")
    monkeypatch.setenv("OPENVERSE_CLIENT_SECRET", "sec")

    def boom(*a, **k):
        raise RuntimeError("network down")

    monkeypatch.setattr("requests.post", boom)
    assert openverse_auth_headers() == {}    # 提额失败绝不阻塞零配置路径（降级哲学）


def test_openverse_search_attaches_bearer_when_configured(_clean_openverse, monkeypatch):
    monkeypatch.setenv("OPENVERSE_CLIENT_ID", "cid")
    monkeypatch.setenv("OPENVERSE_CLIENT_SECRET", "sec")
    monkeypatch.setattr("requests.post",
                        lambda *a, **k: _FakeResp({"access_token": "tok-9", "expires_in": 3600}))
    seen_headers = []

    def fake_get(url, params=None, headers=None, timeout=None):
        seen_headers.append(dict(headers or {}))
        return _FakeResp({"results": []})

    monkeypatch.setattr("requests.get", fake_get)
    provider_openverse.search(ImageSearchRequest(query="tulou"), license_tier_filter="all")
    assert seen_headers and all(
        h.get("Authorization") == "Bearer tok-9" for h in seen_headers)


def test_openverse_search_anonymous_without_credentials(_clean_openverse, monkeypatch):
    seen_headers = []

    def fake_get(url, params=None, headers=None, timeout=None):
        seen_headers.append(dict(headers or {}))
        return _FakeResp({"results": []})

    monkeypatch.setattr("requests.get", fake_get)
    provider_openverse.search(ImageSearchRequest(query="tulou"), license_tier_filter="all")
    assert seen_headers and all("Authorization" not in h for h in seen_headers)
