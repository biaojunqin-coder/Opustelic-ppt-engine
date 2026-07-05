---
status: progress
type: 开源拆解
target: Instrumenta Powerpoint Toolbar (iappyx)
repo: https://github.com/iappyx/Instrumenta
license: MIT
star: ~400（用户口径，仓库本身不含 star 数据，以 GitHub 为准）
本地路径: 04_制作明珠/Instrumenta
版本: v1.71（git HEAD: ceb9d4b "Improved Mac compatibility and security improvements"）
拆解日期: 2026-06-30
拆解人: Claude (Opus 4.8)
和我们的相似度: ★★★☆☆（技术栈完全不同——VBA 加载项 vs 我们 python-pptx；但"咨询级版式纪律的工具化"这件事高度对口，算法可直接移植）
---

# Instrumenta Powerpoint Toolbar 深度拆解

> 一句话：**它是一个前麦肯锡顾问用 VBA 复刻"咨询公司内部专有 PPT 插件"的开源版（MIT，270+ 功能），把顾问手工调版式的肌肉记忆——对齐 / 等距分布 / 同尺寸 / 对齐到表格 / 38 项质检自动修——全部固化成可一键执行的宏。最值得偷的不是它做了什么功能，而是它怎么把"版式纪律"变成可计算的几何算法 + 可配置的 fail-closed 质检引擎。**

保真说明：以下结论全部来自本地仓库实读（v1.71），关键处带文件:行号出处。star≈400 是用户口径，仓库不含 star 数据。技术栈是 **PowerPoint VBA（.bas / .frm / .cls）**，不是 Python，但算法是语言无关的，本笔记重点抽可移植到 python-pptx 的逻辑。

---

## ① 是什么 + 定位

- **一句定义**（README:5-7）：作者在战略咨询干了 10 年，习惯了咨询公司的专有 PPT 加载项；进"业界"后找不到免费开源替代，于是 COVID 期间业余时间写了 Instrumenta——"a free and open source consulting powerpoint toolbar"。
- **目标用户**：做咨询级 / 投资人 deck 的人，需要把一堆框 / 文本 / 表格调得**像素级整齐**。不是给做生日贺卡 PPT 的人用的。
- **形态**：Office Ribbon 上的一条工具栏。**全部代码在 PowerPoint VBA 里跑**（.bas 文件是 build 后导出的，仅供参考；真正源在 `InstrumentaPowerpointToolbar.pptm`，存成 .ppam 即成品加载项）。Ribbon 用 office-ribbonx-editor 配（CustomUI.xml）。
- **跨平台**：Win 全功能 / Mac 大部分能跑（README:31-39）。Mac 的坑：部分图标缺失、shape 锁定不支持、导出邮件 / Word 需装 AppleScript 插件绕 sandbox。
- **功能量级**：270+ 功能，分 9 组（README:18-29）——Generic / Text / Shapes / Pictures / **Align-distribute-size** / Table / Export / Paste-insert / Advanced。
- **关键边界（和我们的根本不同）**：
  - 它是 **VBA 加载项**，运行在装好 PowerPoint 的人手里、对**手工打开的 deck 做交互式操作**；我们是 **python-pptx 在服务端从 0 生成 deck**。
  - 它**不生成内容**——它是给已有 deck 做"精装修"的电动工具；选中→点按钮→调整。我们是"盖楼"。
  - 但**两者的目标审美完全一致**：咨询级排版纪律。所以它的几何算法、它对"什么叫不整齐"的定义，是我们制作层可以直接搬的。

---

## ② 对齐 / 批量格式化怎么实现（★ 本次最核心的料）

### 2.1 地基：旋转感知的"真实包围盒"几何层（GetReal* / SetReal*）

这是**整个工具栏的承重墙、也是最该偷的一件事**。源在 `ModuleObjects.bas`，注释明确写了是贡献者 o485 写的（ModuleObjects.bas:24-32）。

