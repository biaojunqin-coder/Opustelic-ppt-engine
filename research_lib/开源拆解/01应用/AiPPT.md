---
status: progress
type: 开源拆解
target: 文多多 AiPPT (veasion / docmee 出品)
repo: https://github.com/veasion/AiPPT
license: GPL-3.0（强 copyleft·见⑤坑）
star: ~1.9k（用户口径；本仓库不含 star 数据，以 GitHub 为准）
本地路径: /Users/qinbiaojuan/Documents/PPT开源参考/01_AI端到端应用/AiPPT
拆解日期: 2026-06-30
拆解人: Claude (Opus 4.8)
和我们的相似度: ★★☆☆☆（产物形态完全不同——它是「PPTX↔JSON 浏览器渲染引擎」，我们是「python-pptx 服务端造原生 deck」；但在"原生图表/原生形状的数据契约"这一层是同行，值得偷）
---

# 文多多 AiPPT 深度拆解

> 一句话：**开源出来的只是「前端 PPT 渲染引擎」——把一套 PPT 的 JSON 模型在浏览器里用 Canvas / SVG 双后端逐元素重绘（含原生图表、187 个 OOXML 预设形状、动画），并能反向 PPT→JSON→下载 .pptx。真正的「AI 生成 PPT」服务端代码不开源（`server/README.md` 明说）。它最该被我们偷的，不是渲染代码，是它沉淀的「原生图表 / 原生形状的数据契约」——即 OOXML 那套结构怎样被压成干净的 JSON，反过来又怎样还原回 .pptx。**

保真说明：以下结论全部来自本地仓库实读，关键处带文件:行号出处。star=1.9k、"原生图表/3D" 等是用户/README 口径，已在文中标注哪些是宣传、哪些在开源代码里真实可见。

---

## 0. 三个最重要的判断（先看这个）

1. **「服务端 = AI 生成那段」不开源，开源的是渲染引擎。** `server/README.md` 原文：「目前该项目仅开源了前端PPT渲染引擎代码，服务端代码暂未开放……可以先通过开放平台API/UI方式接入」。所以 README 首页吹的"AI 生成 PPT"在本仓库里**没有一行实现**，要 AI 生成得去买 docmee.cn 的 API。**对我们的意义：这仓库不是"AI→PPT"的参考，是"PPT 模型→像素"和"PPT 模型 ↔ OOXML"的参考。**
2. **README 吹的"3D 特效"在开源代码里不存在。** 全仓 grep `3d/extrusion/bevel/sp3d/camera/scene3d/立体`，在手写源码（ppt2svg/ppt2canvas/element/animation/geometry）里**零命中真实 3D 渲染**（命中的全是 base64 光标图标和 OOXML `extrusionOk` 这个布尔字段名）。3D 属闭源商用版能力。**所以用户问的"3D 怎么做"——答案是：这个开源仓库做不了 3D，别在这儿找。**
3. **最值钱的是「数据契约」不是「渲染器」。** 它的图表 JSON（`series/category/value/dataPoint/excelData` + Excel 公式串 `Sheet1!$B$2:$B$5`）几乎是 OOXML chart 内嵌 xlsx 的 1:1 镜像（element.js:479-545）。我们用 python-pptx 反方向造图表时，**喂给 `chart.add_series` 的数据结构应该长这样**——这套契约可直接抄。

---

## ① 是什么 + 定位

- **一句定义**（README:19）：「商用级 AI 生成 PPT 项目，包含：AI 生成 PPT / PPT 解析成 JSON / JSON 反渲染为 PPT」。
- **出品方**：veasion（个人）+ docmee.cn（文多多，商业公司）。开源仓库是商用产品的"前端引擎切片 + 引流"——README 大半篇幅是商业合作、私有化部署、开放平台 API 推广。
- **三个真实能力**（对应仓库里真有代码的部分）：
  1. **JSON → 渲染**：把 PPT 的 JSON 模型画到 Canvas 或 SVG（`index.html` 是这个 demo）。
  2. **PPT → JSON**：上传 .pptx，解析+渲染+在线编辑（`ppt2json.html` 是这个 demo，含 jsoneditor 直接编辑 JSON）。
  3. **JSON → .pptx 下载**：编辑后导出回 PowerPoint 文件（README 提及，导出序列化逻辑应在闭源 server 端，前端只负责渲染+编辑模型）。
