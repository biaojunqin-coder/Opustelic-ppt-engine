---
status: progress
type: 开源拆解
category: 05图表库
project: highcharts
license: 商业（source-available·非 OSI 开源·商用必付费）
license_blocks_us: true
version_snapshot: v13.0.0
tags: [waterfall, variwide, marimekko, mekko, gantt, sankey, bullet, heatmap, 高stakes图表]
最有用一点: "Variwide(Mekko)的画法——把 z 值归一化重映射 X 轴像素宽度，列宽∝z 且累加铺满整轴，这正是我们自研 Mekko 缺的那块算法。"
---

# Highcharts 轻拆 · 聚焦高 stakes 图表（waterfall / Mekko / Gantt）

> 拆解对象：`/Users/qinbiaojuan/Documents/PPT开源参考/05_图表库/highcharts`（working repo，TS 源码，v13.0.0）
> 拆法：grep 定位 + 读 `ts/Series/<图表>/` 源码 + `docs/` + `license.txt`，**不 `ls -R`**。
> 落点视角：我们底座是 **python-pptx**（Python，画原生 PPT 形状/图表），Highcharts 是 **JS/SVG 浏览器渲染**，技术栈完全不同 → 它对我们是**算法/数据结构参考**，不是可调用的库。

---

## ① 是什么 + 定位 + License（最先说，因为它决定了我们能不能用）

- **是什么**：基于 SVG（部分 canvas/WebGL）的 JS 图表框架。`package.json` 自述 "JavaScript charting framework"。家族含 Highcharts(基础) / Stock / Maps / **Gantt** 四个包。
- **定位**：商用图表库的事实标准之一，图表类型极全（`ts/Series/` 下 ~90 个图表目录）。咨询/金融/BI 圈用得多，正因为它把 **waterfall / variwide(Mekko) / Gantt / sankey / bullet** 这些「难图」全做了。
- **⚠️ License = 商业 source-available，不是开源**（关键结论，反复确认）：
  - `license.txt`：明确指向 `shop.highcharts.com` 谈授权。
  - `package.json` → `"license": "SEE LICENSE IN <license.txt>"`（**不是** MIT/Apache，npm 不识别为 OSI 开源）。
  - **每个源文件头部**都印着（亲见，waterfall/variwide/gantt/xrange/sankey/bullet 全一致）：
    ```
    Integration of this software requires a license.
    - For commercial use, see www.highcharts.com/license
    - For non-commercial, see www.highcharts.com/license-eula
    ```
  - `readme.md` 原文：「Highcharts is a **source-available** product. Please refer to shop.highcharts.com for details on licensing.」
  - **免费档**：官方政策是**仅限非商业 / 个人 / 演示**可免费（走 non-commercial EULA）；**任何商用（含给客户做 deck 卖钱、SaaS 内嵌）必须买商业 license**。我们做「咨询级 / 投资人 deck」= 高 stakes 商用 → **落在付费区，不能白嫖**。
  - 源码能读（working repo 公开在 GitHub），但**读 ≠ 可用**；直接照抄其 SVG 代码进商用产品有 license 风险。**安全姿势 = 只借鉴「数据结构 + 几何算法思路」自研，不 copy 代码。**

---

## ② 三种高 stakes 图怎么实现（重点·数据结构 + 画法思路）

> 共同底座：三者**都继承自 `ColumnSeries`（柱状图）**，靠重写 `translate / afterColumnTranslate` 改 shapeArgs(x/y/width/height) 来变形。这是 Highcharts 的核心套路——**新图表 = 老图表 + 坐标变换**，不是从零画。我们自研也可复用这个思路（python-pptx 里 = 算 EMU 矩形框 + 连接线）。

### 2.1 Waterfall（瀑布图）— 财务桥图，最高频
源码：`ts/Series/Waterfall/WaterfallSeries.ts`（28KB，逻辑最重）

- **数据结构**：本质是带「累加语义」的柱图。每个点 `{y}`，外加两个布尔标记：
  - `isSum: true` → 该列显示**从序列起点到此的总和**（y 被忽略，自动算）。
  - `isIntermediateSum: true` → 显示**自上一个中间和以来的小计**（y 被忽略，自动算）。
  - 普通点：y 是增量（正=上升绿、负=下降红）。
