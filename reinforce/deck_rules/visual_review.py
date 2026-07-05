"""视觉缺陷结构化机检（提炼自 ppt-master `references/visual-review.md` 的 H1-H9/S1-S10 规则 taxonomy）。

⚠️ 范围声明（2026-07-01·六路深挖技术脚本对照后的诚实裁剪，别看见"H1/H4"字样就以为整套搬过来了）：
原版是给"批量渲染成 PNG 后用 Playwright + subagent 自动修复"的完整闭环系统（含迭代/回滚/分批调度协议，
`visual_review.py` 渲染器依赖本地浏览器 Chromium + 一个 live-preview HTTP 服务）——那套机制是为
ppt-master 自己"脚本/subagent 批量产出后再自动挑错修复"的工作流设计的。我们的制作纪律是逐页手写 +
spec_lock 强制重读（防呆在生成时，不是生成完再补救），且 Playwright 不在我们依赖里，建那整套自动修复
闭环不成比例（新依赖 + 本地浏览器渲染管线，是一次独立基础设施投入，不是顺手实现）。

这里只做"能从 SVG 源码结构/属性直接算出来、不需要真实渲染"的几条机检：
- H1 出画布（保守版：跳过带 transform 的元素，宁可漏检不猜矩阵变换后的真实包围盒）
- H4 对比度（WCAG 真实数学公式，非启发式估计；但只比对"文字 fill" vs "页面级整页背景"，
  不做嵌套卡片的局部合成——文字若坐落在卡片色块上而非直接页面背景上，这里的基准不准）
- H8 图片引用破损（轻量版：只查 href 是否为空/缺失，不验证文件是否真实存在或能否渲染）
- S6 CJK 字距过松（letter-spacing/font-size 比值，纯属性数学）
- 字号网格（02 设计系统 8 级）：抠 SVG 里 `<text font-size>` 逐个核对（2026-07-01 yanjiu研究驱动
  评估揪出：`rules.check_font` 此前只有单测覆盖、从未接入 `pipeline.build_deck` 生产链路，
  在这里统一从 SVG 反抠字号补上，不用改 pipeline.py）

真正需要"看渲染后的样子才能判断"的项——H2/H3/H6/H9 精确版 + S1-S5/S7-S10 全部（视觉重心/网格
对齐/呼吸感留白这类）——没有勉强用脆弱的几何近似硬判，那样误报率比不查还误导人，转成人审清单
条目，见 `reinforce/review.py` 的 `slide_content` 清单。

补充（2026-07-01·`research_lib/开源拆解/04制作/Instrumenta.md` 价值评估🟢采纳）：对齐/等距分布/同尺寸
三条——Instrumenta（前麦肯锡顾问开源的 VBA 版式质检引擎）把这几项列为核心机检项，跟上面四条同属
"结构级可判定、不需渲染"的纯几何数学，直接搬。**跟 Instrumenta 原版的差异**：原版操作真实
PowerPoint 对象模型（Left/Top/Width/Height 精确到 EMU），这里只能从 SVG 源码正则抠 `<rect>` 的
x/y/width/height，没有"这几个元素是不是同一组"的语义信息——所以只抓"近失误"（差值在很小容差内但
不为0，像手摆没量准）而不是全量两两比较，降低跟不相关元素误配对的噪音，宁可漏检不瞎猜（同 H1 的
transform 跳过同一条哲学）。
"""

from __future__ import annotations

import math
import re

from reinforce.deck_rules import rules as G

CANVAS_W, CANVAS_H = 1280, 720
_TAG_RE = re.compile(r"<(rect|circle|text|image)\b([^>]*?)/?>")
_ATTR_RE = re.compile(r'([\w:-]+)\s*=\s*"([^"]*)"')
_SVG_ROOT_RE = re.compile(r"<svg\b([^>]*)>")
ACCEPTED_ASPECT_RATIOS = {"16:9": 16 / 9, "4:3": 4 / 3}  # 05 质量门 constraint verify·行业标准格式


def _attrs(attr_str: str) -> dict:
    return dict(_ATTR_RE.findall(attr_str))


def _num(d: dict, k: str, default: float = 0.0) -> float:
    try:
        return float(d.get(k, default))
    except (TypeError, ValueError):
        return default


# 2026-07-02 saopan扫盘揪出：font-size="14px" 走 _num 会静默归 0——check_font_grid 报幽灵违规
# got:0、check_font_variety_per_page 把带单位的字号全并成一种 0、check_contrast 大字阈值判定失效。
# 单独给长度属性(font-size/letter-spacing)一个带单位解析：px 是 SVG 用户单位本身、pt 有确定换算
# (CSS 1pt=4/3px)，em/%/rem 这类相对单位没有绝对像素语义 → 返回 None，调用处跳过该元素不瞎猜。
_PX_LEN_RE = re.compile(r"^\s*([+-]?(?:\d+\.?\d*|\.\d+))\s*(px|pt)?\s*$", re.IGNORECASE)


def _px_len(value: str | None) -> float | None:
    if value is None:
        return None
    m = _PX_LEN_RE.match(value)
    if not m:
        return None
    n = float(m.group(1))
    return n * 4 / 3 if (m.group(2) or "").lower() == "pt" else n


def _canvas_size(svg: str) -> tuple[float, float]:
    """从 <svg> 根标签解析画布尺寸：viewBox 优先（vendor 转换引擎按 viewBox 建坐标系），
    退而用 width/height，都解析不到才落回默认 1280x720。
    2026-07-02 saopan扫盘揪出：check_aspect_ratio 自己解析 viewBox 放行 1920x1080/4:3，
    但 out_of_canvas 判越界、_page_background 找整页背景 rect 都写死 1280x720——合法的
    1920x1080 页整页误报出画布，且找不到背景导致 contrast/invisible_text 静默跳过。
    """
    m = _SVG_ROOT_RE.search(svg)
    if m:
        a = _attrs(m.group(1))
        vb = a.get("viewBox")
        if vb:
            nums = [t for t in re.split(r"[\s,]+", vb.strip()) if t]
            if len(nums) == 4:
                try:
                    w, h = float(nums[2]), float(nums[3])
                    if w > 0 and h > 0:
                        return w, h
                except ValueError:
                    pass
        w, h = _num(a, "width", -1.0), _num(a, "height", -1.0)
        if w > 0 and h > 0:
            return w, h
    return float(CANVAS_W), float(CANVAS_H)


# 纯旋转变换闭式AABB（2026-07-01 yanjiu研究驱动评估🟡走样需修，出处：
# research_lib/开源拆解/04制作/Instrumenta.md L45-58 GetRealWidth/GetRealHeight——但那条公式
# 假定绕矩形自身中心旋转，SVG rotate(θ) 缺省绕原点(0,0)旋转，跟"绕自身中心"不是同一回事，
# 这里改用更通用的"旋转4个角点求真实AABB"闭式解法，同时覆盖 rotate(θ) 绕原点/rotate(θ,cx,cy)
# 绕任意点两种情况，比 Instrumenta 那条特例公式适用范围更广）。
_ROTATE_ONLY_RE = re.compile(r'^\s*rotate\(\s*([-\d.]+)\s*(?:[,\s]+([-\d.]+)\s*[,\s]+([-\d.]+)\s*)?\)\s*$')


