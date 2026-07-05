---
status: progress
type: 开源拆解
target: frontend-slides (zarazhangrui)
repo: https://github.com/zarazhangrui/frontend-slides
license: MIT
star: ~24k（用户给的数，本仓库未含 star 数据，以 GitHub 为准）
本地路径: /Users/qinbiaojuan/Documents/PPT开源参考/01b_待深看skill/frontend-slides
拆解日期: 2026-06-30
拆解人: Claude (Opus 4.8)
和我们的相似度: ★★★★★（同为 Claude Code skill 形态做 deck，最像的一个）
---

# frontend-slides 深度拆解

> 一句话：**它是「纯 Markdown 提示词 + 渐进披露 + fail-closed 规则」组成的 Claude Code skill，把"做 PPT"这件事彻底拆成 prompt 工程问题——没有一行业务运行时框架代码，靠的是一套写得极克制的 SKILL.md 工作流图 + 按需加载的设计系统文档。** 这恰恰是和 PPT Engine 最像、也最该照镜子的对象。

保真说明：以下结论全部来自本地仓库实读，关键处带文件出处（行号以实读为准）。star=24k 是用户口径，仓库本身不含 star 数据。

---

## ① 是什么 + 定位

- **一句定义**（README:3）：「A coding-agent skill for creating stunning HTML presentations — from scratch or by converting PowerPoint files. It is packaged as a Claude Code plugin, and the core `SKILL.md` can also be read by other coding agents.」
- **目标用户**：非设计师。核心卖点是 **"show, don't tell"**——不让用户用语言描述审美，而是**直接生成 3 张可视预览让用户挑**（README:17、SKILL.md Phase 2）。
- **四条哲学**（README:541-551，值得整段抄）：
  1. 你不必是设计师才能做出好东西，你只需要对看到的东西做反应。
  2. **依赖即债务**（Dependencies are debt）——单 HTML 文件 10 年后还能跑，2019 年的 React 项目祝你好运。
  3. **通用 = 被遗忘**（Generic is forgettable）——每个 deck 都该像定制的，不像模板生成的。
  4. **注释是善意**——代码该向未来的人解释自己。
- **它的"高 stakes"取向**：虽然定位通用，但它把 board / legal / regulatory / healthcare / investor-update 单列为"高正式度"分支，专门要求选更克制的模板（bold-template-pack/README.md:39-42）。**这条和我们"收窄高 stakes 段"的纪律撞了个正着。**
- **关键边界（和我们最大的不同）**：它做的是 **HTML 网页 deck（单文件、浏览器跑）**，**不做原生 PPTX、不做 waterfall/Mekko/Gantt 这类咨询图表**。它的"专业感"来自排版/配色/动效的设计品味，不是来自数据图表的硬功夫。

---

## ② 它作为 Claude Skill 怎么组织（★ 本次最核心的料）

### 2.1 形态：纯 Markdown，零运行时框架

- 全仓 163 个文件里 **147 个是 .md**，代码只有 2 个 .py + 2 个 .sh + 2 个 .js + 2 个 .css。**没有任何"引擎"——skill 本体就是一堆提示词文档**。Claude 读 SKILL.md → 按里面的指令现写 HTML。
- 双形态分发（README:32-93）：
  - **Claude Code 插件**：`.claude-plugin/marketplace.json` 定义 marketplace source，`plugins/frontend-slides/.claude-plugin/plugin.json` 是插件本体，命令是 `/frontend-slides:frontend-slides`。
  - **手动 skill**：把 SKILL.md 等几个文件 cp 到 `~/.claude/skills/frontend-slides/`，命令 `/frontend-slides`。
  - **其他 agent**（Codex/Gemini CLI 等）：直接把 GitHub 链接丢给 agent，让它从 SKILL.md 开读。
  - 注意：`plugins/frontend-slides/skills/frontend-slides/` 下是**全套文件的副本**（插件打包用），根目录那份是"裸 skill / 给其他 agent 读"用。**同一套内容维护两份**——这是它为了同时支持"插件"和"裸 skill"付的冗余代价，是个值得注意的坑。

### 2.2 SKILL.md 结构：一张「工作流图」+ NON-NEGOTIABLE 规则带

SKILL.md（381 行）的骨架是**分阶段状态机**，不是流水叙述：

