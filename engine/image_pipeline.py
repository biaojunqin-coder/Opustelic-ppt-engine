"""图像获取链路薄适配层（D18 FR7.4 六源获取 + FR4.2 BYO key + FR4.3 生图管线）。

职责：spec_lock.images 清单行（schema 见 reinforce/spec_lock.py::IMAGE_ROW_REQUIRED）
→ 按 acquire_via 六源分发获取 → 统一返回 {"status", "path", "note", ...}。
vendor 资产（engine/ppt_master/）的接线原则：**能 import 绝不重写**——
web 四免 key 图库检索复用 vendor scripts/image_search.py 的 search_and_download
（那是查询递进/评分/许可证分级/下载质检的成熟链路）；本层只做参数拼装与返回值归一。

三条铁律（来自需求 specs/需求_第一轮实测反馈.md）：
1. FR4.2 用户做主：配了 key 走生图管线，没配走"真人接管"标注（D18 FR4.2 用户拍板）——
   默认不依赖生图，acquire_image 的 ai 路径无 key 时返回 handoff_to_human，绝不 raise。
2. §六 降级不阻塞：生图 API 失败（网络/额度/响应异常）一律降级为"真人接管"标注，
   deck 产出不被生图链路卡死。
3. FR4.3 无字底图：AI 只出无字底图，中文 slogan 与 logo 由 SVG 排版层用真字体/真 logo
   贴合成（绕开 AI 中文渲染乱码与 logo 走样两大硬点）——prompt 恒定拼 NO_TEXT_CLAUSE，
   行级 text_policy 不覆盖此铁律。

不建 image_manifest.py（任务可选项·拍板不建）：行级获取结果由返回 dict 承载、
web 下载溯源落 out_dir/image_sources.json（与 vendor 工作流同名同义）、deck 级生成
溯源进 reinforce/asset_ledger.py::record_image_generation——三处已覆盖，再造一层是叠床架屋。
"""

from __future__ import annotations

import base64
import json
import os
import re
import sys
import types
from pathlib import Path

_HERE = Path(__file__).resolve().parent            # engine/
_PROJECT_ROOT = _HERE.parent                        # 项目根
_VENDOR_SCRIPTS = _HERE / "ppt_master" / "scripts"  # vendor 脚本（image_search.py 等）
_VENDOR_REFS = _HERE / "ppt_master" / "references"  # vendor 风格资产（renderings/palettes）

# acquire_image 统一返回 status 枚举（D18 FR7.4）
ACQUIRE_STATUSES = {"ok", "handoff_to_human", "pending_user", "not_implemented"}

# ── D18 FR4.3 生图模型路由默认值 ────────────────────────────────────────────
# 需求拍板：主路径 Nano Banana Pro（品牌手册参考图）· 中文/国内合规场景 Seedream（火山
# 引擎·§六隐私条"参考图不出境走国内线"同款路由）· 品牌色严苛场景 FLUX.2（hex 直出）。
# ⚠️ 模型 id 在不同聚合平台命名有差异（如 OpenRouter 加 "google/" 前缀），这里存的是
# 裸模型名默认值，可被 load_image_api_keys 返回的 models 段逐槽覆盖（逃生门）。
GEN_MODEL_DEFAULT = "gemini-3-pro-image-preview"      # Nano Banana Pro（Google 官方 id）
GEN_MODEL_CJK = "doubao-seedream-4-5-251128"          # Seedream（同 vendor BACKEND_REGISTRY 默认）
GEN_MODEL_BRAND_HEX = "flux-2-pro"                    # FLUX.2（BFL）

# D18 FR4.3 工程铁律：无字底图。恒定拼在 AI 生图 prompt 末尾，text_policy 不覆盖。
NO_TEXT_CLAUSE = (
    "Hard rule: this is a text-free base image. Absolutely NO text, NO letters, "
    "NO words, NO numbers, NO labels, NO captions, NO logos, NO watermarks "
    "anywhere in the image. Any HEX codes or color names mentioned above are "
    "rendering guidance only - never display them as visible text."
)

# ── D18 FR4.2 BYO key 配置查找 ──────────────────────────────────────────────
_ENV_AGGREGATOR_KEY = "IMAGE_GEN_API_KEY"    # 聚合平台通用 key（配套 IMAGE_GEN_BASE_URL）
_ENV_AGGREGATOR_URL = "IMAGE_GEN_BASE_URL"
# provider 专属 env（次序即优先序）；带默认 base_url 的填上，没有公认默认的留 None
_ENV_PROVIDER_KEYS: tuple[tuple[str, str | None], ...] = (
    ("OPENROUTER_API_KEY", "https://openrouter.ai/api/v1"),
    ("GEMINI_API_KEY", None),
    ("VOLCENGINE_API_KEY", None),
    ("ARK_API_KEY", None),
    ("BFL_API_KEY", None),
)
KEY_FILE_NAME = ".image_keys.json"           # 项目根 BYO key 文件（已进 .gitignore·绝不入库）