def _parse_pure_rotate(transform: str):
    """transform 属性值若整体恰好是单个 rotate(...)（没有跟 translate/scale/matrix 复合）→
    返回 (angle_deg, cx, cy)（cx/cy 缺省时为 None，按原点处理）；否则返回 None——复合变换仍然
    需要矩阵乘法才能算真实包围盒，正则做不到，宁可漏检不瞎猜（同原有哲学不变，这里只是把
    "纯旋转"这个可以闭式求解的子情形从"整体跳过"里挑出来）。
    """
    m = _ROTATE_ONLY_RE.match(transform.strip())
    if not m:
        return None
    # 2026-07-02 saopan扫盘揪出：正则 [-\d.]+ 会放行 "1.2.3" 这类畸形数字，裸 float() 一炸
    # 让 run_visual_gate→build_deck 全链 ValueError 崩穿——一处手误击穿整个视觉门。包住后
    # 走"复杂 transform 跳过不瞎猜"的既有路径，机检门自身必须比它检查的内容更皮实。
    try:
        angle = float(m.group(1))
        if m.group(2) is not None:
            return angle, float(m.group(2)), float(m.group(3))
        return angle, None, None
    except ValueError:
        return None


def _rotate_point(x: float, y: float, angle_deg: float, cx: float, cy: float) -> tuple:
    theta = math.radians(angle_deg)
    cos_t, sin_t = math.cos(theta), math.sin(theta)
    dx, dy = x - cx, y - cy
    return cx + dx * cos_t - dy * sin_t, cy + dx * sin_t + dy * cos_t


def check_out_of_canvas(svg: str, *, canvas_w: float | None = None, canvas_h: float | None = None) -> list[dict]:
    """H1 出画布（保守版）：只查直接写 x/y/width/height(rect)·cx/cy/r(circle)·x/y(text 锚点)的
    元素。无 transform 的元素直接按原始坐标查；transform 恰好是单个纯 rotate(θ[,cx,cy])(闭式可解，
    见 _parse_pure_rotate)按旋转后的真实位置/包围盒查；其余复合变换(matrix/scale/
    translate+rotate)需要矩阵运算才能算真实包围盒，正则做不到，宁可漏检不瞎猜。
    画布尺寸缺省从 SVG 自身解析（_canvas_size·2026-07-02 修硬编码1280x720），显式传参仍可覆盖。
    """
    if canvas_w is None or canvas_h is None:
        canvas_w, canvas_h = _canvas_size(svg)
    issues = []
    for tag, attr_str in _TAG_RE.findall(svg):
        a = _attrs(attr_str)
        transform = a.get("transform")
        rot = _parse_pure_rotate(transform) if transform else None
        if transform and rot is None:
            continue  # 复合变换·跳过不瞎猜
        rot_suffix = "·旋转闭式AABB" if rot else ""
        if tag == "rect":
            x, y, w, h = _num(a, "x"), _num(a, "y"), _num(a, "width"), _num(a, "height")
            if rot is not None:
                angle, cx, cy = rot
                if cx is None:
                    cx, cy = 0.0, 0.0
                corners = [(x, y), (x + w, y), (x, y + h), (x + w, y + h)]
                rc = [_rotate_point(px, py, angle, cx, cy) for px, py in corners]
                x0, y0 = min(p[0] for p in rc), min(p[1] for p in rc)
                x1, y1 = max(p[0] for p in rc), max(p[1] for p in rc)
                if x0 < 0 or y0 < 0 or x1 > canvas_w or y1 > canvas_h:
                    issues.append({"rule": "out_of_canvas", "sev": "warn",
                                    "note": f"<rect> 旋转{angle:g}°后真实包围盒({x0:.0f},{y0:.0f})-"
                                            f"({x1:.0f},{y1:.0f}) 超出画布 0,0,{canvas_w},{canvas_h}（H1{rot_suffix}）"})
            elif x < 0 or y < 0 or x + w > canvas_w or y + h > canvas_h:
                issues.append({"rule": "out_of_canvas", "sev": "warn",
                                "note": f"<rect> ({x:g},{y:g},{w:g}x{h:g}) 超出画布 0,0,{canvas_w},{canvas_h}（H1）"})
        elif tag == "circle":
            cx0, cy0, r = _num(a, "cx"), _num(a, "cy"), _num(a, "r")
            if rot is not None:
                angle, pcx, pcy = rot
                if pcx is None:
                    pcx, pcy = 0.0, 0.0
                cx0, cy0 = _rotate_point(cx0, cy0, angle, pcx, pcy)  # 圆旋转=圆心平移·半径不变
            if cx0 - r < 0 or cy0 - r < 0 or cx0 + r > canvas_w or cy0 + r > canvas_h:
                issues.append({"rule": "out_of_canvas", "sev": "warn",
                                "note": f"<circle> 圆心({cx0:g},{cy0:g})半径{r:g} 超出画布（H1{rot_suffix}）"})
        elif tag == "text" and "x" in a and "y" in a:
            x, y = _num(a, "x"), _num(a, "y")
            if rot is not None:
                angle, pcx, pcy = rot
                if pcx is None:
                    pcx, pcy = 0.0, 0.0
                x, y = _rotate_point(x, y, angle, pcx, pcy)
            if x < 0 or y < 0 or x > canvas_w or y > canvas_h:
                issues.append({"rule": "out_of_canvas", "sev": "warn",
                                "note": f"<text> 锚点({x:g},{y:g}) 超出画布（H1{rot_suffix}）"
                                        f"·只查锚点不查文字实际渲染宽度"})
    return issues


def _srgb_to_linear(c: float) -> float:
    c = c / 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def _hex_to_rgb(hexcolor: str):
    h = hexcolor.lstrip("#")
    # 2026-07-03 二轮扫盘揪出：3 位简写（#fff）此前返回 None → 对比度/隐形文字/CVD 检查对
    # 简写色元素静默漏检。展开成 6 位（#abc ≡ #aabbcc，CSS/SVG 同义）——同仓
    # spec_lock.py::_norm_hex 已修过同一个 bug，写法对照它保持一致。
    if re.fullmatch(r"[0-9A-Fa-f]{3}", h):
        h = "".join(ch * 2 for ch in h)
    if len(h) != 6 or not re.fullmatch(r"[0-9A-Fa-f]{6}", h):
        return None
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _relative_luminance(hexcolor: str):
    rgb = _hex_to_rgb(hexcolor)
    if rgb is None:
        return None
    r, g, b = rgb
    return 0.2126 * _srgb_to_linear(r) + 0.7152 * _srgb_to_linear(g) + 0.0722 * _srgb_to_linear(b)