- **技术形态**：**纯原生 JS（非模块化）、零构建、零框架**。没有 package.json / node_modules，直接 `<script>` 引一堆 `.js`。`static/esm-js/README.md` 说作者另外用 vue/react 重写过（aippt-vue、aippt-react 单独仓库）。
- **核心文件体量**（`wc -l`）：ppt2svg.js 2264 行、animation.js 2903 行、ppt2canvas.js 1327 行、chart.js 833 行、element.js 692 行、geometry.js 499 行（但单行超长，实际 15.7 万字符——是个巨型形状字典）。

---

## ② 它怎么做 deck + 原生图表【重点维度】

### 2.1 整体架构：一份模型，两个渲染后端，一套共享引擎

```
PPT JSON 模型 (pptxObj)
   │  pptxObj.pages[i].children[]   每个 child = 一个元素(text/image/geometry/table/chart...)
   │  每个元素: { id, type, extInfo:{ property:{ anchor, fillStyle, strokeStyle, geometry, chart, ... } }, children:[] }
   │
   ├──► Ppt2Svg   (ppt2svg.js)      ——画成 SVG，用 D3 风格链式封装(D3Element)
   └──► Ppt2Canvas(ppt2canvas.js)   ——画成 Canvas 2D
         │
         └── 两者共享: chart.js(图表) · geometry.js(形状公式) · animation.js(动画)
```
- 元素按 `type` 分发绘制：`drawText / drawImage / drawGeometry / drawTable / drawGraphicFrame(图表) / drawConnector`，group 递归（ppt2svg.js:770 `recursionGroupChildren`）。
- **坐标系**：逻辑画布 960×540（16:9，见 element.js:455 `anchor=[(960-width)/2,...]`），anchor=`[x,y,w,h]`。EMU 换算 `value2px = emu/12700`、`value2emu = px*12700`（geometry.js:467-477）——12700 EMU/px 是 OOXML 标准。

### 2.2 原生图表怎么生成（chart.js，833 行，全手画）

**底座：Canvas 2D 手绘，不依赖任何图表库（没有 ECharts/Chart.js/D3-chart）。** 入口 `drawChart(chart, anchor, canvas, ctx)`（chart.js:1）按 `chartData.chartType` 分发：
- `bar` → 再按 `extInfo.type` 分 `drawBarChartWithBar`(条形,水平) / `drawBarChartWithCol`(柱状,垂直)
- `pie` / `doughnut` → `drawPieChart`（`holeSize` 控制圆环空心比例，chart.js:294/340）
- `line` → `drawLineChart`（`extInfo.smooth=='true'` 时用 `quadraticCurveTo` 画平滑曲线，chart.js:480-488）
- 其他类型 → 直接画个框写"该图表暂不支持渲染"（chart.js:49）。**即开源版图表只支持 柱/条/饼/环/折线 5 种，没有 waterfall/Mekko/Gantt 这些高 stakes 类型。**

**几个值得偷的实现细节：**
- **坐标轴刻度算法 `calculateTicks`（chart.js:529-565）**：经典的"nice number"算法——`rawInterval = range/(ticks-1)` → 取 10 的幂 magnitude → 归一化后吸附到 {1,2,5,10} → 算出整齐的刻度数组，并保证刻度数落在 [minTicks, maxTicks] 区间（超了就把步长翻倍重算）。**这是任何自绘图表都要的"刻度取整"基本功，可直接移植成 python。**
- **填充系统 `toCtxPaint`（chart.js:576-691）超完整**：支持 `noFill / color / bgFill / groupFill(组合继承背景) / gradient(线性+射线,带角度旋转矩阵) / texture(图片纹理,含 9 宫格 insets/stretch/duoTone 重着色) / pattern(逐像素生成图案)`。这套 paint 模型就是 OOXML `<a:solidFill>/<a:gradFill>/<a:blipFill>/<a:pattFill>` 的 JS 实现。
- **颜色解码 `toColor`（chart.js:778-810）**：颜色存成**有符号整数**（如 `-478429`），`(color>>16)&255` 取 RGB，`(color>>24)&255` 取 alpha；还支持 `lumMod/lumOff`（OOXML 的亮度调制/偏移，用于主题色派生）、`alpha` 多种量纲（>1000 按 /100000，0~1 直接用）。**这是 OOXML 主题色→实际 RGB 的还原逻辑。**
- **高清渲染**：canvas 物理尺寸 ×2、`ctx.scale(2,2)`、`imageSmoothingQuality='high'`（chart.js:6-13）——Retina 适配套路。