_CJK_RE = re.compile(r"[一-鿿]")
_HEX_COLOR_RE = re.compile(r"#[0-9a-fA-F]{6}\b")
_REF_NAME_RE = re.compile(r"[a-z0-9][a-z0-9-]*")     # 风格名白名单（防路径穿越）
_SIZE_RE = re.compile(r"\s*(\d+)\s*[xX×]\s*(\d+)\s*")
_PLACEHOLDER_BRACKET_RE = re.compile(r"\[\.\.\..*?\.\.\.\]")  # md 里的 "[...xxx...]" 占位符


# ═══════════════════════════════════════════════════════════════════════════
# vendor 接缝（惰性 import·测试在真模块上 monkeypatch search_and_download）
# ═══════════════════════════════════════════════════════════════════════════

def _ensure_console_encoding_shim() -> None:
    """补 vendor 缺失依赖 console_encoding 的垫片（D18 FR7.4 接线时查实）。

    vendor 全部脚本模块级 `from console_encoding import configure_utf8_stdio`，
    但该文件没随 vendor 搬入仓库（这些脚本在本仓库从未被直接跑过，缺口一直没暴露）。
    铁纪律不往 vendor 目录写文件 → 在薄适配层注入语义一致的垫片（把 stdio 配成
    UTF-8·上游同名函数的功能）。将来 vendor 若补了真文件，find_spec 命中即让位。
    """
    if "console_encoding" in sys.modules:
        return
    import importlib.util  # noqa: PLC0415
    if importlib.util.find_spec("console_encoding") is not None:
        return

    def configure_utf8_stdio() -> None:
        for stream in (sys.stdout, sys.stderr):
            try:
                if hasattr(stream, "reconfigure"):
                    stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:  # stdio 被测试框架/管道替换时容错——垫片绝不反客为主
                pass

    mod = types.ModuleType("console_encoding")
    mod.configure_utf8_stdio = configure_utf8_stdio
    mod.__doc__ = "D18 薄适配层垫片：vendor console_encoding 缺失时的同语义替身"
    sys.modules["console_encoding"] = mod


def _vendor_image_search():
    """惰性 import vendor 的 image_search 模块（web 路径唯一 vendor 接缝）。

    vendor 脚本以顶层模块名互相引用（config/console_encoding/image_sources...），
    需把 scripts 目录接进 sys.path。已核实项目内无同名顶层模块冲突（D18 接线检查）。
    惰性而非模块级 import：让不走 web 路径的调用（含大部分单测）零 vendor 依赖。
    """
    p = str(_VENDOR_SCRIPTS)
    if p not in sys.path:
        sys.path.insert(0, p)
    _ensure_console_encoding_shim()
    import image_search  # noqa: PLC0415 vendor 顶层脚本模块
    return image_search


# ═══════════════════════════════════════════════════════════════════════════
# FR4.2 BYO API key 配置
# ═══════════════════════════════════════════════════════════════════════════

