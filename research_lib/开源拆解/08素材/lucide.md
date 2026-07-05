# Lucide 拆解笔记（图标素材库）

> 拆解对象：`/Users/qinbiaojuan/Documents/PPT开源参考/08_素材库/lucide`
> 上游：https://github.com/lucide-icons/lucide · 官网 https://lucide.dev · **ISC License**（`LICENSE`，"Lucide Icons and Contributors"）· Feather 衍生子集另挂 MIT（`LICENSE` 后半，Cole Bemis）
> 本机 SVG 实测 **1744 个**（`ls icons/*.svg | wc -l`）；README 自述"1600+"（`README.md:29`）——以实测为准。
> 拆解日期：2026-06-30 · 拆解人：Claude（PPT Engine 研究层）· 轻拆（ls + 关键文件，非全源码精读）
> 方法：根目录 `ls -la` + `LICENSE` + `README.md` + 抽样 SVG/元数据 JSON + 全库 `stroke-width`/`fill` 分布统计 + 与同目录 `tabler-icons` 对照。**结论带文件/命令出处，不掺常识推断。**
> 定位说明：PPT Engine **制作层的图标素材来源候选**。本笔记核心任务：摸清它能不能直接喂进 python-pptx、与 tabler 二选一还是都要、坑在哪。

---

## ⭐ 一句话：最值得纳入的 1 件事

**全库 1744 个图标 100% 同规格——`24×24` viewBox、`fill="none"`、`stroke="currentColor"`、`stroke-width="2"`、圆角端点，零例外（实测 `grep` 全库 `stroke-width` 只有 `"2"` 一个取值、`fill` 只有 `none`/`currentColor`）。**

这个"一致性"对 PPT Engine 是硬价值：高 stakes deck 最忌图标风格打架。Lucide 是**纯单线描边一种风格**，无 outline/filled 双轨之争（这点正好和 tabler 相反，见④），随便抓 10 个图标拼一页天然协调。而 `stroke="currentColor"` 意味着**改色 = 改一个属性**（把 `currentColor` 替成 deck 主题色），不用碰 path——这是它最适合"程序化批量套主题色"的工程特性。

→ **战术结论先行**：Lucide 适合做 PPT Engine 的**默认线性图标底座**；但它**不能直接 `add_picture` 进 pptx**（python-pptx 只吃栅格图），必须经一道 SVG→PNG/EMF 的转换闸，且转换前要先把 `currentColor` 替成具体色值（PNG 栅格化不认 `currentColor`）。见③。

---

## ① 是什么 + 定位 + license（可商用？）

- **是什么**：开源图标库，README 自述"a beautiful & consistent icon toolkit made by the community"，是 **Feather Icons 的社区 fork**（`README.md:3` alt 文本明说 "fork of Feather Icons"）。提供 1744 个矢量 SVG，用于数字/非数字项目。
- **license = ISC，可商用**：`LICENSE` 头 "ISC License, Copyright (c) 2026 Lucide Icons and Contributors"；README 明文 "**Lucide is totally free for commercial use and personal use**"（`README.md:72`）。ISC ≈ 简化版 MIT（更短、措辞等价），保留版权声明即可商用、改、分发。
  - **子集例外**：约 110 个从 Feather 继承的图标（`LICENSE` 后半列了全名单：airplay/alert-circle/arrow-*/calendar/clock/...）挂 **MIT**（Cole Bemis, 2013-present）。MIT 同样可商用，**对我们无实质差别**——两份都只要求"保留版权/许可声明"。
  - ⚠️ **明确不收品牌 logo**：`README.md:62` + `BRAND_LOGOS_STATEMENT.md`——出于法律/一致性/维护原因，**永不加 GitHub/Twitter/各家 App 的品牌标**。所以"客户要在 deck 上放某 SaaS 的官方 logo"这种需求，Lucide 一个都给不了（tabler 同理也不该用其 brand 图标，版权属各品牌方）。

## ② 有什么（数量 / 格式 / 风格 · vs tabler-icons）

**数量与组织**
- **1744 个 `.svg`** + **1744 个同名 `.json` 元数据**（`icons/` 目录共 3488 条 = 两者各半）。
- 元数据 JSON 结构（样例 `icons/house.json`）：`tags`（同义词，供搜索）、`categories`（归类）、`aliases`（旧名/弃用别名，如 `house` 的旧名 `home` 标了 `deprecated`）、`contributors`。**这是它比"一堆裸 SVG"值钱的地方——自带可检索的标签词典**，做"按语义找图标"时能直接用。
- `categories/` 下 42 个类目文件（accessibility/arrows/charts/finance/...），但⚠️**这些 JSON 是空壳 `{title, icons:[]}`**——真正的"图标→类目"映射反向存在每个图标自己的 `categories` 字段里。要按类目聚合得自己遍历 1744 个 JSON 反建索引。