**数据契约（element.js:432-690，最该抄的部分）：**
图表数据进来就是一张**二维表 `rowColumnDataList`**（第一行=表头/系列名，第一列=类目名），`createChart` 把它转成内部 `chartData`：
```
chartData = {
  chartType,
  series: [{
    text:     { formula:'Sheet1!$B$1',         data:[系列名] },      // 系列名 + Excel 公式引用
    category: { formula:'Sheet1!$A$2:$A$N',     data:[类目...] },
    value:    { formula:'Sheet1!$B$2:$B$N', formatCode:'General', data:[数值...] },
    dataPoint:[{ property:{ fillStyle, strokeStyle } }, ...],         // 数据点级样式(饼图每瓣单独着色)
    property: { fillStyle, strokeStyle }                              // 系列级样式
  }],
  categoryAxis, valueAxes, extInfo:{ holeSize / smooth / majorGridlines / type ... }
}
// 外层还原封保留 excelData:[{ sheetName:'Sheet1', rows: rowColumnDataList }]  ← 内嵌工作簿原始数据
```
**关键洞察：它把 Excel 公式串（`Sheet1!$B$2:$B$5`）和原始二维表 `excelData` 都留在模型里**（element.js:484/489/494/532-537）。这正是 OOXML 图表"内嵌一个 xlsx 工作簿"的镜像——反渲染回 .pptx 时，chart 的 `c:numRef/c:strRef` 和内嵌 `embeddings/Microsoft_Excel_Worksheet.xlsx` 都能从这里还原。**python-pptx 造图表时喂的 `categories + series.values`，本质就是这套契约的子集。**

### 2.3 图表如何嵌进场景（两后端的关键差异）

- **SVG 后端（ppt2svg.js:788-805 `drawGraphicFrame`）**：图表**先画到一个离屏 canvas**，`canvas.toDataURL('image/png')` 转 PNG，再作为 SVG `<rect>` 的 **texture fill** 贴进矢量场景。→ **即 SVG 里的图表其实是一张位图，不是矢量。** 务实取舍：避免把 833 行 canvas 绘制逻辑再用 SVG path 重写一遍。
- **Canvas 后端（ppt2canvas.js:617-628）**：直接在主画布 ctx 上 `drawChart`，共用同一个 ctx，零中转。
- 两者调用的是**同一个 `drawChart`**——渲染引擎与渲染目标解耦，是干净的分层。

### 2.4 原生形状怎么做（geometry.js —— 真正的硬核）

**这是一个完整的 OOXML preset-geometry 公式引擎**，含 **187 个内置形状**（`grep '"...":{"guides"'` 计数）——curvedDownArrow、cube、cloudCallout、circularArrow、star16、funnel… 覆盖 PowerPoint 形状库。每个形状定义 = `{ guides:[公式...], paths:[路径...], adjusts:[可调句柄...] }`，全部是 OOXML `<a:custGeom>` 的 JS 搬运。
- **公式求值器 `fmlaEvaluate`（geometry.js:293-342）**：实现了 OOXML 形状公式的全套算子——`*/`(muldiv) `+-`(addsub) `+/`(adddiv) `pin`(clamp) `abs max min mod sqrt` `sin cos tan at2` `cat2 sat2`(cos/sin×atan2) `?:`(ifelse) `val`。角度单位是 1/60000 度（OOXML 标准）。
- **路径求值 `pathEvaluate` + 圆弧转贝塞尔 `arcToBezierCurve`（geometry.js:344-435）**：OOXML 的 `A`(arc) 命令在 SVG/Canvas 里没有直接对应，它把圆弧分段近似成三次贝塞尔（`cv=4/3*sin(θ/2)/(1+cos(θ/2))` 是经典的贝塞尔逼近圆弧魔数）。
- `geometryPaths(property, zoom)` → 算出一组 path → SVG 后端逐条 `append('path')`（ppt2svg.js:836-839）、Canvas 后端 `ctx` 描边填充。
- **价值**：这是把"PowerPoint 矢量形状在浏览器端逐像素精确复现"的完整实现。**但对我们用处有限**——python-pptx 造原生形状时用的是 `MSO_SHAPE` 枚举（直接让 PowerPoint 自己渲染形状），不需要我们自己解公式画 path。**这套引擎是"渲染器/查看器"才需要的，造 deck 不需要。**