def load_image_api_keys(project_root: str | Path | None = None) -> dict | None:
    """读取 BYO 生图 key 配置（D18 FR4.2）。

    **用户做主：配了 key 走生图，没配走真人标注（D18 FR4.2 用户拍板）**——
    生图是可选配置，默认关闭；本函数返回 None 即"未开启生图"，acquire_image
    的 ai 路径据此自动降级为 handoff_to_human（真人接管标注·不阻塞 deck 产出）。

    查找顺序（先到先得）：
      1. 环境变量 ``IMAGE_GEN_API_KEY``（聚合平台通用·搭配 ``IMAGE_GEN_BASE_URL``）；
      2. 环境变量 provider 专属：OPENROUTER / GEMINI / VOLCENGINE / ARK / BFL_API_KEY；
      3. 项目根 ``.image_keys.json``（该文件已进 .gitignore——key 绝不入库）：
         {"api_key": "...", "base_url": "https://...", "models": {"default"|"cjk"|"brand_hex": "覆盖id"}}

    返回 {"api_key", "base_url", "models", "source"} 或 None。
    fail-closed 例外：key 文件存在但 JSON 坏 / 缺 api_key → raise ValueError——
    "想配但配坏了"≠"没配"，静默当未配置会让用户误以为生图已开、实际全走了真人接管。

    ⚠️ 两条互不相干的 key 链（D19 FR6.1 理清·此前只有生图链有文档）：
      - **AI 生图链（本函数管）**：上面的 IMAGE_GEN_*/OPENROUTER_* 等 env +
        ``.image_keys.json``——只喂 ``_acquire_ai``，跟 web 图库检索无关；
      - **web 图库链（vendor config 管·本函数不碰）**：``PEXELS_API_KEY`` /
        ``PIXABAY_API_KEY``（keyed 图库）与 ``OPENVERSE_CLIENT_ID/SECRET``
        （OAuth 提额·FR6.4）走进程 env 或共享 ``.env``（查找链见 vendor
        ``engine/ppt_master/scripts/config.py::get_env_candidates``：CWD/.env →
        engine/ppt_master/.env → 项目根/.env → ~/.ppt-master/.env·进程 env 优先），
        由 ``_acquire_web`` 经 vendor ``_load_search_env_file`` 惰性加载——
        D19 前该加载只在 vendor CLI ``main()`` 里跑，经 pipeline 走的路径配了
        ``.env`` 也白配（"福建搜不到"误诊主因之一）。``.env`` 已进 .gitignore
        （key 绝不入库·同 ``.image_keys.json`` 纪律）。
    """
    root = Path(project_root) if project_root else _PROJECT_ROOT

    v = (os.environ.get(_ENV_AGGREGATOR_KEY) or "").strip()
    if v:
        return {"api_key": v,
                "base_url": (os.environ.get(_ENV_AGGREGATOR_URL) or "").strip() or None,
                "models": {}, "source": f"env:{_ENV_AGGREGATOR_KEY}"}

    for name, default_url in _ENV_PROVIDER_KEYS:
        v = (os.environ.get(name) or "").strip()
        if v:
            return {"api_key": v, "base_url": default_url,
                    "models": {}, "source": f"env:{name}"}

    key_file = root / KEY_FILE_NAME
    if key_file.is_file():
        try:
            data = json.loads(key_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"{key_file} 不是合法 JSON（想配生图但配坏了≠没配·fail-closed 报错"
                f"而非静默当未配置）：{exc}") from exc
        api_key = str((data or {}).get("api_key") or "").strip()
        if not api_key:
            raise ValueError(f"{key_file} 缺 api_key 字段（格式见 load_image_api_keys docstring）")
        return {"api_key": api_key,
                "base_url": (data.get("base_url") or "").strip() or None,
                "models": dict(data.get("models") or {}),
                "source": f"file:{KEY_FILE_NAME}"}

    return None  # 无任何配置 = 用户未开启生图（合法状态·非错误）


# ═══════════════════════════════════════════════════════════════════════════
# FR4.3 风格词段读取 + prompt 分层拼装（ppt-master 机制：行级只写主体+意图，风格自动注入）
# ═══════════════════════════════════════════════════════════════════════════

def _read_ref_file(subdir: str, name: str) -> str:
    """读 vendor references/<subdir>/<name>.md；名字不存在 → ValueError 列出可用清单。

    风格名走白名单正则（小写字母数字连字符），防路径穿越；名字错=deck 级锁配置错，
    属 fail-closed 该拦即拦（与"生图 API 失败运行期降级"是两类错误——配置错要人改）。
    """
    if not name or not _REF_NAME_RE.fullmatch(name):
        raise ValueError(f"风格名 {name!r} 不合法（只认小写字母/数字/连字符）")
    path = _VENDOR_REFS / subdir / f"{name}.md"
    if not path.is_file():
        avail = sorted(p.stem for p in (_VENDOR_REFS / subdir).glob("*.md") if p.stem != "_index")
        raise ValueError(f"{subdir} 里没有 {name!r}·可用：{avail}")
    return path.read_text(encoding="utf-8")


def _extract_blockquotes(md_text: str) -> list[str]:
    """抽出 markdown 全部 blockquote 段（连续 "> " 行合并成一段·拼 prompt 用）。"""
    blocks: list[str] = []
    cur: list[str] = []
    for line in md_text.splitlines():
        if line.startswith(">"):
            cur.append(line.lstrip(">").strip())
        elif cur:
            blocks.append(" ".join(x for x in cur if x))
            cur = []
    if cur:
        blocks.append(" ".join(x for x in cur if x))
    return [b.strip() for b in blocks if b.strip()]


def _clean_snippet(text: str) -> str:
    """清掉 vendor fewshot 里的 "[...rendering paragraph...]" 类占位符（拼 prompt 去噪）。"""
    return _PLACEHOLDER_BRACKET_RE.sub("", text).strip()


