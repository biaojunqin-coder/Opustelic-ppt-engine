# Frappe Gantt 拆解（甘特图怎么画 → 移植成 python-pptx 矩形拼）

> 轻拆 · 源码级 · 2026-06-30
> 仓库：`05_图表库/gantt`（frappe/gantt · ~6k★ · MIT · 专做 Gantt）
> 拆它的唯一目的：**PPT Engine 制作层要画咨询级 Gantt（python-pptx 原生没有），这库就是「任务条+时间轴+依赖箭头」的标准答案，把它的定位公式直接搬成矩形坐标。**
> 出处全部精确到行（`文件:行`），公式可直接照抄。

---

## ① 是什么 + 定位 + license

- **A modern, configurable, Gantt library for the web**（README.md:5）。一句话本质：`Gantt charts are bar charts that visually illustrate a project's tasks, schedule, and dependencies`（README.md:13）——**甘特图 = 横条图 + 时间轴 X 坐标**，没别的玄学。
- 纯前端、零运行时依赖、输出 **SVG**（不是 canvas，所以每个图元都是可读的 `<rect>/<path>/<text>`，正好对应 PPT 的 shape）。ERPNext 在用（README.md:17）。
- License：**MIT**（license.txt，Copyright Frappe Technologies）—— 可商用、可改、可搬算法，留版权声明即可。
- 体量极小：核心就 `src/` 下 7 个文件——`index.js`（主类/时间轴/网格，1636 行）、`bar.js`（任务条，753 行）、`arrow.js`（依赖箭头，103 行）、`date_utils.js`（日期换算，307 行）、`defaults.js`（视图档位/默认值）、`popup.js`、`svg_utils.js`。**拆这 4 个 .js 就拆透了画法。**

数据结构（最小任务对象，README.md:58-67）：
```js
{ id: '1', name: 'Redesign website', start: '2016-12-28', end: '2016-12-31', progress: 20,
  dependencies: '1,2'  // 逗号分隔的前置任务 id 串
}
```

---

## ② 它怎么画 Gantt（核心 · 这正是我们缺的）

整张图 = **一个全局起点 `gantt_start` + 一个列宽 `column_width` + 把每条任务的「日期」换算成「像素」**。三步：定 X（什么时候开始）、定宽（持续多久）、定 Y（第几行）。

### 2.1 全局时间原点 + 列宽（一切坐标的基准）

- `gantt_start` = 所有任务里最早的 start（`index.js:299-306` 取 min start / max end），再 `start_of` 对齐到视图单位（`index.js:308`），最后 `setHours(0,0,0,0)` 抹平到当天 0 点（`index.js:348`）。**这是 X=0 的锚。**
- `column_width` = 每个时间格的像素宽，默认 45（Day 视图），不同视图档不同（`defaults.js`：Week=140 / Month=120 / Year=120）。配置见 README column_width。
- `config.step` / `config.unit`：每列代表多少时间。Day 视图 step=`1d`、unit=`day`；Hour 视图 step=`1h`。来自 `defaults.js` DEFAULT_VIEW_MODES（行 15-108）。

### 2.2 任务条 X 坐标 —— 「开始日期距原点多少格 × 列宽」（最关键公式）

`bar.js:587-620 compute_x()`：
```js
const diff = date_utils.diff(task_start, gantt_start, unit) / step;  // 距原点几格
let x = diff * column_width;                                          // 几格 × 列宽 = 像素 X
```
- `date_utils.diff(a,b,scale)`（`date_utils.js:128-174`）= 两日期差，按 scale 折算（days = 毫秒差/1000/60/60/24，还做了时区补偿 `date_utils.js:131-134`）。
- **一句话：`x = (任务start − 全局start 的天数) ÷ 每格天数 × 列宽`**。这就是任务条左边缘的横坐标。

### 2.3 任务条宽度 —— 「持续天数 × 列宽」