- **画法核心三步**（我们自研 waterfall 必抄这套状态机）：
  1. **`processData()`**：顺序遍历 y，维护两个游标 `sum`(总累加) / `subSum`(小计累加)。遇普通点 `sum += y; subSum += y`；遇 `isSum` 把该点 y 改写成当前 `sum`；遇 `isIntermediateSum` 改写成 `subSum` 并把 `subSum` 归零。同时记录 `dataMin/dataMax` 给 Y 轴定范围。→ **这一步把「相对增量」翻译成「绝对高度」，是瀑布图的灵魂。**
  2. **`afterColumnTranslate`（order:2 事件）**：算每列矩形 box。非堆叠时维护 `previousY`(上一列顶端)，普通列 `box.y = translate(max(previousY, previousY+y))`、高度 = 到 previousY 的距离；然后 `previousY += y`。**浮空柱的"悬浮起点"= 上一列的终点**——这是瀑布图视觉上"接力悬浮"的来源。sum/intermediateSum 列单独从 threshold(通常0) 起画实心柱。
  3. **`getCrispPath()` + `drawGraph()`**：画**列间连接线**（上一列顶 → 下一列顶的水平虚线/实线）。先画空 path 占位拿到 strokeWidth，再 `animate` 到精确路径（为了像素对齐 crisp）。**这条连接线是瀑布图区别于普通柱图的标志**，别漏。
- **配色**：`upColor`(涨) 自动套给 y>0 的点，y<0 用 negativeColor。`pointAttribs()` 里处理。
- **坑**：浮点累加用 `correctFloat()` 包一层（#3710 注释，避免 0.1+0.2 漂移）；最小柱高 `minPointLength`(默认5px) 保证零值列也可见。

### 2.2 Variwide ＝ Mekko / Marimekko / 马赛克图（变宽柱图）— 咨询最爱
源码：`ts/Series/Variwide/VariwideSeries.ts`（9KB）+ `VariwideComposition.ts`(改 X 轴 tick)

- **官方定性**（`docs/.../variwide-chart.md` + glossary 亲见）：
  - Variwide = **「related to Marimekko」**：列高=y，**列宽=z**（第三维）。
  - 与纯 Marimekko/Mosaic 的差别（glossary §Mosaic plot 写明 "Also known as Marimekko or Mekko"）：**Marimekko 让各列宽度归一化铺满整个绘图区**；variwide 默认只是「宽度∝z」。但**当 X 是 category 轴时，variwide 的列宽会被分配到铺满整条 X 轴 = 退化成 Mekko**（见下 postTranslate）。→ **对我们：variwide 的算法就是 Mekko 的算法，缺的只是"再叠一层 Y 方向 100% 堆叠"就是完整 Marimekko。**
- **数据结构**：`pointArrayMap: ['y', 'z']`，`parallelArrays: ['x','y','z']`。点 = `{x?, y, z}`，y 决定高、z 决定**相对宽度**。
- **画法核心（这是本次最值钱的算法，我们自研 Mekko 直接照搬思路）**：
  1. **`processData()`**：累加所有 z 得 `totalZ`，并记录每列**左侧累计 z** 到 `relZ[i]`（即第 i 列左边缘前面所有 z 之和）。
  2. **`postTranslate(index, x)`**：把「线性 X 像素」重映射成「按 z 加权的 X 像素」。关键公式：
     - 线性槽位：`linearSlotLeft = i/N * len`
     - **z 加权槽位**：`slotLeft = (relZ[i]/totalZ) * len`，`slotRight = (relZ[i+1]/totalZ) * len`
     - 再按点在线性槽内的比例插值到 z 槽 → 返回畸变后的 X。
     - **本质 = 把 X 轴从「等分」拉伸成「按 z 占比分」，所有列宽加起来 = 整个轴长 len。这就是 Mekko 列宽铺满的数学。**
  3. **`afterColumnTranslate`**：对每个点用 postTranslate 算 left/right，`shapeArgs.width = right-left`（最小1px）。
- **配套**：`pointPadding:0 / groupPadding:0`（默认值，`VariwideSeriesDefaults.ts`）→ 列与列**严丝合缝无缝隙**，这是 Mekko 必须的（有缝就不是 Mekko 了）。

### 2.3 Gantt（甘特图）— 项目/路线图，投资人 deck 常用
源码：`ts/Series/Gantt/GanttSeries.ts`（6KB，薄）+ **真正引擎在 `ts/Series/XRange/XRangeSeries.ts`（25KB）**

