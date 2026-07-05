# PPTist 拆解笔记

> 拆解对象：`01_AI端到端应用/PPTist`
> 仓库：https://github.com/pipipi-pikachu/PPTist · 9.1k★ · v2.0.0 · AGPL-3.0
> 拆解日期：2026-06-30 · 拆解人：Claude（PPT Engine 研究层）
> 方法：`ls -R` + README_zh + doc/ + 关键源码精读，**结论均带出处行号，不掺常识推断**；存疑处显式标注。

---

## 一句话：最值得偷的 1 件事

**形状导出走 PPTX 原生 `custGeom`（自定义几何）矢量路径、而非图片** —— 任意 SVG path 在导出前用 `svg-pathdata` 的 `A_TO_C`/`QT_TO_C` 等 transformer **统一降解成 pptxgenjs 只认的 `M`/`L`/`C`/`Z` 四种命令**（arc/二次曲线→三次贝塞尔），于是任意形状导出后在 PowerPoint 里仍是可编辑矢量。这正好命中我们「可编辑 pptx 是铁律」的死穴。出处：`src/utils/svgPathParser.ts:7-58`、`src/hooks/useExport.ts:686`（`addShape('custGeom', ...)`）。

---

## ① 是什么 + 定位

- **是什么**：基于 Web 的在线演示文稿（幻灯片）编辑/演示应用，Vue3 + TypeScript，不依赖 UI 组件库。还原了 Office PowerPoint 大部分常用功能，支持 文字/图片/形状/线条/图表/表格/视频/音频/公式 九类元素。（出处 README_zh.md:16, 23）
- **作者自我定位（关键，原文照搬）**：核心定位是「**Web 幻灯片编辑/演示应用**」，编辑能力和编辑体验是最核心优势。对各场景的推荐度作者自评（README_zh.md:35-42）：
  - Web 幻灯片编辑/演示：⭐⭐⭐⭐⭐（最推荐）
  - **AIPPT 生成工具：⭐⭐**（只给两星！原文：「更适合作为结构化生成结果的承载、编辑和二次加工底座，而不是开箱即用的完整 AIPPT 商业方案」）
  - PPT 文件预览 / Office PPT 制作工具：各 ⭐⭐
- **作者明确的边界声明**（README_zh.md:30）：目标受众是「有 Web 幻灯片开发需求的开发者」，「不提供任何在线服务，不应直接作为工具使用，不支持开箱即用」。
- **技术栈关键依赖**（package.json:14-46）：`pptxgenjs@3.12`（导出 PPTX）、`pptxtojson@2.0.6`（导入 PPTX，作者自研姊妹库）、`prosemirror-*`（富文本）、`echarts@6`（图表渲染）、`html-to-image`（导图片）、`dexie`（IndexedDB 本地存储）。
- **⚠️ 对我们的相关性边界**：PPTist 是 **Web 端到端在线编辑器**（DOM/SVG 渲染 + 浏览器内 pptxgenjs 导出）；PPT Engine 是 **python-pptx 原生制作层**。技术栈完全不同栈，**不能直接复用代码**，能偷的是 ②schema 设计思想 与 ③导出映射方法论。

---

## ② AI_PPT_SCHEMA 长什么样（重点）

⚠️ **关键发现：PPTist 有两套独立的 AI 数据结构，不要混淆**：

### 2A. 模板式 AIPPT（轻量语义数据 → 套模板）

- 结构定义：`src/types/AIPPT.ts`（仅 41 行）；示例数据：`public/mocks/AIPPT.json`；原理：`doc/AIPPT.md`。
- AI 只产出**极简的「语义内容」**，不含任何坐标/样式。五种页面类型（AIPPT.ts:1-43）：
  ```ts
  AIPPTCover      { type:'cover',      data:{ title, text } }
  AIPPTContents   { type:'contents',   data:{ items: string[] }, offset? }
  AIPPTTransition { type:'transition', data:{ title, text } }
  AIPPTContent    { type:'content',    data:{ title, items:{title,text}[] }, offset? }
  AIPPTEnd        { type:'end' }
  ```