**格式**
- 仓库里**只有源 SVG**（`24×24`、`stroke` 版）。官方分发包在 `packages/`：`lucide-static`（裸 SVG + 预渲染 PNG + sprite）、`lucide-react/vue/svelte/angular/solid/preact/astro/react-native`——**全是前端框架包，没有官方 Python 包**（③ 详述影响）。

**风格**
- **唯一一种风格：单线描边（outline / stroke-based）**。全库实测：`fill="none"` 1744 个、`stroke-width="2"` 1744 个、viewBox 全 `0 0 24 24`、`stroke-linecap/linejoin="round"`。仅 21 处出现 `fill="currentColor"`（个别需实心的小元素，如圆点）。极致克制、统一。

**vs tabler-icons（同在 `08_素材库/`，可直接对照）**

| 维度 | **Lucide** | **tabler-icons** |
|---|---|---|
| 数量 | **1744**（实测 `icons/*.svg`） | **6146**（`outline` 5093 + `filled` 1053，实测 `find`） |
| license | **ISC**（Feather 子集 MIT） | **MIT**（`LICENSE`，Paweł Kuna） |
| 风格 | **只有线性一种** | **双轨：outline（描边）+ filled（实心 `fill="currentColor"`）** |
| 规格 | 24×24 / stroke-width 2 / fill=none，**零例外** | 24×24；outline 是 stroke 版、filled 是 `fill` 版（样例首图即 `fill="currentColor"`） |
| 元数据 | 每图一个 JSON（tags/categories/aliases） | SVG 文件头注释挂 `unicode`/`version`（`<!-- unicode: "fe2b" -->`）；另有 `aliases.json` |
| 出身 | Feather 的社区 fork | 独立项目 |
| 取舍 | **风格统一、量适中、改色干净** | **量大 3.5 倍、有实心款**，但**outline/filled 混用易风格打架**，且 SVG 带注释需清洗 |

一句话差异：**tabler 胜在"量大 + 有实心填充款"，Lucide 胜在"风格绝对统一 + 改色更干净 + 自带标签词典"。**

## ③ 怎么复用进 python-pptx

⚠️ **核心约束（来自已拆的 `04制作/python-pptx.md`）：python-pptx 不能直接吃 SVG。**
- `add_picture()` **只接栅格图**（png/jpg…，经 Pillow）——见该笔记 `:32` 形状表。喂 SVG 不行。
- 想走"SVG path → 可编辑矢量形状（custGeom）"也走不通：**python-pptx 的 `FreeformBuilder` 不认 SVG 的三次贝塞尔 `C` 命令**（该笔记 `:167` 那条「对照点」明说）。要硬走得自己往 oxml 注入 `a:cubicBezTo`，库没封装。而 Lucide 的 path 全是 arc/曲线混合，逐条手翻不现实。

**于是落地路径只有"栅格化贴图"这一条主路（外加一条可选的矢量难路）：**

1. **主路 · SVG → PNG → `add_picture`**（推荐，最稳）
   - **先改色再栅格化**：PNG 不认 `currentColor`，必须先把 SVG 里的 `stroke="currentColor"` 文本替换成 deck 主题色（如 `#1F4E79`），这一步正是 Lucide "改一个属性即换色"价值的兑现点。
   - 再用 `cairosvg`（`cairosvg.svg2png(...)`）或 `svglib`+`reportlab` 把改好色的 SVG 渲成高 DPI PNG（建议 ≥4× 即 96px+，避免 deck 放大发虚）。
   - `slide.shapes.add_picture(png_path_or_BytesIO, left, top, width, height)` 贴上。
   - ⚠️ **本项目 `.venv` 现状：python-pptx / cairosvg / svglib / Pillow 一个都没装**（实测 `.venv/bin/python -c "import ..."` 全 ImportError）。制作层一旦动工，这套依赖要先补。
   - 代价：贴上去是**位图，不可编辑、不可在 PPT 里再改色/改线宽**；放大有上限（受栅格 DPI 限制）。但对"图标"这种小装饰元素，位图完全够用，是行业常规做法。

2. **可选难路 · SVG → EMF（矢量）→ `add_picture`**
   - EMF 是 Windows 矢量格式，python-pptx 的 `add_picture` 能接 EMF 并在 PPT 里保持矢量（放大不糊）。但 SVG→EMF 需外部工具（如 Inkscape CLI `inkscape in.svg --export-type=emf`，或 LibreOffice headless）转，链路重、跨平台（macOS 上要装 Inkscape）。**仅当客户强要求"图标无限放大不糊"时才上。**