def _page_background(svg: str) -> str | None:
    """找跟画布同尺寸的 rect 当"整页背景"——check_contrast/check_invisible_text 共用同一份探测逻辑。
    画布尺寸从 SVG 自身解析（_canvas_size）而非写死 1280x720——否则 1920x1080 页的背景 rect
    永远配不上，对比度/隐形文字两条检查在非默认画布上静默失效。"""
    canvas_w, canvas_h = _canvas_size(svg)
    for tag, attr_str in _TAG_RE.findall(svg):
        if tag != "rect":
            continue
        a = _attrs(attr_str)
        if _num(a, "width") == canvas_w and _num(a, "height") == canvas_h and a.get("fill"):
            return a["fill"]
    return None


def contrast_ratio(hex_a: str, hex_b: str):
    """WCAG 对比度比值（标准公式，范围 1~21）。任一方不是合法十六进制色返回 None（如渐变 url(#g) 跳过不猜）。"""
    la, lb = _relative_luminance(hex_a), _relative_luminance(hex_b)
    if la is None or lb is None:
        return None
    lighter, darker = max(la, lb), min(la, lb)
    return (lighter + 0.05) / (darker + 0.05)


def _opaque(a: dict) -> bool:
    """rect 是否可当"文字的实际底色"看待：fill-opacity/opacity 未声明或 ≥1 才算。
    半透明矩形的可见色是"声明色 × 底下内容"的合成结果（如 某品牌 实测卡片
    fill="#0F3D2E" fill-opacity="0.04"——声明深绿、渲染近白），拿声明色当背景比对
    会制造反向假阳性，单层推断算不准 → 不当候选（D18 FR1.5 边界声明）。"""
    for key in ("fill-opacity", "opacity"):
        if key in a:
            try:
                if float(a[key]) < 1.0:
                    return False
            except ValueError:
                return False  # 解析不了的透明度不猜
    return True


def _bg_rect_candidates(svg: str) -> list[tuple]:
    """收集可当"文字背景"的矩形（D18 FR1.5）：有正宽高、fill 是具体颜色值（非 none）、
    无 transform（不猜变换后的真实位置·同 H1 哲学）。半透明矩形（_opaque 为 False）**也收**
    但打标——它虽给不出可比对的底色，却真实挡在文字和页面背景之间，命中时该"跳过不瞎猜"
    而非假装文字坐在页面背景上（某品牌 page_22 实测：fill-opacity=0.55 色条上的白字
    被拿去跟白页面背景比出 4 条"隐形文字"，实际渲染底色是中绿）。
    返回 [(x, y, w, h, fill, opaque)] 按文档序——SVG 后画的在上层，面积并列时取文档序靠后者。"""
    out = []
    for tag, attr_str in _TAG_RE.findall(svg):
        if tag != "rect":
            continue
        a = _attrs(attr_str)
        fill = a.get("fill")
        if not fill or fill.strip().lower() == "none" or "transform" in a:
            continue
        x, y, w, h = _num(a, "x"), _num(a, "y"), _num(a, "width"), _num(a, "height")
        if w <= 0 or h <= 0:
            continue
        out.append((x, y, w, h, fill, _opaque(a)))
    return out


def _nearest_enclosing_fill(rects: list[tuple], tx: float, ty: float) -> tuple:
    """最近包含矩形推断（D18 FR1.5）：所有几何上包含锚点 (tx,ty) 的矩形里选**面积最小**的
    ——嵌套时小卡片比整页背景更贴近文字真实底色；面积并列取文档序靠后者（渲染栈更上层）。
    返回 (found, fill)：最近包含矩形不透明 → (True, 其fill)；最近包含矩形半透明 →
    (True, None)（有覆盖层但可见色是合成结果算不准 → 调用方跳过该文字，不退页面背景——
    页面背景已被这层挡住、不再是文字真实底色）；没有任何包含矩形 → (False, None)
    （调用方退回整页背景）。

    ⚠️ 边界声明：只做单层几何包含推断，不做透明度叠加合成、不做渲染栈遮挡判断
    （包含锚点但被更晚绘制的不相关矩形遮住的情形推断不出），锚点是 <text> 的 x/y 基线点、
    非文字包围盒——跨卡片边缘的长文字取的是锚点落点那张卡的底色。这些要真实渲染才算得准，
    机检宁可按最可能的单层解释推断、极端叠加场景留人审。"""
    best = None
    best_area = None
    for x, y, w, h, fill, opaque in rects:
        if x <= tx <= x + w and y <= ty <= y + h:
            area = w * h
            if best_area is None or area <= best_area:  # <=：并列取文档序靠后（更上层）
                best, best_area = (fill if opaque else None), area
    return (best_area is not None), best


def _text_background(svg_rects: list[tuple], a: dict, page_bg: str | None) -> str | None:
    """单个 <text> 的背景色推断（D18 FR1.5 共用入口）：有 x/y 锚点 → 最近包含矩形
    （不透明→用其fill；半透明→返回 None 让调用方跳过该文字·合成色算不准不硬比）；
    没有包含矩形、或 text 无锚点/带 transform（定位不了真实落点）→ 退回整页背景。"""
    if "transform" not in a and "x" in a and "y" in a:
        tx, ty = _num(a, "x"), _num(a, "y")
        found, fill = _nearest_enclosing_fill(svg_rects, tx, ty)
        if found:
            return fill  # fill=None 即"半透明覆盖·跳过不瞎猜"
    return page_bg


def check_contrast(svg: str) -> list[dict]:
    """H4 可读性对比度（D18 FR1.5 升级）：文字背景从"整页背景"升级为**最近包含矩形**——
    对每个 <text>，找几何上包含其锚点的、面积最小的实心 rect（fill 非 none·不透明·无
    transform），用该 rect 的 fill 当背景色跑 WCAG 公式（小字阈值 4.5，font-size≥24px
    大字阈值降 3.0）；找不到包含矩形才退回整页背景。升级动机：第一轮实测 24 页里深色卡片上
    的白字/金字全被拿去跟白色页面背景比，contrast+invisible 两条合计 121 条假阳性（需求
    定稿时基线·后经 D17 _canvas_size 修复余 77 条），机检警报刷屏让真问题被淹没。

    ⚠️ 边界（docstring 声明·D18 FR1.5）：只做单层几何包含推断，不做透明度叠加合成——
    半透明卡片（fill-opacity<1）的可见色是合成结果、不当背景候选（见 _opaque），这类文字
    退回整页背景比对；渐变背景 url(#g) 不是十六进制色 → contrast_ratio 返回 None 跳过不猜。
    """
    page_bg = _page_background(svg)
    rects = _bg_rect_candidates(svg)
    issues = []
    for tag, attr_str in _TAG_RE.findall(svg):
        if tag != "text":
            continue
        a = _attrs(attr_str)
        fill = a.get("fill")
        if not fill:
            continue
        bg = _text_background(rects, a, page_bg)
        if not bg:
            continue
        ratio = contrast_ratio(fill, bg)
        if ratio is None:
            continue
        if "font-size" in a:
            fs = _px_len(a["font-size"])
            if fs is None:
                continue  # 相对单位(em/%)算不出绝对像素·大小字阈值判不了·跳过不瞎猜
        else:
            fs = 16.0  # 无字号声明沿用原缺省16px·走小字阈值
        threshold = 3.0 if fs >= 24 else 4.5
        if ratio < threshold:
            issues.append({"rule": "low_contrast", "sev": "warn",
                            "note": f"文字色{fill} vs 背景{bg}(最近包含矩形推断) 对比度{ratio:.2f}<{threshold}"
                                    "（H4·WCAG公式）·若两色其一是 spec_lock 品牌色，这是品牌级决策不是单页改色"})
    return issues


