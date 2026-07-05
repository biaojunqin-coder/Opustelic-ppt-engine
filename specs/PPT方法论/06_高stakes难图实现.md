# 高 stakes 难图自研实现（汇总 6 图表库 + 2 制作明珠拆解）

> **来源**：拆 `d3`/`echarts`/`plotly.js`/`highcharts`/`frappe-gantt`/`plotlyPowerpoint` + `ppt-master`/`Mck-ppt-design-skill`（笔记在 `research_lib/开源拆解/05图表/` 与 `04制作/`）。每条带出处。
>
> **核心结论**：waterfall/Mekko/Gantt **没有任何库能原生产"可编辑 pptx"**（HTML/SVG/JS 库导出都是图片；highcharts 还是商业 license）——但拆出了**完整的算法范本**，可纯 Python 移植成 python-pptx 手法卡（`add_shape` 矩形拼 / custGeom）。**这是「咨询级 vs 通用 PPT」的护城河，也是本项目差异化主场。**

## 〇、统一内核：先算区间，再摆矩形（d3 stack 启发）
【出处:d3 `docs/d3-shape/stack.md:336/357/378`】d3 用 `stack → 每点输出 [y0,y1] 区间 + 换一个 offset 函数`把瀑布(`stackOffsetDiverging`)、Mekko(`stackOffsetExpand` 100%纵轴)、堆叠柱统一。
→ **本项目三种高 stakes 图共用一个「算区间」纯 Python 内核**（涨复用率，正中铁律「复用率≥50%」），上层只是把区间换成 EMU 后 `add_shape(RECTANGLE/ROUNDED_RECTANGLE, left, top, width, height)`。

---

## 一、Waterfall 瀑布图（方案最成熟·多源印证）
**数据契约**【出处:plotly `calc.js:42-99`】：`measure` 数组（`relative`增量 / `total`总计 / `absolute`绝对）+ 滚动 `previousSum` 累加——**用户只填每段增量，引擎自动算浮空柱坐标**。
**画法**（四源一致）：
- echarts【grep 实证】：两个同 `stack` 名柱系列 + 底部占位段刷 `transparent` 隐形。
- highcharts【waterfall 父类】：双游标状态机（sum/subSum 把增量翻成绝对高度）+ 列间连接线 `getCrispPath`。
- ppt-master `engine.py::waterfall` + Mck-skill `#49`：纯矩形拼 + 桥接短线（已有现成 python-pptx 代码可参照）。
**python-pptx 实现**：每根 `add_shape(RECTANGLE)`，`top` 由 `previousSum` 决定；涨 `ACCENT_GREEN`/跌 `ACCENT_RED`/总计 `NAVY`（plotly 默认 #3D9970/#FF4136/#4499FF 同色逻辑）；列间 `add_connector` 画台阶连接线。

> **真实模板可核对**（2026-07-01 补·之前写本节时没真正打开过库核对）：`engine/ppt_master/templates/charts/waterfall_chart.svg`——
> 实测画法跟上面描述一致：涨绿(`#10B981`)/跌红(`#F43F5E`)/总计深灰蓝(`#1E293B`)三色渐变矩形 + 虚线网格 + 图例。
> 直接当 SVG 版起点参考（适配 spec_lock 配色后用，不要照搬它自带的渐变色值——见制作工作流 SKILL「模板供结构不供皮肤」纪律）。

## 二、Gantt 甘特图（frappe-gantt 公式可直接搬）
**核心公式**【出处:frappe-gantt `bar.js:592-596,72,622-627`】：
- 任务条 `X = (任务start − 全局最早start) / 每格天数 × 每格宽`
- 宽 `= 工期格数 × 每格宽`；`Y = 表头高 + 行号 ×(条高+行距)`
**画法**：每任务 `add_shape(ROUNDED_RECTANGLE)`；进度条 = 第二个叠放矩形（highcharts `XRangeSeries` 的 `partialFill` 同思路）；依赖 = `add_connector` 直角弯 + 箭尖【arrow.js:13-89】。
**⚠️ 里程碑菱形**：frappe-gantt **没有**，必须我们自建（`start==end` → `MSO_SHAPE.DIAMOND`）——**这正是把 Gantt 做成「咨询级」的差异点**。

> **真实模板可核对**：`engine/ppt_master/templates/charts/gantt_chart.svg`——比上面描述更简化：任务条+里程碑菱形(`polygon`)+TODAY虚线都有，
> 但**没有依赖连接线**（无 `add_connector` 直角弯+箭尖，多任务并行时只是平行条，不画依赖箭头）。
> 适用 6-12 个任务、无强依赖关系展示需求的场景；**真要画依赖箭头，仍按上面 frappe-gantt 公式自研那一段**，模板这里不够用。
> （另：`top_down_tree.svg` 现成支持 2-4 层级的组织架构图/OKR级联/WBS分解，CLAUDE.md 没点名但属于"高stakes硬图"近邻，一并记下。）

