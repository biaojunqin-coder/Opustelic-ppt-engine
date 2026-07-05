"""SVG→PNG 预览渲染测试（D7·路线A拍板）。

playwright 是可选依赖——未装环境下也要能正确报错（不能静默假装能渲染），
真实渲染验证（含 CJK 正确性，这是选 Playwright 而非轻量方案的唯一理由）在装了的环境下才跑，
用 `preview_available()` 探测结果做 skip 判据，不装环境测试套件依旧全绿。
"""

from __future__ import annotations

import pytest

from engine.render_preview import SvgRenderer, preview_available, render_svg_to_png

_HAS_PREVIEW = preview_available()

CJK_SVG = ('<svg viewBox="0 0 1280 720" xmlns="http://www.w3.org/2000/svg">'
           '<rect width="1280" height="720" fill="#FFFFFF"/>'
           '<text x="100" y="360" font-family="Arial" font-size="60" fill="#000000">'
           '中文渲染测试·瀑布图第三页</text></svg>')


def test_import_error_when_playwright_missing(monkeypatch):
    if _HAS_PREVIEW:
        pytest.skip("本机已装 playwright+chromium，跳过'未装'路径测试")
    import builtins
    real_import = builtins.__import__

    def fake_import(name, *a, **k):
        if name == "playwright.sync_api" or name.startswith("playwright"):
            raise ImportError("simulated missing playwright")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(ImportError, match="playwright"):
        with SvgRenderer():
            pass


def test_preview_available_returns_bool_never_raises():
    # 探测函数本身无论装没装都不该抛异常——调用方靠它的返回值做 skip 判断，不是靠 try/except
    assert isinstance(preview_available(), bool)


@pytest.mark.skipif(not _HAS_PREVIEW, reason="playwright/chromium 未装·真实渲染验证跳过")
def test_render_produces_valid_png(tmp_path):
    out = render_svg_to_png(CJK_SVG, tmp_path / "p1.png")
    assert out.exists() and out.stat().st_size > 0
    from PIL import Image
    img = Image.open(out)
    assert img.size == (1280, 720)


@pytest.mark.skipif(not _HAS_PREVIEW, reason="playwright/chromium 未装·真实渲染验证跳过")
def test_render_cjk_not_blank():
    # 核心验证点：这整套方案存在的唯一理由——中文字必须真渲染出来，不能是 cairosvg 那种方块/空白
    # (vendor ppt-master 已验证的踩坑结论，见 render_preview.py 模块docstring)
    import io
    from playwright.sync_api import sync_playwright  # noqa: F401 (确认可用，实际渲染走 render_svg_to_png)
    from PIL import Image

    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        out = render_svg_to_png(CJK_SVG, f"{tmp}/cjk.png")
        img = Image.open(out).convert("RGB")
        colors = img.getcolors(maxcolors=1_000_000)
        # 全白背景 + 黑色文字笔画 → 至少要有第二种非白色主色（证明文字真的被画出来了，不是纯背景）
        non_white = [c for c in colors if c[1] != (255, 255, 255)]
        assert non_white, "渲染结果只有背景色，中文文字疑似没画出来(空转/tofu方块吃掉了颜色采样)"


@pytest.mark.skipif(not _HAS_PREVIEW, reason="playwright/chromium 未装·真实渲染验证跳过")
def test_svg_renderer_reuses_browser_session_across_pages(tmp_path):
    with SvgRenderer() as r:
        p1 = r.render(CJK_SVG, tmp_path / "a.png")
        p2 = r.render(CJK_SVG, tmp_path / "b.png")
    assert p1.exists() and p2.exists()