- **落地路径**（doc/AIPPT.md:1-9）：定义结构 → AI 生成语义数据 → 与「标注好类型的模板页」匹配填充 → 配图（文生图/图库检索）→ 出片。
- **模板怎么来**：就是在 PPTist 里做的普通页面，用「幻灯片类型标注」功能给页面/节点打 `slideType` + `textType`/`imageType` 标记，导出 JSON 即成模板（doc/AIPPT.md:15-22，「实际上并不存在专门提供给 AIPPT 的模板」）。
- 节点标记类型（`src/types/slides.ts:148`）：`TextType = 'title'|'subtitle'|'content'|'item'|'itemTitle'|'notes'|'header'|'footer'|'partNumber'|'itemNumber'`；`ImageType = 'pageFigure'|'itemFigure'|'background'`（slides.ts:264）。

### 2B. 非模板式 schema —— AI 直接生成整页数据（★我们最该参考的）

- 文档：`doc/AI_PPT_SCHEMA.md`（759 行，**专为 AI 生成写的、刻意收窄的子集**，开篇即注「专用于 AI 生成，并非完整数据定义」）。AI 直接吐出带绝对坐标的整页 JSON，跳过模板。
- **画布约定（硬契约，AI_PPT_SCHEMA.md:5-19）**：
  - 逻辑宽度固定 `1000`，逻辑高度固定 `562.5`（16:9），原点左上角，单位逻辑 px，y 向下增大。
  - 除线条外所有元素用矩形包围盒 `{left, top, width, height, rotate}` 表达，旋转中心=元素中心，`left/top/w/h` 始终描述「未旋转前」的盒。
- **元素类型与必填字段**（逐类精读 AI_PPT_SCHEMA.md）：
  - `text`（210-254）：`content` 是富文本 HTML 字符串；必填 `defaultFontName`/`defaultColor`；建议 `fixedHeight:true`「以保证稳定布局约束」+ `vAlign`。
  - `image`（256-353）：`src` + **必填 `description`**（图片语义描述，「承载真实画面意图」，用于后续文生图/检索）；schema 要求 AI 先统一填占位 src，描述才是载荷。含 `filters`（CSS filter 字典）、`clip`（百分比裁剪 `range:[[x1,y1],[x2,y2]]`）。
  - `shape`（355-450）：`viewBox:[w,h]` + `path`（SVG d 串）+ `fill`；**path 只准用 `M L Q C A Z`**（390）—— 这条约束与导出端能力严格对齐（见③）。
  - `line`（452-493）：特殊——无 `height`、无 `rotate`，`start`/`end` 定方向，`width`=描边粗细，`points:['','arrow','dot']` 定端点。
  - `table`（495-628）：`colWidths`（占比、和为1）+ `data:TableCell[][]`，合并单元格用主格的 `rowspan/colspan` 表达。
  - `chart`（630-710）：`chartType` 八种；`data:{labels, legends, series:number[][]}`；饼/环只用 `series[0]`，散点 `series[0]=x、series[1]=y`。
- **共享样式子结构**（AI_PPT_SCHEMA.md:38-92）：`outline`/`shadow`/`gradient` 三个复用块，全 schema 共享。
- **富文本是「白名单子集」（94-131，★强约束设计）**：只认 `p ul ol li blockquote` + `strong em u strike sup sub code span`；**「严禁使用未列出的标签或样式」**；`span` 只认 `color/background-color/font-size/font-family`。列表硬性要求 `<li>` 内必包 `<p>`。
- **字体白名单（133-152）**：16 款定死可选字体（思源黑/宋、霞鹜文楷、MiSans、Inter…），缺省=系统默认。
- **隐性排版规则喂给 AI（248-254，很妙）**：文档直接告诉模型「文本框上下左右各 10px 内边距、段落间 5px 段间距」，让 AI 自己反推 `width/height`。