## 三、Mekko / Marimekko（最硬空位·纯自研·缺的几何已找到）
**关键几何**【出处:highcharts variwide】：**列宽 = `relZ[i] / totalZ × 轴长`**（把 X 轴按各列 z 值占比铺满整轴，`pointPadding:0` 无缝）；列内再按占比堆叠（d3 `stackOffsetExpand` 100%）。
**python-pptx 实现**：第 i 列 `add_shape(RECTANGLE)`，`width = relZ[i]/totalZ × 总宽`，`left = 前缀和`；列内分段 `height = 占比 × 总高` 堆叠 + 分色。
**为何是护城河**：plotly/echarts **顶级库都放弃 Mekko**（无「数值驱动柱宽」原语）——这是通用方案的绝对盲区、我们最大差异化。highcharts 那条列宽公式是纯算术、无 license 风险，可直接搬。

> **真实核对（2026-07-01）**：`engine/ppt_master/templates/charts/` 71 张里 `grep -i mekko` **零命中**——
> ppt-master 自己也没有 Mekko 模板，证实"最硬空位"判断没错，这段自研方案是唯一选项，没有现成模板可参照。

---

## 四、配色（图表专用）
- **数据色**【open-color】：130 个跨色相同档感知亮度对齐的色——多系列/多色块图（Mekko/堆叠）直接用。
- **主色 + 语义 + 纪律**【Mck-skill】：NAVY 主色 + 强调四色（仅 3+ 并列项才用）+ 「一个高亮其余全灰」（mckinsey-charts）。**两者拼起来才是咨询级配色**（open-color 无语义层、麦肯锡明令废弃 cyan）。

## 五、落点 + 待办

**✅ 已拍板（2026-07-01·之前悬置的"是否采用 ppt-master 做底座"决策）**：**部分采用，不是非此即彼**——
- **Waterfall / Gantt / Org-chart 这类库里已有现成模板的**：以 `templates/charts/{waterfall_chart,gantt_chart,top_down_tree}.svg` 当**起点**适配（见各节"真实模板可核对"备注），不从零手画坐标，但视觉细节（色值/字号/阴影）必须按当次 deck 的 spec_lock 重新蒙皮，禁止照搬模板自带视觉值（制作工作流 SKILL「模板供结构不供皮肤」纪律）。
- **Mekko 这类库里真空缺的**：继续走本文自研算法，没有第二个选项。
- **判断依据**：六路深挖（2026-07-01）实测核对了 71 张图表模板，waterfall/gantt 画法跟本文描述基本吻合（gantt 模板比本文方案更简化，缺依赖连接线，复杂依赖场景仍需按 frappe-gantt 公式自研那段补全），Mekko confirmed 真空缺。已不再是"可能是底座"的悬置状态。
- 这三套算法（含 Mekko 自研、waterfall/gantt 模板适配方案）= python-pptx/SVG 制作层的**「高 stakes 画法卡」**，沉淀成范本卡进 `exemplars/`，共用「算区间」内核保复用率。
- **✅ 已实装（2026-07-01）**：`engine/chart_shapes.py::waterfall_chart/gantt_chart/mekko_chart`——三个函数只画图表本体
  （`<g>` 片段，画布区 x/y/w/h 按当页 spec_lock zones 传入），标题/来源/图例仍由本页手写 SVG 拼。
  坐标已用手算样例逐条核对（`tests/test_chart_shapes.py` 16 项，含 waterfall 穿零区间/gantt 里程碑+依赖箭头/
  mekko 列宽占比），并过 `svg_compat` 导出兼容性机检。Gantt 依赖箭头用 SVG `<marker>` + `marker-end`，
  svg2pptx 转换引擎原生支持转成 DrawingML 线端（`drawingml_styles.py::_classify_marker`），非位图兜底。
  调用方式见制作工作流 SKILL 阶段2"🔒 waterfall/Gantt/Mekko 图表几何必须用 chart_shapes.py"。

> ⚠️ 可信度：算法范本来自真实开源实现（带行号出处），坐标计算已实装+单测手算验证+过导出兼容机检；
> **仍未在真实 deck 端到端跑过一次**（颜色需按 spec_lock 重新蒙皮、多个图表同页时 Gantt 的 `marker` id 需去重
> 等实战细节未验证）——落到具体某份 deck 前仍需人审一次真实产出。