def check_invisible_text(svg: str, *, threshold: float = 30.0) -> list[dict]:
    """隐形文字检测（2026-07-01 yanjiu研究驱动评估🟢采纳，出处：
    research_lib/开源拆解/04制作/Instrumenta.md L143「隐形文字(文字色≈背景色·RGB欧氏距离<30)」）：
    跟 check_contrast(H4·WCAG"读起来费不费劲"的可读性公式)是不同的问题——这条查"文字色和背景色
    数值上几乎相等"，判定为几乎不可见("根本看不见"而非"对比度低")，两者漏检的案例不同(如两色
    对比度技术上过线，但视觉上因为都是浅灰而近乎隐形的边界情况)。

    D18 FR1.5：背景推断与 check_contrast 同步升级为"最近包含矩形"（深色卡片上的白字不再
    被拿去跟白色页面背景比出"隐形"）；边界同 check_contrast docstring——单层几何包含推断，
    不做透明度叠加合成。
    """
    page_bg = _page_background(svg)
    rects = _bg_rect_candidates(svg)
    issues = []
    for tag, attr_str in _TAG_RE.findall(svg):
        if tag != "text":
            continue
        a = _attrs(attr_str)
        fill = a.get("fill")
        if not fill:
            continue
        fg_rgb = _hex_to_rgb(fill)
        if fg_rgb is None:
            continue
        bg = _text_background(rects, a, page_bg)
        bg_rgb = _hex_to_rgb(bg) if bg else None
        if bg_rgb is None:
            continue
        dist = sum((c1 - c2) ** 2 for c1, c2 in zip(fg_rgb, bg_rgb)) ** 0.5
        if dist < threshold:
            issues.append({"rule": "invisible_text", "sev": "warn",
                            "note": f"文字色{fill} 与背景{bg}(最近包含矩形推断) 几乎相同"
                                    f"(RGB欧氏距离{dist:.1f}<{threshold:g})"
                                    "·不是对比度低是根本看不见（隐形文字·Instrumenta）"})
    return issues


# 色盲模拟：Machado et al. 2009 (severity=1.0) 变换矩阵，**定义在线性 RGB 空间**（论文明确，
# DaltonLens-Python/colorspacious 等开源实现收录同一组数值）。
# 2026-07-02 saopan扫盘揪出（B1-2 换矩阵的 why）：此前用的是 HCIRN/colorjack 一脉的简化矩阵、
# 直接乘在 gamma 空间的 0-255 值上，注释却自称"线性RGB空间"——两处叠加的结果是等亮度红/绿对
# （色盲唯一的经典痛点）模拟后依然保持大差异，#CC0000/#009900 这类教科书混淆对系统性 0 检出；
# 实测那套简化矩阵即使搬进线性空间乘，三对典型红绿模拟后 sRGB 距离仍在 108~140，判据救不回来，
# 病根在矩阵本身。Machado 矩阵模拟后同样三对降到 30~80，与真实 CVD 模拟器结果一致。
_CVD_MATRICES = {
    "protanopia": ((0.152286, 1.052583, -0.204868),
                   (0.114503, 0.786281, 0.099216),
                   (-0.003882, -0.048116, 1.051998)),
    "deuteranopia": ((0.367322, 0.860646, -0.227968),
                     (0.280085, 0.672501, 0.047413),
                     (-0.011820, 0.042940, 0.968881)),
    "tritanopia": ((1.255528, -0.076749, -0.178779),
                   (-0.078411, 0.930809, 0.147602),
                   (0.004733, 0.691367, 0.303900)),
}


def _linear_to_srgb(c: float) -> float:
    """_srgb_to_linear 的逆变换（0-1 线性 → 0-255 sRGB）。分段点取 0.03928/12.92——跟本模块
    _srgb_to_linear 用的 WCAG 分段点互为反函数，保证灰阶往返无损。越界先截断（矩阵含负系数，
    强饱和色模拟后可能落在 [0,1] 外）。"""
    c = max(0.0, min(1.0, c))
    s = c * 12.92 if c <= 0.03928 / 12.92 else 1.055 * (c ** (1 / 2.4)) - 0.055
    return s * 255


def _simulate_cvd(rgb: tuple, kind: str) -> tuple:
    """模拟指定色盲类型看到的颜色（(r,g,b) 0-255 → (r,g,b) 0-255）。
    2026-07-02 saopan扫盘揪出：此前矩阵直接乘在 gamma 空间的 0-255 值上——CVD 矩阵定义在
    线性光空间，gamma 空间硬乘系统性算错模拟色。现在先过 WCAG 同款分段 gamma 转线性、
    乘完再逆变换回 sRGB。"""
    m = _CVD_MATRICES[kind]
    lin = tuple(_srgb_to_linear(c) for c in rgb)
    return tuple(_linear_to_srgb(m[i][0] * lin[0] + m[i][1] * lin[1] + m[i][2] * lin[2])
                 for i in range(3))


def _rgb_dist(a: tuple, b: tuple) -> float:
    return sum((c1 - c2) ** 2 for c1, c2 in zip(a, b)) ** 0.5