3. **旁路 · 直接用官方预渲染 PNG**
   - `packages/lucide-static` 自带预渲染 PNG。但那是**固定黑色/默认色**，不能套 deck 主题色——对高 stakes deck 基本不可用（颜色不统一）。**不推荐**，只在"快速占位、不在乎颜色"时用。

## ④ 对 PPT Engine 的落点（tabler vs lucide：选哪个 / 都要？）

**商务/咨询图标覆盖实测（抽 20 个高频名，Lucide 全部命中）**：trending-up、trending-down、arrow-up-right、target、presentation、chart-pie、chart-column、dollar-sign、briefcase、building-2、users、handshake、lightbulb、circle-check、triangle-alert、gauge、milestone、flag、layers、workflow —— **20/20 ✓**。做投资人/咨询 deck 的常用语义（增长箭头、靶心、饼图、警示、里程碑旗）都齐。

**选型建议（带出处推理，非铁律 · 待真实 deck 验证升格）：**
- **默认底座选 Lucide**。理由：①风格绝对统一（高 stakes deck 最忌图标打架，Lucide 物理上不可能混风格）②`currentColor` 改色干净，契合"程序化套主题色"③自带 tags/aliases 词典，做"按语义检索图标"省一层工④ISC=MIT 级宽松，商用零负担。
- **tabler 作补充库**，两种情况补：①**需要实心填充图标**（filled 款做强调/选中态/对比时更有视觉重量，Lucide 给不了）②**Lucide 缺某个具体图标**（tabler 量大 3.5 倍，长尾覆盖更广）。
- ⚠️ **不要在同一份 deck 里混用两库的描边图标**——两家线宽/圆角细节不完全一致，混了反而破坏一致性。补充库的正确用法是"Lucide 没有的、或要实心款的，才去 tabler 拿"，而非随机混抓。
- **共同前提**：两库都靠③那条"SVG→PNG→add_picture（先改色）"链路落地，制作层得先把这条转换闸 + 依赖（cairosvg/Pillow）建好，图标库才谈得上"能用"。

## ⑤ 坑

1. **python-pptx 不吃 SVG**（最大坑，见③）：必须经栅格化/EMF 转换，不能直接贴。制作层若没建转换闸，图标库等于摆设。
2. **PNG 栅格化前必须先替 `currentColor`**：直接渲带 `currentColor` 的 SVG，渲染器要么报错要么出黑色/透明，颜色全错。**改色必须在栅格化之前**。
3. **`categories/*.json` 是空壳**：想"按类目列图标"会扑空——真映射在每个图标自己的 JSON 里，得遍历 1744 个反建索引。
4. **README 数字过时**：自述"1600+"，实际 1744。引用数量以本机 `ls` 实测为准，别照抄 README。
5. **无品牌 logo**（`BRAND_LOGOS_STATEMENT.md`）：客户要某公司/产品官方标，Lucide 永远没有；tabler 即便有 brand 图标，版权也属各品牌方、商用前需各自确认，**别当成"开源可商用"随便用**。
6. **无官方 Python 包**：`packages/` 全是前端框架包。Python 侧用法 = 自己读 `icons/*.svg` 文本 + 转换，没有 `pip install lucide` 这种现成轮子（PyPI 上有第三方 `lucide`/`lucide-python` 类包，但非官方、需另核实可信度，本次未联网验证）。
7. **位图不可再编辑**：走 PNG 路贴进去的图标，在 PowerPoint 里改不了色/线宽/大小（只能整体缩放且会糊）。若客户习惯在 PPT 里手动调图标，要么走 EMF 矢量路，要么接受这个限制。

---

## 出处与可信度

- **直接实测（高可信）**：图标数 1744、全库 stroke/fill 一致性、tabler 数量对比、商务图标命中、`.venv` 缺依赖、categories 空壳——均为本机命令/文件直读结果。
- **跨笔记引用（高可信）**：python-pptx 不吃 SVG / FreeformBuilder 不认 `C` —— 引自同库 `04制作/python-pptx.md:32,167`（该笔记为源码精读所得）。
- **待联网核实**：PyPI 第三方 lucide-python 包的可信度/维护状态（坑⑥）；EMF 经 add_picture 在新版 PowerPoint 的矢量保真度（建议制作层动工时实测一张验证）。
- **性质提醒**：本笔记是**轻拆**（ls + 关键文件 + 抽样统计），非全包逐文件精读；选型建议是「带出处的强候选」，**升格为铁律需真实高 stakes deck 落地验证**。
