# python-pptx 拆解笔记

> 拆解对象：`/Users/qinbiaojuan/Documents/PPT开源参考/04_制作明珠/python-pptx`
> 仓库：https://github.com/scanny/python-pptx · ~3.4k★ · **v1.0.2（2024-08-07，`HISTORY.rst:6`）** · MIT（`LICENSE`，作者 Steve Canny）· 本机 git HEAD `278b47b`
> 依赖极轻：仅 `lxml>=3.1.0` + `Pillow>=3.3.2`（`pyproject.toml`）；图表内嵌 Excel 另需 `xlsxwriter`（`src/pptx/chart/xlsx.py:8`）。requires-python `>=3.8`。
> 拆解日期：2026-06-30 · 拆解人：Claude（PPT Engine 研究层）
> 方法：`ls -R` + `docs/user/*.rst` + `features/*.feature`（BDD 活文档）+ 核心源码精读。**结论均带文件:行号出处，不掺常识推断**；存疑/需联网核实处显式标注。
> 定位说明：这是 **PPT Engine 制作层钦定的原生底座**（「可编辑 pptx 是铁律」→ 必须走能生成真·OOXML 的库）。本笔记的核心任务是摸清：**做咨询级/投资人 deck 的高 stakes 图表（waterfall/Mekko/Gantt），它的天花板在哪、难图怎么绕。**

---

## ⭐ 一句话：最值得偷的 1 件事

**它的图表是「带内嵌真 Excel 工作簿的原生 `c:chart`」，不是贴图——这正是我们要的"可编辑铁律"在图表上的落地形态，但它的图表引擎永久停在 PowerPoint 2007 那批类型，waterfall/funnel/treemap/box 这些 2016+ 新图（走 `cx:chart`/chartex 命名空间）一个都做不了。**

`add_chart()` 时，`src/pptx/chart/xlsx.py` 用 `xlsxwriter.Workbook(..., {"in_memory": True})` 给每张图**真的生成一个 .xlsx 嵌进 pptx**（`xlsx.py:34-36`），`replace_data()` 同时改 chart XML 和这个 Excel blob（`chart/chart.py:165-167`）。于是产出的图在 PowerPoint 里双击能打开数据表、能改数、是活的。**这是它区别于"matplotlib 出图→`add_picture` 贴上去"的根本价值**，也是我们制作层选它的最硬理由。

→ **战术结论先行**：高 stakes 段里，**Gantt、Mekko、bridge/waterfall 都不能靠它的 chart 引擎**。Gantt/Mekko 走 ②④ 说的 `add_shape`/`build_freeform` 手画矩形（可行，直角图形它撑得住）；真·waterfall 若客户要"双击可改数的原生瀑布图"则它做不到，得退而求其次用堆叠柱+透明底座模拟（见 ④）。

---

## ① 能力边界：能创建/编辑哪些

**作者自述定位（README.rst）**：「创建、读取、更新 PowerPoint(.pptx) 文件的 Python 库」，**不需要安装/授权 PowerPoint**，跨平台（macOS/Linux 都行）。典型用途：从数据库查询/分析输出/JSON 动态生成 pptx。

### 1.1 八类形状全景（`docs/user/understanding-shapes.rst:11-43`，作者亲述"有且仅有六类"）

| 形状类型 | 创建入口（`src/pptx/shapes/shapetree.py`） | 能力要点 |
|---|---|---|
| **auto shape**（预制形状） | `add_shape(MSO_SHAPE, l,t,w,h)` `:375` | ~239 个枚举值（`enum/shapes.py` 含流程图等；docs 自述"约 180 个"`understanding-shapes.rst:16`）；可填充/描边/放文字/带 adjustment 手柄 |
| **text box**（文本框） | `add_textbox(l,t,w,h)` `:389` | 本质是无填充无边框的矩形 autoshape |
| **picture**（图片） | `add_picture(...)` `:353` | 栅格图（png/jpg…），经 `Pillow` |
| **graphic frame**（容器） | 由 `add_chart`/`add_table` 间接产生 | **chart 和 table 不是 shape，是装在 graphic frame 里的 DrawingML 对象**（`docs/user/charts.rst:66-69`）——这是个反直觉但关键的概念 |
| **chart**（图表） | `add_chart(type,...)` `:236` | 见 ② |
| **table**（表格） | `add_table(rows,cols,...)` `:589` | 见 1.3，**支持合并单元格** |
| **group shape**（组合） | `add_group_shape()` `:278` | 可嵌套，递归 shape tree（`understanding-shapes.rst:75`） |
| **connector / line**（连接线） | `add_connector(...)` `:260` | 直线/连接符 |
| **freeform**（自由形状） | `build_freeform(...)` `:398` → `FreeformBuilder` | **画难图的关键，但只有直线段，见 ③** |
| **OLE 对象** | `add_ole_object(...)` `:296` | 嵌入文件对象 |
| **movie / 媒体** | `add_movie(...)` `:547` | 视频 |