### 2.5 动画（animation.js，2903 行）

仓库里最大的文件，是一套**纯前端的 OOXML 动画时间线播放引擎**（进入/退出/强调/路径动画的 timeline 调度）。同样是"播放器"能力，与我们"生成可编辑 .pptx"目标正交——python-pptx 连动画 API 都很弱，这块**基本无法借鉴到我们的制作层**，仅作"原来 OOXML 动画模型长这样"的参考。

---

## ③ 能借什么

| 可借的东西 | 在哪 | 怎么用到 PPT Engine |
|---|---|---|
| **图表数据契约（series/category/value/dataPoint/excelData + Excel 公式串）** | element.js:432-690 | 直接定义成我们图表层的中间 JSON schema；python-pptx 据此填 `chart_data` + 内嵌工作簿 |
| **刻度取整算法 calculateTicks（nice-number）** | chart.js:529-565 | 移植成 python，给任何"需要算 Y 轴整齐刻度"的自绘/校验场景用 |
| **OOXML 颜色解码（有符号 int→RGBA + lumMod/lumOff 主题色派生）** | chart.js:778-810 | 我们处理主题色/解析既有 pptx 颜色时直接抄 |
| **paint 模型分类（noFill/color/gradient/texture/pattern/groupFill）** | chart.js:576-691 | 作为"填充能力清单"对照——确认我们的图表/形状填充覆盖了哪些 OOXML fill 类型 |
| **"引擎与渲染目标解耦"分层** | chart.js 被 svg/canvas 共用 | 印证：制作逻辑（算数据/算布局）应与输出后端（python-pptx / 预览渲染）分离 |
| **EMU 换算常量 12700/px、角度 1/60000 度、960×540 逻辑画布** | geometry.js:467-477 | OOXML 单位常识，落进我们的常量表 |
| **OOXML 形状公式引擎（fmlaEvaluate / arc→bezier）** | geometry.js:293-435 | 仅当我们将来要做"PPT 预览/缩略图"才需要；造 deck 用不上 |

---

## ④ 对 PPT Engine 的落点【重点维度：原生图表实现可借鉴什么】

**前提对齐**：我们的制作层是 **python-pptx 服务端造原生可编辑 .pptx**，目标是咨询级高 stakes deck（waterfall/Mekko/Gantt）。AiPPT 是**浏览器端 PPT 查看/编辑引擎**。两者方向相反（它是"读+渲染"，我们是"写+生成"），但在"原生图表的数据怎么组织"这一层是同一个 OOXML 真相源。

**1. 直接采纳：图表中间模型 = excelData(二维表) + chartData(派生结构)。**
我们图表层应该有一个干净的中间 JSON：上游（AI/数据）只产出**二维表 + 图表类型 + 少量 extInfo（holeSize/smooth/gridlines）**，下游 python-pptx adapter 把它翻译成 `CategoryChartData`/`XyChartData` 并写内嵌工作簿。AiPPT 的 `createChart→createPieChart/createBarLineChart`（element.js）就是这个"二维表→图表模型"翻译器的现成样板，连"饼图按 dataPoint 逐瓣着色、折线用 strokeStyle、柱状用 fillStyle"这种分支都给好了。

**2. 直接采纳：保留 Excel 公式引用与原始数据。**
OOXML 原生图表必须内嵌一个 xlsx 工作簿，图表的 numRef/strRef 指向 `Sheet1!$B$2:$B$5`。AiPPT 在模型里完整保留了 `formula` 字段和 `excelData.rows`——这提醒我们：**python-pptx 的 `chart_data.add_series` 会自动建内嵌工作簿，但若要做"图表数据可回编辑/可追溯到源表"，得自己把原始二维表也存档**（我们的产物层可加一份 sidecar 数据表）。

**3. 直接移植：calculateTicks + toColor 两个小工具。**
- `calculateTicks`（nice-number 刻度）——做高 stakes 图表时，Y 轴/数据轴的刻度取整是"看起来专业"的关键，python 端值得有同款。
- `toColor`（含 lumMod/lumOff）——处理主题色派生、或解析客户给的既有 pptx 配色时直接能用。

