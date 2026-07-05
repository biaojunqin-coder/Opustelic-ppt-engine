# plotly.js 拆解笔记

> 拆解对象：`05_图表库/plotly.js`
> 仓库：https://github.com/plotly/plotly.js · ~17k★ · **本地副本 v3.6.0**（package.json:3）· MIT · Plotly Technologies Inc.
> 拆解日期：2026-06-30 · 拆解人：Claude（PPT Engine 研究层）
> 方法：grep + README + 源码精读（`src/traces/waterfall/*`、`src/traces/bar/*`）+ 官方 Python 文档联网核实，**JS 端结论带文件:行号、Python 端结论带链接，不掺常识推断**；存疑处显式标注。
> 定位：**资源地图称「waterfall 原生最佳」**。拆它是为看「瀑布图业界最好的原生数据结构长什么样」，反哺我们 python-pptx 制作层手搓 waterfall 的手法卡设计。
> ⚠️ 路线提醒：plotly 是 **Web/SVG 渲染库**，产出 `<svg>` 或 canvas，**不产 OOXML**。它和我们「pptx 原生可编辑图表」是两条栈——它的价值是「数据结构 + 算法范本」，不是「插件直接用」。

---

## 一句话：最值得偷的 1 件事

**waterfall 不是新图表类型，而是「一个 `measure` 数组驱动的智能堆叠条」——把『这一项是涨跌量(relative)还是累计柱(total)还是重置基准(absolute)』编码进一个与数据等长的字符串数组，由 calc 算法用一个滚动的 `previousSum` 把『增量』翻译成『绝对堆叠位置』。** 见 `src/traces/waterfall/calc.js:42-99`：核心就是一个 for 循环维护 `previousSum`，relative 项做 `cdi.s = previousSum + newSize; previousSum += newSize`（:79-81），total/absolute 项把当前柱画到 `previousSum` 高度而不累加（:65-74）。**这正是我们手搓 waterfall 该照搬的数据契约**——用户只填「每段的增量 + 一个 measure 标记」，引擎负责累加成堆叠坐标，绝不让用户自己算「这根浮空柱该从 Y=37 画到 Y=52」。plot 层更印证「waterfall = bar 的特例」：`waterfall/plot.js:15` 直接 `barPlot.plot(...)` 复用柱状图渲染，自己只额外画了一层连接线（:25 `plotConnectors`）。

---

## ① 是什么 + 定位 + License

- **是什么**：Plotly 的开源 JS 图表库，「dozens of chart types」——统计图 / 3D / 科学图 / 地图 / 金融图（README:9）。是 plotly.py（Python）、plotly R、Dash 的**底层渲染引擎**——Python 端 `go.Waterfall` / `px.timeline` 最终都序列化成这套 JS 的 trace JSON 来画。
- **架构**：每种图叫一个 **trace**，放在 `src/traces/<name>/`，标准切成 `attributes.js`(参数schema) / `defaults.js`(默认值) / `calc.js`(数据预处理) / `plot.js`(SVG渲染) / `hover.js` 等。waterfall、bar、funnel、funnelarea、barpolar 都在 `src/traces/` 下。
- **License**：**MIT**（LICENSE，Copyright 2016-2024 Plotly Technologies Inc.；README:5/179）。最宽松，可放心读源码/抄算法/抄数据结构，**对我们零障碍**。
- ⚠️ 本地副本 **v3.6.0**，不是官网最新 6.x。waterfall / timeline 的核心机制多年稳定，结论一致；但具体 API 细节以本地源码为准。

---

## ②【重点】waterfall 原生怎么做——数据结构 + 配置

这是 plotly 的强项，逐层拆给我们当范本。

### 2A. 数据契约（用户填什么）——`attributes.js`
一根瀑布图 trace 的核心入参（`src/traces/waterfall/attributes.js`）：

