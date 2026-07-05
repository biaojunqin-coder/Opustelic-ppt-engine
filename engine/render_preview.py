"""SVG → PNG 预览渲染（2026-07-01·创意层"渲染→自检"闭环的渲染引擎，路线A拍板·D7后续）。

后端：Playwright(Chromium)。出处【vendor ppt-master `scripts/visual_review.py` 头部注释】——
"cairosvg backend was evaluated and rejected because cairo's text API has no font-fallback chain
— CJK characters render as tofu boxes"：他们真实测过更轻量的 cairosvg，中文字体无回退链渲染不出来，
最终改用真浏览器。我们的 deck 几乎全中文，直接沿用这条已验证结论，不重新踩一遍坑。

跟 ppt-master 原版的简化差异：原版依赖一个"live-preview HTTP server"（解析 `<use data-icon>`
图标引用 + 相对路径 `<image href>`），因为他们的 SVG 会引用外部图标库。我们的 SVG 是
`engine/svg_layout.py`/`engine/chart_shapes.py` 拼出来的自包含字符串（不引用外部文件），
不需要服务器解析这一层——直接 `page.set_content()` 把 SVG 包一层最小 HTML 壳喂给浏览器，
免去起停一个本地 HTTP 服务的生命周期管理。

Playwright 是可选依赖（`pip install playwright && playwright install chromium`，见 pyproject.toml
`[project.optional-dependencies].preview`）——未装/浏览器内核未下载时抛清楚的 ImportError，
不静默假装能渲染（同 MinerU 空转桩教训：宁可明确报错，不可看似能用实则空转）。
"""

from __future__ import annotations

from pathlib import Path

DEFAULT_W, DEFAULT_H = 1280, 720


def _wrap_html(svg: str, width: int, height: int) -> str:
    return (
        "<!DOCTYPE html><html><head><meta charset=\"utf-8\"><style>"
        f"html,body{{margin:0;padding:0;width:{width}px;height:{height}px;overflow:hidden;background:#fff}}"
        f"svg{{display:block;width:{width}px;height:{height}px}}"
        "</style></head><body>" + svg + "</body></html>"
    )


class SvgRenderer:
    """复用同一个浏览器会话渲染多页（避免每页重启浏览器进程·同 ppt-master render_pages() 的优化）。

    用法：
        with SvgRenderer() as r:
            r.render(svg_page1, out1)
            r.render(svg_page2, out2)
    单页场景用模块级 `render_svg_to_png()` 更省事。
    """

    def __init__(self, *, width: int = DEFAULT_W, height: int = DEFAULT_H):
        self.width, self.height = width, height
        self._pw = None
        self._browser = None

    def __enter__(self) -> "SvgRenderer":
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as e:
            raise ImportError(
                "预览渲染需要 playwright（可选依赖，未装）。安装：\n"
                "  .venv/bin/pip install playwright\n"
                "  .venv/bin/playwright install chromium\n"
                "（CJK 正确渲染必须真浏览器，cairosvg 等轻量方案中文字体无回退链会渲染成方块——"
                "见 vendor ppt-master 已验证结论，engine/render_preview.py 模块docstring）"
            ) from e
        self._pw = sync_playwright().start()
        try:
            self._browser = self._pw.chromium.launch()
        except Exception as e:
            self._pw.stop()
            self._pw = None
            raise RuntimeError(
                "playwright 包已装，但 Chromium 内核启动失败（大概率未下载）。安装：\n"
                "  .venv/bin/playwright install chromium\n"
                f"原始报错：{type(e).__name__}: {e}"
            ) from e
        return self

    def render(self, svg: str, out_path: str | Path) -> Path:
        """渲染一页 SVG → PNG，返回写入的文件路径。"""
        if self._browser is None:
            raise RuntimeError("SvgRenderer 必须用 `with SvgRenderer() as r:` 打开后才能 render()")
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        page = self._browser.new_page(viewport={"width": self.width, "height": self.height})
        try:
            page.set_content(_wrap_html(svg, self.width, self.height), wait_until="load")
            page.wait_for_timeout(100)  # 等字体shaping/CJK排版稳定再截图，同 ppt-master 同一条经验
            out_path.write_bytes(page.screenshot(type="png"))
        finally:
            page.close()
        return out_path

    def __exit__(self, *exc) -> None:
        if self._browser is not None:
            self._browser.close()
        if self._pw is not None:
            self._pw.stop()
        self._browser = self._pw = None


def render_svg_to_png(svg: str, out_path: str | Path, *, width: int = DEFAULT_W, height: int = DEFAULT_H) -> Path:
    """单页便捷渲染（内部开关一次浏览器·多页场景请用 `SvgRenderer` 复用会话更快）。"""
    with SvgRenderer(width=width, height=height) as r:
        return r.render(svg, out_path)


def preview_available() -> bool:
    """探测 playwright 包 + Chromium 内核是否都就绪（不抛异常·调用方用来决定要不要跳过预览步骤）。"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            browser.close()
        return True
    except Exception:
        return False