```
Core Principles（5条，含"Fixed 16:9 NON-NEGOTIABLE"）
Design Aesthetics（反 AI-slop 的审美宪法）
Fixed Stage Rules（每页不可违背的不变量）
Content Density Modes（reading deck vs speaking deck 二选一）
Phase 0  Detect Mode（A 新建 / B 转 PPT / C 改稿，含 Mode C 修改规则）
Phase 1  Content Discovery（4 个问题一次性问完）
Phase 2  Style Discovery（"show don't tell" 生成 3 预览）
Phase 3  Generate（按密度 + 选定风格生成全 deck）
Phase 4  PPT Conversion
Phase 5  Delivery
Phase 6  Share & Export（Vercel 部署 / PDF 导出，可选）
Supporting Files（一张表：哪个文件 Phase 几读）
```

**对我们最有借鉴价值的几个结构选择：**

1. **"Phase + 该 Phase 才读哪个文件"做成显式表格**（SKILL.md:367-381、README:521-533）。这就是 **progressive disclosure（渐进披露）**——SKILL.md 只是"地图"，支撑文件按需加载，避免一次性把 12 个 preset + 34 个模板的全部细节塞进上下文。

2. **三级加载粒度（设计文档的金字塔）**——这是它最聪明的工程：
   - **L0 `selection-index.json`**（39KB，含 34 个模板的**压缩元数据**）→ Phase 2 先读这个做候选筛选；
   - **L1 `preview.md`**（每模板一张**轻量风格卡**，~50 行）→ 只读**入围候选**的，用来生成标题页预览；
   - **L2 `design.md`**（每模板一份**完整设计系统**，Signal 那份 529 行）→ **只在用户最终选定后，只读那一个**。
   - 索引里甚至硬编码了这条纪律（selection-index.json `usage.never`）：「Do not bulk-read templates/\*/design.md」。**用 token 预算倒逼加载策略，写进数据文件本身**。

3. **结构化提问（Phase 1）**：4 个问题（Purpose / Length / Content / Density）**一次性全问**，每个带 header + 枚举选项，"if native structured-question UI exists, use it"（SKILL.md:91）。明确**不在出草稿前问用户要不要 inline 编辑**——编辑是草稿后的事，默认带上（SKILL.md:108）。这是很成熟的"别让用户提前做他还没法做的决定"。

### 2.3 有没有质检？有——而且是 fail-closed 思路，但靠"Claude 自验"不靠程序

它**没有独立的校验程序/打分器**（这点和我们的 conformance.json + 自省机不同），但在提示词里埋了多道**强制门**，全用 NON-NEGOTIABLE / NEVER 措辞：

- **Fixed-Stage 不变量**（SKILL.md:38-52）：每页必须 1920×1080 整体缩放，**禁止用响应式断点 reflow**，禁止用 `display:none/block` 切页（会被后面的 `display:flex` 覆盖导致全部页同时可见——这是踩过的坑写成的硬规则），`prefers-reduced-motion` 必须支持，绝不直接对 CSS 函数取负（`-clamp()` 静默失效，必须 `calc(-1 * clamp())`）。
- **Preview Authenticity Rules（NON-NEGOTIABLE）**（SKILL.md:180-188、bold-template-pack/README.md:59-61）：预览页**绝不能**渲染任何内部流程文本——不许出现 `preview`/`template`/`preset`/`Option A/B/C`/文件名/路径/"safe option"/"audience: ..."。**只能用真实 deck 内容当 chrome**。"Before opening previews, inspect the visible text and revise if any internal metadata appears"——**生成后自检再开**。这是把"防止把脚手架/内部标签泄漏到产物里"做成了硬门。
- **生成后双重验证**（SKILL.md:226、bold-template-pack/README.md:77）：「verify both content overflow and panel overlap in rendered browser screenshots. `scrollHeight` checks alone are not enough because grid panels can visually cover each other.」——**明确指出"只查 scrollHeight 不够，网格面板会视觉互相遮盖"**，要求真截图看。
- **Mode C 改稿门**（SKILL.md:76-86）：加内容前先数现有元素对照密度上限；加图前先确认现有内容是否已占满；改完必须在 1280×720 + 一个手机视口截图核对。

