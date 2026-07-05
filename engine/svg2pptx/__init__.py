"""SVG→DrawingML 转换引擎 —— vendored from ppt-master（hugohe3·MIT·决策 D1）。

来源：PPT开源参考/01_AI端到端应用/ppt-master/skills/ppt-master/scripts/{svg_to_pptx,svg_finalize}/
+ console_encoding.py。原 11410 行纯 Python·只依赖 python-pptx。MIT 见 LICENSE.ppt-master。
我们站在它的"制作底座"上，火力集中到它没做的「策略大脑 + 高 stakes 数据保真」（见 specs/决策记录.md D1）。

公共 API：
- create_pptx_with_native_svg(svg_files, output_path, ...)：从 SVG 文件列表构建原生可编辑 .pptx
- convert_svg_to_slide_shapes(svg)：SVG → DrawingML slide XML
"""

from __future__ import annotations

import sys
from pathlib import Path

# 让内部兄弟包(svg_finalize / console_encoding)的绝对 import 可解析
sys.path.insert(0, str(Path(__file__).resolve().parent))

from svg_to_pptx import (  # noqa: E402
    convert_svg_to_slide_shapes,
    create_pptx_with_native_svg,
)

__all__ = ["create_pptx_with_native_svg", "convert_svg_to_slide_shapes", "export_deck"]


def export_deck(svg_files, output_path, **kw) -> bool:
    """便捷导出·默认 use_native_shapes=True（保证原生可编辑·非栅格化文字·D1 质量基准）。

    ⚠️ 关键坑：create_pptx_with_native_svg 默认 use_native_shapes=False 会把**文字栅格化成图片**；
    必须 True 才出全原生可编辑（<a:t> 文字 + <p:sp> 形状）。本封装默认开，端到端调用走这个。
    """
    kw.setdefault("use_native_shapes", True)
    kw.setdefault("verbose", False)
    return create_pptx_with_native_svg([Path(f) for f in svg_files], Path(output_path), **kw)