**问题**：PowerPoint 原生的 `shape.Left / .Top / .Width / .Height` 返回的是**未旋转坐标系下的框**。一个旋转了 30° 的形状，它视觉上占的矩形（屏幕上你看到的外接框）和这四个属性完全对不上。原生"对齐"按钮对旋转形状会align错。

**解法**：定义一套 `GetRealTop / GetRealLeft / GetRealWidth / GetRealHeight`，算的是**旋转后视觉外接矩形（axis-aligned bounding box）**：
```
' ModuleObjects.bas:70-85（GetRealWidth 节选）
Case 0, 180:  GetRealWidth = SlideShape.Width
Case 90, 270: GetRealWidth = SlideShape.Height          ' 90/270 度宽高互换
Case Else:    GetRealWidth = W*Abs(Cos(θ)) + H*Abs(Sin(θ))   ' 任意角：投影公式
```
- 标准的"旋转矩形的 AABB"公式：`realW = |w·cosθ| + |h·sinθ|`，`realH = |w·sinθ| + |h·cosθ|`；center 不变，由 center 反推 realTop/realLeft（ModuleObjects.bas:33-102）。
- 反向写入 `SetRealWidth / SetRealHeight` 更精妙：要把"视觉宽"设成某值，得先解出底层 `.Width`。对 0/90/180/270 特判（避免浮点误差），任意角则用 aspectRatio 联立解方程（ModuleObjects.bas:124-184）：
  ```
  .Width = newRealWidth / (|cosθ| + |sinθ|/aspectRatio)
  .Height = .Width / aspectRatio
  ```
- **`SetRealLeft/Top` 用 offset 平移法**（先 GetReal 算当前真实位置，求差，平移底层 `.Left`），优雅地回避了"已知 AABB 反解 center"的麻烦（ModuleObjects.bas:104-122）。

> **为什么这是最该偷的**：所有上层对齐 / 分布 / 同尺寸 / 去间距函数，**没有一个直接碰 `.Left/.Width`，全走 GetReal*/SetReal***。这意味着整个工具栏对"被旋转过的形状"天然正确——而这正是 PowerPoint 原生对齐、以及绝大多数通用 agent / 大厂 skill 做不对的地方。这是"咨询级"和"差不多得了"的分水岭。

### 2.2 对齐（Align）的三档锚点策略 + 子形状递归

`ModuleObjectsAlignAndDistribute.bas` 里 6 个 Align 子过程（Lefts/Tops/Rights/Bottoms/Centers/Middles），每个都不是简单调原生 `.Align`，而是引入了**"对齐到谁"的可配置策略**（读注册表 `DefaultAlignmentMethod`，AlignAndDistribute.bas:874-906）：
- `0` = 原生行为（对齐到选区包围盒边）。
- `1` = 对齐到**第一个**形状的边（Left1 = 选区第 1 个形状的 GetRealLeft）。
- `2` = 对齐到**最后一个**形状的边。

这解决了顾问的真实痛点：原生"左对齐"是对齐到最左那个，但顾问往往想"全部对齐到我先选的那个基准框"。三档可配。

另外每个 Align 都处理了 **`HasChildShapeRange`**（用户在 group 内部多选子形状的情况），对子选区单独走一遍同样逻辑（AlignAndDistribute.bas:866-885）——这种对 group 内部编辑的细致照顾，是成熟工具和玩具的区别。

### 2.3 排序原语：上层算法全部先排序再操作

所有"按空间关系处理"的函数都先把选区灌进数组排序。提供了一整套（AlignAndDistribute.bas:698-856）：
- `ObjectsSortByLeftPosition / Right / Top / Bottom`：冒泡排序，键是 GetReal* 真实坐标。
- `QuicksortTopLeftToBottomRight`：双键快排（先 Top 后 Left），把任意散布的形状排成"阅读顺序"（AlignAndDistribute.bas:777-806）。
- **回写技巧**：排完序的数组，靠形状 `.Name` 重建一个 ShapeRange（`SlideRange.Shapes.Range(NamesArray)`），再调原生批量操作（AlignAndDistribute.bas:764-773）——绕开了 VBA 里 ShapeRange 不可直接重排的限制。