**判断**：它的"防假绿"是**靠 Claude 在提示词约束下自验 + 真截图**，没有"自动判定不许当真"的元层纪律。**我们比它强的恰恰在这里**——我们有 conformance.json 硬数据 + "自省最高只给 🟡、🟢必须人工自测" 的元铁律。它给我们的反向印证是：**提示词里把"内部标签别泄漏到产物""只查高度不够要查遮挡"这种具体反模式写死，非常有效**。

---

## ③ 它做 deck 的方法（HTML / 叙事）

### 3.1 技术路线：单文件 HTML，CSS/JS 全内联，零依赖

- 产物 = **一个自包含 .html**，所有 CSS/JS inline，图片放 `assets/`（html-template.md:338-350）。无 npm、无构建、无框架。
- **固定舞台模型（贯穿全局的"承重墙"）**：每页在 1920×1080 画布上排版，靠一段 JS（html-template.md:114-123 / `deck-stage.js`）算 `Math.min(w/1920, h/1080)` 整体 `transform: scale()`，**letterbox/pillarbox 而非 reflow**。手机上也保持 16:9。`viewport-base.css` 是强制基座，要求**整段复制进每个产物**。
- **切页机制**：`.active`/`.visible` 控 `visibility/opacity/pointer-events`，**显式禁止 `display` 切换**（viewport-base.css:40-59，SKILL.md:47 给了为什么）。
- **inline 编辑**（html-template.md:177-256）：草稿后默认带；用 JS hover + 400ms 延时，**明确警告别用 CSS `~` 兄弟选择器**（`pointer-events:none` 会断 hover 链——又一条踩坑写成的规则）。

### 3.2 叙事/内容怎么处理：靠"密度模式"+"按 purpose 选风格"，没有真正的叙事引擎

- **没有"叙事结构生成器"**（这点要看清，别高估）。它处理叙事靠两个旋钮：
  1. **Content Density Mode**（SKILL.md:55-63）：开场就问"这是**演讲 deck（low density/speaker-led）**还是**阅读 deck（high density/reading-first）**"，然后用它驱动**页数、字号、每页字数、布局密度**。low → 一页一个想法、大字、留白、最多 1-3 条要点；high → 自包含页、结构化网格/表格、4-8 条要点。**超了就拆页，绝不压字号到拥挤**（SKILL.md:63、215）。
  2. **Purpose → Mood → 风格**（SKILL.md:146-151）：Pitch/Teaching/Conference/Internal 映射到 mood，mood 映射到推荐 preset。
- **图文协同设计**（SKILL.md:120-126）：如果用户给了图，要求**"不是先排页再塞图，而是从一开始就围绕图+文一起设计大纲"**（3 张截图→3 个功能页，1 个 logo→标题/结尾页），且 logo 要 base64 嵌进 3 张预览让用户看到自己品牌的三种样子。
- **PPT 转换**（Phase 4 + extract-pptx.py）：用 python-pptx 抽**标题/正文/图片/演讲者备注**，图存 assets/，备注转成 HTML 注释保留。抽完先给用户确认再进 Phase 2 选风格。脚本只 96 行，**纯抽取无重排**——重排交给 Claude 按选定风格重做。

### 3.3 "设计系统即可执行配方" —— design.md 的粒度（强烈建议照抄这套写法）

34 个 bold 模板每个一份 `design.md`，**写得像给设计师的 brand book，但精确到可被 LLM 直接执行**。以 Signal（design.md，529 行）为例，它的结构：

- **YAML frontmatter**：完整 `colors`（13 色带十六进制）、`color-aliases`（语义别名映射）、`typography`（13 个 token，每个含 fontFamily/Size/Weight/lineHeight/letterSpacing/textTransform）、`spacing`、`components`（约 20 个组件，每个给 border/padding/background/description）。**整套设计 token 化**。
- **正文**：Overview（视觉论点："The Economist 的克制 × 私人情报简报"）、逐色用途说明、Type Scale 表、**Signature Treatments（非可选的招牌动作）**、Do's/Don'ts（各 ~10 条具体到"别在 body 用 gold""别用纯白 #FFFFFF"）、Responsive、**CJK & International（极详尽——含中文配对、"思源黑体替代""斜体金色强调在中文里降级为纯色金"这种 glyph 级处理）**、Iteration Guide、Known Gaps（诚实列出局限）。
- **关键工程点**：design.md 里写的是源模板的 viewport-fluid 值（vw/vh/clamp），但每份开头都有一段 **"Frontend Slides Fixed-Stage Policy"**（Signal design.md:197-205）：明确"**这段策略优先级高于本文件后面任何响应式描述**，把 vw/vh 当设计比例翻译成 1920×1080 坐标，不要当作活的响应式规则"。**用"策略覆盖"的写法解决了"复用外部模板库但要改造成固定舞台"的冲突**——非常干净。