def load_rendering_prompt(rendering: str) -> str:
    """读 references/image-renderings/<rendering>.md 返回风格词段（D18 FR7.4）。

    优先抽 "## 1. Style paragraph" 节下的 blockquote（20 个 rendering 文件都有、
    文件自述 paste-ready）；节结构变了退化到文件第一个 blockquote；再退全文——
    宁可多喂不喂错。deck 级 image_rendering 锁选哪个由确认工序定，这里只管取词。
    """
    text = _read_ref_file("image-renderings", rendering)
    m = re.search(r"^##[^\n]*Style paragraph", text, re.MULTILINE | re.IGNORECASE)
    section = text[m.end():] if m else text
    quotes = _extract_blockquotes(section) or _extract_blockquotes(text)
    return _clean_snippet(quotes[0]) if quotes else text.strip()


def load_palette_prompt(palette: str) -> str:
    """读 references/image-palettes/<palette>.md 返回色彩行为词段（D18 FR7.4）。

    palette 文件描述"色彩怎么用"（占比/角色/性情），核心词段是 fewshot 里含
    "Color behavior" 的 blockquote（14 个 palette 文件的共同结构）；没有就拼全部
    blockquote；再没有回退全文。注意：palette 不供 HEX，HEX 来自 spec_lock.palette，
    调用方把 HEX 写进行级 intent 或由视觉管道包代入。
    """
    text = _read_ref_file("image-palettes", palette)
    quotes = _extract_blockquotes(text)
    for q in quotes:
        if "color behavior" in q.lower():
            return _clean_snippet(q)
    if quotes:
        return _clean_snippet(" ".join(quotes))
    return text.strip()


def build_image_prompt(row: dict, *, rendering: str | None = None,
                       palette: str | None = None) -> str:
    """分层拼装 AI 生图 prompt（D18 FR4.3·ppt-master 机制）。

    行级只写主体+意图（row.intent / row.purpose），deck 级风格词段自动注入
    （rendering=渲染风格锁、palette=色调行为锁——多张图读起来像同一份 deck 的机制），
    末尾恒定拼无字底图铁律（NO_TEXT_CLAUSE·text_policy 不覆盖）。
    """
    subject = str(row.get("intent") or row.get("purpose") or "").strip()
    if not subject:
        raise ValueError("images 行缺 intent/purpose——AI 生图没有主体描述无从拼 prompt")
    parts = [subject]
    if rendering:
        parts.append(load_rendering_prompt(rendering))
    if palette:
        parts.append(load_palette_prompt(palette))
    parts.append(NO_TEXT_CLAUSE)
    return "\n\n".join(parts)


def select_gen_model(row: dict, *, models_override: dict | None = None) -> str:
    """按需求 FR4.3 选生图模型。

    路由（先命中先赢）：
      1. 品牌色严苛（行级 brand_color_strict 真值，或 intent/purpose 里出现 #RRGGBB
         色值=要求 hex 直出）→ FLUX.2；
      2. 中文/国内合规场景（intent/purpose 含 CJK——中文写意图≈国内单/素材不出境的
         代理判断，§六隐私条同款路由）→ Seedream（火山引擎国内线）；
      3. 默认 → Nano Banana Pro（品牌手册参考图主路径）。
    models_override（来自 load_image_api_keys().models）可逐槽覆盖 id——聚合平台
    命名差异的逃生门（如 OpenRouter 要 "google/gemini-3-pro-image-preview"）。
    """
    o = models_override or {}
    text = " ".join(str(row.get(k) or "") for k in ("intent", "purpose"))
    if row.get("brand_color_strict") or _HEX_COLOR_RE.search(text):
        return o.get("brand_hex") or GEN_MODEL_BRAND_HEX
    if _CJK_RE.search(text):
        return o.get("cjk") or GEN_MODEL_CJK
    return o.get("default") or GEN_MODEL_DEFAULT


# ═══════════════════════════════════════════════════════════════════════════
# HTTP seam（测试 mock 点·单测绝不真联网）
# ═══════════════════════════════════════════════════════════════════════════

def _http_post_json(url: str, headers: dict, payload: dict, timeout: int = 300) -> dict:
    """POST JSON 返回 JSON（生图 API 调用的唯一出网点之一·测试 monkeypatch 这里）。"""
    import requests  # noqa: PLC0415 惰性——无 key 用户全程不需要
    resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def _http_get_bytes(url: str, timeout: int = 300) -> bytes:
    """GET 二进制（生图响应给 url 时的下载点·测试 monkeypatch 这里）。"""
    import requests  # noqa: PLC0415
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.content