### 2.4 "等距+等尺寸"一步到位（ResizeAndSpaceEvenly）

这是**比 PowerPoint 原生"分布"更强的一招**（AlignAndDistribute.bas:60-211）：原生"水平分布"只挪位置、不改尺寸，形状本身大小不齐照样难看。Instrumenta 的做法是**让用户输入想要的固定间距（pt），然后反解出每个形状应有的统一宽度**，使它们既等宽又等距：
```
ShapeSize = (totalWidth - (N-1)*spacing) / N     ' 总宽减掉所有间距，平摊给 N 个形状
```
还有 `PreserveFirst / PreserveLast` 变体（第一个 / 最后一个尺寸不动，只把增量分给其余），用线性方程重算（AlignAndDistribute.bas:108-149）。

### 2.5 拉伸到对齐（Stretch）—— 顾问的"补齐到一条线"

8 个 Stretch 子过程（AlignAndDistribute.bas:214-466）：StretchTop/Left/Bottom/Right + 4 个 "ShapeEdge" 变体。逻辑是把一组形状的某条边**拉到基准线**（同时改尺寸而非平移），让一排框的顶边 / 底边严丝合缝对齐成一条直线。这是顾问做"卡片墙"时手工最费时的活。

### 2.6 ArrangeShapes —— 自动识别行列网格

`ArrangeShapes`（AlignAndDistribute.bas:1258-1408）是个聪明的启发式：
1. 先按"水平投影是否重叠"把形状聚成**列簇**（两形状 X 区间相交 → 同列，AlignAndDistribute.bas:1291-1292），列内居中对齐 + 成组。
2. 列簇之间水平等距分布。
3. ungroup 后，再按"垂直投影是否重叠"聚成**行簇**，行内居中 + 行间垂直等距分布。
一次点击把一堆乱摆的框**自动归整成对齐的网格**。这是"批量格式化"最有含金量的一个。

### 2.7 对齐到表格（AlignToTable）—— 把浮动框吸附进表格网格

`ModuleObjecstAlignToTable.bas`（整文件 335 行）：选中"一张表 + 若干浮动形状"，自动把每个形状**吸附到它中心落在的那个单元格的中心**：
- 先在多选里**按面积找出最大的那个表**当锚（AlignToTable.bas:38-48）。
- 累加行高 / 列宽，算出每行每列的边界数组 `TableRows()/TableCols()` 和中心数组 `TableXCenter()/TableYCenter()`（AlignToTable.bas:81-91）。
- 对每个浮动形状，算其中心点落在哪个 [行边界, 列边界] 区间，移到对应单元格中心（AlignToTable.bas:93-116）。
这招让"在表格上叠 Harvey Ball / 红绿灯图标"这种咨询常见排版变得一键完成。

### 2.8 复制 / 克隆位置（CopyPosition / Clone）

- `CopyPosition / PastePosition / PastePositionAndDimensions`（ModuleCopyPosition.bas，整文件 79 行）：把一个形状的 Top/Left/Width/Height 记到模块级变量，粘到另一个形状上——"把这个框做得跟那个一样大、放一样位置"。**注意：这里直接用 `.Top/.Left` 原生坐标，没走 GetReal***，是个小不一致（对旋转形状会不准）。
- `ObjectsCloneRight / CloneDown`（ModuleObjectsClone.bas，110 行）：复制并**精确贴着原形状右侧 / 下方**摆放（`.Left = OldLeft + Width`），多选时先 Group 再复制再 Ungroup 保持相对关系。等价于"按住 Ctrl 拖拽复制"但像素精确、可重复。

