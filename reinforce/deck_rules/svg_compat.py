"""SVG → PPTX 导出兼容性机检（提炼自 ppt-master `references/shared-standards.md` §1/§2，779 行黑名单）。

⚠️ 真实背景：这份文档此前从未被读过——手写了 CFO/Descente 等多份 SVG，全靠运气没踩雷
（用的元素够简单：rect/text/circle/line，没碰 mask/style/class/rgba 这些）。第一次真读完整份
文档后才发现：我们的转换引擎 `engine/svg2pptx`（vendor 自 ppt-master）和这份黑名单是**同一套规则**，
之前"没出事"是没遇到诱发条件，不是真的遵守。现在补成机检，自动拦截而非靠记忆。

只机检**能用确定性正则判死**的项（结构性黑名单 + PPT 不识别的颜色/透明度语法）；
更语义化的规则（如"inline tspan 不能带 x/y/dy 除非真的换行"）留文档提醒，机检会有误判风险。
"""

from __future__ import annotations

import re

# 结构性黑名单（shared-standards.md §1）：出现即导出失败/损坏
_STRUCTURAL_BANNED = [
    (r"<mask\b", "mask"), (r"<style\b", "<style>"), (r'\bclass="', "class 属性"),
    (r"<foreignObject\b", "foreignObject"), (r"<symbol\b", "symbol"),
    (r"\btextPath\b", "textPath"), (r"@font-face", "@font-face"),
    (r"<animate\w*\b", "animate*"), (r"<set\b", "<set>"),
    (r"<script\b", "script"), (r"<iframe\b", "iframe"),
]
# PPT 不识别的颜色/透明度语法（§2）：有正确替代写法，必须用替代
# 2026-07-02 saopan扫盘揪出：原 `\bopacity` 的词边界在 fill-opacity 的 "-o" 处也成立（- 非词字符），
# 把官方推荐替代写法 fill-opacity/stroke-opacity 一并误杀成 error（项目自带模板
# pyramid_isometric.svg 实测被拦）。改负向后顾 (?<![-\w]) 排除带前缀的属性名，并兼容单引号属性值。
_COMPAT_BANNED = [
    (r"rgba\s*\(", "rgba()", "用 fill=\"#HEX\" + fill-opacity=\"0.x\" 替代"),
    (r'<g\b[^>]*(?<![-\w])opacity=["\']', "<g opacity=>", "对每个子元素分别设 fill-opacity/stroke-opacity"),
    (r'<image\b[^>]*(?<![-\w])opacity=["\']', "<image opacity=>", "叠一层 <rect fill=\"底色\" opacity=\"x\"/> 遮罩层"),
]
# 裸露未转义的 XML 保留字符（§1.0）：一个字符就让整个文件导出失败
_XML_ENTITY_OK = re.compile(r"&(amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);")

_SVG_ROOT_RE = re.compile(r"<svg\b([^>]*)>")
# 2026-07-02 saopan扫盘揪出：属性正则只认双引号——viewBox='...'（XML 合法写法）被误报"缺 viewBox"。
# 两个捕获组各接一种引号，_parse_attrs 里挑非 None 的那组。
_ATTR_RE = re.compile(r'([\w:-]+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\')')


def _parse_attrs(attr_str: str) -> dict:
    return {m.group(1): m.group(2) if m.group(2) is not None else m.group(3)
            for m in _ATTR_RE.finditer(attr_str)}