`bar.js:629-665 compute_duration()` + `bar.js:72`：
```js
// 逐天循环 [_start, _end) 数天数（行 633-648），可剔除被 ignore 的天（周末/假日）
this.duration = convert_scales(duration_in_days+'d', unit) / step;   // 折算成"格数"
this.width = config.column_width * this.duration;                    // 格数 × 列宽 = 像素宽（行 72）
```
- **一句话：`width = 持续格数 × 列宽`**。起+宽 = 任务条左右边缘，X 坐标系闭合。
- 注意它**逐天 for 循环**数天（`bar.js:633`），不是简单 end−start，目的是能跳过周末/假日（`ignored_dates`）——高 stakes deck 里"工期排除周末"很常见，这逻辑值得保留。

### 2.4 任务条 Y 坐标 —— 「表头高 + 行号 × 行高」

`bar.js:622-627 compute_y()`：
```js
this.y = config.header_height                       // 时间轴表头占的高
       + options.padding / 2
       + task._index * (this.height + options.padding);  // 第几行 × (条高+行距)
```
- `_index` = 任务在数组里的序号（第 0、1、2… 行）。`height` = `bar_height`（默认 30）。`padding` 默认 18（行距）。
- **一句话：每条任务垂直堆叠，行高 = bar_height + padding。** 简单粗暴，正好对应 PPT 里一行一行往下摆矩形。

### 2.5 任务条本体（一个圆角矩形）+ 进度叠加条

`bar.js:119-136 draw_bar()`：就一个 `<rect>`，`x/y/width/height` 来自上面，`rx=ry=corner_radius`（圆角默认 3，`bar.js:68` 夹到不超过半高）：
```js
createSVG('rect', { x, y, width, height, rx: corner_radius, class: 'bar' });
```
进度条（`bar.js:159-195 draw_progress_bar()`）= **同 x/y、宽度按 progress% 缩短的第二个 rect** 盖在上面：
```js
progress_width = (bar宽 × progress) / 100;   // bar.js:204-205（精确版还会跳过 ignored 区）
createSVG('rect', { x, y, width: progress_width, height, class: 'bar-progress' });
```
→ **PPT 直接照搬：底层一个全长矩形（浅色）+ 上层一个 progress% 长的矩形（深色），就是"已完成 30%"的视觉。**

### 2.6 时间轴刻度 + 网格（X 轴的「尺子」和背景线）

任务条要对齐时间，得有刻度线和列线。`index.js:533-596 make_grid_ticks()`：
- 横向行线（`index.js:548-564`）：每 `row_height = bar_height + padding` 画一条 `<line>`，从 0 到 `row_width`。
- **竖向刻度线**（`index.js:567-595`）：遍历 `this.dates`（所有时间格），每格画一条竖 `<path d="M tick_x tick_y v tick_height">`，每画完 `tick_x += column_width`（行 593）。`thick_line` 档（如周一、每季度，`defaults.js` 各视图定义）线更粗（行 569-574）。
- `this.dates` 怎么来：`index.js:351-363 setup_date_values()`——从 `gantt_start` 起，每次 `add(cur, step, unit)` 推一格，直到 `gantt_end`，攒成数组。**`dates.length × column_width` = 整图总宽**（`index.js:419`）。

### 2.7 时间轴双层表头（上=月/年，下=日/周）

`index.js:797-887`。每格算一个 `date_info`：
- X 坐标和任务条同一套：`x = diff/step × column_width`（`get_date_info` 内，复用 2.2 公式）。
- **双层**：`upper_text`（上层，大粒度，如 "December"）`upper_y: 17`；`lower_text`（下层，小粒度，如 "28"）`lower_y: upper_header_height + 5`（`index.js:884-885`）。
- 上层文字**只在变化时才显示**（如月份变了才打一次 "January"），靠 `defaults.js` 里每个视图的 `upper_text: (d, ld) => d.getMonth() !== ld.getMonth() ? ... : ''`（行 63-66 等）实现——避免每格都重复打月份。

> **②小结（搬运清单）**：原点 `gantt_start` → 列宽 `column_width` → 每条任务 `x=日期差/step×列宽`、`width=工期格数×列宽`、`y=表头高+行号×(条高+行距)` → 顶上叠双层表头 + 竖刻度线。**全是加减乘除，没有任何依赖运行时的东西，可 100% 移植。**