| 参数 | 类型 | 作用 | 出处 |
|---|---|---|---|
| **`measure`** | `data_array` | **灵魂**。与数据等长的字符串数组，每项 ∈ `{relative, total, absolute}`。默认 `relative`（涨跌量）；`total` = 在此处画一根「累计总额」柱；`absolute` = 重置基准到某绝对值（用于设期初值/中途重置） | attributes.js:40-51（描述原文：default relative / 'total' to compute sums / 'absolute' to reset or declare initial value） |
| `x` / `y` | data_array | 一轴是类目（每段标签），一轴是数值（每段增量）。`orientation` 决定哪轴是数值轴 | :61-65, :110 |
| `base` | number | 整体基线偏移（在位置轴单位） | :53-59 |
| `increasing` / `decreasing` / `totals` | object | **三组独立配色**：涨 / 跌 / 总计柱各自的 `marker.color` + 边框 | :115-117, directionAttrs :12-37 |
| `connector` | object | 段间连接线：`mode ∈ {spanning, between}`（:128-134，默认 between）、`line.{color,width,dash}`、`visible` | :119-142 |
| `textinfo` | flaglist | 柱上显示什么：`label/text/initial/delta/final` | :85-96 |

**关键洞察**：用户**只填「每段增量 + measure 标记」**，从不填「浮空柱的起止坐标」。`total` 柱甚至**不需要用户给值**——引擎自己用累计的 `previousSum` 填（见 2B）。这是瀑布图易用性的命门。

### 2B. 累加算法（引擎做什么）——`calc.js:42-99`
一个 for 循环 + 一个滚动 `previousSum`，把「增量」翻译成「堆叠坐标」：
- **relative（默认）**：`newSize = cdi.s; cdi.s = previousSum + newSize; previousSum += newSize`（:79-81）——这一段从上一段顶部接着画，方向由 `rawS<0 ? 'decreasing':'increasing'`（:78）自动判定涨跌（决定用哪组配色）。
- **total**：`cdi.s = previousSum`（:71-74）——把柱画到「当前累计高度」，**不改 previousSum**（所以是一根从 0 到累计值的实心总额柱）。`cdi.isSum = true; cdi.dir = 'totals'`。
- **absolute**：`previousSum = cdi.s`（:65-69）——**重置**累计基准到该绝对值（用于期初值或中途归零再起）。同样标 `dir='totals'`。
- 同时算 `cNext`（:50-55）：判断「这一段和下一段是否都有效」→ 决定段间连接线画不画。

### 2C. 连接线渲染——`plot.js:25-101`
`plotConnectors` 手画 SVG `path`：`spanning` 模式贯穿连（:66-73），`between` 模式只连相邻段端点（:76-84）。waterfall 自己只比 bar 多这一层线，**其余 100% 复用 `barPlot.plot`**（plot.js:15）。

### 2D. 默认配色（开箱即专业）——`defaults.js:13-15`
- 涨 `INCREASING_COLOR = #3D9970`（墨绿）、跌 `DECREASING_COLOR = #FF4136`（红）、总计 `TOTALS_COLOR = #4499FF`（蓝）。涨跌取自 `src/constants/delta.js:5/9`（全局金融涨跌色，复用到 candlestick/indicator）。
- **落点**：这套「绿涨/红跌/蓝总计」是金融界默认语义色，我们手法卡可直接沿用当默认（再让用户覆盖）。

### 2E. 布局参数——`layout_attributes.js`
`waterfallmode ∈ {group, overlay}`（多 trace 并排/叠放，默认 group）、`waterfallgap`（相邻类目间距）、`waterfallgroupgap`。多组瀑布对比时用。

---

## ③ Gantt 怎么做 + 缺什么

**plotly.js 的 JS 核心没有 gantt / timeline trace**（grep `timeline|gantt` 仅命中一处变量名+一处注释，见下）。Gantt 是 **Python 端 plotly.express 的 `px.timeline`** 提供的便捷封装——本质仍是**横向 bar**，用日期当数值轴。