def check_viewbox_consistency(svg: str, *, tol: float = 0.02) -> list[dict]:
    """viewBox 与 width/height 一致性（2026-07-01 yanjiu研究驱动评估🟢采纳，出处：
    research_lib/开源拆解/01应用/ppt-master.md L83，源自 svg_quality_checker.py）：
    只有 width/height、缺 viewBox → error；两者都声明但数值不一致(容差2%，同 visual_review.py
    check_aspect_ratio 同一套判定逻辑) → error——vendor 转换引擎按 viewBox 建坐标系，
    数值对不上会导致导出后画布比例/元素坐标错乱，跟本模块其余检查同一严重度(非品味问题)。
    两者都没声明（还没到画布尺寸这步）不是这条检查的目标，跳过不瞎猜。
    """
    m = _SVG_ROOT_RE.search(svg)
    if not m:
        return []
    a = _parse_attrs(m.group(1))
    has_wh = "width" in a and "height" in a
    if "viewBox" not in a:
        if has_wh:
            return [{"rule": "svg_viewbox_missing", "sev": "error",
                     "note": "<svg> 根标签缺 viewBox（有 width/height 但无 viewBox·导出后坐标系可能错乱）"}]
        return []
    # 2026-07-02 saopan扫盘揪出：viewBox 数值只按空白切——逗号分隔"0,0,1280,720"是 SVG 规范
    # 明写的合法列表语法(comma-or-space separated)，此前被误报 malformed。
    nums = [t for t in re.split(r"[\s,]+", a["viewBox"].strip()) if t]
    if len(nums) != 4:
        return [{"rule": "svg_viewbox_malformed", "sev": "error",
                 "note": f'<svg> viewBox="{a["viewBox"]}" 格式非法(应为4个数字)'}]
    try:
        vb_w, vb_h = float(nums[2]), float(nums[3])
    except ValueError:
        return [{"rule": "svg_viewbox_malformed", "sev": "error",
                 "note": f'<svg> viewBox="{a["viewBox"]}" 含非数字'}]
    if not has_wh or vb_w <= 0 or vb_h <= 0:
        return []
    try:
        w, h = float(a["width"]), float(a["height"])
    except ValueError:
        return []  # width/height 带单位(如"100%")非纯数字，跳过不瞎猜
    if abs(w - vb_w) / vb_w > tol or abs(h - vb_h) / vb_h > tol:
        return [{"rule": "svg_viewbox_mismatch", "sev": "error",
                 "note": f"<svg> width/height=({w:g},{h:g}) 与 viewBox 声明的({vb_w:g},{vb_h:g}) "
                         f"不一致(容差{tol:.0%})"}]
    return []


def check_svg_compat(svg: str) -> list[dict]:
    """机检 SVG 是否踩中 ppt-master 转换引擎的已知不兼容写法。全部 error（导出会失败/损坏，非品味问题）。"""
    issues: list[dict] = []
    # 2026-07-03 二轮扫盘批D：黑名单此前大小写敏感——<MASK>/<Style>/CLASS=/RGBA( 这类变体漏检
    # （vendor 转换引擎同样不认这些写法，大小写变了照样导出损坏），改 IGNORECASE 一律拦。
    # 合法 XML 实体白名单（_XML_ENTITY_OK）不跟着放宽：&AMP; 本就不是合法实体，该按裸 & 拦。
    for pattern, name in _STRUCTURAL_BANNED:
        if re.search(pattern, svg, re.IGNORECASE):
            issues.append({"rule": "svg_banned_feature", "sev": "error",
                           "note": f"用了禁用特性「{name}」(shared-standards.md §1)·PPT 导出会失败"})
    for pattern, name, fix in _COMPAT_BANNED:
        if re.search(pattern, svg, re.IGNORECASE):
            issues.append({"rule": "svg_incompat_syntax", "sev": "error",
                           "note": f"用了 PPT 不识别的「{name}」(shared-standards.md §2)·改法：{fix}"})
    # 裸 & ：排除合法实体后，剩下的 & 都是非法的
    bare_amp = _XML_ENTITY_OK.sub("", svg)
    if "&" in bare_amp:
        issues.append({"rule": "svg_unescaped_xml", "sev": "error",
                       "note": "含未转义的裸 & （非 &amp;/&lt; 等合法实体）·一个字符让整个文件导出失败"})
    issues += check_viewbox_consistency(svg)
    return issues