---

## ③ 交互 / 里程碑 / 依赖怎么表达

- **依赖箭头**（核心，`arrow.js` 全 + `index.js:897-916`）：
  - 数据：task 的 `dependencies` 是逗号串，`index.js:200-205` split 成数组、`setup_dependencies()`（行 223-）建反向表。
  - 建箭头：`make_arrows()`（`index.js:905-908`）对每条依赖 new 一个 `Arrow(from=前置任务bar, to=本任务bar)`。
  - **画法（`arrow.js:13-89 calculate_path()`）**：箭头是一条 `<path>`，起点 = from 条的**底边中点**（`start_x = from.x + from.width/2`，行 14-15；`start_y` 在 from 条下沿，行 26-31），终点 = to 条的**左边缘**（`end_x = to.x − 13`，行 33；`end_y` 在 to 条垂直中点，行 34-39）。中间用 SVG 圆弧 `a rx ry 0 0 sweep dx dy` 拐 90° 直角弯（行 63-74 / 80-87），末尾 `m -5 -5 / l 5 5 / l -5 5` 画箭头尖（行 72-74）。
  - 两种走法：to 在 from 右侧 → 简单"下拐右"（行 80-87）；to 在 from 左侧/重叠 → 复杂"下-左绕-下-右"四段弧（行 63-74）。`from_is_below_to`（行 41-42）决定上拐还是下拐。
- **里程碑（milestone）**：本库**没有专门的菱形里程碑图元**（grep 无 milestone）。它的"零工期"会退化成很窄的条。→ **PPT Engine 这里要自己补**：start==end 的任务画成 45° 菱形（咨询 deck 标配），是本库缺的、我们要加的点。
- **进度/日期可拖拽编辑**：`bar.js` 大量篇幅（draw_resize_handles 行 288-340、update_bar_position 行 437-468、compute_start_end_date 行 539-556 反算日期）——**这些对 PPT 完全无用**（静态出图不需要拖拽），移植时整段跳过，能省一大半代码。
- **popup 悬浮卡**：`defaults.js:128-148` 默认弹"start − end (N days) / Progress: X%"。→ PPT 里对应"在条上/条边标注工期文字"，可参考它的文案格式。
- **expected progress（应完成度）**：`bar.js:575-585` 按今天 vs start 算"按计划此刻该完成多少"，画第三条参考条（`bar.js:138-157`）。高 stakes deck 想做"计划 vs 实际"对比时可借鉴。

---

## ④ 对 PPT Engine 落点（SVG 画法 → python-pptx 矩形拼）★最重要

我们要把这套坐标公式搬进制作层，用 `slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h)` 一个个摆矩形。**映射表（直接照搬，单位换算成 EMU/Inches/Pt 即可）**：

| Frappe（SVG，像素） | PPT Engine（python-pptx） | 公式出处 |
|---|---|---|
| 全局 `gantt_start` | 选定起始日期（最早任务）作为画布左边界锚 | index.js:299-308 |
| `column_width`（每格像素） | 每格占多少 EMU = 可用画布宽 ÷ 总格数；总格数=`(end−start)/step` | bar.js:72 / index.js:419 |
| 任务条 X = `diff/step × column_width` | `left = 左边距 + (任务start−start).days ÷ 每格天数 × 每格宽` | **bar.js:592-596（核心）** |
| 任务条 width = `工期格数 × column_width` | `width = 工期天数 ÷ 每格天数 × 每格宽` | **bar.js:72 / 652-656** |
| 任务条 Y = `表头高 + _index×(条高+行距)` | `top = 表头高 + 行号 × (条高 + 行距)` | **bar.js:622-627** |
| `<rect rx=corner_radius>` 任务条 | `add_shape(ROUNDED_RECTANGLE, left, top, width, height)` | bar.js:119-129 |
| 进度叠加条（缩短的第二 rect） | 同 left/top、width×progress% 的第二个矩形盖上 | bar.js:159-205 |
| 竖刻度线 `tick_x += column_width` | 每格画一条竖线（细线 connector / 窄矩形），thick 档加粗 | index.js:567-595 |
| 双层表头 upper/lower_text | 顶部两行文本框：上=月/年、下=日/周；上层仅变化时打 | index.js:874-885 / defaults.js |
| 依赖箭头 `<path>` 直角弯+箭尖 | `add_connector` 折线 + 箭头端，或自绘 freeform；起点=from右/底、终点=to左 | **arrow.js:13-89** |
| 视图档（Day/Week/Month 的 step+列宽） | 我们的"时间粒度"参数：日/周/月，决定每格代表多久 | defaults.js:15-108 |