### 1.2 文本能力（完整，`src/pptx/text/text.py`）

- `TextFrame`：`word_wrap`(`:194`)、`auto_size`(`:57`，MSO_AUTO_SIZE)、四边 `margin_*`(`:105-141`)、`vertical_anchor`(`:181`)。
- `_Paragraph`：`add_run()`(`:478`)、`alignment`(`:484`)、**`level`(`:517`，0-8 级缩进，做多级要点列表用)**。
- `_Run`：`font`（含 `color.rgb` / `color.theme_color` / size / bold / italic）。
- → **结论**：文本排版能力足够做正文/标注/数据标签；富文本（一段内多种格式）靠多 run 拼。

### 1.3 表格能力（含合并，`src/pptx/table.py`）

- 取单元格 `cell(row, col)`(`:34`)；**`_Cell.merge(other_cell)`(`:260`) / `split()`(`:312`)** 完整支持合并/拆分。
- 合并语义齐：`is_merge_origin` / `is_spanned`(`:205`)、`gridSpan`(`:303`)、`rowSpan`(`:292`)。BDD 证据 `features/tbl-cell.feature`。
- → **结论**：复杂表头（合并跨列/跨行）做得了。**Mekko/marimekko 若退化成"带合并+可变列宽的表格"也是一条路**，但表格列宽是手动算的、不会按数据自动成比例（需我们自己算 EMU）。

### 1.4 母版/版式（读为主，`src/pptx/slide.py`）

- `prs.slide_layouts[i]`、`slide_masters`、`placeholders`：**能读、能基于版式 placeholder 插内容**（`features/` 有 `placeholder.insert_chart` 等），但**新建母版/版式不是它的强项**——典型用法是"拿一个现成模板 .pptx 当底，往 placeholder 里灌"。
- placeholder 可 `insert_chart` / `insert_picture` / `insert_table`（`docs/api/placeholders.rst`）。

---

## ② 高 stakes 图表可行性（本笔记重点）

### 2.1 原生 chart 支持的完整类型清单（真相源：`src/pptx/enum/chart.py` 的 `XL_CHART_TYPE`，`:60-290`）

逐条核过，**全部是 PowerPoint 2007 era 的传统图表族**：

- **柱/条**：COLUMN_CLUSTERED / STACKED / STACKED_100，BAR 同三种，以及 3D 版、cone/cylinder/pyramid 异形柱
- **线**：LINE / LINE_MARKERS / STACKED / STACKED_100、3D_LINE
- **饼/环**：PIE / PIE_EXPLODED / **PIE_OF_PIE / BAR_OF_PIE**、DOUGHNUT / DOUGHNUT_EXPLODED、3D_PIE
- **面积**：AREA / STACKED / STACKED_100、3D
- **XY/气泡**：XY_SCATTER（+ LINES / SMOOTH / NO_MARKERS 变体）、BUBBLE（+3D）
- **雷达**：RADAR / RADAR_MARKERS / RADAR_FILLED
- **股价**：STOCK_HLC / OHLC / VHLC / VOHLC（高低收等 4 种）
- **曲面**：SURFACE / SURFACE_WIREFRAME / TOP_VIEW(_WIREFRAME)

docs 一句话总结（`docs/user/charts.rst:5-6`）：**"Most chart types other than 3D types are supported."** —— 注意这话的潜台词是"老图表集里除 3D 外都支持"，**不含任何 2016+ 新图**。

### 2.2 ❌ 做不了的现代图表（高 stakes 重灾区）