def _generate_via_api(*, prompt: str, model: str, api_keys: dict,
                      out_path: Path, size: str | None = None) -> float | None:
    """经聚合平台调生图 API（OpenAI 兼容 /images/generations——聚合平台事实标准）。

    成功落盘 out_path，返回单张成本估计（响应 usage.cost 有就取·没有 None 如实上报，
    台账按 unknown 记——§六成本可见不等于编造成本）。失败 raise，由 _acquire_ai
    统一降级（本函数不管降级，职责单一）。
    """
    base_url = str(api_keys.get("base_url") or "").rstrip("/")
    if not base_url:
        raise RuntimeError(
            "api_keys 缺 base_url（聚合平台地址）——在 .image_keys.json 加 base_url "
            "或设 IMAGE_GEN_BASE_URL（用 OPENROUTER_API_KEY 则自带默认地址）")
    payload: dict = {"model": model, "prompt": prompt, "n": 1}
    parsed = _parse_size(size)
    if parsed:
        payload["size"] = f"{parsed[0]}x{parsed[1]}"
    headers = {"Authorization": f"Bearer {api_keys['api_key']}",
               "Content-Type": "application/json"}
    j = _http_post_json(f"{base_url}/images/generations", headers, payload)

    data = (j.get("data") or [{}])[0]
    if data.get("b64_json"):
        out_path.write_bytes(base64.b64decode(data["b64_json"]))
    elif data.get("url"):
        out_path.write_bytes(_http_get_bytes(data["url"]))
    else:
        raise RuntimeError(f"生图响应无图像数据（既无 b64_json 也无 url）·响应键：{sorted(j)}")

    cost = (j.get("usage") or {}).get("cost")
    return float(cost) if isinstance(cost, (int, float)) else None


# ═══════════════════════════════════════════════════════════════════════════
# 小工具
# ═══════════════════════════════════════════════════════════════════════════

def _parse_size(size) -> tuple[int, int] | None:
    """解析行级 size（"1200x800" / "1200×800"）→ (w, h)；解析不了 None（不猜）。"""
    if not size:
        return None
    m = _SIZE_RE.fullmatch(str(size))
    return (int(m.group(1)), int(m.group(2))) if m else None


def _orientation_from_size(size: tuple[int, int] | None) -> str:
    if not size:
        return ""
    w, h = size
    if w > h:
        return "landscape"
    if h > w:
        return "portrait"
    return "square"


def _measure_image(path: Path) -> tuple[int, int] | None:
    """PIL 量落盘文件实测尺寸；量不了 None（上游元数据可能是预览尺寸·以磁盘为准）。"""
    try:
        from PIL import Image  # noqa: PLC0415
        with Image.open(path) as im:
            return int(im.width), int(im.height)
    except Exception:
        return None


def _classify_ratio(ratio: float) -> str:
    """宽高比 → 版式类别。阈值与 vendor analyze_images.classify_ratio /
    image-layout-spec.md 完全一致（抄阈值不 import——避免在纯本地路径上拉起
    vendor 的 config/console_encoding 依赖链）。"""
    if ratio > 2.0:
        return "Ultra-wide"
    if ratio > 1.5:
        return "Wide landscape"
    if ratio > 1.2:
        return "Standard landscape"
    if ratio > 0.8:
        return "Near square"
    return "Portrait"


def analyze_acquired(paths) -> list[dict]:
    """量已获取图片的实测尺寸喂布局（D18 FR7.4·参考 vendor analyze_images.py）。

    每条：{filename, path, width, height, aspect_ratio, layout_hint, filesize_kb}；
    读不了的文件如实带 error 字段列出，不静默跳过也不代判（铁律 2）。
    layout_hint 只分类不定版式——版式由 pattern_id（81 模式）声明，这里供核对。
    """
    out: list[dict] = []
    for p in paths:
        p = Path(p)
        rec: dict = {"filename": p.name, "path": str(p)}
        try:
            from PIL import Image  # noqa: PLC0415
            with Image.open(p) as im:
                w, h = int(im.width), int(im.height)
            ratio = w / h
            rec.update(width=w, height=h, aspect_ratio=round(ratio, 4),
                       layout_hint=_classify_ratio(ratio),
                       filesize_kb=round(p.stat().st_size / 1024, 1))
        except Exception as exc:
            rec["error"] = str(exc)
        out.append(rec)
    return out