---

## ④ 对 PPT Engine 的落点（最该带走的）

### 4.1 skill 组织形态：可直接照搬的 3 件事

1. **【最值得偷】三级渐进披露 + 把加载纪律写进数据本身**。
   我们做咨询级 deck，图表手法（waterfall/Mekko/Gantt/…）会越来越多，**完全可以复制它的 L0 索引 / L1 卡片 / L2 全配方 三级结构**：
   - L0：一个 `chart-index.json`，每种图表手法压缩元数据（适用场景/数据形态/stakes 等级/反例）；
   - L1：每手法一张"什么时候用 + 一眼长相"的轻卡；
   - L2：每手法一份完整"配方"（数据要求、布局算法、配色、坑），**只在选定后才读那一份**。
   并把 `usage.never: 不许 bulk-read` 直接写进索引——**用 token 预算倒逼"别全读"**。这对我们"复用率 ≥ 50%"的 KPI 是直接利好：索引层薄、配方层可独立增删。

2. **把"反模式"写死进提示词**，而不是只写"要做好"。它的高价值规则全是**具体到代码层的踩坑**："`display:none` 切页会被 flex 覆盖""CSS `~` 选择器断 hover 链""只查 scrollHeight 不够要查面板遮挡""`-clamp()` 静默失效"。**我们的 SKILL/手法文档也该是这种"血写的反模式清单"，而非泛泛原则。**

3. **"Preview/产物里绝不能泄漏内部标签"做成硬门**。它的 Preview Authenticity Rules 本质是"防脚手架泄漏到交付物"——和我们"只读护栏 + scaffold 不覆盖肉"是同源关切，但它管的是**运行时产物**这一层。我们生成 deck 时也该有一条:**绝不把 status/占位/内部页型名/"🟡"这类元层标记渲染进给客户的 deck**。

4. **结构化提问 + 密度模式二分**。开场用结构化问题一次问完（Purpose/Length/Content/Density），并把 **speaker-led vs reading-first** 作为驱动整个生成的总旋钮——这对咨询 deck 极其对路（投资人路演=low，留底/尽调材料=high），**建议直接纳入我们的工作流前置问句**。

### 4.2 可借鉴的 prompt 工程（具体话术）

- **审美宪法段**（SKILL.md:20-36）："You tend to converge toward generic 'on distribution' outputs… avoid the 'AI slop' aesthetic"，然后**点名禁用 Inter/Roboto/Arial、紫渐变白底、甚至点名 Space Grotesk 这个 LLM 爱收敛到的字体**。这种"**指名道姓反收敛**"比"请有创意"有效得多——值得我们在视觉层照搬一段。
- **Signature Treatments = 非可选**（Signal design.md:308-318）：把一个设计系统最招牌的 1-2 个动作标成"whenever the element type is used, non-optional"，并写明"没有这个动作就读起来像另一套系统"。**给我们的"页型手法"写法立了个范式：每个手法定义 1 个不可省的招牌动作。**
- **策略覆盖优先级声明**（Signal design.md:197-205）：当复用外部资产和本项目约束冲突时，用一段"This policy has higher priority than…"显式声明覆盖关系。**我们复用 Novel Engine 资产 / 外部模板时，同款写法可避免规则打架。**
- **诚实的 Known Gaps 段**：每份 design.md 末尾列自己的局限（字体加载失败的退化、CJK 缺斜体轴、magic number 风险）。**和我们"防假绿"精神一致——文档自己先认怂，比假装完美强。**

### 4.3 和我们的异同（一张对照）

