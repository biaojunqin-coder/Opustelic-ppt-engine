# plotlyPowerpoint 拆解笔记

> 拆解对象：`/Users/qinbiaojuan/Documents/PPT开源参考/05_图表库/plotlyPowerpoint`
> 仓库：https://github.com/jonboone1/plotlyPowerpoint · 作者 Jon Boone（jonboone1）· **本地副本 setup.py 标 v1.2.17 / dist 最高 1.2.16 / PKG-INFO 1.2.16** · MIT · 末次提交 2022-11-22
> 拆解日期：2026-06-30 · 拆解人：Claude（PPT Engine 研究层）
> 方法：`ls` + README + `setup.py` / `requirements.txt` + **核心源码 `plotlyPowerpoint/core.py`（仅此一个文件，856 行）逐行精读**，结论均带行号出处，不掺常识推断；存疑处显式标注。
> 定位：**「图表库渲染 → 插 PPTX」的桥接轮子**。拆它是为看「若制作层走 plotly 渲染再贴图」这条路长什么样、有没有现成思路可借——并对照我们「原生可编辑」铁律看张力。

---

## 一句话：最值得偷的 1 点

**它把「一张幻灯片 = 一个 dict」做成了一套声明式 schema——你只丢一个未聚合的原始 DataFrame + 一个描述图表的字典数组，库自动完成 `过滤 → groupby 聚合 → 画图 → 插片`，调用方一行 pandas 都不用写**（`createSlides(charts)`，core.py:54）。这套「数据 + 声明 = 幻灯片」的 IR（中间表示）思路，正是 PPT Engine 制作层值得抄的「人/LLM 友好的图表描述层」；至于它底层怎么把图放进 pptx，反而是**反面教材**（见下②③）。

---

## ① 是什么 + 定位 + License

- **是什么**：一个 ~856 行单文件的 Python 库（`core.py` 是全部逻辑，`__init__.py` 只做 `from core import *`），把 plotly 画的图批量塞进一个 PowerPoint 模板，产出 `output.pptx`。
- **定位**：自动化「带图表的分析报告 deck」。README 原话——「automate powerpoint creation including certain charts/visualizations」，并明确建议把产出当**「幻灯片素材库」**用：跑一次生成所有图、再手工挑选删减（README:131）。
- **License**：MIT（setup.py:20；LICENSE 文件，但**注意 LICENSE 里 `Copyright (c) [year] [fullname]` 占位符没填**，年份/作者名都是模板字面值——轻微瑕疵，不影响 MIT 授权本身）。
- **依赖**：`plotly>=4.14.3`、`pandas>=1.2.4`、`python-pptx==0.6.19`（**钉死老版本**）、`scipy`、`numerize`（requirements.txt）。其中 `scipy.stats.pearsonr`（core.py:5）和 `numerize`（core.py:4）**import 了但全文件未使用**——死依赖，徒增安装负担。
- **支持的图表类型**（core.py 里 `if chartDefinition['type'] ==` 穷举）：`line` / `bar` / `facetLine` / `facetBar` / `filledLine` / `facetFilledLine` / `table`，共 7 种。**全是 plotly 基础图**，无 waterfall / Mekko / Gantt（与我们高 stakes 段无交集）。

---

## ② 它怎么把 plotly 图表放进 pptx —— **渲染成 PNG 图片再贴进占位符**

**核心机制一句话：plotly 图 → `write_image()` 导出成 PNG 落盘到 `charts/` → python-pptx 的 `insert_picture()` 把这张 PNG 塞进模板的图片占位符。是「图片化」，不是原生图表。** 逐字证据：

1. **渲染成图片**（core.py:683-700）：
   - 第 687-688 行：若无 `charts/` 文件夹则 `os.makedirs('charts')`。
   - 第 691 行：`filename = 'charts/chart' + str(z) + '.png'`（按数组下标命名）。
   - 第 700 行：`fig.write_image(filename, scale=2)` —— **这一行就是「图表→图片」的全部**。`fig` 是 plotly 的 Figure 对象，`write_image` 走的是 plotly 的静态导出（底层依赖 kaleido / 旧版 orca 引擎）渲染成位图。
2. **图片插进 pptx**（core.py:724-727）：
   ```python
   if chartDefinition['type'] != 'table':
       #insert image
       picture = slide.placeholders[chartDefinition['item-index']['chart']].insert_picture(filename)
   ```
   靠 python-pptx 的 `PicturePlaceholder.insert_picture()`，把 PNG 填进模板里预留的**图片占位符**（idx 由用户在 dict 的 `item-index.chart` 指定）。
3. **新建幻灯片 + 填文字**（core.py:707-721）：`prs.slide_layouts[...]` 取版式 → `add_slide` → 往 title/description/subtitle 占位符 `.text =` 赋值。
4. **存盘**（core.py:856）：`prs.save("output.pptx")` —— **文件名写死，每次运行覆盖**（README:131 也提醒了这点）。

**唯一例外 = `table` 类型走原生表格**（core.py:730-853，是图片化之外的另一条分支）：
- 用 `insert_table()` 建**真·PPT 原生表格**（core.py:732），逐格 `cell.text =` 写值，按 `column_formats` 做数字/货币/百分比/日期格式化（:760-771）。
- 还手搓 OOXML 设边框（`_set_cell_border` 用 `OxmlElement` 拼 `a:lnL/R/T/B`，core.py:19-31）、设单元格/表头填充色、字号、并用像素算式把表格垂直居中（:840-853）。
- → **这部分（table 分支）产出的是可编辑的原生表格**，与图表分支的「贴死图片」形成鲜明对比。若要从本库偷代码，**该偷的是 table 分支的 python-pptx 用法**，不是图表分支。