**落地要点（务必照做）**：
1. **先定"每格代表多少天 + 每格多少 EMU"两个数，整张图的所有 left/width 全由这两个数线性推出**——这是本库最该偷的设计：单一坐标基准，不要每个条各算各的。
2. **进度=两层矩形叠**（底浅+上深缩短版），别想复杂；对应 bar.js 的 bar + bar-progress 双 rect。
3. **里程碑要自己补菱形**（本库没有，§③）：start==end → `add_shape(DIAMOND)`，是咨询 deck 把 Gantt 做"高级"的关键差异点。
4. **依赖箭头**用 python-pptx 的 connector 接两条矩形的"右中→左中"锚点，弯折逻辑可大幅简化（arrow.js 那套绕行只为像素级避让，PPT 里直角折线足够）。
5. **整段跳过拖拽/resize/事件**（bar.js 一半代码、popup.js、svg_utils 的 animate）——静态出图用不上，移植时只搬"算坐标 + 画矩形"那几个 compute_* 函数。

---

## ⑤ 坑

1. **逐天 for 循环数工期**（`bar.js:633-648`、`index.js:632-636`）：跨大时间范围 + 多任务时是 O(天数×任务数)，几年期 deck 会慢。我们移植时若不需要"排除周末"，直接 `(end−start).days` 一步算，别抄循环。
2. **Month/Year 视图列宽是近似**（`index.js:582-594`）：月视图按"每月天数 × 列宽 ÷ 30"、年按"÷365"摊，因为月/年长度不等。bar.js:598-617 还专门留了一段被注释掉的"伪 30 天月"补偿代码——说明**月/年粒度下任务条 X 会有累积误差**。高 stakes deck 若用月粒度，需自己校准对齐，别盲信线性公式。
3. **时区补偿**（`date_utils.js:131-134`）：diff 里手动加了 `getTimezoneOffset` 差值。python 用 `datetime`/`date` 算天数一般无此问题，但若任务带时分秒、跨夏令时，仍要留意；建议我们统一只取日期（抹掉时分秒，对应它的 `setHours(0,0,0,0)` index.js:348）。
4. **里程碑缺失**（§③）：别指望库里有现成菱形，必须自建。
5. **进度宽度的 ignored 区修正很绕**（`bar.js:197-226`）：为了"进度条遇到周末要跳过"做了多轮 while 补偿。若我们不做"排除周末"，进度宽就是 `width × progress%` 一行，别抄那坨。
6. **`date_utils.diff` 的月/年用了近似**（`date_utils.js:143` `monthDiff += date_a.getDate()/31`）：月差是浮点估算不是精确历法差。仅用于布局够用，**别拿它当业务级日期计算**。

---

## 一句话结论（对我们做 Gantt 最有用的 1 点）

**任务条 X 坐标 = `(任务start − 全局最早start) ÷ 每格天数 × 每格宽`（`bar.js:592-596`）—— 整张甘特图就靠"一个全局时间原点 + 一个列宽"两个数把所有日期线性映射成像素，我们照这条公式把日期换成 EMU，用 python-pptx 一行 `add_shape(ROUNDED_RECTANGLE, left, top, width, height)` 摆矩形即可复刻，python-pptx 的 Gantt 护城河就此打通。**