**`XL_CHART_TYPE` 枚举里彻底没有**：waterfall（瀑布/桥）、funnel（漏斗）、treemap（矩形树图）、sunburst（旭日）、box & whisker（箱线）、histogram（直方图）、map（地图）、combo（自定义组合）。

**根因——两套图表命名空间**：
- 传统图表 = `c:chart`，命名空间 `http://schemas.openxmlformats.org/drawingml/2006/chart`（python-pptx 在 `oxml/ns.py:9` 注册了 `"c"`）。python-pptx 的整个 chart 引擎（`chart/xmlwriter.py` 1840 行）只生成这套。
- 2016+ 新图表 = **`cx:chart` / chartex**（"chart extensions"，命名空间是 `http://schemas.microsoft.com/office/drawing/2014/chartex` 一类的扩展），数据模型与 `c:chart` 不同。

**本地源码铁证：python-pptx "知道 chartex 但完全不实现"**：
- `src/pptx/opc/constants.py:31` 定义了 content-type 常量 `OFC_CHART_EX = "application/vnd.ms-office.chartex+xml"`，**但 `grep` 全 `src/` 这个常量从未被任何代码引用**（实测 `grep -rn OFC_CHART_EX src/` 只命中定义行本身）——纯死常量，占了个名字。
- `oxml/ns.py` 的命名空间表里**没有注册 `cx:` 前缀**——库连给 chartex 元素起前缀的能力都没接。
- → **结论**：python-pptx **既不生成、实质上也不解析** chartex 图表。waterfall/funnel/treemap/sunburst/box/histogram 用它的 chart 引擎做 = 死路。

**联网核实（GitHub 一手 issue，全部溯源）——为什么不做，以及作者立场（重要，别误判）**：

- **主 issue = #583「New Chart Types in Office 2016」**（https://github.com/scanny/python-pptx/issues/583，作者 perkes，2019-12-27 开，**至今 open，无任何 label**）。⚠️ **更正一个常见误传：#583 既没标 won't-fix 也没标 enhancement，就是裸 open。** perkes 原帖已亲自定位根因（verbatim）："The most obvious difference is the names of the tags `<cx:chart>` instead of `<c:chart>`, actually **all tags are cx instead of c**. I tried adding a new class to xmlwriter.py and a new enum to enum.chart but that proved to be insufficient. It seems **many parts of the code assume the tags to be named `<c:.*>`.**" —— 印证了上面"全局假设 c:"的本地观察。
- **作者 scanny 的真实立场 = 条件性愿意，不是拒绝**（#583 三段回复 verbatim）：
  - 2019-12-28："probably also **a lot of more detailed work for each chart type to make it generate properly**."
  - 2019-12-31（点破连 MS-API 都没暴露这些类型）："the `XlChartType` enumeration... **doesn't seem to include the new types**... The first thing I'll be looking for is **how much of the existing chart structure it preserves (series, plots, etc.) and how much it breaks**."
  - 2021-09-17（停滞主因）："**There haven't been any sponsors to come forward for this, so no, no developments.** If you wanted to move things forward the first step is **an analysis document**... like a PEP... submit the document as a PR and then we can discuss."
  - → **定性："herculian"（大力神级）工作量 + 无人赞助 + 无合格分析文档 → 长期 open 未做。是"缺资源"不是"拒绝"——方法论里别写成"官方明确放弃"。**
- **配套 issue / PR（均未落地）**：#371「treemap / `cx:plotAreaRegion`」（2018-04-09，更早，原帖贴了完整 treemap 的 `cx:chartSpace` 真实 XML）、#651「Waterfall chart」（2020-09-10）、**PR #778「Waterfall enhancement proposal, for #583」（作者 sanand0，state=open / merged=false，至今未合并）** —— 即 scanny 要的那份"分析文档 PR"已有人提，但卡在讨论阶段没并。
- **chartex 数据模型为何"改前缀也救不了"（最硬的根因）**：chartex 把 series/plot/category 层级模型，换成了 **id 引用的维度（dimension）模型**——数据放顶层 `<cx:chartData><cx:data>`，用 `<cx:strDim type="cat">`/`<cx:numDim type="size">` 描述，系列再 `<cx:dataId val="0"/>` 按 id 引用；图型靠 series 上的 `layoutId="treemap"` 字符串区分（而非独立元素类型）。**python-pptx 的 plot/series 对象层基本被打破，不能复用**。命名空间精确串：`http://schemas.microsoft.com/office/drawing/2014/chartex`（chartex = "chart extended"，是 **Microsoft 私有扩展、不在 ISO/IEC 29500 标准 xsd 里**；规范见 MS-ODRAWXML）。