---

## ③ 能借什么（可复用的排版 / 对齐算法）

**纯算法、语言无关、可直接移植到 python-pptx 的清单：**

| 算法 | 出处 | 移植价值 |
|---|---|---|
| **旋转 AABB 正反算**（GetReal*/SetReal*） | ModuleObjects.bas:33-184 | ★★★★★ 制作层任何"对齐 / 测距 / 碰撞"都该先过这层。python-pptx 的 `shape.rotation` 同样只给原始框，这套公式照搬即可。 |
| **三档对齐锚点**（包围盒 / 首 / 尾） | AlignAndDistribute.bas:874-906 | ★★★★ "对齐到基准框"是顾问真实需求，比单一对齐模式专业。 |
| **等距+等宽反解**（ResizeAndSpaceEvenly） | AlignAndDistribute.bas:93-211 | ★★★★ `size=(total-(N-1)*gap)/N` 一行公式，生成"卡片排"必备。 |
| **网格自动归整**（ArrangeShapes 的投影聚簇） | AlignAndDistribute.bas:1283-1408 | ★★★★ "X 区间相交→同列 / Y 区间相交→同行"的聚簇启发式，可做"把生成的散框自动排成矩阵"。 |
| **吸附到表格单元格中心** | AlignToTable.bas:81-116 | ★★★ 做"表格上叠图标 / 评分"版式时直接用。 |
| **双键快排成阅读顺序**（Top→Left） | AlignAndDistribute.bas:777-806 | ★★★ 任何"按视觉顺序遍历形状"都要它（如自动编号、storyline 抽取）。 |
| **BBox 重叠检测 / 共边检测** | SlideGrader.bas:1461-1484 | ★★★ `ShapeSharesEdge`（容差 3pt 判是否与任意形状对齐）和 `BBoxOverlap`，是质检和"吸附辅助线"的基础。 |
| **单位换算**（in/cm/mm/pt ↔ pt，72 DPI） | ModuleFunctions.bas:58-101 | ★★ python-pptx 用 EMU，但"对用户显示用 cm/in、内部用 pt"的换算表 + 小数分隔符本地化思路可借。 |

**④ 之外，真正最该偷的一件——见 ④。**

---

## ④ 对 PPT Engine 落点（制作层版式纪律可借什么）★

### 4.1 头号收获：把"版式纪律"做成 fail-closed 质检引擎（Slide Grader）

`ModuleSlideGrader.bas`（整文件 1601 行）是**整个仓库对我们最有战略价值的部分**——它不是工具，是一套**自动质量门**，和我们"七铁律 / fail-closed 质量门 / 防假绿"的世界观直接同构。结构（SlideGrader.bas:37-88 的 `GraderCheckConfig` + 26-35 的 `SlideIssue`）：

- **38 项检查，分 6 大类**，每类一个字母前缀：
  - **T 标题（6 项）**：缺标题、非 action-title（**专门查"标题里有没有洞察动词"**，内置 ~120 个动词表 SlideGrader.bas:1324-1356）、标题字号 / 字体跟全 deck 众数不一致、标题以句号结尾、重复 / 近似重复标题（**用 Levenshtein 距离 ≤2 判近似** SlideGrader.bas:1437-1459）。
  - **Q 文本质量（8 项）**：双空格、首尾空格、占位符残留（lorem ipsum/[TODO]/[TBD]/click to add…）、空文本框、超字数、项目符号标点不一致（有的句号有的没有）、删除线、双标点。
  - **F 排版（7 项）**：字体家族数超限（默认 ≤2）、字号种类超限（默认 ≤4）、字号过小（<10pt）、下划线、正文全大写、正文颜色偏离 deck 标准、**隐形文字（文字色≈背景色，RGB 欧氏距离<30）**。
  - **L 版式（8 项）**：文字溢出框（比较 `BoundHeight` vs 内部可用高）、超出 slide 边界、形状重叠、隐形形状（无填充无线无字）、旋转文本框、形状过多（>20）、无内容、**孤立漂浮**（不与任何其他形状共边 = 没对齐到任何东西）。
  - **C 颜色（4 项）**：单页色数超限（>5）、同尺寸形状填充色不一致、accent 不一致、文字 / 背景低对比（RGB 距离<80）。
  - **D 表格 / deck（4 项）**：表头行与正文行不可区分、半满表格有空格、隐藏页、备注里有 draft 标记（TODO/TBC/DRAFT）。

