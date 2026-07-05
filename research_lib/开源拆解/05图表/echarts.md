# Apache ECharts 轻拆 · waterfall「模拟」通法

> 拆解对象：`/Users/qinbiaojuan/Documents/PPT开源参考/05_图表库/echarts`（本地克隆）
> 拆解日期：2026-06-30 · 维度：①定位 ②waterfall 模拟 ③Gantt/custom ④PPT Engine 落点 ⑤坑
> 资源地图原判：waterfall「模拟」· Mekko ❌ · Gantt ~ —— **本次拆解全部印证**。

## ① 是什么 + 定位 + license

- **Apache ECharts**：纯 JavaScript 声明式可视化库，底层基于自家 canvas 引擎 `zrender`（README 首段）。Web/浏览器侧渲染，**不是后端出图库**（对 PPT 的关系见 ④）。
- **License：Apache License V2**（`LICENSE` 头确认 = Apache 2.0，2004 版；README「## License」节亦写明）。Apache 2 = 可商用、可改、需保留版权与 NOTICE，**对本项目商用友好**。出处：`README.md` + `LICENSE` + `NOTICE`。
- 论文背书：*ECharts: A Declarative Framework...*, Visual Informatics 2018（README 末「## Paper」）—— 说明它是「声明式 option 配置 → 图」范式，这点对 ④ 很关键。
- **原生 series 类型清单**（出处 `src/chart/` 目录直接 `ls`）：
  `bar / boxplot / candlestick / chord / custom / effectScatter / funnel / gauge / graph / heatmap / line / lines / map / parallel / pictorialBar / pie / radar / sankey / scatter / sunburst / themeRiver / tree / treemap`。
  → **无 `waterfall`、无 `gantt`、无 `mekko/marimekko`**（目录里逐一核对，确无对应文件/目录）。这是「模拟 / ❌ / ~」三档判断的源头硬证据。

## ② waterfall 怎么「模拟」（业界通法 · 本节重点）

ECharts 没有 waterfall 这个 series type，瀑布图是**用「堆叠柱状图 + 底部透明占位段」拼出来的**。机制拆解（均带 echarts 源码出处）：

**机制 A — 堆叠：靠 `stack` 字段同名归组。**
- `bar` 系列支持 `stack` 配置项，出处 `src/chart/bar/BaseBarSeries.ts:205`（默认 `// stack: null`，即不堆叠）。
- 堆叠规则：**多个 bar series 的 `stack` 取同一个字符串值 → 它们在同一类目上累加堆叠**（同 stack 名 = 叠在一起）。累加/数据归一逻辑落在 `src/chart/bar/BaseBarSeries.ts`、`src/chart/helper/createSeriesData.ts`（grep `stack` 命中处）。
- 因此瀑布图 = **2 个 bar series 共用同一个 `stack` 名**：
  - series 1（「占位 / 垫脚」段）：从 0 累加到「该柱起点高度」，**设为透明不可见**；
  - series 2（「可见」段）：在占位段之上画出真正要展示的增量条。

**机制 B — 透明占位：靠 `itemStyle.color: 'transparent'`。**
- 透明色填充在测试用例里有现成惯用法，出处 `test/bar-polar-real-estate.html`（grep `transparent` 命中，属 bar 堆叠场景）。瀑布的「悬浮感」就是把垫脚段刷成 `transparent` 实现的——视觉上只看到漂在半空的增量条，垫脚段隐形但仍占据高度。

**完整套路（业界标准做法，可直接复用的 option 结构）：**
```
对每根柱，先算「累计起点 base[i]」= 前面所有柱的净累计高度。
series = [
  { name:'占位', type:'bar', stack:'wf',
    data: base,                         // 每根柱的起点高度
    itemStyle:{ color:'transparent' },  // ← 关键：垫脚段隐形
    emphasis:{ itemStyle:{ color:'transparent' } } },  // hover 也别露出来
  { name:'增量', type:'bar', stack:'wf',
    data: delta,                        // 每根柱的可见增量（正/负）
    itemStyle:{ color: 涨绿/跌红 } }     // 升降可分色
]
```
- 起点 `base[i]` 和增量 `delta[i]` 是**调用方在喂数据前自己算好的**（前缀和），echarts 只负责「同 stack 名 → 堆起来」+「透明 → 隐形」两件事。瀑布的「逻辑」在数据预处理，**不在库里**。
- **近亲佐证**：echarts 原生 `candlestick`（K线图）本身就是「浮动矩形」——其数据维度是四元组 `open / close / lowest / highest`（出处 `src/chart/candlestick/CandlestickSeries.ts:99-103`，`defaultValueDimensions`），即每个图元由「起止两个值」定义一段悬浮区间，和 waterfall「悬浮增量条」是同一种「浮动柱」家族。但 candlestick 是金融专用语义（涨跌/影线），**不能直接当通用 waterfall 用**，所以瀑布仍走「堆叠柱 + 透明」这条通法。

## ③ Gantt / 自定义系列能力（资源地图判「Gantt ~」的根据）