### 2.3 ✅ 能做且有价值的图表能力

- **细粒度格式控制**：轴（`chart/axis.py` 523 行：min/max scale、tick mark、gridlines、number_format）、数据标签（`chart/datalabel.py`：位置/字体/数字格式）、图例（`chart/legend.py`）、单点着色（`chart/point.py`，至少部分类型可给单个柱/扇区上色，`docs/user/charts.rst:273-276`）。
- **`replace_data()`**（`chart/chart.py:159-167`）：**这是模板化的官方一等公民**——拿一个做好格式的图，整批换数据、保留所有格式，同时更新内嵌 Excel。BDD `features/cht-replace-data.feature` 覆盖 Bar/Column/Line/Pie/XY/Bubble。
- **内嵌真 Excel**（`chart/xlsx.py`）：见 ⭐。产出图可在 PPT 内编辑数据。

### 2.4 ⚠️ 其它 chart 限制

- **不能新建 combo（多 plot）图**：`docs/user/charts.rst:181` 作者亲述 *"python-pptx doesn't yet support creating multi-plot charts, but you can access multiple plots on a chart that already has them."* → 想要"柱+线"组合图，**只能拿现成模板改数据，不能从零建**。
- **3D 类型不支持**（`charts.rst:5-6`）。

### 2.5 chartex（waterfall 等）社区 workaround 实据 — 三条路线，只有一条现实

| 路线 | 思路 | 实据 / 下场 |
|---|---|---|
| **A. 改 XML 前缀 `c:`→`cx:`** | 用现有 API 生成一部分，再把标签改成 cx | ❌ **无成功案例**。因数据模型根本不同（②.2 维度模型），改前缀远不够，等于重写。scanny 自评 "herculian"。 |
| **B. 预制模板 + 替换数据** | 在 PPT 手工做好 waterfall，程序只换底层数据 | ⚠️ **对 chartex 图表不可靠**。硬证据：Node 库 **pptx-automizer**（专做"模板替图表数据"）处理 waterfall 时报 **`Zipped file not found: ppt/charts/chartNaN.xml`**——图表定位逻辑遇 chartex 算出非法文件名（issue #28，已修但要专门打补丁）。python-pptx 原生 `replace_data()` 面向 `c:chart`，**对 cx:chart 模板不保证可用**。 |
| **C. 不用 chart，用形状拼绘** | waterfall/Mekko/Gantt 全用矩形+连接线+文本框手画 | ✅ **第三方明确推荐为现实解**。SlideForge 博客原话：想要 waterfall/funnel/marimekko/sunburst/treemap/Gantt —"**you're out of luck via native chart API**"，其方案是把图当形状组合画（waterfall = "矩形的水平 flex 布局 + accent 线 + 数值标签"），下载后仍可编辑。**这正是本 Engine 收窄段（高 stakes）该走的路、也是护城河来源**（通用 agent / 大厂 skill 做不出这段）。详见 ④.2。 |

> 📎 出处（一手）：#583 / #371（含真实 cx XML）/ #651 / PR #778（未合并）见上；pptx-automizer 坑 = singerla/pptx-automizer#28；形状拼绘定性 = slideforge.dev 博客（商业产品博客，定性可信、细节当二手）。

---

## ③ 关键 API：画难图的底层武器

### 3.1 `add_shape` —— 预制形状 + 可调手柄

```python
shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, height)  # shapetree.py:375
```
- ~239 个 `MSO_SHAPE`（`enum/shapes.py`），含矩形/箭头/流程图块等。
- **adjustment 手柄**：`shape.adjustments[0] = 0.15`（`shapes/autoshape.py` 的 `AdjustmentCollection`，`:89`）——能调圆角半径、箭头宽度这类参数化几何。
- 底层是 `a:prstGeom`（预设几何，`oxml/shapes/autoshape.py:165`）。

### 3.2 `build_freeform` + `FreeformBuilder` —— 自定义几何（custGeom）