def check_colorblind_safe(palette: dict, *, min_distance: float = 85.0) -> list[dict]:
    """色盲友好配色检测（2026-07-01 yanjiu研究驱动评估🟢采纳·CVD视觉模拟，机制确定性、零模型参与，
    DaltonLens-Python/colorspacious 等开源库同类实现）：对 palette 里两两颜色对，正常视觉下可区分
    但 CVD 模拟后变得几乎相同 → warn（色盲用户可能分不清，这才是色盲特有的确切信号）。

    判定原语（2026-07-02 saopan扫盘揪出后重设计）：此前"正常可区分"门控和"模拟后分不清"判定
    都用 WCAG 亮度对比度——但正常视觉区分红/绿靠色相不靠亮度，等亮度红绿对（色盲唯一的经典
    痛点）对比度≈1 直接被门控跳过，#CC0000/#009900、#D62728/#2CA02C、#E74C3C/#2ECC71 三对
    教科书混淆色实测全 0 检出，检查形同虚设。换成 sRGB 欧氏距离（同模块 invisible_text 的
    "两色数值上几乎相等=看不见"同一原语）：门控"正常视觉可区分"=距离≥min_distance；判定
    "模拟后分不清"=模拟色距离<min_distance。阈值 85 的依据：上面三对典型红绿在 Machado 线性
    模拟后距离实测落在 30~80 区间（须全检出），黑白对 441 远在其上（不得误报），invisible_text
    的 <30 是"根本看不见"档、85≈其近3倍对应"类别色需要的区分度"档——数字来自真实混淆对实测，
    不是凭空编造。亮度差巨大的红绿对（如暗红#460917 vs 荧光绿#02FD5E）模拟后亮度差保留、
    距离仍大 → 正确不报（色盲者靠明度就能区分，旧算法拿它当典型恰是判据本末倒置）。

    spec_lock.py 目前只锁色值本身、没有这层检查——用法：构建 spec_lock 时对 palette 跑一次
    (同 validate_spec_lock 的"人工调用一次"用法)，不强制接进 pipeline 每页循环：这是 deck 级
    一次性的调色板质检，不是逐页机检，build_deck 当前 page-level issues 结构也未预留 deck 级 slot。
    """
    names = list(palette.keys())
    issues = []
    for i, name_a in enumerate(names):
        rgb_a = _hex_to_rgb(palette[name_a])
        if rgb_a is None:
            continue
        for name_b in names[i + 1:]:
            rgb_b = _hex_to_rgb(palette[name_b])
            if rgb_b is None:
                continue
            normal_dist = _rgb_dist(rgb_a, rgb_b)
            if normal_dist < min_distance:
                continue  # 正常视觉下本来就接近·不是色盲特有问题
            hits, worst = [], None
            for kind in ("protanopia", "deuteranopia", "tritanopia"):
                sim_dist = _rgb_dist(_simulate_cvd(rgb_a, kind), _simulate_cvd(rgb_b, kind))
                if sim_dist < min_distance:
                    hits.append(kind)
                    worst = sim_dist if worst is None else min(worst, sim_dist)
            if hits:
                # 一对问题色只报一条（命中的模拟类型并列在一起）——红绿对常在 protan/deutan
                # 下同时混淆，逐 kind 各报一条会把一个问题刷成 2-3 条，稀释真实问题数
                issues.append({"rule": "colorblind_unsafe", "sev": "warn", "cvd_type": "+".join(hits),
                               "note": f"「{name_a}」({palette[name_a]}) 与「{name_b}」({palette[name_b]}) "
                                       f"正常视觉下可区分(sRGB距离{normal_dist:.0f})，但{'/'.join(hits)}"
                                       f"模拟视角下最低降到{worst:.0f}<{min_distance:g}，"
                                       f"色盲用户可能分不清（CVD模拟·Machado 2009）"})
    return issues


def check_broken_image_href(svg: str) -> list[dict]:
    """H8 图片引用破损（轻量版）：<image> 标签 href/xlink:href 为空或缺失，不验证文件是否真实存在。"""
    issues = []
    for m in re.finditer(r"<image\b([^>]*)/?>", svg):
        a = _attrs(m.group(1))
        href = a.get("href") or a.get("xlink:href")
        if not href or not href.strip():
            issues.append({"rule": "broken_image_href", "sev": "warn", "note": "<image> 缺 href/xlink:href 或为空（H8）"})
    return issues


def check_letter_spacing(svg: str) -> list[dict]:
    """S6 CJK 字距过松：同一 <text> 标签同时直接带 letter-spacing 和 font-size 时，比值 > 5% 判松。"""
    issues = []
    for tag, attr_str in _TAG_RE.findall(svg):
        if tag != "text":
            continue
        a = _attrs(attr_str)
        if "letter-spacing" not in a or "font-size" not in a:
            continue
        ls, fs = _px_len(a["letter-spacing"]), _px_len(a["font-size"])
        if ls is None or fs is None:
            continue  # 带相对单位解析不出绝对像素·跳过不瞎猜（_px_len 文档注释同一病根）
        if fs > 0 and ls / fs > 0.05:
            issues.append({"rule": "loose_letter_spacing", "sev": "warn",
                            "note": f"letter-spacing={ls:g} / font-size={fs:g} = {ls/fs:.1%} > 5%（S6·CJK 字距过松）"})
    return issues


def check_font_grid(svg: str) -> list[dict]:
    """字号硬门接生产链路（2026-07-01 yanjiu研究驱动评估揪出：`rules.check_font` 写好+单测覆盖，
    但 `engine/pipeline.py` 从未调用——只有 `run_text_gate` 被接线，字号网格从未真正机检过任何一份
    生成出来的 SVG）：抠所有 `<text>` 的 `font-size`，逐个跑 `rules.check_font`（8 级网格·02 设计系统），
    不在网格 → warn。一个字号出现在多处各判各的（不去重）——同 `check_letter_spacing` 风格，
    每处违规都是一个独立的可定位问题，去重会藏起"这一页到底有几处字号不对"的真实数量。
    """
    issues = []
    for tag, attr_str in _TAG_RE.findall(svg):
        if tag != "text":
            continue
        a = _attrs(attr_str)
        if "font-size" not in a:
            continue
        fs = _px_len(a["font-size"])
        if fs is None:
            continue  # 相对单位/畸形值·跳过不瞎猜（此前 _num 静默归0·报幽灵违规 got:0）
        issues.extend(G.check_font(int(round(fs))))
    return issues


def check_font_variety_per_page(svg: str, *, max_sizes: int = 4) -> list[dict]:
    """单页字号种类数上限（2026-07-01 yanjiu研究驱动评估🟡走样需修，出处：
    research_lib/开源拆解/04制作/Instrumenta.md L143「字号种类超限(默认≤4)」）：跟
    check_font_grid(单个字号是否落在8级网格上)、spec_lock.font_grid(deck级网格是什么)都不是
    同一件事——这条查"这一页用了几种不同字号"，是遗漏维度不是走样(本项目"预注册优于事后侦测"
    的设计比 Instrumenta 事后统计众数更优，不建议改成那套，但这个维度本身此前确实没有对应物)。

    ⚠️ 阈值沿用 Instrumenta 默认值(≤4)，未经本项目真实deck校准是否适配咨询级deck——但只是
    warn(先当观察信号非硬拦截)，且这个阈值来自真实拆过的开源实现(不是本项目凭空编造数字，
    跟 check_field_budget/count_visual_blocks 那种"完全没有来源"的情况不同)，先接上收集真实
    信号，比空等"校准完成"更有价值——warn 级的可逆性足够低风险，不是"标尺来自真实样本"纪律
    要拦的对象(那条纪律拦的是编造 error 级硬阈值，不是审慎地用有来源的数字起步观察)。
    """
    sizes = set()
    for tag, attr_str in _TAG_RE.findall(svg):
        if tag != "text":
            continue
        a = _attrs(attr_str)
        fs = _px_len(a.get("font-size"))
        if fs is not None:  # 相对单位解析不了就不计入种类数·别把"14px"们静默归成一种 0
            sizes.add(fs)
    if len(sizes) > max_sizes:
        return [{"rule": "font_variety_over_limit", "sev": "warn", "got": len(sizes), "cap": max_sizes,
                 "note": f"本页用了{len(sizes)}种字号{sorted(sizes)}，超过{max_sizes}种"
                         f"（字号种类过多易显凌乱，是否可以合并成更少档位？·Instrumenta启发）"}]
    return []


