"""D18 FR7.5 图标接线——5 库 11631 个图标（engine/ppt_master/templates/icons/）的存在性验证与读取。

spec_lock 侧契约（reinforce/spec_lock.py 已就位）：icons={"library": 5库锁1, "inventory": [图标名…]}，
一 deck 锁一库、Executor 只准用 inventory 清单内图标。本模块补三件确定性工具：
① list_icon_libraries()  —— 有哪些库可选（真实 ls，不写死清单）；
② verify_inventory()     —— inventory 逐名验证文件真存在，缺名返回缺失清单（fail-closed 素材：
                            调用方拿到 missing 非空该拒绝/强制重选，本函数只报事实不代做决策）；
③ icon_svg()             —— 读单个图标 SVG 源码（finalize 内嵌 <use data-icon="名"> 占位时用）。

图标名 = 文件名去 .svg（如 tabler-outline 库的 "abacus" → abacus.svg），传名带不带 .svg 后缀都认。
"""

from __future__ import annotations

from pathlib import Path

# 5 个图标库所在目录（chunk-filled / phosphor-duotone / simple-icons / tabler-filled / tabler-outline）
ICONS_DIR = Path(__file__).resolve().parent / "ppt_master" / "templates" / "icons"


def list_icon_libraries() -> list[str]:
    """列出可用图标库（icons/ 下的子目录名·排序保确定性）。目录缺失 → []。"""
    if not ICONS_DIR.is_dir():
        return []
    return sorted(p.name for p in ICONS_DIR.iterdir() if p.is_dir())


def _icon_path(library: str, name: str) -> Path:
    """图标名 → 文件路径（防路径穿越：解析后必须仍在该库目录内，越界直接拒——fail-closed）。"""
    fname = str(name) if str(name).endswith(".svg") else f"{name}.svg"
    p = (ICONS_DIR / str(library) / fname).resolve()
    lib_root = (ICONS_DIR / str(library)).resolve()
    if lib_root not in p.parents:
        raise ValueError(f"图标名 {name!r} 解析越出库目录（禁止 ../ 之类路径穿越）")
    return p


def verify_inventory(library: str, names: list[str] | None) -> dict:
    """逐个验证 inventory 图标文件存在 → {library, library_exists, missing, valid}。

    fail-closed 给调用方决定：库不存在 → missing=全部名字、valid=False；
    库存在但有缺名 → missing=缺失清单、valid=False（该强制重选，别静默放行让页面上
    出现空 <use> 占位）。names 为空清单 → valid 跟库存在性走（空清单本身该不该允许
    由 validate_spec_lock 管——它已拒"icons 填了但 inventory 为空"）。
    """
    names = list(names or [])
    lib_exists = bool(library) and (ICONS_DIR / str(library)).is_dir()
    if not lib_exists:
        return {"library": library, "library_exists": False, "missing": names, "valid": False}
    missing = []
    for nm in names:
        try:
            if not _icon_path(library, nm).is_file():
                missing.append(nm)
        except ValueError:
            missing.append(nm)  # 路径穿越名按"缺失"计——反正不许用
    return {"library": library, "library_exists": True, "missing": missing,
            "valid": not missing}


def icon_svg(library: str, name: str) -> str:
    """读单个图标 SVG 源码（finalize 内嵌占位用）。文件不存在 → FileNotFoundError（fail-closed，
    不返回空串——空串内嵌进页面就是静默丢图标）。"""
    p = _icon_path(library, name)
    if not p.is_file():
        raise FileNotFoundError(
            f"图标 {name!r} 在库 {library!r} 中不存在（{p}）——先用 verify_inventory 验清单再引用")
    return p.read_text(encoding="utf-8")
