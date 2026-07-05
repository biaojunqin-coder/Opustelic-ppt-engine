# Tabler Icons 拆解笔记（08 素材库）

> 轻拆（ls + 元数据，未逐个读 6146 个 SVG）。落点：制作层咨询级 deck 的图标素材源。
> 源：`/Users/qinbiaojuan/Documents/PPT开源参考/08_素材库/tabler-icons`（本地已 clone，v3.44.0）
> 拆解日期：2026-06-30

---

## ① 是什么 + 定位 + License（可商用？）

- **是什么**：纯 SVG 图标集，24×24 网格、2px 描边设计语言，由 Paweł Kuna 维护。官网 tabler.io/icons。
- **定位**：Web 项目用的高质量免费图标库；资源地图称「最全」——本仓库实测 **6146 个**（README 自报 `<!--icons-count-->6146`，与目录文件数吻合）。
- **License：MIT，可商用 ✅**（出处：仓库根 `LICENSE`，"Copyright (c) 2020-2026 Paweł Kuna"，授权含 use/copy/modify/merge/publish/distribute/sublicense/**sell**）。
  - 唯一义务：分发软件「实质副本」时附带版权声明 + 许可声明。**实务上把单个图标 path 嵌进 pptx 不构成「分发软件副本」，几乎零合规负担**；稳妥起见在我们素材库的 LICENSES 汇总里记一条 attribution 即可。

## ② 有什么（数量 / 分类 / 格式 / 风格 / 尺寸）

- **总量 6146**，两套风格（出处：`icons/` 下两子目录实测文件数）：
  - **outline（线性）5093 个** — `icons/outline/*.svg`
  - **filled（填充）1053 个** — `icons/filled/*.svg`
- **格式**：源文件全是 **SVG**，每个文件头部带 HTML 注释元数据（`tags:` 关键词数组、`category:`、`version:`、`unicode:`），便于检索/做映射表。
- **尺寸 / 画布**：统一 `viewBox="0 0 24 24"`，`width/height=24`。**全集同栅格**，缩放一致性极好。
- **41 个分类**（出处：对 `outline/*.svg` 抽 `category` 字段聚合）。咨询 deck 高频段都齐：

  | 分类 | 数量 | 分类 | 数量 | 分类 | 数量 |
  |---|---|---|---|---|---|
  | System | 772 | Brand | 375 | Devices | 356 |
  | Design | 340 | **Arrows** | 332 | Map | 262 |
  | Letters | 214 | Document | 203 | Numbers | 196 |
  | Shapes | 183 | Text | 180 | Media | 155 |
  | E-commerce | 150 | Communication | 117 | Buildings | 94 |
  | Math | 88 | Health | 87 | Currencies | 76 |
  | **Charts** | 39 | Database | 42 | ...(余略) | |

- **官方还提供 13 个发行包**（`packages/`）：icons-react / vue / svelte / angular / solidjs / preact / react-native / webfont / **sprite** / **png** / **pdf** / **eps**。
  - ⚠️ 关键坑：`icons-png` / `icons-pdf` / `icons-eps` 目录里**只有 `build.mjs` 构建脚本，0 个预生成文件**（实测 `find icons-png -name "*.png" | wc -l` = 0）。要 PNG/PDF/EPS 得自己跑 build。**别指望直接拿到现成 PNG。**

## ③ 怎么复用进 python-pptx deck（核心：能否喂我们 BLOCK_ARC/custGeom 路线）

**先看两套风格的 SVG 本质（决定能不能直接喂 custGeom）：**

- **filled（填充）= 可直喂 custGeom ✅✅** —— 单个 `<path d="...">`，`fill="currentColor"`，**闭合区域填充**；带洞的图标靠反向缠绕子路径 + 默认 nonzero 规则挖洞（实测 filled 全集 0 个显式 `fill-rule`）。
  - 这恰好就是 **custGeom 干的事**：定义一个闭合轮廓 + 填一个色。把 SVG 的 `M/L/C/Z` 命令 → DrawingML 的 `moveTo/lnTo/cubicBezTo/close`，坐标按 24→EMU 等比缩放即可。**filled 这 1053 个是我们路线的天然弹药。**
  - 样本（`filled/star.svg`）：一条 `M8.243 7.34 ... z` 闭合路径——直接是五角星轮廓。
- **outline（线性）= 不能直喂 custGeom ⚠️** —— `fill="none" stroke="currentColor" stroke-width="2"`，是**被描边的开放路径**（如 `arrow-right` = 3 条独立线段 `M5 12l14 0` 等）。
  - custGeom 是「填区域」不是「描线」：要还原 outline 视觉，得把 2px 描边 **膨胀成闭合轮廓**（stroke→outline / offset），这是非平凡几何运算。**直接当 custGeom 路径喂 = 得到一堆细针状填充，渲染错。**

**→ 三条复用通道（按工程性价比排序）：**

1. **filled 图标 → custGeom**（最契合我们既有 BLOCK_ARC/custGeom 路线）：写个 SVG-path→DrawingML 转换器，只吃 filled 子集。一次性建「图标名→custGeom XML」映射表，deck 里按需调。**矢量、可改色、随母版主题色走（原 `currentColor` 正好对应「跟随文字色」）。**
2. **任意图标 → 转 PNG/EMF 后 `add_picture()`**（最省事、最通用，覆盖 outline）：用 cairosvg / Inkscape / 官方 `icons-png` build 脚本把 SVG 栅格化成高分辨率 PNG（或转 EMF 保矢量），python-pptx `slide.shapes.add_picture()` 落图。**绕开 custGeom，outline 也能用，但失去 pptx 原生矢量可编辑性。**
3. **outline → stroke-to-outline 后再 custGeom**（要原生矢量线性图标才做）：需引入描边转轮廓库，复杂度高，**首版不做**。

## ④ 对 PPT Engine 的落点

- **直接收编进我们的 `08 素材库`** 作为图标供给源，MIT 无合规阻力。
- **优先做「filled 子集 → custGeom 映射」小工具**：和我们已有 custGeom 能力同构，能产出**主题色自适应的原生矢量图标**（这是通用 agent / 大厂 skill 做不出的「咨询级精修」细节，契合铁律 4 收窄高 stakes 段）。
- **HTML 注释里的 `tags` + `category`** 是现成的图标检索语料：可建「语义→图标名」索引，给制作层「这页讲增长→自动选 trending-up 图标」之类的智能挑图打底。
- **Charts(39) / Arrows(332) / Currencies(76) / E-commerce(150)** 这几类正好覆盖咨询/投资人 deck 高频图元（KPI、流程箭头、财务、市场）。

## ⑤ 坑

1. **PNG/PDF/EPS 包是空壳脚本**（见 ②）——要现成位图得自己 build，别误以为 clone 完就有。
2. **outline ≠ filled，别一把 path 全塞 custGeom**：outline 是描边路径，直喂 custGeom 渲染会错（见 ③）。必须先按子目录分流。
3. **`currentColor` 依赖上下文取色**：SVG 里颜色写死成 `currentColor`，转 pptx 时必须显式赋色（custGeom 的 `solidFill` / 图片的预渲染色），不会自动继承。
4. **filled 挖洞靠缠绕方向（nonzero）**：转 DrawingML 时**子路径方向/闭合必须保真**，否则洞填实、图标糊成一坨。建议 custGeom 显式用 even-odd 心智校验输出。
5. **outline 的圆角 join**（`stroke-linecap/linejoin=round`）：走 PNG/EMF 通道能保真；若硬转 custGeom 还原线性，圆角端点会丢。
6. **版本漂移**：本地是 v3.44.0 快照，图标会随上游增删（filled 文件头 `version` 各异）。我们映射表要锁版本，别假设图标名永久稳定。

---

### 一句话结论
**最值得纳入的 1 点：filled 子集（1053 个单一闭合路径 SVG）能近乎零摩擦转成我们已有的 custGeom，产出「跟随主题色的原生矢量图标」——这正是咨询级 deck 要、而通用工具给不了的精修弹药；outline 那 5093 个先走 PNG/EMF 图片通道兜底即可。**