def _append_sources_manifest(manifest_path: Path, item: dict) -> None:
    """web 下载溯源落盘（与 vendor image_sources.json 同名同义·按 filename 去重替换）。

    刻意不写 generated_at：引擎核心不碰系统时钟（项目既有纪律）——需要时间戳的
    台账记录由调用方带 timestamp 调 record_image_generation。
    """
    payload: dict = {}
    if manifest_path.is_file():
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload = {}  # 坏 manifest 重建（同 vendor _read_existing_manifest 行为）
    items = [i for i in (payload.get("items") or []) if i.get("filename") != item["filename"]]
    items.append(item)
    payload["items"] = items
    payload.setdefault("license_verification",
                       "provider metadata used; manual review recommended for external delivery")
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")


# ═══════════════════════════════════════════════════════════════════════════
# D19 FR6.1/FR6.3：keyed 图库跳过可见化 + 中国地名消歧
# ═══════════════════════════════════════════════════════════════════════════

# D19 FR6.1：keyed 图库缺 key 的跳过理由（"四库只有两库在跑"用户不可见是二轮实测
# "福建搜不到"的误诊主因——跳过必须可见化，理由里带注册指引与实测数据支撑）。
_KEYED_PROVIDER_SKIP_REASONS = {
    "pexels": "缺 PEXELS_API_KEY——Pexels 实测有 4.7K 张福建类内容·免费注册即时发放"
              "（https://www.pexels.com/api/·key 放共享 .env 或进程 env）",
    "pixabay": "缺 PIXABAY_API_KEY——免费注册即时发放"
               "（https://pixabay.com/api/docs/·key 放共享 .env 或进程 env）",
}

# D19 FR6.3 地名消歧：英文中国城市名 → 省级限定词。调研实锤（需求 §九·31 次检索一手
# 核实）：Commons 搜 "Fuzhou street" 前 5 全是**上海福州路**——裸城市名在国际图库里
# 会命中同名路名/旧译名，附省级限定是最小有效解。名单先覆盖福建九地市+武夷山（本单
# 场景），按需扩；中文查询不在此消歧（FR6.2 的 locale + 中文直搜命中的是中文 metadata，
# 歧义面小一个量级）。Wikimedia `incategory:` 类目限定是更强的消歧，但 gsrsearch 语法
# 只有 wikimedia 懂、四库共享同一 query 字符串，做它需 provider 级分流改动——省级限定
# 已覆盖调研病例，incategory 留二期（vendor 最小 diff 纪律）。
_CN_CITY_PROVINCE_EN = {
    "fuzhou": "Fujian", "xiamen": "Fujian", "quanzhou": "Fujian", "putian": "Fujian",
    "zhangzhou": "Fujian", "longyan": "Fujian", "sanming": "Fujian", "nanping": "Fujian",
    "ningde": "Fujian", "wuyishan": "Fujian",
}
_QUERY_WORD_RE = re.compile(r"[A-Za-z]+")


def disambiguate_cn_place(query: str) -> str:
    """英文查询含中国城市名且未带省级限定 → 追加省名（D19 FR6.3·轻量实现）。

    "Fuzhou street" → "Fuzhou street Fujian"（防上海福州路混入——调研实锤：Commons 搜
    Fuzhou street 前 5 全是上海福州路）。已带省名/非名单城市/中文查询原样返回。
    """
    if not query or _CJK_RE.search(query):
        return query  # 中文查询走 FR6.2 通路·不在此消歧
    words = [w.lower() for w in _QUERY_WORD_RE.findall(query)]
    provinces = {p for w in words if (p := _CN_CITY_PROVINCE_EN.get(w))}
    missing = [p for p in sorted(provinces) if p.lower() not in words]
    if not missing:
        return query
    return f"{query.strip()} {' '.join(missing)}"


# ═══════════════════════════════════════════════════════════════════════════
# FR7.4 六源获取主分发
# ═══════════════════════════════════════════════════════════════════════════