> **schema 设计哲学三连（对我们最有价值的「思想」）**：
> ① **为 AI 生成专门裁一套收窄子集**，而非把完整内部数据结构丢给模型——降低出错面、稳定可渲染。
> ② **白名单而非黑名单**：富文本标签/样式/字体全部正面枚举 + 「严禁列外」措辞。
> ③ **把渲染器的隐性规则（内边距/段间距/坐标系）显式写进 prompt 文档**，让模型据此算布局，而不是事后纠偏。

---

## ③ PPTX 导出怎么做到 95%+ 保真（重点·核心引擎 `src/hooks/useExport.ts` 1005 行）

整条链路：内部 Slide 数据 → 逐元素映射成 pptxgenjs 的 add* 调用 → 浏览器内 `pptx.writeFile()` 落 .pptx。**全程在前端、不经后端**。

### 3.1 单位换算体系（保真地基，useExport.ts:31-36）
- 画布逻辑基数 `viewportSize=1000`（store/slides.ts:53），但换算锚定在 **960**：
  ```
  ratioPx2Inch = 96 * (viewportSize / 960)   // 逻辑px → 英寸（pptxgenjs 位置单位）
  ratioPx2Pt   = 96/72 * (viewportSize / 960) // 逻辑px → 磅（字号/线宽单位）
  ```
- 所有 `x/y/w/h` 一律 `/ratioPx2Inch`，所有字号/线宽/边距 `/ratioPx2Pt`。
- 画布比例映射到 PPT 母版尺寸（469-483）：0.5625→`LAYOUT_16x9`，0.625→16x10，0.75→4x3，A3 横/竖用 `defineLayout` 自定义。

### 3.2 ★形状=原生矢量而非图片（最大的保真杀招）
- 普通形状走 `pptxSlide.addShape('custGeom', { points, ... })`（useExport.ts:686）——PowerPoint 里是**可编辑矢量自定义几何**。
- 桥接靠 `formatPoints`（321-364）把 SVG 点转成 pptxgenjs 的 `{x,y,moveTo}` / `{curve:{type:'cubic'|'quadratic'|'arc',...}}` / `{close:true}`。
- **关键降解**（svgPathParser.ts:9-13）：导出前用 `svg-pathdata` 链式 transform：`TO_ABS` → `NORMALIZE_HVZ`（H/V/Z 归一）→ `NORMALIZE_ST` → `QT_TO_C`（二次曲线→三次）→ `A_TO_C`（圆弧→三次贝塞尔）。**最终只剩 M/L/C/Z**——正好是 pptxgenjs custGeom 可靠支持的集合。这解释了为何 ②schema 把 path 限定在 `M L Q C A Z`。
- **降级兜底**：标了 `special:true` 的「难解析形状」（path 用了 L/Q/C/A 以外命令，slides.ts:368）→ 渲染成 SVG 再转 base64 当**图片**导出（useExport.ts:622-649）。即「能矢量则矢量，实在不行才退化成图」。
- 线条同样走 custGeom（732-756），含箭头端点 `beginArrowType/endArrowType`。

### 3.3 富文本 HTML → pptxgenjs TextProps（`formatHTML` 154-310）
- 核心思路（原注释 152-153）：「将 HTML 按样式分片平铺，每片继承祖先样式，遇块级元素换行」。
- HTML 经 `toAST` 解析后递归下沉样式：块级标签（div/li/p）在前一分片打 `breakLine`（163-169）；`strong→bold`、`em→italic`、`sup/sub→superscript/subscript`、`a→hyperlink`、`ul/ol/li→bullet`（206-301）。
- **细节保真点**：字号 `parseInt(font-size)/ratioPx2Pt`（248）；`background-color→highlight`（254）；下划线/删除线两种写法都覆盖（256-277）；列表 `bullet` 缩进 = 字号 ×1.25（289-294）。
- **渐变文字降级**（181-196）：HTML 里 `linear-gradient` 文字→取所有色标 RGB **求平均色**当纯色（pptx 文本不支持渐变字），并跳过 `background-clip/-webkit-background-clip/color:transparent`。
- ⚠️ 默认兜底字体写死 `'微软雅黑'`（554, 698, 890）。

