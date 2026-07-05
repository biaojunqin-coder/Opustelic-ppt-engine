# PptxGenJS 拆解笔记

> 拆解对象：`04_制作明珠/PptxGenJS`
> 仓库：https://github.com/gitbrent/PptxGenJS · ~5.8k★ · **本地副本 v4.0.1** · MIT · 作者 Brent Ely
> 拆解日期：2026-06-30 · 拆解人：Claude（PPT Engine 研究层）
> 方法：`ls -R` + README + CHANGELOG + 源码（src/*.ts，约 50 万字符）+ demos/modules 精读，**结论均带出处行号，不掺常识推断**；存疑处显式标注。
> 定位：**JS 路线参照**。我们制作层主力是 python-pptx；拆它是为看「JS 原生路线在图表上是否更强、有什么 API/实现思路可借」。

---

## 一句话：最值得偷的 1 件事

**每张图表都同步生成一份「内嵌的真 Excel 工作簿」（一个完整的迷你 `.xlsx` ZIP，含 sharedStrings / worksheets / styles / theme），作为图表的数据源塞进 pptx**——见 `src/gen-charts.ts:32 createExcelWorksheet()`，它 `new JSZip()` 现造 `[Content_Types].xml`、`xl/workbook.xml`、`xl/worksheets/sheet1.xml` 等全套 OOXML 部件（`gen-charts.ts:35-60`）。效果：导出的图表在 PowerPoint 里**「编辑数据」按钮能正常打开 Excel 改数**（CHANGELOG.md:96 专门修过这个），是「活图表」而非贴死的图片。**这正是 python-pptx 用 `add_chart()` 也在做的事，但 PptxGenJS 把整个 xlsx 部件的手写 XML 摊开在一个函数里、零依赖（只靠 JSZip 压包）**——如果我们要在 python-pptx 之外手搓任何图表 XML（比如做它不支持的 waterfall），这个函数就是「图表数据源部件长什么样」的最佳逐字范本。

---

## ① 能力边界：原生图表 vs python-pptx，谁更强？

**结论：两者图表原生能力几乎一样、且都受同一上限封死——只能产出 PowerPoint 原生认识的那 ~10 种图表，谁都做不出 waterfall/Mekko。** 真要说差别，PptxGenJS 在「图表配置项的丰富度 + combo 组合图」上略占优，python-pptx 在「读改现有 pptx」上独占。

### 原生支持的图表类型（封死在类型系统里，共 10 种）
出处 `src/core-enums.ts:42`，`CHART_NAME` 联合类型**穷举**：
```ts
export type CHART_NAME = 'area' | 'bar' | 'bar3D' | 'bubble' | 'bubble3D'
                       | 'doughnut' | 'line' | 'pie' | 'radar' | 'scatter'
```
`ChartType` / `CHART_TYPE` 两个 enum（core-enums.ts:109、:697）也是**同样这 10 个**，一个不多。这 10 种正好 = OOXML `c:chartSpace` 原生支持的图表族。`addChart()` 的入参类型就是 `CHART_NAME | IChartMulti[]`（slide.ts:167、core-interfaces.ts:1811），编译期就把范围锁死。

### 「变体」靠 grouping 参数堆，不算新类型
- **stacked / percentStacked / clustered**：不是独立类型，是 `barGrouping` 字符串参数（core-interfaces.ts:1463；XML 落点 gen-charts.ts:789-790 `<c:grouping val="...">`，:1022-1023 `<c:overlap>`）。stacked area 同理（gen-charts.ts:784）。
- 所以「堆叠柱/百分比堆叠柱/堆叠面积」都只是 bar/area 的参数态。

### vs python-pptx 的对照（基于框架公知，**非本仓库证据**，标注存疑）
- python-pptx 的 `XL_CHART_TYPE` 同样只覆盖 column/bar/line/pie/doughnut/area/radar/xy(scatter)/bubble 这一族，**同样没有 waterfall/Mekko/Gantt/treemap/sunburst/box&whisker**（这些是 Office 2016+ 的「新式图表」，用的是 `chartEx`/`cx:` 命名空间，两个库都没实现）。
- **谁更强**：图表类型覆盖面 ≈ 打平。配置项 PptxGenJS 更细（见③的清单 + combo 组合图，python-pptx 做 combo 要手搓 XML）。**唯一硬差距**：python-pptx 能**打开并修改已有 .pptx**；PptxGenJS **只能从零生成、不能读入**（README 通篇只讲 create/export，无 open/parse；导入是其姊妹生态 `pptxtojson` 另一个库的事）。

---

## ② 高 stakes 图表：waterfall / Mekko / Gantt 原生支持吗？

**一律不支持。三个都没有。** 这是本次拆解对 PPT Engine 最关键的判定——**指望换 JS 路线白捡高 stakes 图表，此路不通。**

| 高 stakes 图表 | PptxGenJS 原生？ | 证据 |
|---|---|---|
| **Waterfall（瀑布/桥图）** | ❌ 无 | `CHART_NAME` 无此项（core-enums.ts:42）；全仓库源码搜 `waterfall` **零命中**（仅命中 demos 里的 minified 第三方 bundle，是误报） |
| **Marimekko / Mekko** | ❌ 无 | 同上，`mekko`/`marimekko` 源码零命中 |
| **Gantt（甘特）** | ❌ 无 | 同上，`gantt` 源码零命中；无任何示例 |
| Funnel（漏斗） | ⚠️ **陷阱：是形状不是图表** | `'funnel'` 只在 core-enums.ts:212/412/607 出现，且**夹在 `frame` 与 `gear6` 之间**——它属于 `SHAPE_TYPE`（形状），**不在 `gen-charts.ts` 里出现一次**，即不能当图表 `addChart('funnel')`。别被这个词误导。 |

**怎么解读**：waterfall / Gantt 在真·咨询 deck 里，业界（含本库用户）通常**不靠原生图表，而是用「堆叠条 + 透明占位段」手工拼**——PptxGenJS 给的积木是齐的：`barDir`（横向条做 Gantt）、`barGrouping:'stacked'`、单段 `chartColors` 上色、`invertedColors`（负值反色，core-interfaces.ts:1249）。但**这是「用通用积木搭」，不是「调一个 waterfall API」**，复杂度全在调用方。→ 直接印证我们铁律 4「PPT 收窄高 stakes 段」的判断：**waterfall/Mekko/Gantt 是大厂 skill 和现成库都做不出的段，正是 PPT Engine 该自建手法卡去啃的护城河，别期待任何现成库代劳。**

---

## ③ 能借什么（即便我们走 python-pptx）

### 3A. 【最该借】图表数据源 = 内嵌真 xlsx 的逐字 XML 范本
`gen-charts.ts:32-540` 的 `createExcelWorksheet()` 是一份**可直接照抄的「图表内嵌 Excel 部件」OOXML 教科书**：现造 `[Content_Types].xml` / `_rels` / `xl/workbook.xml` / `xl/worksheets/sheet1.xml` / `sharedStrings.xml` / `styles.xml` / `theme1.xml`（:35-60 起一路手写）。
→ **落点**：哪天我们要在 python-pptx 之外手搓 waterfall 这类库不支持的图表，「数据源 xlsx 该塞哪些部件、每个部件 XML 长啥样」这里有现成答案，省去啃 ECMA-376 原始规范。

### 3B. 【该借】combo（多类型组合）图 + 双轴的实现思路
- API 设计：`addChart(IChartMulti[], data, opts)`——**多个图表类型用数组传**，每个元素 `{ type, data, options }`，靠 `secondaryValAxis`/`secondaryCatAxis` 布尔把某一系列甩到副轴（core-interfaces.ts:1208 `IChartMulti`、:1368/:1402）。
- 渲染：`makeXmlCharts()` 检测 `Array.isArray(rel.opts._type)` 就 forEach 每个 type 各调一次 `makeChartType()`，再统一拼 cat/val 轴并按 `usesSecondaryValAxis` 决定是否加副轴（gen-charts.ts:608-656）。
- 实例：demo_chart.mjs:1782-1837「BAR(stacked) + LINE(副轴)」的咨询级双轴组合图。
→ **落点**：python-pptx 原生**不友好 combo**（要手动往同一 `plotArea` 塞第二个 `<c:lineChart>`）。这套「数组 + 副轴布尔」的**入参建模**值得抄进我们的图表手法卡 API 设计——把「主图类型 / 副图类型 / 谁上副轴」做成声明式参数，而非让用户手摆 XML。

### 3C. 【该借】图表配置项的「全集清单」当需求 checklist
PptxGenJS 把 PowerPoint 图表面板里能点的几乎全暴露成了扁平参数（core-interfaces.ts 图表段 ~1240-1480）：`valAxisLogScaleBase`（对数轴）、`catAxisLabelRotate`（轴标签旋转）、`showDataTable`（图下数据表，gen-charts.ts:661-676）、`dataLabelPosition`、`firstSliceAngle`（饼图起始角）、`holeSize`（甜甜圈孔径）、`barGapWidthPct`/`barOverlapPct`、`invertedColors`、`plotArea`/`chartArea`（各自描边填充）……
→ **落点**：当成「咨询级图表至少要能调哪些项」的**反向需求清单**——我们的图表手法卡要对标的最低配置面，照着它逐条核我们 python-pptx 封装漏没漏。

### 3D. 【可借】HTML `<table>` → 幻灯片的一行式 API
`pptx.tableToSlides("tableElementId")`（README:162），自动把网页表格切成多页 pptx 表格（含自动分页）。源码在 gen-tables.ts。
→ 跟我们 python-pptx 路线栈不同（它读 DOM），但「表格自动溢出分页」的切分逻辑思路可参考。

---

## ④ 对 PPT Engine 的落点（汇总）

1. **路线判定（最重要）**：**不要为了图表能力切到 JS/PptxGenJS**。它的原生图表 = python-pptx 同一上限，waterfall/Mekko/Gantt 双方都无。切栈白费、还丢掉 python-pptx「读改现有 pptx」的独门能力。**维持 python-pptx 为制作层主力的决策，本次得到正面验证。**
2. **高 stakes 段必须自建**：③印证铁律 4。waterfall/Gantt 的实现路径已明确——**堆叠条 + 透明占位段**手工拼（两库都这么干），这应落成 PPT Engine 的**图表手法卡**，不是找库。
3. **手搓图表 XML 时直接抄 3A**：`createExcelWorksheet()` 是内嵌数据源部件的逐字范本，进我们的「制作层参考实现」收藏。
4. **图表 API 设计抄 3B + 用 3C 当 checklist**：combo 的「数组 + 副轴布尔」声明式建模，配置项全集当封装完备度的验收清单。

---

## ⑤ License + 坑

### License：MIT（最宽松，可放心借鉴/抄代码）
- `LICENSE`：MIT，Copyright (c) 2015-2022 Brent Ely。可商用、可改、可闭源分发，仅需保留版权声明。**对我们零障碍**（对照：同生态 PPTist 是 AGPL-3.0，传染性强，不能直接抄代码）。
- ⚠️ 一个出处小注：README 顶部 © 写「2015-present」，LICENSE 文件写「2015-2022」——年份不一致，无实质影响。

### 坑 / 注意
1. **版本号对不上用户描述**：用户说 5.8k★，但**本地副本 package.json 是 v4.0.1**（不是某些资料里的 3.x）。星数大致吻合该项目量级，但**笔记里所有结论以本地 v4.0.1 源码为准**。
2. **`funnel` 是形状不是图表**（②已述）——最容易踩的认知坑，`addChart('funnel')` 不存在。
3. **只能生成、不能读入**：无 open/parse 既有 pptx 的能力。需要「改模板」场景它做不了（这正是 python-pptx 强项）。
4. **图表 + 媒体同页历史性炸文件**：CHANGELOG 多次出现「chart 与 image/media 同一张幻灯片导致 PowerPoint 报『需要修复』」(CHANGELOG.md:92/116，:377 同页 addChart+addImage 报错)——OOXML rId 关系管理的硬坑，提示**任何手搓 pptx 关系部件时，rId 唯一性是高危区**，我们手搓 XML 时引以为戒。
5. **Bubble 图曾被限 26 列**（CHANGELOG.md:93，因列名用 A-Z 单字母）——映射 Excel 列名时的经典越界坑。
6. **依赖**：运行期仅 `jszip`（打包 pptx）；Node 侧可选 `image-size`/`https`（取远程图）。浏览器构建里这些被 `package.json` 的 `browser` 字段 stub 成 false——零运行时依赖是其卖点。

---

## 附：源码地标（便于复查）

| 关注点 | 文件:行 |
|---|---|
| 图表类型穷举（10 种） | `src/core-enums.ts:42`（CHART_NAME）、:109、:697 |
| `funnel` = 形状非图表 | `src/core-enums.ts:212`（夹在 frame/gear6 间） |
| **内嵌 Excel 数据源（最该抄）** | `src/gen-charts.ts:32` createExcelWorksheet() |
| 图表主 XML / combo 分发 | `src/gen-charts.ts:547` makeXmlCharts()、:608-656 多类型+副轴 |
| 单类型图表 XML | `src/gen-charts.ts:768` makeChartType()；stacked :784-790；overlap :1022 |
| combo 入参建模 | `src/core-interfaces.ts:1208` IChartMulti；addChart 签名 :1811 |
| 图表配置项全集 | `src/core-interfaces.ts` ~1240-1480 |
| combo 实例 | `demos/modules/demo_chart.mjs:1775-1837` |
| 表→幻灯片 | `src/gen-tables.ts`；README:162 tableToSlides |