**数据流水线（图表分支，core.py:60-108）**——这是它真正的巧思：
- `temp = chartDefinition['data']`（拿原始 df）→ 按 `filters` 声明动态过滤 → 按 `color`/`axis`/`facet` 拼 `groupList` + 按 `metrics` 拼聚合字典 → `temp.groupby(groupList).agg(metricDict)`（:108）自动聚合到画图所需粒度。**调用方只管丢原始数据 + 写声明，聚合全自动**。

---

## ③ 对 PPT Engine 的落点 —— 桥接思路可借，但实现与铁律 4「原生可编辑」正面冲突

### 3A. 【反面教材·张力点】图片化 = 不可编辑，正是我们要避开的
- `write_image → insert_picture`（core.py:700 + 727）产出的图表在 PowerPoint 里**就是一张死图**：不能改数、不能换色、不能调坐标轴、放大锯齿、字体不随母版。这与 PPT Engine **「原生可编辑」**的取向直接对立。
- **结论**：这条「plotly 渲染→贴图」路线，**我们图表段不该走**。它的存在恰好反向印证了我们的判断——要做咨询级 deck，图表必须是 PowerPoint 原生的 `c:chartSpace`（可双击编辑数据），而非任何渲染引擎的位图。对照隔壁 `04制作/PptxGenJS.md` 的结论：原生图表才有「编辑数据」按钮能打开 Excel 改数。**plotlyPowerpoint 恰是那条被否定的对照路径的活样本。**

### 3B. 【该借·真价值】声明式「幻灯片 IR」+ 自动聚合管线
- **值得抄的不是它怎么贴图，而是它的输入契约**：`[{data, type, metrics, axis, filters, options, item-index}, ...]` 这套「一个 dict 描述一张图表幻灯片」的 schema（README Step 7 + core.py 全程消费），把「画什么图」声明化、和「怎么落到 pptx」解耦。
- 对 PPT Engine：制作层如果设计一个**「图表意图描述层」**（人或 LLM 产出结构化图表定义 → 引擎翻译成原生 OOXML 图表），这套 dict schema 的字段划分（metrics 带 `method` 聚合方式、filters 带 `type`/`operation`/`value`、options 管朝向/网格线/轴标题）是现成的**字段设计参考**。**偷 schema,弃渲染。**
- **自动 groupby 聚合**（core.py:88-108）也值得借：让调用方丢「宽口径原始数据 + 声明聚合维度」，引擎自动 `groupby().agg()` 到位——省去为每张图手搓 DataFrame，对 LLM 友好。

### 3C. 【可选退路】仅在「一次性、不需编辑」的低 stakes 场景
- 若哪天有「快速出个内部数据看板 deck、图表不要求可编辑」的低 stakes 需求，这种「图表库渲染→贴图」是**最省事的实现**（一个 `write_image` + `insert_picture` 搞定，不碰 OOXML）。但这明确**在我们收窄的高 stakes 段之外**（铁律 4），仅作技术储备记录。

---

## ④ 坑（采纳前必看）

1. **图表是死图、不可编辑**（core.py:700/727）——**最大坑**，见 3A。与铁律 4 冲突，高 stakes 段禁用此路。
2. **`fig.write_image` 需要额外渲染引擎**——plotly 静态导图依赖 `kaleido`（或旧 `orca`），**但 requirements.txt 没列 kaleido**。README Step 1 也坦承「I have yet to figure out how to install required packages with the install of this library」「if you want to visualize... you may have to install additional requirements」——**装完直接跑大概率因缺渲染引擎报错**，需用户自行补装。
3. **`eval` 执行字符串过滤器**（core.py:73-86）：filters 被拼成 Python 表达式字符串再 `eval(filters[i])`。**有代码注入风险**（若 filter 的 `variable`/`value` 来自不可信输入），且报错信息极不友好。生产环境/对外服务禁用。
4. **输出文件名写死 `output.pptx`**（core.py:856），且**每次运行覆盖**、强制写在当前工作目录;`charts/` 目录同理（core.py:691）。无任何参数可改——不可重入、不适合并发/批处理。
5. **大量硬编码业务逻辑漏进了库**：core.py:696 有 `elif chartDefinition['name'] == 'Lead Quality - Lead Status Over Time':` 这种**针对某个具体图名**的特判尺寸；:694 引用了 `barsubplot` 类型但上面 7 种图里**根本没实现它**。说明这是从作者私人项目里抠出来的，**未做通用化清理**，照搬有暗坑。
6. **死代码 / 死依赖**：`scipy.stats.pearsonr`、`numerize` import 未用（core.py:4-5）；多段数据标签逻辑被注释掉（:301-310、:463-474）。
7. **`python-pptx==0.6.19` 钉死**（requirements.txt:13）——与现代 python-pptx 共存可能版本打架；且 0.6.19 较老。
8. **零测试**：requirements 列了 pytest/behave/flake8，但仓库**无任何 test 文件**（egg-info SOURCES 也无）。质量无回归保障。

---

## 附：关键证据行号速查（core.py）

| 关注点 | 行号 |
|---|---|
| 主入口 `createSlides(charts)` | 54 |
| filters 拼字符串 + `eval` 执行 | 73-86 |
| 自动 `groupby().agg()` 聚合 | 88-108 |
| **图表→PNG：`fig.write_image(filename, scale=2)`** | **700** |
| **PNG→pptx：`insert_picture(filename)`** | **727** |
| table 走原生 `insert_table`（唯一可编辑分支） | 730-853 |
| `_set_cell_border` 手搓 OOXML 边框 | 19-31 |
| 输出写死 `output.pptx`（每次覆盖） | 856 |
| 硬编码特定图名 / 未实现的 barsubplot | 694-698 |