def check_edge_alignment(svg: str, *, tol: float = 3.0) -> list[dict]:
    """对齐（Instrumenta 启发）：两个(或以上) <rect> 的 x（左边界）或 y（上边界）差值落在 (0, tol] 内——
    很可能是想对齐但没对准（典型如两张卡片左边界差 1-2px，肉眼看不出但读起来不齐）。
    差值=0 视为已对齐不报；差值>tol 视为有意错开不报。只比 <rect>（卡片/图表矩形最常见的对齐场景），
    不比 <text>——文字锚点跟视觉左边界常有字体量出的系统性偏差，比了会全是误报。
    """
    xs, ys = [], []
    for tag, attr_str in _TAG_RE.findall(svg):
        if tag != "rect":
            continue
        a = _attrs(attr_str)
        xs.append(_num(a, "x"))
        ys.append(_num(a, "y"))
    issues = []
    for label, vals in (("x（左边界）", xs), ("y（上边界）", ys)):
        uniq = sorted(set(vals))
        for a, b in zip(uniq, uniq[1:]):
            gap = b - a
            if 0 < gap <= tol:
                issues.append({"rule": "near_miss_alignment", "sev": "warn",
                                "note": f"两个(或以上) <rect> 的{label}只差{gap:g}px({a:g} vs {b:g})——"
                                        f"像是想对齐但没对准，确认是否该改成同一个值（对齐·Instrumenta）"})
    return issues


def check_equal_distribution(svg: str, *, tol_ratio: float = 0.15) -> list[dict]:
    """等距分布（Instrumenta 启发）：同一行(y/height 相同)≥3 个 <rect> 按 x 排序后，检查彼此间距是否
    基本相等——最大最小间距差 > 平均间距的 tol_ratio 判不匀。典型如一排 3-5 张卡片/图例块，
    等距是"编排整齐"的基本要求，人工摆放最容易在这里翻车。忽略重叠(负间距)——那不是这条检查的目标。
    """
    groups: dict[tuple, list[dict]] = {}
    for tag, attr_str in _TAG_RE.findall(svg):
        if tag != "rect":
            continue
        a = _attrs(attr_str)
        y, h = round(_num(a, "y"), 1), round(_num(a, "height"), 1)
        if h <= 0:
            continue
        groups.setdefault((y, h), []).append({"x": _num(a, "x"), "w": _num(a, "width")})
    issues = []
    for (y, h), items in groups.items():
        if len(items) < 3:
            continue
        items.sort(key=lambda it: it["x"])
        gaps = [items[i + 1]["x"] - (items[i]["x"] + items[i]["w"]) for i in range(len(items) - 1)]
        gaps = [g for g in gaps if g > 0]
        if len(gaps) < 2:
            continue
        avg = sum(gaps) / len(gaps)
        if avg <= 0:
            continue
        spread = (max(gaps) - min(gaps)) / avg
        if spread > tol_ratio:
            issues.append({"rule": "uneven_distribution", "sev": "warn",
                            "note": f"y={y:g} 这一行 {len(items)} 个 <rect> 间距不均：{[round(g, 1) for g in gaps]}"
                                    f"（最大最小差{spread:.0%}>{tol_ratio:.0%}·像手摆没用等距分布，"
                                    f"等距分布·Instrumenta）"})
    return issues


def check_uniform_size(svg: str, *, tol: float = 3.0) -> list[dict]:
    """同尺寸（Instrumenta 启发）：同一行(y 相同)≥2 个 <rect>，高度只差 tol 内但不相等——很可能该是
    同尺寸的一组（如一排指标卡/图例块）。差几像素比明显不同尺寸更像失误——明显不同尺寸大概率是
    有意为之，这里只抓"看起来想一样但没量准"这类近失误。
    """
    groups: dict[float, list[float]] = {}
    for tag, attr_str in _TAG_RE.findall(svg):
        if tag != "rect":
            continue
        a = _attrs(attr_str)
        y = round(_num(a, "y"), 1)
        h = _num(a, "height")
        if h <= 0:
            continue
        groups.setdefault(y, []).append(h)
    issues = []
    for y, heights in groups.items():
        if len(heights) < 2:
            continue
        uniq = sorted(set(heights))
        for a, b in zip(uniq, uniq[1:]):
            gap = b - a
            if 0 < gap <= tol:
                issues.append({"rule": "near_miss_size", "sev": "warn",
                                "note": f"y={y:g} 同一行两个(或以上) <rect> 高度只差{gap:g}px({a:g} vs {b:g})"
                                        f"——像是想同尺寸但没量准（同尺寸·Instrumenta）"})
    return issues


def check_aspect_ratio(svg: str, *, tol: float = 0.02) -> list[dict]:
    """constraint verify 一支（05 质量门·宽高比）：<svg> 根元素声明的画布宽高须落在 16:9 或 4:3
    容差内——行业标准格式判定（客观技术规格，非"最佳实践"判断，不需真实样本背书）。
    页数区间/语言两支 constraint verify 未落地（05 只引了 PPTEval 有这概念，没给这个项目自己的真实
    数字依据；语言校验对目前纯中文场景价值低），按"标尺来自真实样本非模型常识"的纪律不编阈值。
    """
    m = _SVG_ROOT_RE.search(svg)
    if not m:
        return []
    a = _attrs(m.group(1))
    w, h = _num(a, "width"), _num(a, "height")
    if (w <= 0 or h <= 0) and a.get("viewBox"):
        # 2026-07-03 二轮扫盘揪出：只按空白切、不吃逗号分隔——"0,0,1280,720" 合法形态
        # （SVG 规范允许逗号+空白混用）解析成 1 段 → 整条检查静默跳过。改成逗号+空白兼容，
        # 对照同文件 _canvas_size() 与 svg_compat.py 的既有兼容写法统一。
        nums = [t for t in re.split(r"[\s,]+", a["viewBox"].strip()) if t]
        if len(nums) == 4:
            try:
                w, h = float(nums[2]), float(nums[3])
            except ValueError:
                return []
    if w <= 0 or h <= 0:
        return []
    ratio = w / h
    if any(abs(ratio - r) / r <= tol for r in ACCEPTED_ASPECT_RATIOS.values()):
        return []
    nearest_name, nearest_r = min(ACCEPTED_ASPECT_RATIOS.items(), key=lambda kv: abs(ratio - kv[1]))
    return [{"rule": "aspect_ratio_off", "sev": "warn",
             "note": f"画布 {w:g}x{h:g}(比例{ratio:.3f}) 未落在 16:9/4:3 容差内"
                     f"(最接近{nearest_name}={nearest_r:.3f})（constraint verify·宽高比）"}]