### 3A. px.timeline 怎么用（Python 端，联网核实）
- `px.timeline(df, x_start=, x_end=, y=, color=)`：每行 = 一个横向矩形，从 `x_start` 画到 `x_end`（X 轴 `type=date`），`y` 是任务名，`color` 上色。v4.9 引入，取代已弃用的 `figure_factory.create_gantt()`。
- `y` 设成分组变量（如 Resource）可让多任务挤一行做「资源视图」。
- 来源：[plotly.com/python/gantt](https://plotly.com/python/gantt/)、[px.timeline API](https://plotly.com/python-api-reference/generated/plotly.express.timeline.html)

### 3B.【关键】缺什么——咨询级 Gantt 的硬伤
px.timeline **不支持**（官方文档核实，[gantt.md](https://github.com/plotly/plotly.py/blob/main/doc/python/gantt.md)）：
- ❌ **里程碑**（零工期的菱形标记）——而真实项目 deck 的 Gantt 几乎必有里程碑节点
- ❌ **任务依赖箭头**（task A→B 的连接线）
- ❌ **today / 基准线**（垂直参考线标「现在」）

→ 这三样正是咨询级 Gantt 区别于「玩具横条图」的地方。**连 plotly 这种最成熟的库都只给『带颜色的横条』**，里程碑/依赖/today 线全要调用方自己 `add_shape`/`add_trace` 手搓。

### 3C. plotly 官方自己承认 Gantt 没做好（铁证）
`src/traces/bar/cross_trace_calc.js:189-193` 开发者注释原文：
```
// not sure if it really makes sense to have dates for bar size data...
// ideally if we want to make gantt charts or something we'd treat
// the actual size (trace.x or y) as time delta but base as absolute
// time. But included here for completeness.
```
→ 双重价值：①**官方亲口承认** Gantt 在 JS 核心是「included for completeness」的半成品，没正经 trace。②**点破了实现思路**——「把 size 当时间增量(duration)、把 `base` 当绝对起始时间」。这正是用 `bar` 的 `base` 偏移做 Gantt 的路径（bar/attributes.js:171 有 `base`），是我们手搓 Gantt 手法卡的算法骨架。

---

## ④ Mekko 为何不行

**plotly 全栈无 Mekko / Marimekko，连半成品都没有。**
- 证据：`grep -ril "mekko|marimekko" src/` **零命中**（JS 核心彻底没有）。Python 端 plotly.express 也无 `px.mekko` / `px.marimekko`。
- **为什么难**：Mekko（变宽堆叠柱，柱宽 ∝ 占比、柱内再按比例分段）需要**每根柱独立宽度 + 双重百分比归一**。plotly 的 bar 模型里同一 trace 所有柱**共享统一 width**（bar/attributes.js 的 `width` 是标量或等长数组，但布局引擎 `barmode` 按统一网格摆位），没有「按数值驱动柱宽 + 柱间无缝拼接」的布局原语。要做只能把每根柱拆成独立 trace 手摆 `base`/`width`/`x`，复杂度爆炸——所以**最成熟的开源库也直接放弃**。
- → 强力印证铁律 4：**Mekko 是 plotly 这种顶级库都不做的段，正是 PPT Engine 护城河的最硬一块**，只能靠自建手法卡（矩形 + 双重比例算法）从零搭。

---

## ⑤【核心】对 PPT Engine 的落点

### 5A. plotly 渲染成图片插 pptx 的桥接思路（vs 我们要的原生可编辑）
- **桥接路径**：plotly figure → **Kaleido**（`fig.write_image("x.png")`）导出 PNG/SVG/PDF → python-pptx `slide.shapes.add_picture()` 贴进去。来源：[Kaleido](https://github.com/plotly/Kaleido)、[static-image-export](https://plotly.com/python/static-image-export/)。
- ⚠️ **三个致命局限，决定它只能当「应急/预览」不能当「主交付」**：
  1. **死图片，零可编辑**：插进 pptx 的是一张位图（或 SVG 矢量但仍是图形，非 `c:chart`）。**客户在 PowerPoint 里点不动数据、改不了一个字、调不了一根柱**——直接违反我们「咨询级 deck 要可编辑」的核心价值（铁律 4 高 stakes 段）。
  2. **部署重**：Kaleido **1.0.0+ 要求装 Chrome**（[Kaleido README](https://github.com/plotly/Kaleido)）——一个画图要拖一个浏览器引擎，CI/容器里是大坑。
  3. **字体/主题割裂**：plotly 的字体、配色、模板和 pptx 母版是两套，贴进去风格对不上母版，要额外调。
- **结论**：**plotly 不进我们主交付链路**。它的正确用法是「**数据结构 + 算法的范本仓库**」——我们抄它 waterfall 的 `measure` 契约和 `previousSum` 累加算法，用 **python-pptx 手搓原生可编辑的堆叠条**实现，而不是让 plotly 渲染图片。

### 5B. 该抄进手法卡的三件具体资产
1. **waterfall 数据契约**：照搬 `measure` 数组（relative/total/absolute）+「用户只填增量、引擎累加坐标」的设计（②）。这是瀑布图易用性的命门，直接定义我们 waterfall 手法卡的 API。
2. **累加算法**：`calc.js` 的 `previousSum` 滚动逻辑（2B）——逐字可移植到 Python，输出「每根柱的堆叠起止 + 涨跌方向」，喂给 python-pptx 画透明占位段 + 实心段。
3. **默认语义色**：绿涨#3D9970 / 红跌#FF4136 / 蓝总计#4499FF（2D）当手法卡默认。
4. **Gantt 算法骨架**：bar `base` 偏移 = 任务起始时间、bar 长度 = 工期（③C 官方注释点破的思路）；**且必须补 plotly 都没给的里程碑/依赖/today 线**（③B）——这三样正是我们 Gantt 手法卡相对「现成库」的增量价值。

---

## ⑥ 坑 / 注意

1. **栈错位（最大的坑）**：plotly 产 **SVG/canvas**，**不产 OOXML**。别误以为「拆了 plotly 就能直接生成 pptx 图表」——它和我们是两条栈，只能借数据结构/算法，渲染层完全不通用。
2. **「waterfall 原生最佳」要正确理解**：是「**Web 渲染场景**下原生数据结构最优雅」，**不等于「能直接产出 pptx 原生瀑布图」**。PowerPoint 的 OOXML 也没有原生 waterfall chart 类型（Office 2016+ 的 waterfall 走 `chartEx`/`cx:` 扩展命名空间，python-pptx/PptxGenJS 都没实现——见 PptxGenJS 拆解笔记②）。所以无论哪条路，pptx 里的瀑布图都得「堆叠条 + 透明占位段」手搓，plotly 给的是**该怎么算**的范本而非**该怎么写 XML**。
3. **Gantt/Mekko 别指望 plotly 代劳**：Gantt 是半成品横条（官方注释自认）、Mekko 全无。护城河得自建。
4. **Kaleido 装 Chrome**：1.0.0+ 拖浏览器引擎，部署成本高（⑤A）。若真要走「图片应急路线」，预留这个依赖坑。
5. **本地副本 v3.6.0 ≠ 最新**：核心机制稳定，但若查具体新 API 需对照官网最新版。
6. **funnel 是真图表（与 PptxGenJS 相反）**：plotly 的 `src/traces/funnel/` 是正经漏斗图 trace（不是形状）。但漏斗不在我们高 stakes 收窄清单内，仅备注避免和 PptxGenJS 笔记（funnel=形状）混淆。

---

## 附：源码地标（便于复查）

| 关注点 | 文件:行 |
|---|---|
| **waterfall 数据契约（measure 等）** | `src/traces/waterfall/attributes.js:40-142` |
| **waterfall 累加算法（previousSum）** | `src/traces/waterfall/calc.js:42-99` |
| waterfall = bar 特例（复用渲染） | `src/traces/waterfall/plot.js:15`；连接线 :25-101 |
| waterfall 默认配色 | `src/traces/waterfall/defaults.js:13-15` |
| 全局涨跌色常量 | `src/constants/delta.js:5/9` |
| waterfall 布局（mode/gap） | `src/traces/waterfall/layout_attributes.js` |
| **Gantt 官方自认半成品（注释）** | `src/traces/bar/cross_trace_calc.js:189-193` |
| bar 的 base 偏移（Gantt/占位关键） | `src/traces/bar/attributes.js:171` |
| Mekko 零命中证据 | `grep -ril "mekko\|marimekko" src/` → 空 |
| px.timeline / 里程碑缺失 | [gantt.md](https://github.com/plotly/plotly.py/blob/main/doc/python/gantt.md)、[px.timeline](https://plotly.com/python-api-reference/generated/plotly.express.timeline.html) |
| Kaleido 静态导出 + 装 Chrome | [Kaleido](https://github.com/plotly/Kaleido)、[static-image-export](https://plotly.com/python/static-image-export/) |