- **三级严重度**：`Error / Warning / Info`（SlideGrader.bas 各 AddIssue 调用），对应红 / 黄 / 灰——和我们的状态色阶完全可对齐。

- **基线驱动 = 不靠绝对阈值，靠"全 deck 众数"**：`ComputeBaselines`（SlideGrader.bas:217-286）先扫一遍全 deck，**按 CustomLayout 分组**统计标题字号 / 字体 / 正文色的众数，再逐页比对偏离。这是"一致性"质检的正确姿势——不是规定"标题必须 28pt"，而是"你这页跟你自己其余页不一样"。`GetModeSingleForLayout`（SlideGrader.bas:1519-1551）按版式取众数。

- **★★★ fail-closed 的精髓：检查 ≠ 自动修，自动修是白名单**：
  - 38 项里**只有 9 项**有 `fixKey`（T5/Q1/Q2/Q4/Q7/Q8/F4/L5/D3，见 `FixIssue` 的 dispatcher SlideGrader.bas:1061-1071）。
  - `CanFix()`（SlideGrader.bas:1051-1053）= `Len(fixKey)>0 And Not IsFixed`——**没 fixKey 的问题（如"标题缺洞察动词""色数过多""低对比"）一律不允许自动修，只报警等人改**。
  - 这正是我们"防假绿"纪律的镜像：**机器只敢自动处理"机械确定无歧义"的（去双空格、删删除线、去句号），凡涉及判断 / 设计取舍的，只标问题、绝不替人拍板**。

> **落点结论**：我们制作层 / 自省层应该长一个"PPT Linter"——把这 38 项（尤其 action-title 动词检、隐形文字、孤立漂浮、同尺寸异色、deck 内一致性众数检）作为**生成后的 fail-closed 出关闸**。可直接对照 `conformance.json` 思路：每项 = 一条规则，分 Error（阻断）/ Warning / Info，且**自动修严格白名单制**。这一条几乎是把"咨询级版式纪律"翻译成可执行规则的现成蓝本。

### 4.2 二号收获：内置 DSL（Instrumenta Script）—— 批量格式化的"声明式"形态

`SCRIPT.md`（23KB）定义了一个小脚本语言（Modules: InstrumentaScript_Main/Cond/Expr/Set/Str）：
```
SELECT WHERE type = TEXTBOX
SET font.bold = TRUE
SELECT ALL
SET font.size = 12
```
有 `SELECT WHERE`（按 name/type/尺寸过滤）、`SET`（批量改属性）、`ROTATE`、`GROUP`、条件、表达式。**对我们的启发**：制作层若要让用户 / agent 批量微调，与其暴露一堆零散 API，不如设计一个"选择器 + 属性赋值"的声明式层——这正是 python-pptx 之上可以加的薄 DSL。

### 4.3 三号收获：成熟工具的工程细节（值得照抄的"专业感"来源）