| 维度 | frontend-slides | PPT Engine（我们） |
|---|---|---|
| 形态 | 纯 Markdown 提示词 skill，零运行时 | skill + 真引擎层（architecture.py 八组件×五层 + 自省 + scaffold + conformance） |
| 产物 | 单文件 HTML 网页 deck | 咨询级 deck（收窄高 stakes 段） |
| 专业感来源 | 排版/配色/动效设计品味 | **数据图表硬手法**（waterfall/Mekko/Gantt——它做不出的段） |
| 叙事 | 密度模式 + purpose→mood 两个旋钮，无叙事引擎 | （我们的差异化应在这里加码：真正的叙事结构） |
| 质检 | 提示词内 fail-closed 自验 + 真截图，**无独立判定程序** | **conformance.json 硬数据 + 自省机 + "🟢必须人工自测"元铁律**（我们更硬） |
| 防假绿 | 防"内部标签泄漏到产物" | 防"自动判定/LLM 打分当做好了"（元层更高） |
| 复用策略 | 三级渐进披露 + 索引内写死加载纪律（**值得抄**） | 复用率≥50% 是 KPI——正好可用它的三级结构落地 |
| 分发 | 插件 + 裸 skill 双形态（维护两份副本=坑） | （我们单一标准，避开此坑） |

**一句话定位差**：它证明了"**纯提示词 skill 也能把设计品味做到很高**"；我们要在它够不到的两块——**数据图表硬手法 + 真叙事结构 + 元层 fail-closed**——立差异化。它的**工程组织（三级披露 / 反模式写死 / 策略覆盖 / 结构化提问 / 密度旋钮）则几乎可以整套搬过来。**

---

## ⑤ License + 坑

- **License：MIT**（LICENSE 文件 + README:592-594）。可自由 use/modify/share，**借鉴其 prompt 结构、design.md 写法、selection-index schema 无障碍**。注意 bold-template-pack 来自姊妹仓 `zarazhangrui/beautiful-html-templates`（34 个模板的源），若直接搬模板内容需一并确认那个仓的 license。
- **坑 / 局限**：
  1. **同套内容维护两份**（根目录 + `plugins/.../skills/...` 副本）——插件 + 裸 skill 双形态的代价，改一处要同步两处，易漂移。我们若做插件分发要规避（用符号链接或构建步骤生成副本，别手抄）。
  2. **无独立质检程序**——质量完全押在"Claude 在提示词约束下自验 + 人去看截图"。规模化/防回归弱于有硬数据门的方案（这正是我们的优势位）。
  3. **`design.md` 里大量 `{colors.xxx}` / `{typography.xxx}` 占位**（Signal preview.md:31、34 能看到 `{typography.label.fontFamily}` 这种**未被解析就直接出现在文档里**的残留）——说明它的占位是给"人/LLM 理解"的伪模板语法、并无真正的模板引擎渲染，LLM 读时要自己脑补替换。是"提示词工程"而非"程序化模板"的本质暴露，偶有漏替风险。
  4. **依赖外网字体（Fontshare/Google Fonts）+ 部署依赖 Vercel/Playwright**——离线/内网/合规场景会卡（design.md Known Gaps 自己也承认字体加载失败会退化）。咨询客户常在内网，我们要把字体内嵌/本地化作为硬需求。
  5. **fixed-stage 在超大屏（>2560px）grid 纹理会变粗**、CJK 无斜体轴导致招牌动作降级——它都诚实写在 Known Gaps，照抄时要连这些边界一起继承认知。

---

## 附：本次实读的关键文件（出处锚点）

- `SKILL.md`（381 行，工作流主图）
- `README.md`（595 行，含哲学/架构表/部署坑）
- `html-template.md`（产物 HTML/JS 架构 + inline 编辑 + 图片管线）
- `viewport-base.css`（固定舞台强制基座）
- `animation-patterns.md`（效果→情绪映射表，头部最有用）
- `bold-template-pack/README.md` + `selection-index.json`（三级披露 + 路由 schema + 内写死的加载纪律）
- `bold-template-pack/templates/signal/{preview.md,design.md}`（轻卡 vs 完整配方 的粒度样本，design.md 是教科书级）
- `scripts/extract-pptx.py`（PPT 抽取，96 行，纯抽取无重排）
- `.claude-plugin/marketplace.json` + `plugins/frontend-slides/`（插件分发形态）