- **架构**：`GanttSeries extends XRangeSeries extends ColumnSeries`。**Gantt 自己很薄**，几乎所有几何在 XRange。**想自研 Gantt = 先实现 XRange（区间条）。**
- **XRange 数据结构**：点 = `{x, x2, y}`。x=起点、x2=终点（横轴方向的"一段"），y=行（哪个任务/分类）。`pointArrayMap: ['x2','y']`。
- **Gantt 在 XRange 上加的料**：
  - `pointArrayMap: ['start','end','y']`，且 `getColumn('x')` 把 `start` 经 `time.parse()` 转成时间戳 → **Gantt = 时间轴版 XRange**，数据写成 `{name, start:'2026-01-01', end:'2026-03-01'}`。
  - **`milestone: true`** → `drawPoint` 把矩形换成**菱形**（`renderer.symbols.diamond`），`translatePoint` 把宽度强制=高度并居中（里程碑是个点不是段）。
  - **`completed: 0~1`** → 进度条：走 XRange 的 **partialFill** 机制（见下）。
  - **`dependency`** → 任务依赖箭头，靠 **`Gantt/Pathfinder.js`**（A* 寻路画折线连接器）。
  - **Y 轴 = `TreeGridAxis`**（树状网格轴）→ 支持父子任务、折叠展开。
- **XRange 几何要点（自研抄这些）**：
  - **`getColumnMetrics()` 玩了个 trick**：临时 **swap xAxis/yAxis**，借用 ColumnSeries 的列宽/padding 算法（因为 XRange 的"柱"是横躺的），算完再 swap 回来。省了重写一套 metrics。
  - **`translatePoint()`**：`plotX = translate(x)`，`plotX2 = translate(x2)`，width = |plotX2-plotX|，height = 行高(metrics.width)。
  - **partialFill（进度填充）**：在原矩形上叠一个**裁剪矩形** `clipRect`，宽度 = `length * fillAmount`，套个深一档的颜色 → 这就是进度条/完成度的画法。我们自研 Gantt 进度条直接抄这个「底条 + 裁剪覆盖条」两层结构。

---

## ③ 其它高 stakes 图（桑基 / 子弹 / 热力）

### 3.1 Sankey（桑基图）— 流量/资金流向
源码：`ts/Series/Sankey/SankeySeries.ts`（28KB）+ `SankeyColumnComposition.ts`(列布局)
- **数据结构**：`{from, to, weight}` 的边列表 + 自动生成节点（`NodesComposition`）。节点不用你给坐标，**算法自动分层布局**。
- **画法核心（自研桑基必懂）**：
  1. **`createNodeColumns()`**：按依赖关系把节点分到若干**纵列**（column = 同一层级的节点）。
  2. **`translationFactor`**：取所有列里「最挤的那列」的缩放因子，保证最高的列也塞得下绘图区高度 → 所有列共用一个 px/weight 比例。
  3. **`translateNode()`**：每个节点高度 ∝ 其总流量 weight；节点在列内按 `getNodePadding` 间隔堆叠。
  4. **`translateLink()`**：每条边画成**贝塞尔曲线带**（`curveFactor` 控弯曲度），起止 y 由 `getY()` 按节点内偏移算，带宽 = weight × translationFactor。
- **衍生**：`DependencyWheel`（环形桑基）、`Organization`（组织架构图）都 extends Sankey → 同一套节点-边布局复用。

### 3.2 Bullet（子弹图）— KPI / 实际vs目标，仪表盘高频
源码：`ts/Series/Bullet/BulletSeries.ts`（小）
- **数据结构**：`{y, target}`（parallelArrays: `['x','y','target']`）。y=实际值（主条），target=目标值（横标线）。
- **画法**：继承 ColumnSeries 画主条；`drawPoints()` 额外画一个**窄横向 rect 作为 target 标记**（叠在主条上，宽度可配 `targetOptions.width`），位置 = `yAxis.translate(target)`。定性区间（差/中/好背景带）= 用 **yAxis 的 plotBands**（不在 series 里，在轴配置里）。
- **自研子弹图**：= 一根细柱 + 一条目标横线 + 背景三色带，python-pptx 里就是 3 个矩形叠放，很好实现。

### 3.3 Heatmap（热力图）+ Tilemap
源码：`ts/Series/Heatmap/`、`ts/Series/Tilemap/`
- **数据结构**：`{x, y, value}` 网格。value 经 **colorAxis**(连续色阶) 映射成格子填充色。
- **画法**：本质是规则网格的矩形铺砌，每格颜色 = colorAxis.toColor(value)。Tilemap 支持六边形/圆形格子。
- 注：热力图我们做的话，难点在**色阶映射(colorAxis)**而非几何，可借鉴其 value→color 的连续插值。