# ── D18 FR3.2 chart 兑现机检 ────────────────────────────────────────────────
# 第一轮实测确诊：storyline 声明 20 种 chart，渲染出的 SVG 里兑现 0 种（全部塌缩成卡片网格）
# ——声明与渲染之间没有任何强制传导管道。这里按"chart 类型→期望视觉元素"做启发式核对，
# 查不到 → warn 喂人审（是刻意改用其他表达还是没兑现，语义判断留人）。
# **宁漏勿噪**：判定"已兑现"的条件刻意宽松（阈值保守），未知 chart 名不查——启发式有误报
# 风险（需求§七已定 warn 级缓解），漏报比刷屏可接受。
_CHART_EL_RE = re.compile(r"<(path|polyline|polygon|rect|circle)\b([^>]*?)/?>")
# path d 属性的曲线/弧命令（C/S/Q/T/A 大小写）——直线装饰（纯 M/L）不算折线图证据
_CURVE_CMD_RE = re.compile(r"[CSQTA]", re.IGNORECASE)
_LINE_CMD_RE = re.compile(r"[Ll]")


def _chart_elements(svg: str) -> list[tuple]:
    """抽 chart 判定用元素：[(tag, attrs)]。rect 排除整页背景（跟画布同尺寸）。"""
    canvas_w, canvas_h = _canvas_size(svg)
    out = []
    for tag, attr_str in _CHART_EL_RE.findall(svg):
        a = _attrs(attr_str)
        if tag == "rect" and _num(a, "width") == canvas_w and _num(a, "height") == canvas_h:
            continue
        out.append((tag, a))
    return out


def _has_line_shape(els) -> bool:
    """折线/曲线证据：path 的 d 含曲线命令 或 ≥2 个折线段命令（多段折线）；或 polyline ≥3 个点。"""
    for tag, a in els:
        if tag == "path":
            d = a.get("d", "")
            if _CURVE_CMD_RE.search(d) or len(_LINE_CMD_RE.findall(d)) >= 2:
                return True
        elif tag == "polyline":
            pts = re.findall(r"[-\d.]+[\s,]+[-\d.]+", a.get("points", ""))
            if len(pts) >= 3:
                return True
    return False


def _solid_rects(els) -> list[dict]:
    return [a for tag, a in els
            if tag == "rect" and a.get("fill") and a["fill"].strip().lower() != "none"]


def _has_bar_shape(els) -> bool:
    """柱状证据：≥2 个高度不同的实心 rect（正常柱状图各柱高随数据变化）。"""
    heights = {_num(a, "height") for a in _solid_rects(els) if _num(a, "height") > 0}
    return len(heights) >= 2


def _has_taper_shape(els) -> bool:
    """金字塔/漏斗证据：≥3 个宽度互不相同的实心 rect（逐层递变的宽松近似——不校验单调性，
    宁漏勿噪）；或存在 polygon（梯形层/三角是这两类图最常见的画法）。"""
    if any(tag == "polygon" for tag, _ in els):
        return True
    widths = {_num(a, "width") for a in _solid_rects(els) if _num(a, "width") > 0}
    return len(widths) >= 3


def _has_arc_shape(els) -> bool:
    """环/饼证据：circle 带 stroke-dasharray（SVG 环图标准画法）或 path 的 d 含 A 弧命令。"""
    for tag, a in els:
        if tag == "circle" and a.get("stroke-dasharray"):
            return True
        if tag == "path" and re.search(r"[Aa]", a.get("d", "")):
            return True
    return False


def _has_map_shape(els, svg: str = "") -> bool:
    """地图证据：path 数 ≥3（轮廓/省界通常多路径）或存在 <image>（底图贴图画法）。"""
    return sum(1 for tag, _ in els if tag == "path") >= 3 or "<image" in svg


# chart 声明名 → 判定函数（只列需求 FR3.2 拍板的启发式映射；未列出的 chart 名一律不查——
# 坏例子映射靠飞轮从每单实测积累，别凭模型常识预填一堆没校准过的判定）
CHART_REALIZATION_CHECKS = {
    "line": _has_line_shape, "line_compare": _has_line_shape,
    "bar": _has_bar_shape, "bar_callout": _has_bar_shape,
    "pyramid": _has_taper_shape, "kol_pyramid": _has_taper_shape,
    "funnel": _has_taper_shape, "aipl_funnel": _has_taper_shape,
    "donut": _has_arc_shape, "pie": _has_arc_shape,
    "map": _has_map_shape, "expansion_map": _has_map_shape,
}


def check_chart_realized(svg_text: str, declared_chart: str | None) -> list[dict]:
    """chart 兑现机检（D18 FR3.2·warn）：按 storyline/spec_lock 声明的 chart 类型，在渲染出的
    SVG 里找期望的视觉元素——声明 line_compare 的页连一条折线都没有，就是"声明了没兑现"的
    结构信号。查不到 → warn 喂人审（可能是刻意改用其他表达，机检不代判好坏·铁律2）；
    未知 chart 名（映射表没有的）→ 不查返回 []。宁漏勿噪：判定"已兑现"的条件刻意宽松。
    """
    if not declared_chart:
        return []
    checker = CHART_REALIZATION_CHECKS.get(declared_chart)
    if checker is None:
        return []  # 未知 chart 名不查·宁漏勿噪
    els = _chart_elements(svg_text)
    ok = checker(els, svg_text) if checker is _has_map_shape else checker(els)
    if ok:
        return []
    return [{"rule": "chart_not_realized", "sev": "warn", "chart": declared_chart,
             "note": f"声明 chart=「{declared_chart}」，渲染 SVG 里未见对应视觉元素"
                     f"——是刻意改用其他表达还是没兑现？（D18 FR3.2·启发式宁漏勿噪·"
                     f"第一轮实测声明20种兑现0确诊）"}]


_DENSITY_CELL = 40  # 40px 格·1280x720 画布下整除成 32x18 网格