### 3.4 其余元素映射要点
- **图片**（579-620）：base64 走 `data`、URL 走 `path`；裁剪 `clip` 反推原图尺寸再算 `sizing:{type:'crop'}`（600-616，数学较绕）；椭圆裁剪用 `rounding:true`。
- **图表**（758-848）：映射到 pptxgenjs 原生 ChartType（**非图片**，可编辑）；主题色补齐逻辑——给 1 色用 `tinycolor.analogous(10)` 生成近似色系（771），bar/column 通过 `barDir:'col'/'bar'` 区分，环形图 `holeSize:60`。
- **表格**（851-937）：先扫一遍算出被合并的「隐藏格」坐标集 `hiddenCells`（852-864）跳过不输出；主题行列（rowHeader/colFooter 等）+ 斑马纹（`getTableSubThemeColor`）映射 `fill`。
- **公式 latex**（940-963）：渲染成 SVG → base64 图片（公式无原生对应，只能图片化）。
- **阴影**（`getShadowOption` 367-423）：把 h/v 偏移换算成 pptx 的 `offset`+`angle`（八方向分段判断）。
- **音视频**（965-985）：按扩展名白名单（avi/mp4/mov… mp3/wav…）才 `addMedia`。

### 3.5 「95%+」的真实含义（务必清醒）
- 这是**导出**还原度（PPTist→PPTX）；README 另注**导入**（PPTX→PPTist，靠 pptxtojson）只有 **80%+**（README_zh.md:61-62）。
- 作者明示丢失项（README_zh.md:40-41）：动画、特殊图表、多层嵌套、非标准元素、部分高级样式；「无法 100% 还原，对像素级要求极高需自行评估」。
- **不丢的关键**：正因为形状/图表/文本/表格走原生对象而非整页截图，导出件**进 PowerPoint 后可继续编辑**——这恰是我们要的，而非「保真截图」。

---

## ④ 能借什么（按可迁移度排序）

1. **【方法论·高】「内部数据结构 vs 喂 AI 的收窄 schema」二分**：PPTist 把 `src/types/slides.ts`（806 行完整内部模型）和 `doc/AI_PPT_SCHEMA.md`（759 行 AI 专用收窄子集）**刻意分开**。我们的 deck schema 也应分两层：制作层 python-pptx 全量模型 ⊃ AI 生成层精简白名单。
2. **【方法论·高】导出映射「能矢量则矢量、不行才图片」的降级阶梯**：custGeom 优先 → special 形状/公式/渐变字退化为图片/近似色。我们 python-pptx 侧做 waterfall/Mekko/Gantt 时同理——优先 `MSO_SHAPE`/freeform 矢量，极端图形才退 image。
3. **【数据结构·中】共享样式子结构复用**：`outline`/`shadow`/`gradient` 三件套全 schema 共享（AI_PPT_SCHEMA.md:38-92）。我们 schema 同样该抽公共样式块。
4. **【数据结构·中】矩形包围盒 + 旋转中心 + 「未旋转前」语义**（AI_PPT_SCHEMA.md:32-37）：坐标契约写法可直接借鉴进我们的 prompt 契约。
5. **【提示工程·中】把渲染器隐性规则显式写进文档喂模型**（内边距 10px、段间距 5px、坐标系）——让 AI 自算布局而非事后纠偏。
6. **【交互逻辑·中】`useAIPPT.ts` 的模板自适应**（538 行，下方专列）：字号自动收缩 + 内容项溢出自动拆页，是「轻量数据套固定模板」流派的成熟实现，若我们做模板式 fallback 可参考。
7. **【参考·低】单位换算常量**：px↔inch/pt 的 96/72 换算系数（useExport.ts:31-36）可作我们 EMU 换算的对照。