- **没有原生 `gantt` series**（`src/chart/` 无此目录）。Gantt 在 echarts 里要靠 **`custom` 系列**手画。
- **`custom` 系列 = 任意图元逃生舱**：核心是 `renderItem` 回调（出处 `src/chart/custom/CustomSeries.ts:378` 定义 `renderItem?`；渲染主循环在 `src/chart/custom/CustomView.ts:228/288` 的 `makeRenderItem`）。`renderItem(params, api)` 由开发者返回自定义图元（rect/group/line…），配合 `api.value()`/`api.coord()` 把数据值映射到坐标，**几乎能画任何二维图形**。
- Gantt 的画法：每个任务一个 `rect` 图元，x 起点 = 开始时间、宽度 = 工期、y = 任务行；全靠 `custom` + `renderItem` 自绘。**能做，但要写渲染代码，不是配置项一行开**——这正是「Gantt ~（半支持/需自定义）」的含义。
- 同理：Mekko/Marimekko（变宽堆叠柱）echarts **无原生**，理论上也能 `custom` 硬画，但资源地图标 ❌ ——因为这是浏览器侧的逐图元绘制，搬到 PPT 侧成本/收益不划算（见 ④）。

## ④ 对 PPT Engine 的落点（最关键）

**结论先行：echarts 的代码不能直接用（JS/canvas/浏览器栈，python-pptx 是 Python 出原生 PPT 形状），但它的「思路」能 100% 搬。**

**可搬的核心思路 ——「堆叠柱 + 透明占位段」模拟 waterfall，在 python-pptx 里同样成立：**
- python-pptx 能建原生**堆叠柱图表**（`XL_CHART_TYPE.COLUMN_STACKED`），也能逐 series / 逐 data point 设 `format.fill`。
- 把 echarts 那套照搬：**series 1 = 占位段（fill 设为无填充 / `fill.background()`）+ series 2 = 增量段（涨跌分色）**，`base/delta` 前缀和在 Python 侧算好再喂图表。→ 得到**原生可编辑的 PPT 瀑布图**（用户在 PPT 里还能改数据），比贴一张 echarts 导出的 PNG 图片高一个段位。
- 这正落在本项目护城河定义上（CLAUDE.md 铁律 4：waterfall/Mekko/Gantt 这类「通用 agent 和大厂 skill 做不出的段」）。**echarts 验证了「瀑布=堆叠柱+透明」是跨技术栈的通法**，给 python-pptx 实现路径背了书。
- **Gantt 在 PPT 侧反而可能比 echarts 更顺**：echarts 要 `custom`+`renderItem` 逐图元自绘；python-pptx 直接摆原生矩形 shape（按时间轴定位 left/width）就能拼 Gantt，且原生形状可编辑。echarts 这里只提供「Gantt = 一堆定位矩形」的概念模型，不提供可复用代码。
- **声明式 option 的启发**：echarts「数据 + option → 图」的声明式范式，可借鉴为 PPT Engine 制作层的「图表 spec → python-pptx 调用」中间层（spec 描述 waterfall 的 base/delta/配色，引擎翻译成 pptx 堆叠柱），与本项目五层架构的「制作层」吻合。

**不可搬的部分**：echarts 全部渲染发生在浏览器 canvas（`zrender`），产物是网页/图片，不是 `.pptx` 原生形状。若直接用 echarts，只能「截图贴 PPT」=丢失可编辑性，**不符合本项目「原生可编辑高 stakes deck」定位**。所以 echarts 的角色是**「方法论参照物」而非「依赖库」**。

## ⑤ 坑

1. **waterfall 是「拼」出来的，不是「选」出来的**：没有 `type:'waterfall'`，新手会找不到。瀑布的正确/错误（累计起点算错就全盘错位）**全压在数据预处理（前缀和）上**，库不帮你兜底——这块逻辑搬到 python-pptx 也得自己写、自己测。
2. **透明占位段的 hover/legend 漏馅**：垫脚段只设 `itemStyle.color:transparent` 不够，`emphasis`（hover 高亮态）和 tooltip/legend 也要一并处理，否则鼠标划过会露出占位段、图例里多一项「占位」。搬到 PPT 侧对应的坑是：占位 series 别让它进图例/数据标签。
3. **负值瀑布更绕**：增量为负时「垫脚段起点」要相应下移，base/delta 的符号处理比纯正值复杂，echarts 不内建、得手算（PPT 侧同理）。
4. **candlestick ≠ 通用瀑布**：虽是浮动柱家族，但它绑死金融语义（open/close/lowest/highest + 涨跌/影线，出处 `CandlestickSeries.ts:99-103`、`borderColorDoji` 等于开=收的特殊态 line 124），**不能拿来当通用 waterfall**，别走错路。
5. **技术栈错配是最大坑**：echarts 是 JS/浏览器库，**直接当 PPT 出图引擎用 = 只能截图**，丢可编辑性、违背本项目定位。它对 PPT Engine 的价值是「思路/概念模型」，把它当依赖库选型会走偏。
6. **Mekko/Marimekko 真没有**：资源地图标 ❌ 属实，硬要做得 `custom` 自绘（变宽柱），浏览器侧成本高、搬 PPT 更不划算，优先级最低。

---
**一句话**：echarts 自身无原生瀑布图，业界通法是「**两个同 `stack` 名的柱系列 + 底部段刷 `itemStyle.color:'transparent'` 隐形**」拼出悬浮增量条——这套「堆叠柱+透明占位」思路与数据前缀和预处理，可原样搬进 python-pptx（占位 series 设无填充 + 增量 series 涨跌分色），产出**原生可编辑的 PPT 瀑布图**，正中本项目护城河。