def count_visual_blocks(svg: str) -> int:
    """数视觉块（2026-07-01 yanjiu研究驱动评估🟢采纳，出处：05号本文档§四引
    02_页型手法精华.md L73「每内容页≥3视觉块」）：数非纯装饰的内容元素——<rect>(排除跟画布
    同尺寸的整页背景)/<circle>/<image>，不数<text>(文字不算独立"视觉块"，是文字本身)。

    ⚠️ 只给数字，不判定"够不够"：「≥3」这个阈值来自单一开源实现且该笔记自己标注"未经拆真实
    deck验证"（同 check_field_budget 不预置阈值的理由——标尺来自真实样本非模型常识，见
    reinforce/deck_rules/rules.py::check_field_budget 文档），落地成机检门前需要先拆真实
    deck 校准这个数字是否适配咨询级 deck，这里只提供可复用的测量原语。
    """
    blocks = 0
    for tag, attr_str in _TAG_RE.findall(svg):
        if tag == "text":
            continue
        a = _attrs(attr_str)
        if tag == "rect" and _num(a, "width") == CANVAS_W and _num(a, "height") == CANVAS_H:
            continue  # 整页背景不算视觉块
        blocks += 1
    return blocks


def content_area_ratio(svg: str, *, canvas_w: int = CANVAS_W, canvas_h: int = CANVAS_H) -> float:
    """内容区使用率（出处同 count_visual_blocks，02号L73「内容区使用率≥50%」）：用粗网格
    (40px格)近似算内容元素覆盖的画布面积占比——避免简单"面积求和"在元素重叠时重复计数，不需要
    引入计算几何库做精确多边形并集。只统计 <rect>(排除整页背景)/<circle>/<image> 的包围盒，
    <text> 不计入(同 count_visual_blocks 的理由)。

    ⚠️ 同上：只给数字不判定"够不够"——「≥50%」阈值来源同样薄弱，落地前需真实 deck 校准。
    """
    cols, rows = canvas_w // _DENSITY_CELL, canvas_h // _DENSITY_CELL
    if cols <= 0 or rows <= 0:
        return 0.0
    covered = [[False] * cols for _ in range(rows)]
    for tag, attr_str in _TAG_RE.findall(svg):
        if tag == "text":
            continue
        a = _attrs(attr_str)
        if tag == "rect":
            x, y, w, h = _num(a, "x"), _num(a, "y"), _num(a, "width"), _num(a, "height")
            if w == canvas_w and h == canvas_h:
                continue
        elif tag == "circle":
            cx, cy, r = _num(a, "cx"), _num(a, "cy"), _num(a, "r")
            x, y, w, h = cx - r, cy - r, 2 * r, 2 * r
        elif tag == "image":
            x, y, w, h = _num(a, "x"), _num(a, "y"), _num(a, "width"), _num(a, "height")
        else:
            continue
        if w <= 0 or h <= 0:
            continue
        # 右/下边界用 ceil 而非 "floor+1"——边界正好落在格线上时(如 x+w 恰是 cell 的整数倍)
        # "floor+1" 会多算出一格越界的假覆盖，ceil 才是"这个范围实际跨了几格"的正确算法。
        c0, c1 = max(0, int(x // _DENSITY_CELL)), min(cols, math.ceil((x + w) / _DENSITY_CELL))
        r0, r1 = max(0, int(y // _DENSITY_CELL)), min(rows, math.ceil((y + h) / _DENSITY_CELL))
        for r in range(r0, r1):
            for c in range(c0, c1):
                covered[r][c] = True
    return sum(row.count(True) for row in covered) / (cols * rows)


def run_visual_gate(svg: str) -> list[dict]:
    """汇总十一条结构级视觉机检（H1/H4/H8/S6 + 对齐/等距分布/同尺寸 + 宽高比 + 字号网格 + 隐形文字
    + 字号种类数）。全 warn——不阻断导出，喂人审，跟 spec_lock 越界用色同级。"""
    return (check_out_of_canvas(svg) + check_contrast(svg) + check_invisible_text(svg)
            + check_broken_image_href(svg) + check_letter_spacing(svg)
            + check_edge_alignment(svg) + check_equal_distribution(svg) + check_uniform_size(svg)
            + check_aspect_ratio(svg) + check_font_grid(svg) + check_font_variety_per_page(svg))


# ---------- D26 二轮扫盘：声明→兑现机检（图标/图片·对照 check_chart_realized 模式） ----------

def check_icons_realized(svg_texts: list[str], spec_lock: dict | None) -> list[dict]:
    """图标兑现机检（D26·warn·deck 级）：spec_lock 声明了 icons.inventory，全 deck SVG 里却
    一个 data-icon 占位符都没有 → "声明了没兑现"。

    二轮扫盘确诊：5/6 份真实 deck 声明了图标清单（合计 64 个图标位），SVG 占位符命中率 0%——
    机制文档/prompt/SKILL 全在讲这套占位+finalize 展开，从没有一份真实 deck 用过；chart 有
    兑现机检（FR3.2）图标没有，本函数补齐。宁漏勿噪：有任一占位即算兑现（数量不苛求）。
    """
    icons = (spec_lock or {}).get("icons") or {}
    inventory = icons.get("inventory") or []
    if not inventory:
        return []
    if any("data-icon" in (t or "") for t in svg_texts):
        return []
    return [{"rule": "icons_not_realized", "sev": "warn",
             "note": f"spec_lock 声明图标清单 {len(inventory)} 个（library={icons.get('library')}），"
                     f"全 deck SVG 零 data-icon 占位——是刻意不用图标还是忘了机制？"
                     f"（用法见制作 SKILL 图标段·占位符经导出链 finalize 自动展开·D26 兑现机检）"}]


def check_images_realized(svg_texts: list[str], spec_lock: dict | None,
                          images_dir=None) -> list[dict]:
    """图片兑现机检（D26·warn·deck 级）：spec_lock.images 清单逐行核对落地——filename 既没被
    任何 SVG 引用、workspace images/ 目录下也不存在 → 计入缺失清单。

    二轮扫盘确诊：某品牌 声明 9 张有具体用途的图（KV概念/产品moment/包装卡）实际 0 张落地，
    对照 059（4/4 全落地）说明机制能跑、那单是孤立回归——但此前没有任何机检能发现这种整批
    未兑现。acquire_via=placeholder 的行不计缺失（真人接管是设计过的状态）。全部缺失才 warn
    整单（部分缺失列名单同样 warn）——宁漏勿噪，判好坏留人审（铁律2）。
    """
    from pathlib import Path as _P
    rows = (spec_lock or {}).get("images") or []
    checkable = [r for r in rows if r.get("filename") and r.get("acquire_via") != "placeholder"]
    if not checkable:
        return []
    joined = "\n".join(t or "" for t in svg_texts)
    missing = []
    for r in checkable:
        fn = r["filename"]
        in_svg = fn in joined
        on_disk = bool(images_dir) and (_P(images_dir) / fn).is_file()
        if not (in_svg or on_disk):
            missing.append(fn)
    if not missing:
        return []
    return [{"rule": "images_not_realized", "sev": "warn", "missing": missing,
             "note": f"images 清单 {len(checkable)} 张可核对，{len(missing)} 张未落地"
                     f"（SVG 无引用且 images/ 目录无文件）：{missing[:6]}——设计定稿排的图像位"
                     f"整批蒸发是 某品牌 单确诊的孤立回归形态（D26 兑现机检·判取舍留人审）"}]