### ④补：`useAIPPT.ts` 模板填充的两个聪明点（src/hooks/useAIPPT.ts）
- **`getAdaptedFontsize`（71-111）**：用 `canvas.measureText` 离屏测宽，从原字号往下逐档缩（>22px 步进2、≤22 步进1，下限 10px），直到文本在框内不超 `maxLine` 行。解决「AI 文案长短不一撑爆模板框」。
- **内容项溢出自动拆页（251-304）**：`content` 项 5~6 个拆 3+3、7~8 拆 4+4、9~10 拆 3+3+3… 用 `offset` 续编号；`contents` 目录 >11 项同理。即模板只需做几个标准项数，程序自动拼裁。
- **图文匹配**（189-231）：按元素宽高比从图池筛同比例图，再算裁剪 `range` 居中裁。

---

## ⑤ 对 PPT Engine 的落点（schema 设计 / 导出保真）

### 5.1 Schema 设计落点
- **分层定 schema**：① 制作层＝python-pptx 能力全集；② AI 生成层＝**白名单收窄子集**（正面枚举允许的元素/样式/字体，措辞「严禁列外」）。直接抄 PPTist 这套「双 schema」骨架，但内容换成我们的高 stakes 段（waterfall/Mekko/Gantt 专用元素）。
- **坐标契约**：PPTist 用 1000×562.5 逻辑 px。我们若也让 AI 出逻辑坐标，需定清楚逻辑单位→EMU 的换算锚（PPTist 锚 960，我们按 python-pptx 的 `Emu/Inches/Pt` 定）。
- **富文本策略存疑点 ⚠️**：PPTist 富文本走 HTML 字符串 + ProseMirror，契合 Web；**python-pptx 是 run/paragraph 模型**，HTML 串不能直接喂。落地时 AI 生成层的「文本」字段应改成 **run 数组**（`[{text, bold, color, size}]`）而非 HTML——这是与 PPTist 的关键分叉，不可照搬。
- **图片字段抄 `description` 设计**：让 AI 必填图片语义描述、src 留占位，配图走独立检索/生成管线（AI_PPT_SCHEMA.md:279-280）。

### 5.2 导出保真落点
- **核心可迁移结论**：PPTist 证明了「**形状用自定义几何矢量、图表用原生图表对象**」能同时拿到「高保真 + 可编辑」。我们 python-pptx 侧本就原生输出可编辑对象，**方向一致、且我们起点更高**（不必像它那样在浏览器里靠 pptxgenjs 绕路）。
- **降级阶梯照搬**：矢量优先 → 复杂图形退化 image 的兜底思想，用于我们做不出的极端图元。
- **「95%」当心理锚**：作者对自家导出只敢称 95%+、导入 80%+，且**逐条列丢失项**。这种 fail-closed 的诚实披露，正合我们「防假绿」纪律——我们的保真度声明也该附「已知丢失清单」，而非拍胸脯 100%。
- **不可复用的部分**：`useExport.ts` 全部代码是 TS + pptxgenjs + 浏览器 DOM/Vue 渲染（如 `createVNode`/`render` 把形状渲成 SVG，useExport.ts:624-630），与 python-pptx 栈零交集，**只偷映射逻辑与降级策略，不偷代码**。

---

## ⑥ ⚠️ AGPL License + 坑

### 6.1 License（致命，必须重视）
- **AGPL-3.0**（LICENSE:1 `GNU AFFERO GENERAL PUBLIC LICENSE`，README_zh.md:206）。AGPL 的传染性比 GPL 更强：
  - **网络服务也触发开源义务**（README_zh.md:244）：哪怕只把代码做成网站/网络服务，别人通过网络访问，你也必须**完整公开你最终的全部代码并继续以 AGPL 开源**。对「想做 SaaS deck 服务」是核弹级约束。
  - 必须保留原作者版权声明、不能换协议、不能加额外限制（README_zh.md:243-246）。