**这是不靠预制形状、纯手画任意多边形的入口**，整份 `src/pptx/shapes/freeform.py` 就干这件事：

```python
fb = shapes.build_freeform(start_x, start_y, scale=(x_scale, y_scale))  # shapetree.py:398
fb.add_line_segments([(100, 25), (25, 100)], close=True)                # freeform.py:78
fb.move_to(x, y)                                                         # freeform.py:115（抬笔移动，开新轮廓）
shape = fb.convert_to_shape(origin_x, origin_y)                         # freeform.py:97
```

**设计精髓（对画数据图极友好）**：
- **本地坐标系 + scale**：`scale=Inches(1)/1000` 表示"1000 本地单位 = 1 英寸"（`shapetree.py` build_freeform docstring）。**意味着可以直接拿数据值当坐标画，缩放交给 scale**——画 Gantt 时把"天/周"当本地 x 单位最省事。
- **多轮廓**：`move_to` 开新 contour，重叠区域做"减法"（`freeform.py:32-36` 类 docstring）——能挖洞。
- 底层落到 `a:custGeom`/`a:path`（`oxml/shapes/autoshape.py:45` `CT_CustomGeometry2D`、`:85` `CT_Path2D`）。

### 3.3 ⛔ freeform 的致命边界：**只有直线，没有曲线**

`CT_Path2D` 在 oxml 层**只实现了三个绘图操作**（`oxml/shapes/autoshape.py:88-90, 102-124`）：
- `add_moveTo`（`a:moveTo`）
- `add_lnTo`（`a:lnTo`，直线段）
- `add_close`（`a:close`）

**没有 `add_cubicBezTo`（三次贝塞尔）、没有 `add_quadBezTo`（二次贝塞尔）、没有 `add_arcTo`（圆弧）。**
实测：`grep -rniE "bezier|cubicBez|quadBez|arcTo" src/pptx/` **全空（exit 1）**——整个库不存在任何曲线/圆弧支持。

→ **后果**：
- **直角图形（矩形、阶梯、折线、多边形）→ 完全 OK**：Gantt 条、瀑布柱、Mekko 块、折线桥都是直线段拼的，freeform 撑得住。
- **圆弧/扇形/平滑曲线 → 做不出**：sunburst（环形扇区）、doughnut 的弧、平滑流线、贝塞尔流向图——freeform 一律无能为力。只能 (a) 用预制形状里现成的 `MSO_SHAPE.PIE`/`BLOCK_ARC`/`ARC` 凑（受 adjustment 参数限制、不能任意切角度），或 (b) 用大量短直线段逼近曲线（XML 膨胀、丑），或 (c) 退回贴图。

> 📌 **对照点（值得记）**：隔壁 PPTist（Web 端）能导出任意 SVG path 为可编辑 custGeom，**靠的是 `svg-pathdata` 把 arc/二次曲线降解成三次贝塞尔 `C` 命令**（见 `01应用/PPTist.md` ⭐ 那条）——因为它的导出库 pptxgenjs **认 `C`（cubicBezTo）**。**python-pptx 的 FreeformBuilder 不认 `C`**，所以"SVG→可编辑矢量"这条路在 python-pptx 原生 API 上走不通；要走得自己往 oxml 注入 `a:cubicBezTo`（库没封装，得手撸 lxml 元素）。

---

## ④ 对 PPT Engine 的落点

### 4.1 直接用（开箱即得"可编辑"）
- **基础图表**：column/bar/line/pie/area/scatter/bubble/radar + 它们的 stacked/100% 变体 → `add_chart` 直接出，自带可编辑 Excel。配 `axis`/`datalabel`/`legend` 调格式。
- **模板换数据流**：把咨询级配色/格式的图先在 PPT 里做好存成模板 .pptx，运行时 `replace_data()` 灌数 → **保格式 + 可编辑**。这是规避"从零调格式"的主路子。
- **表格**（含合并单元格）、文本框（多级缩进/富文本）、预制形状、图片 → 全部可靠。

### 4.2 难图怎么绕（高 stakes 三图的具体打法）