**4. 明确不借（避免走偏）：**
- **渲染器本体（ppt2svg/ppt2canvas/geometry 公式引擎/animation）不要抄**——那是"把 PPT 画到屏幕"的查看器，我们不做查看器（要预览直接用 LibreOffice headless 转图/转 pdf 更省）。
- **5 种基础图表的 canvas 绘制代码不要抄**——我们要做的是 waterfall/Mekko/Gantt 这些 AiPPT **明确不支持**的高 stakes 类型，而且是写成原生 OOXML（让 PowerPoint 自己渲染），不是自己 canvas 画位图。AiPPT 在这恰好是反面参照：**它的图表上限（柱/条/饼/环/折线 5 种 + 不支持就显示"暂不支持渲染"）正是通用方案的天花板，也正是我们要超越的地方**（呼应 CLAUDE.md 铁律 4：收窄高 stakes 段）。
- **3D 在这没有**——别把它当 3D 图表参考。

**一句话落点**：从 AiPPT 偷"**原生图表的数据契约 + 两个数值/颜色小工具**"，不偷它的渲染引擎；它的图表能力天花板（5 种基础图 + 位图嵌入）恰好标定了"通用 PPT 方案做不到的高 stakes 图表"边界——那是我们的主场。

---

## ⑤ License + 坑

- **License = GPL-3.0（强 copyleft，最大的坑）。** 仓库根 `LICENSE` 是完整 GNU GPLv3。**含义：任何直接复制/改编它的源码（哪怕是 calculateTicks 这种函数）并分发，都可能触发 GPL 传染——衍生作品须同样以 GPL 开源。** 我们若要用它的算法，安全做法是**读懂思路后用 python 独立重写**（算法本身不受版权保护，nice-number 刻度、EMU 换算都是公知算法），**绝不逐行翻译它的 JS**。涉及商用闭源时尤其要隔离。
- **坑1：开源 ≠ 完整产品。** "AI 生成 PPT"和"JSON→.pptx 导出序列化"的核心都在闭源 server（`server/README.md` 明示）。开源部分只能渲染和编辑模型，**不能端到端跑通"一句话→.pptx"**。
- **坑2：README 宣传与开源代码不符。** 首页吹"原生图表、动画、3D特效"——图表/动画开源里有，**3D 开源里没有**。评估时别被 README 带偏。
- **坑3：非模块化古典 JS。** 全局函数满天飞（`drawChart`/`createChart` 直接挂 window），`esm-js/` 是作者事后补的模块化版。想集成得用它的 vue/react 重写仓库（aippt-vue / aippt-react），不是这个主仓。
- **坑4：图表是"位图嵌 SVG"。** SVG 后端里图表 = PNG dataURL 贴图（ppt2svg.js:794-802），放大会糊、不可选中文字。它的"矢量"是打折扣的。
- **坑5：依赖一堆 vendor JS。** pako(解压)、base64js、marked、jsoneditor、sse(SSE 流)——其中 pako/base64 暗示**解析 .pptx（zip+xml）的能力在前端**，但 ppt2json 的解析主逻辑（解 zip、读 OOXML）这部分代码在仓库里偏薄，重头应也在 server。

---

## 附：实读清单（保真留痕）

- `README.md` / `README_EN.md` / `server/README.md` / `static/esm-js/README.md`：定位、闭源边界、模块化说明。
- `static/chart.js`（全 833 行精读）：5 种图表绘制 + calculateTicks + toCtxPaint + toColor。
- `static/geometry.js`（结构+解析器精读；形状字典抽样）：187 形状 + fmlaEvaluate + pathEvaluate + arcToBezierCurve + EMU 换算。
- `static/element.js:432-690`（精读）：createChart/createPieChart/createBarLineChart —— 二维表→chartData 数据契约。
- `static/ppt2svg.js:770-839`（精读）：drawGraphicFrame(图表贴图) / drawGeometry(形状) / group 递归。
- `static/ppt2canvas.js:610-654`（精读）：canvas 后端 drawGraphicFrame / drawGeometry，对比 svg 后端。
- `index.html:649-734`（精读）：insertElement —— demo 怎么造各类元素、图表示例二维表数据。
- 全仓 grep：3D（零真实命中）、chartData 调用点、geometryMap 计数（187）。