- **商用须独立授权**（README_zh.md:209-238）：作者卖独立商业授权，一年 2999 元 / 永久 5699 元（不含税）；或成为重要贡献者豁免。
- **✅ 对我们的结论（关键风控）**：
  - 我们是 **python-pptx 全新栈 + 从头写**，**不引用、不 import、不 copy-paste PPTist 任何代码/代码片段** → 不构成 AGPL 衍生作品，**不被传染**。
  - **可以借鉴的安全区**：架构思想、schema 设计哲学、导出映射方法论、字段命名灵感——**思想与方法不受版权约束**，照搬「设计模式」合法。
  - **绝对红线**：禁止把 `useExport.ts`/`useAIPPT.ts`/`AI_PPT_SCHEMA.md` 的**代码或文档原文**搬进我们仓库。schema 字段名可作灵感，但表述要自己重写。
  - 本拆解笔记仅作**内部研究**，不分发、不入产物——合规。

### 6.2 实现坑（若未来真要看它跑 / 借鉴细节）
- **纯前端导出的隐患**：pptxgenjs 在浏览器内 `writeFile`，大 deck（图多）易内存/性能瓶颈；外链图片导出靠 `path` 直传 URL（useExport.ts:587），离线/防盗链会断图。
- **字体地狱**：导出把字体名直写进 pptx（如 `SourceHanSans`），**目标机器没装该字体则回退**——AI_PPT_SCHEMA 的 16 款白名单字体多为开源中文字体，PowerPoint 端大概率缺失。我们 python-pptx 侧同样要面对「字体嵌入 vs 回退」问题。
- **导入≠导出对称**：导入用 pptxtojson（80%）、导出用 pptxgenjs（95%），**两套独立库**，round-trip（导入再导出）会叠加双重损耗，非无损。
- **公式/特殊形状图片化**：latex 和 special 形状导出即变图片（useExport.ts:622-649, 940-963），**失去可编辑性**——这部分 PPTist 自己也没解决，是其保真天花板。
- **「special 形状」判定依赖标记**：是否退化为图片取决于元素上 `special:true` 标记（slides.ts:368）是否正确打上，导入端判定不准会误伤。
- ⚠️ **未验证项（诚实标注）**：本次为静态读码，**未实际 npm install 跑起来、未实测导出 pptx 在真 PowerPoint 中打开的保真效果**；「95%+/80%+」均为作者 README 自述数字，非本人复现。如需硬结论须实跑 round-trip 测试。

---

## 关键文件索引（出处锚点）

| 维度 | 文件 | 要点 |
|---|---|---|
| AI 收窄 schema | `doc/AI_PPT_SCHEMA.md`（759行） | 非模板式·AI 直出整页·白名单富文本 |
| AI 模板式结构 | `src/types/AIPPT.ts`（41行）·`public/mocks/AIPPT.json` | 五种页·极简语义数据 |
| 模板式原理 | `doc/AIPPT.md` | 标注→匹配→配图→出片 |
| 完整内部数据模型 | `src/types/slides.ts`（806行） | 九类元素全量定义·TextType/ImageType 标记 |
| ★导出引擎 | `src/hooks/useExport.ts`（1005行） | px→inch/pt 换算·custGeom·formatHTML·降级 |
| ★path 降解 | `src/utils/svgPathParser.ts` | A_TO_C/QT_TO_C → 只剩 M/L/C/Z |
| 模板自适应填充 | `src/hooks/useAIPPT.ts`（538行） | 字号自动缩·溢出自动拆页 |
| 导入 | `src/hooks/useImport.ts`（1346行）+ `pptxtojson@2.0.6` | 80% 还原 |
| License | `LICENSE`·README_zh.md:205-249 | AGPL-3.0·网络服务也传染 |
| 画布原理 | `doc/Canvas.md`·`doc/DirectoryAndData.md` | 1000×562.5 逻辑画布·缩放渲染 |