def acquire_image(row: dict, out_dir: str | Path, *, api_keys: dict | None = None,
                  rendering: str | None = None, palette: str | None = None) -> dict:
    """按 spec_lock.images 行的 acquire_via 六源分发获取图像（D18 FR7.4）。

    参数：
      row：images 清单行 {filename, purpose, pattern_id, acquire_via, intent?, size?,
           text_policy?}（完整 schema 校验在 reinforce.spec_lock.validate_spec_lock，
           这里只防御性拦 filename/acquire_via 缺失的坏行）；
      out_dir：图像落盘目录（一份 deck 一个家：通常 data/decks/<单名>/images/）;
      api_keys：load_image_api_keys() 的返回（ai 路径专用·FR4.2 BYO——不传/None=
           用户未开启生图，ai 行降级真人接管）；
      rendering / palette：deck 级 image_rendering × image_palette 锁（ai 路径 prompt
           自动注入风格词段——多张图读起来像同一份 deck）。

    返回统一 dict（status ∈ ACQUIRE_STATUSES）：
      ok               → path 指向落盘文件（placeholder 例外：path=None，获取诉求
                         即"画占位框"，note 说明）；web 成功附 provider/license/
                         attribution_text，ai 成功附 model/prompt/cost_estimate
                         （直接喂 record_image_generation 记台账）;
      handoff_to_human → 真人接管标注（无 key / 生图失败 / web 无结果·§六不阻塞）;
      pending_user     → 待用户提供素材;
      not_implemented  → formula/slice 本期未实现（诚实标注·二期）。
    """
    if not isinstance(row, dict) or not row.get("filename") or not row.get("acquire_via"):
        raise ValueError("images 行至少需要 filename + acquire_via"
                         "（完整行 schema 由 reinforce.spec_lock.validate_spec_lock 把门）")
    via = row["acquire_via"]

    if via == "web":
        return _acquire_web(row, out_dir)
    if via == "ai":
        return _acquire_ai(row, out_dir, api_keys, rendering=rendering, palette=palette)
    if via == "user":
        return {"status": "pending_user", "path": None,
                "note": f"待用户提供素材 {row['filename']}"
                        f"（用途：{row.get('purpose') or '未注明'}）——收到后放进 {out_dir}"}
    if via == "placeholder":
        return {"status": "ok", "path": None,
                "note": "占位视觉位：制作层按 pattern_id 画占位框即可，无需外部图像"
                        "（path=None 是本源的正常形态）"}
    if via in ("formula", "slice"):
        return {"status": "not_implemented", "path": None,
                "note": f"acquire_via={via} 本期未实现（D18 诚实标注·二期做）——"
                        f"formula=公式/程序化生成，slice=一张大图切同族小插画"}
    raise ValueError(f"未知 acquire_via={via!r}（六源见 reinforce.spec_lock.IMAGE_ACQUIRE_VIAS）")