- **进度反馈**：`ProgressForm` + `SetProgress`（ModuleFunctions.bas:132-145）批量操作显进度条 + DoEvents，避免假死。
- **群组内编辑**：处处判 `HasChildShapeRange`，对 group 内部多选同样生效。
- **样式表概念**：Master stylesheets（H1–H3 / Paragraph / Quote + 5 个自定义样式，README:22），`ModuleMaster.bas` 还能把形状推到所有 / 仅被使用的 layout master（`onlyUsedLayouts` 判 LayoutIsUsed）——"定义一次样式、全 deck 套用"，和我们模板化思路一致。
- **路径 / 注入防护**：`SanitizeFilename`（去 ../ 和非法字符 ModuleFunctions.bas:266-280）、`SanitizeAppleScriptPath`（转义引号防 AppleScript 注入 ModuleFunctions.bas:301-303）、`UrlEncodeString`——一个桌面插件都做了基本注入防护，我们服务端更不能省。

---

## ⑤ License + 坑

- **License = MIT**（LICENSE，Copyright (c) 2021 iappyx）。各 .bas 文件头部也都带 MIT 声明（2021–2026）。**可自由借鉴 / 改 / 商用，需保留版权声明 + MIT 文本**。README:7 额外礼貌请求：若拿去做自己的工具栏，希望告知并按 MIT 给署名。→ **抄算法落到我们代码里时，在对应文件 / NOTICE 注明出处即可合规**。
- **坑 1 — 技术栈完全不同**：这是 **VBA 加载项（运行在用户 PowerPoint 里、交互式操作活动文档）**，我们是 **python-pptx 服务端生成**。**能搬的是算法和质检规则，不能搬任何运行时 / Office 对象模型代码**。许多操作（如调原生 `.Align`、`.Duplicate`、Ribbon 回调）在 python-pptx 里无对应物，得自己用 EMU 几何重写。
- **坑 2 — 几何一致性有漏网**：核心走 GetReal* 旋转感知，但 `CopyPosition`（CopyPosition.bas:35-38）和 `AlignToTable`（AlignToTable.bas:95-96）等少数处**直接用 `.Top/.Left/.Width`**，对旋转形状会不准。移植时应**统一全部走"真实包围盒"**，把作者的不一致补平。
- **坑 3 — 单位 / 本地化**：内部 pt，对用户显示用 in/cm/mm（ModuleFunctions.bas:58-101），还处理小数分隔符（GetDecimalSeperator 取 `1/2` 的中间字符 ModuleFunctions.bas:52-56，应对欧洲逗号小数）。python-pptx 用 EMU（914400/inch），换算关系不同，别照抄常数。
- **坑 4 — 排序用冒泡 + 靠 .Name 重建 ShapeRange**：冒泡 O(n²) 对单页几十个形状无所谓，但靠形状名重建 Range 的 trick 是 VBA 特有限制的产物（AlignAndDistribute.bas:764-773），python 侧直接操作对象列表即可，不必模仿。
- **坑 5 — Slide Grader 的某些检查依赖 Office 渲染态**：如 `TextFrame.textRange.BoundHeight`（实际渲染高度，用于溢出检测 SlideGrader.bas:770）在 python-pptx 里**拿不到**（python-pptx 不渲染文本）。文字溢出 / autofit 类检查移植难度高，需要估算或借助渲染引擎；纯结构 / 文本 / 颜色类检查（占多数）可直接移植。
- **坑 6 — .pptm/.ppam/.exe/.dmg 不收**：README:45 明说出于安全只接受 /src 下的 .bas/.frm/.cls/.xml 文本贡献，不收二进制成品。我们读源码即可，bin/ 里的 .dmg/.exe/.ppam 别碰别信。

---

## 一句话：最值得偷的 1 件事

**把"咨询级版式纪律"翻译成一套 fail-closed 的 PPT Linter——38 项分级检查（含 action-title 动词检、隐形文字、孤立漂浮、deck 内一致性按版式取众数），且自动修严格走白名单（38 项里只 9 项敢自动改，其余只报警等人拍板）；底层所有几何运算都先过"旋转感知真实包围盒"（realW=|w·cosθ|+|h·sinθ|）这层——这恰是 PPT Engine 制作层 / 自省层最该长出来的两块肌肉。**