### 其它存在但本次没深拆（仓库里都有，需要时回来挖）
`Treemap` `Sunburst`(旭日) `Venn`(韦恩) `Streamgraph`(streamgraph 河流图) `Funnel/Pyramid`(漏斗) `Gauge/SolidGauge`(仪表) `Boxplot` `Networkgraph`(力导向) `Pictorial`(象形) `Vector/Windbarb`(矢量场) — `ts/Series/` 下共 ~90 个，是个**高 stakes 图表的"题库"**。

---

## ④ 对 PPT Engine 的落点（核心：商业 license 下怎么"安全借力"）

**总判断：Highcharts 不能直接用（技术栈 JS≠Python + 商业 license 双重拦），但它是我们自研高 stakes 图表的「算法参考书 / 题库」，价值在思路不在代码。**

1. **license 红线**：我们做的是商用高 stakes deck → 落在 Highcharts **付费区**。即便买了 license，它输出的是**浏览器 SVG**，要落进 PPT 还得截图/转矢量，与「python-pptx 直接画原生 PPT 形状」的路线不搭。→ **结论：不引入 Highcharts 作运行时依赖。**
2. **可安全借鉴的（只学思路、白板重写、不 copy 代码）**：
   - **架构哲学**：「新图表 = 基础柱图 + 坐标变换(translate)」。我们 python-pptx 侧同理——先有个「矩形+连接线」基元层，waterfall/Mekko/Gantt 都是它的特化。**这条能省我们大量重复造轮子。**
   - **Waterfall 状态机**（②2.1 的 processData 双游标 sum/subSum + 浮空柱"接力起点=上列终点" + 连接线）——**直接照搬到 Python**，这是教科书级正确实现。
   - **Mekko/Variwide 宽度算法**（②2.2 的 `relZ/totalZ` 归一化重映射 X）——**我们自研 Mekko 缺的就是这块**，公式拿来即用（纯算术，无 license 风险）。
   - **Gantt = XRange(区间条) + 时间轴 + 里程碑菱形 + partialFill 进度（底条+裁剪覆盖条两层）+ 依赖箭头(寻路)**——这套**分解**告诉我们自研 Gantt 的最小组件清单。
   - **Bullet/Sankey 数据结构**（`{y,target}` / `{from,to,weight}`）作为我们 API 设计的对标。
3. **建议沉淀动作**：把 ②的三套算法（waterfall 状态机 / variwide 宽度公式 / xrange+gantt 组件分解）抽成**方法论里的"高 stakes 图表画法卡"**，标注「来源：Highcharts v13 源码拆解·算法借鉴非代码移植」。等真有 python-pptx 制作层时，这几张卡就是实现蓝本。

---

## ⑤ 坑 / 注意

1. **license 是最大坑**：source-available ≠ open-source。GitHub 能看 ≠ 能商用。商用必谈授权且产物是 SVG（不直出 PPT）。**别让"开源参考"这个目录名误导成"可白嫖"。**
2. **技术栈不匹配**：全 TS/JS + SVG/DOM 渲染，**无法在 Python/python-pptx 里调用**。只能当算法参考。
3. **继承链深**：Gantt→XRange→Column→Series，读单个图表文件常看不全（真逻辑在父类）。本次已穿透到 XRange/Column 这层，但若要完整复刻需连父类一起读。
4. **crisp 像素对齐**：源码大量 `crisp()` 调用是为浏览器 SVG 的半像素对齐（避免模糊线）——**PPT 是矢量 EMU 坐标，无此问题，移植时可全部省掉**，别被这些噪音代码带偏。
5. **浮点累加**：waterfall 用 `correctFloat()` 包累加（避免浮点漂移）——**Python 里同样要注意**（用 Decimal 或 round），这个坑跨语言都存在，值得抄。
6. **本次是"轻拆"**：只穿透了 5 张高 stakes 图（waterfall/variwide/gantt+xrange/sankey/bullet）的核心算法，未覆盖动画/事件/无障碍/数据加载等工程层；其余 ~85 个图表目录是"题库"，需要哪张回来挖哪张。

---

### 一句话（它对我们做 waterfall/Mekko/Gantt 最有用的 1 点）

**Variwide(Mekko) 的列宽算法——`relZ[i]/totalZ × 轴长` 把 X 轴从等分重映射成"按 z 占比分配且铺满整轴"——这正是我们自研 Marimekko/Mekko 唯一缺的那块几何，纯算术、无 license 风险、可直接搬进 python-pptx。**