def _acquire_web(row: dict, out_dir: str | Path) -> dict:
    """web 源：复用 vendor image_search 四图库链（D18 FR7.4 + D19 FR6.1/FR6.3）。

    provider 链 = vendor._default_provider_chain()：PEXELS/PIXABAY_API_KEY 有配则
    keyed 库优先，openverse/wikimedia 零配置兜底——四库至少两库随时可用。
    检索词 = 行级 intent（优先）或 purpose，经 disambiguate_cn_place 做中国地名
    省级限定（D19 FR6.3）。无可下载结果 → 降级真人接管（不 raise·与生图失败同一条
    §六 降级哲学：视觉位缺图标注出来，deck 不被卡死）。

    D19 FR6.1 两处：① 进链前先经 vendor ``_load_search_env_file`` 加载共享 .env 的
    图库 key（此前该加载只在 vendor CLI main() 里跑——经 pipeline 走的路径配了 .env
    也白配）；② keyed 图库因缺 key 被跳过时不再静默——返回值恒带 ``skipped_providers``
    [{provider, reason}]（含注册指引），非空时 note 追加 ⚠ 提示，pipeline 消费方据此
    warn（"四库只有两库在跑"必须用户可见）。
    """
    query = str(row.get("intent") or row.get("purpose") or "").strip()
    if not query:
        return {"status": "handoff_to_human", "path": None,
                "note": "web 检索缺查询词（行级 intent/purpose 都空）——真人接管或补 intent 重跑"}
    query = disambiguate_cn_place(query)  # D19 FR6.3 中国地名省级限定

    m = _vendor_image_search()
    env_note = ""
    try:
        m._load_search_env_file()  # D19 FR6.1：共享 .env 的 PEXELS_/PIXABAY_/OPENVERSE_ 进 env
    except Exception as exc:  # .env 坏格式不卡 deck（§六降级哲学）·但要可见不静默
        env_note = f"；⚠ 共享 .env 解析失败（图库 key 未加载）：{exc}"
    chain = m._default_provider_chain()
    skipped_providers = [
        {"provider": p, "reason": _KEYED_PROVIDER_SKIP_REASONS.get(
            p, f"缺 {p.upper()}_API_KEY——该 keyed 图库被跳过")}
        for p in m.KEYED_PROVIDERS if p not in chain]
    skip_note = ""
    if skipped_providers:
        names = "/".join(s["provider"] for s in skipped_providers)
        skip_note = (f"；⚠ keyed 图库 {names} 缺 key 被跳过（本次只跑 {'/'.join(chain)}·"
                     f"配置指引见返回值 skipped_providers）")

    size = _parse_size(row.get("size"))
    request = m.ImageSearchRequest(
        query=query,
        purpose=str(row.get("purpose") or ""),
        orientation=_orientation_from_size(size),
        # 有声明尺寸按声明要（展示 W×H 至少要 W×H 的源图）；没声明用 vendor CLI 默认质量线
        min_width=size[0] if size else 1200,
        min_height=size[1] if size else 800,
        filename=row["filename"],
    )
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / row["filename"]

    # _default_provider_chain 是 vendor 模块级函数（下划线名但语义稳定·D18 明确复用拍板）
    candidate, provider_name, stage = m.search_and_download(
        chain, request,
        output_path=out_path, strict_no_attribution=False)

    if candidate is None:
        return {"status": "handoff_to_human", "path": None,
                "note": f"图库无可下载结果（query={query!r}）——"
                        f"真人接管：换检索词 / 用户供图（acquire_via=user）/ 转 ai 生成"
                        f"{skip_note}{env_note}",
                "skipped_providers": skipped_providers}

    dims = _measure_image(out_path)
    attribution = m.build_attribution_text(row["filename"], candidate)
    attribution_required = candidate.license_tier == "attribution-required"

    _append_sources_manifest(out_dir / "image_sources.json", {
        "filename": row["filename"],
        "purpose": str(row.get("purpose") or ""),
        "search_query": query,
        "provider": provider_name,
        "stage": stage,
        "title": candidate.title,
        "author": candidate.author,
        "source_page_url": candidate.source_page_url,
        "download_url": candidate.download_url,
        "license_name": candidate.license_name,
        "license_url": candidate.license_url,
        "license_tier": candidate.license_tier,
        "attribution_required": attribution_required,
        "attribution_text": attribution,
        "width": dims[0] if dims else candidate.width,
        "height": dims[1] if dims else candidate.height,
        "status": "sourced",
    })

    note = f"web:{provider_name} · {candidate.license_name or candidate.license_tier}"
    if attribution_required:
        note += " · ⚠ 该图许可证要求页内署名（attribution_text 见返回值·交付前必须贴）"
    note += skip_note + env_note  # D19 FR6.1：keyed 跳过/.env 失败可见化（成功也提示·防误诊）
    return {"status": "ok", "path": str(out_path), "note": note,
            "provider": provider_name,
            "license_name": candidate.license_name,
            "license_tier": candidate.license_tier,
            "attribution_required": attribution_required,
            "attribution_text": attribution,
            "source_page_url": candidate.source_page_url,
            "width": dims[0] if dims else candidate.width,
            "height": dims[1] if dims else candidate.height,
            "skipped_providers": skipped_providers}


def _acquire_ai(row: dict, out_dir: str | Path, api_keys: dict | None, *,
                rendering: str | None = None, palette: str | None = None) -> dict:
    """ai 源：BYO key 生图（D18 FR4.2/FR4.3）。

    无 key → handoff_to_human（FR4.2 用户做主：没配 key=没开生图，标注真人接管，
    绝不 raise）；有 key → 分层拼 prompt（无字底图铁律）→ FR4.3 模型路由 → 聚合
    平台调用；**任何失败（配置缺 base_url/网络/额度/响应异常）都降级真人接管
    不阻塞 deck 产出（需求 §六）**——失败原因如实写进 note 供人判断。
    """
    if not api_keys or not str(api_keys.get("api_key") or "").strip():
        return {"status": "handoff_to_human", "path": None,
                "note": "未配置生图 key·此视觉位标注真人接管"
                        "（D18 FR4.2 用户做主：配 key 才开生图——配置方式见 "
                        "engine.image_pipeline.load_image_api_keys）"}
    try:
        prompt = build_image_prompt(row, rendering=rendering, palette=palette)
        model = select_gen_model(row, models_override=api_keys.get("models"))
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / row["filename"]
        cost = _generate_via_api(prompt=prompt, model=model, api_keys=api_keys,
                                 out_path=out_path, size=row.get("size"))
        return {"status": "ok", "path": str(out_path),
                "note": f"ai:{model}（prompt 已拼无字底图指令·成图是否真无字由人审确认[REVIEWS 有专项]——生成参数≠成图保证·D26 诚实化）",
                "model": model, "prompt": prompt, "cost_estimate": cost}
    except Exception as exc:  # §六：生图失败降级真人接管·不 raise 不阻塞
        return {"status": "handoff_to_human", "path": None,
                "note": f"生图失败·降级真人接管（§六不阻塞 deck 产出）：{exc}"}