| 目标图 | python-pptx 原生 chart？ | 落地打法 |
|---|---|---|
| **Gantt（甘特）** | ❌ 无此类型 | ✅ **`build_freeform` 或 `add_shape(RECTANGLE)` 手画条**。把时间轴当本地 x 坐标、行当 y，矩形纯直线 → freeform 完美胜任。坐标/比例自己算（util 里有 `Emu`/`Inches`/`Pt`，`src/pptx/util.py`）。 |
| **Mekko / Marimekko** | ❌ 无此类型 | ✅ **手画矩形网格**：列宽按段占比算 EMU、每列内再按子占比切块，`add_shape`/freeform 画 + 各自填色 + 文本标注。或退化成"合并单元格表格"（1.3）。**纯直角 → freeform 撑得住**。 |
| **Waterfall / Bridge（瀑布/桥）** | ❌ 无原生 waterfall（那是 chartex） | 两条路：(a) **伪瀑布** = `COLUMN_STACKED` 堆叠柱，底层系列设为"透明占位"把柱顶上去 → 仍是**可编辑原生图表**、能改数，但"连接虚线"和真 waterfall 的自动增减色得手动补；(b) **freeform 手画**阶梯矩形 → 像素级可控但**不可双击改数**（是死图形不是 chart）。**高 stakes 优先 (a) 保"可编辑"，对桥线要求高再叠 (b) 的装饰。** |

> ⚠️ 所有"手画"方案产出的是**形状**不是 **chart 对象**：好处是像素级可控、能进 PowerPoint 当矢量编辑；代价是**没有内嵌数据、双击不出数据表**。要不要"可编辑数据"是选 chart-模拟 还是 freeform-手画 的分水岭——**这条得在 deck 需求里跟"高 stakes 可编辑铁律"对齐清楚**。

### 4.3 架构契合度
- **依赖极轻**（lxml + Pillow + xlsxwriter），无服务、无浏览器、纯 Python，**完全契合 Engine "可独立测试的引擎层"**——能直接 import 进我们的制作模块，单测友好。
- **MIT 授权**：代码可放心借鉴/搬。
- **能力是"读写对称"的**：既能写也能解析 pptx，符合我们"改现有 deck"的潜在需求。

---

## ⑤ 坑 / 注意事项

1. **chart ≠ shape**：`add_chart` 返回的是 **GraphicFrame**，图表对象要 `.chart` 取（`docs/user/charts.rst:61-69`）。table 同理。新手必踩。
2. **freeform 无曲线**（③.3 重申）：任何圆弧/平滑曲线类高 stakes 图（sunburst、流向、平滑桥线）原生做不出，得手撸 oxml 注 `cubicBezTo` 或贴图。**这是制作层最硬的天花板，立项画图前先确认目标图是不是纯直角。**
3. **chartex 是死路**（②.2）：`OFC_CHART_EX` 常量存在会让人误以为"支持"，实则从未被引用。别在 waterfall/funnel/treemap 上浪费时间试 chart 引擎。
4. **combo 图不能从零建**（②.4）：要组合图只能改模板。
5. **单位是 EMU**：1 inch = 914400 EMU，所有坐标/尺寸底层是 `Length`(EMU)；用 `Inches()`/`Pt()`/`Cm()`/`Emu()` 包装（`src/pptx/util.py`）。手画图时坐标算错=图飞出画布。
6. **3D 不支持**（②.4）。
7. **颜色策略**：默认按 theme Accent 1-6 上色，超 6 系列用明暗变体；**作者建议"改模板 theme 色"而非逐点设色**（`docs/user/charts.rst:268-276`）——契合我们"模板驱动"打法。
8. **版本注意**：v1.0.x（2024-08）才加了类型注解 + `py.typed`（`HISTORY.rst`），是该用的现代版本；网上大量旧教程基于 0.6.x，API 名可能有出入。

---

## 附：源码体量速查（判断"哪块成熟"）

- chart 引擎共 ~5200 行，最大 `chart/xmlwriter.py`（1840 行，生成 chart XML）、`chart/data.py`（864）、`chart/axis.py`（523）→ **chart 这块下了重本、很成熟**（就是只覆盖老图表）。
- `features/` 有 18 个 `cht-*.feature` BDD 场景（axis/datalabels/legend/marker/replace-data/series/ticklabels…）→ 图表行为有活文档兜底，可信。
- freeform 仅 `freeform.py`（~360 行）+ oxml，小而专。
