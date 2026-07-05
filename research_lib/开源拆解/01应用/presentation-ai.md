# 开源拆解 · presentation-ai（ALLWEONE® AI Presentation Generator · 2.9k★）

> 日期：2026-06-30 · 方法：`ls -R` + 读 README/LICENSE + 亲读 outline/generate 两条 API 路由 + 编排中枢(PresentationGenerationManager) + 生成页(generate/[id]) + Outline 编辑器 + 后修 agent 图(LangGraph) + Compare 取舍组件。保真带文件行号出处，代码即真相，不靠 README 宣称掺料。
> 仓库本地路径：`/Users/qinbiaojuan/Documents/PPT开源参考/01_AI端到端应用/presentation-ai` · 上游：[github.com/allweonedev/presentation-ai](https://github.com/allweonedev/presentation-ai) · Gamma.app 开源平替。
> **一句话最值得偷的**：**「生成」不是一个动作，是两道独立的、各自有按钮/各自有门的阶段**——大纲先出且完全可编辑（拖排/改字/增删/逐页指定版式），用户改完点同一个按钮才从「Generate Outline」翻成「Generate Presentation」进入出片；这套「大纲层先冻结、用户改完才喂下游」的两段式，正是我们策略层「每步拍板」的现成 UX 骨架。

---

## 0. 最重要的判断（先说结论）

1. **它的「每步拍板」做在两个层、用两套不同机制**，都值得偷：
   - **大纲层（生成前）= 状态机 + 单按钮双态**：`shouldStartOutlineGeneration` / `shouldStartPresentationGeneration` 两个布尔旗各管一段（`PresentationGenerationManager.tsx:113-119`）；生成页底部就一个按钮，标签随 `hasOutline` 在「Generate Outline ↔ Generate Presentation」之间翻（`generate/[id]/page.tsx:90-98`）。**大纲不出、下游不准跑**（`:734-739` 没大纲直接 toast 拦截）。
   - **后修层（生成后）= LangGraph `interruptBefore` 真中断 + Compare 取舍**：后修 agent 在**执行任何工具前暂停**（`route.ts:70` `interruptBefore:["tools"]`），靠 `Command({resume})` 续跑（`:75-79`）；改完不是直接落，而是弹 **Original vs Modified 并排缩略图，用户点哪个就采纳哪个**（`Compare.tsx:46-104`）。**这才是真·human-in-the-loop 闸**，不是 UI 摆设。
2. **它没有「质量门 / fail-closed 返工」**——大纲和slides的校验只有「字段非空」级（`outline/route.ts:231`、`generate/route.ts:42-47`），内容质量全交给 prompt 自律。**这正是我们要补的**：它的「人确认」是**靠人眼当唯一闸**，我们要的是「人确认 + 机检硬门」双保险。
3. **底座是一套自研 XML DSL**（`<PRESENTATION>→<SECTION layout>→ 组件`），不是 PPTX、不是 HTML、不是 Marp/reveal。组件库相当丰富（含 waterfall/Mekko 不在内，但有 CHART/TABLE/STATS/PYRAMID/TIMELINE/CYCLE/INFOGRAPHIC 等），靠流式解析器边收边渲染。

---

## 1. 是什么 + 定位

- **一句话**：输入主题 → AI 出大纲(可编辑) → 选主题/配图/风格 → 流式出片 → 富文本编辑 + 对话式后修 → 演示/导出 PPTX 的**端到端通用 AI PPT Web 应用**；明确对标 Gamma.app（`README.md:10`）。
- **形态**：Next.js(App Router) + tRPC/Server Actions + Prisma/Postgres + **Plate.js** 富文本编辑器 + **LangChain/LangGraph** + AI SDK(`@ai-sdk/react` 的 `useChat`/`useCompletion`)。多模型：OpenAI / Together / Ollama / LM Studio（本地模型一等公民，`README.md:211-238`）。
- **和我们差异**：**它是「通用 PPT」**（38 套主题、任意主题、任意受众），我们刻意收窄到「咨询级/投资人高 stakes 段」（铁律4）。**形态层（Web 全栈 + 自研 XML 渲染）也与我们差异大**——但**它的「两段式人确认 UX」与「后修 HITL 中断」是平台无关的交互范式，可整套搬到我们的策略/制作工作流**。
- **相关性**：资源地图点名它「outline 先行 + 用户编辑确认 UX · 最贴每步拍板」，本次就是来挖**这个「每步拍板」到底怎么落地**——结论：落在两处，机制不同（见 §2）。

- **大纲管线全貌**（前端编排，`PresentationGenerationManager.tsx`）：
  `create 页建空 presentation → 跳 generate/[id] → startOutlineGeneration() 置旗 → useChat 打 /api/presentation/outline → 流式 markdown(含<TITLE>/<THEME>) → RAF 节流解析成 outline[] → onFinish 落库 → 用户在 OutlineList 改 → 点按钮 startPresentationGeneration() → useCompletion 打 /api/presentation/generate → 流式 XML → SlideParser 边解析边 setSlides`。

---

## 2. ⭐ outline 先行 + 用户确认的 UX 怎么实现（重点）

### 2.A 大纲与出片是两个独立阶段，用「布尔旗状态机」隔开

编排全在一个隐形组件 `PresentationGenerationManager`（返回 `null`，只跑副作用，`:991`）。它持有两条独立的 AI 流：

| 阶段 | Hook | 打哪个 API | 触发旗 | 产物 |
|---|---|---|---|---|
| 大纲 | `useChat`（聊天式，留消息历史） | `/api/presentation/outline` | `shouldStartOutlineGeneration` | `outline: string[]`（每项=`# 标题\n- 要点`） |
| 出片 | `useCompletion`（补全式，纯文本流） | `/api/presentation/generate` | `shouldStartPresentationGeneration` | `slides`（XML 解析后的 PlateSlide[]） |

- **两旗互斥推进**：`startOutlineGeneration()` 只置大纲旗；出片副作用里**先查 `hasGeneratedOutline(outline)`，没大纲就 `setShouldStartPresentationGeneration(false)` + toast 拦死**（`:734-739`）。→ **下游永远拿不到「未经大纲」的输入**，这就是「先拍板大纲、再出片」的硬保证。
- **大纲流是「聊天」不是「补全」**：用 `useChat` 是有意的——它保留消息历史，方便**重新生成大纲**（`startOutlineGeneration()` 可反复点，`Header.tsx:103-115` 的 Regenerate）以及把 web 搜索的 tool-call 结果一起流回展示（`ToolCallDisplay`）。

### 2.B 单按钮双态 = 「确认」这一步的 UI 落点

生成页（`generate/[id]/page.tsx`）底部固定栏**只有一个主按钮**，它的标签和行为完全由状态推导（`:90-98`）：

```
isGeneratingOutline      → "Generating Outline..."   (禁用)
isGeneratingPresentation → "Generating Presentation..."(禁用)
isSavingBeforeGenerate   → "Saving Outline..."        (禁用)
hasOutline=false         → "Generate Outline"         ← 第一步
hasOutline=true          → "Generate Presentation"    ← 用户确认后的第二步
```

`handleGenerate()` 的两段式逻辑（`:316-350`）是整个「拍板」的核心：
- **没大纲** → 滚动到大纲区 + `startOutlineGeneration()`（出大纲）。
- **有大纲** → `setIsSavingBeforeGenerate(true)` → **`persistCurrentGenerationSettings()` 先把用户编辑过的最新大纲落库**（`:273-314`，存失败就 toast 中止、不进出片）→ 跳 `/presentation/[id]` → `startPresentationGeneration()`。
  → **关键**：用户对大纲的所有改动**在点按钮的瞬间被冻结落库**，再喂下游。这就是「拍板=把当前草稿定版」的实现。

### 2.C 大纲完全可编辑（确认前给足干预手段）

`OutlineList.tsx` 把 `outline: string[]` 渲染成可操作卡片，编辑动作**实时 `syncOutline` 回写全局 `setOutline`**（`:139-144`）：
- **拖拽重排**：`@dnd-kit`，`handleDragEnd` → `arrayMove` → 同步（`:146-164`）。
- **改标题**：`handleTitleChange` 行内编辑即时回写（`:166-175`）。
- **增/删卡**：`handleAddCard`(`crypto.randomUUID()`)、`handleDeleteCard`（`:177-191`）。
- **逐页指定版式**：每张卡可挂一个 layout 模板覆盖 `outlineTemplateOverrides[id]`（`:193-199`，下游出片时按页喂给 prompt，见 §3）。
- **生成中渐进显示**：还没到 `numSlides` 张时补骨架占位 `Skeleton`（`:201-254` 的 `showLoadingSkeletons`）——**流式出大纲时用户已能看到逐条冒出来**。
- 顶部 Header 是可折叠的参数区（`Header.tsx`）：prompt、slides 数、长宽比、语言、web 搜索开关，**确认前都能改**，改完点 Regenerate 重出大纲。

### 2.D 大纲 prompt 的产出契约（后端 `outline/route.ts`）

- 用 LangChain `createAgent`，**web 搜索为可选工具**（`:311-313` `tools: webSearch ? [search_tool] : []`）。
- 系统 prompt 强约束输出格式（`:40-85`）：先 `<TITLE>...</TITLE>`，再每个主题 `# 标题` + 2-3 个 `- 要点`，**禁用粗斜体下划线**，要点必须 `- ` 开头——**就是为了让前端能用正则 `split(/^# /gm)` 干净切成卡片**（`PresentationGenerationManager.tsx:88-97`）。
- 可选 `autoTheme`：大纲流末尾再吐一个 `<THEME>` XML 块（品牌色/字体），前端 `extractGeneratedPresentationTheme` 抽出来当生成主题（`:293-301`）。
- **关键 metadata**：`numberOfCards`/`language`/`tone`/`audience`/`scenario`/`textContent`(密度) 全随用户消息带上（`:26-38`）——**这些就是「策略层参数」**，在大纲阶段就锁定并影响后续出片。

### 2.E ⭐ 后修阶段的第二套「拍板」：LangGraph 中断 + Compare 取舍

生成后还有一条对话式后修线（`/api/agent/presentation`），这套「拍板」机制更硬：
- **执行工具前真暂停**：agent 图 `interruptBefore:["tools"]`（`route.ts:68-74`）——LLM 决定要改什么、但**改动落地前流被中断**，前端拿到「准备改什么」的预览。
- **用户决定后才续跑**：带 `resumeData` 时用 `graph.stream(new Command({resume:resumeData}), ...)` 恢复（`route.ts:75-79`）；靠 Postgres checkpointer 存图状态（`createAgent.ts:8,138`）。
- **取舍 UI = 并排缩略图二选一**：`Compare.tsx` 把「Original / Modified」两版 slides 各渲一列缩略图，**点 Original 保留原样、点 Modified 采纳新版**（`:46-104`）；`ToolMessage.tsx:110/155/176` 在不同工具结果里挂这个 Compare。
- 后修工具集（`tools.ts`）：`regenerate_slide`/`create_slide`/`delete_slide`/`edit_slide_properties`/`replace_image`/`change_theme`/`create_custom_theme`，**每个工具的 server 实现都只返回一句「成功」字符串、真正的改动在前端按 Compare 取舍后落**（如 `:39-43`、`:199-201` 工具体只 `return "...successfully"`）——**即：后端 agent 只产「提案」，落不落由前端人确认**。这点设计极干净。

---

## 3. 出片底座：自研 XML DSL（速记，非重点但要知道）

- **结构**：一个 `<PRESENTATION>` 根 → 每页 `<SECTION layout="left|right|vertical|background">` → 页内放一个主组件 + 可选根 `<IMG>`(必须放最后)（`generation-prompt.ts:491`、`:649-657`）。
- **组件库**（`createAgent.ts:57` 列举）：COLUMNS/BULLETS/ICONS/CYCLE/ARROWS/TIMELINE/PYRAMID/STAIRCASE/BOXES/STEPS/COMPARE/BEFORE-AFTER/PROS-CONS/TABLE/CHARTS/STATS/INFOGRAPHIC + H1-4/P/QUOTE/CALLOUT/CODE/LABEL/CONTRIBUTOR。
- **图表**：`<CHART charttype="bar">` 内**直接放 markdown 表格**当数据（`generation-prompt.ts:541-549`），支持 waterfall/range/OHLC/candlestick/boxplot/heatmap/sankey 等（用不同表头字段名区分，`:549`）——**注意：这是「让 LLM 写 markdown 表 → 前端渲染」，不是程序算几何**，咨询级精度存疑（见 §5 坑）。
- **infographic**：`@antv/infographic`，prompt 要求写成「完整视觉简报」（标签/实体/数值/序列/关系/朝向/takeaway），按 SECTION layout 决定横/竖（`generation-prompt.ts:551-554`）。
- **流式渲染**：`SlideParser`（`utils/parser.ts`）边收 XML 块边解析，配 `requestAnimationFrame` 节流 `setSlides`（`PresentationGenerationManager.tsx:168-208`）——出片时**逐页冒出来**的实时观感来源于此。
- **逐页版式喂下游**：§2.C 的 `outlineTemplateOverrides` 在出片时序列化成 `outlineTemplateHints` 注入 prompt（`generation-prompt.ts:629-647`），LLM 按页用指定 XML 结构填充。

---

## 4. ⭐ 对 PPT Engine 的落点（策略层「每步拍板」能借什么）

1. **【直接偷·两段式骨架】把「策略」和「制作」做成两道各自有闸的阶段，下游永远拿不到未确认的上游产物**。对应它的双布尔旗 + 「没大纲不准出片」硬拦截（`:734-739`）。我们的策略工作流（拆题→框架→逐页论点）出的「论点大纲」必须**先冻结落库、用户改完点确认**，制作工作流才接手出片——绝不让 AI 一口气从主题冲到成品。这是它最干净、最该整套搬的范式。
2. **【直接偷·单按钮双态】用一个推导式按钮承载「确认」语义**，标签随状态翻（Generate Outline ↔ Generate Presentation），避免两个并列按钮的歧义。低成本、强引导。对应 `generate/[id]/page.tsx:90-98`。
3. **【直接偷·后修 HITL】高 stakes 段的每次 AI 改动，落地前必须人确认**——它的 `interruptBefore:["tools"]`(执行前暂停) + Compare(并排二选一) 是教科书级实现。我们做投资人 deck 时，**AI 改 waterfall/Mekko/数字的每一步都该出「改前 vs 改后」让用户点**，而不是直接覆盖。对应 `route.ts:70` + `Compare.tsx`。**这条把「每步拍板」从「生成前一次」升级成「每次编辑都拍」，正中我们诉求。**
4. **【直接偷·后端只出提案、前端才落】** 它的后修工具体只 `return "成功"`、真改动由前端按用户取舍落（`tools.ts:39-43`）。我们可借这个「**agent 产 diff/提案 → 人确认 → 才 commit 到 deck**」的解耦，天然契合我们「人为主角拍板」。
5. **【必须补·它没有的机检门】它的「确认」=人眼当唯一闸，没有任何 fail-closed 机检**（校验只到字段非空，`outline/route.ts:231`）。我们要的是**人确认 + 机检硬门双保险**：在「人点确认」之前/同时，跑非 LLM 的硬判据（waterfall 首尾是否对得上、Mekko 宽度和=100%、引用页码真实存在），不过就拦在拍板前。**它给了 UX，没给质量门——质量门是我们相对它的核心增量（铁律2/3）。**
6. **【可借·策略参数前置锁定】** tone/audience/scenario/textContent 在大纲阶段就随 metadata 锁定并贯穿出片（`outline/route.ts:26-38` → `generation-prompt.ts:341-353`）。我们的「受众=投资人/客户高管」「场景=融资/尽调」也应在策略阶段一次锁定，下游全程读同一份。
7. **【形态层不照搬】** 自研 XML DSL + Plate.js + AntV infographic 是「Web 通用 PPT」的选择；我们若走 PPTX/python-pptx 路线，**借的是「两段式 + HITL 取舍」的交互架构，不是它的渲染栈**。它的 `<CHART>` 让 LLM 写 markdown 表 → 前端渲染，**对咨询级数字精度不足**，是反面参照（见坑3）。

---

## 5. License + 坑

- **License = MIT**（`LICENSE`，Copyright 2024 ALLWEONE Team，标准 MIT 无附加条款）。✅ 借代码/思路均无版权障碍；商用友好。我们要偷的是**交互架构与状态机设计**（思想不受版权约束），更无虞。
- **坑1（对我们最关键）**：**全程没有 fail-closed 质量门**。大纲校验仅「prompt 非空 + numberOfCards/language 非空」（`outline/route.ts:231`），出片校验仅「title/outline/language 非空」（`generate/route.ts:42-47`）。内容对不对、数字准不准**完全靠 LLM 自律 + 用户人眼**。**别误以为「它有 outline 确认 = 它有质量保证」**——它只有「人确认」，没有「机检」。
- **坑2**：**大纲↔出片是「松耦合」，大纲只当「主题清单」**——出片 prompt 明令「用大纲覆盖范围，但最终文案要重写得比大纲更强，别照抄」（`generation-prompt.ts:59`、`:656-657`）。即**用户确认的大纲措辞不保证出现在成品里**，只保证「话题被覆盖」。高 stakes 场景这可能是惊喜也可能是失控点，需留意。
- **坑3**：**图表是「LLM 写 markdown 表 → 前端渲染」**（`generation-prompt.ts:541-549`），waterfall/candlestick 等靠表头字段名触发渲染器，**没有程序级几何/数值校验**（首尾是否对得上、占比是否=100% 全无人查）。**咨询级 deck 的数字严谨性它给不了**——这恰是我们收窄高 stakes 段的立足点。
- **坑4**：后修 agent 用了**激进的消息裁剪** `trimMessages(maxTokens:4, ...)`（`createAgent.ts:15-31`），且 `tool_choice:"required"` + `parallel_tool_calls:false`（`:40-43`）——它**几乎不带历史上下文、每轮强制调一个工具**。设计取向是「单轮单工具、靠 checkpointer 续」，**复杂多步后修的连贯性靠 LangGraph 图状态而非长上下文**。借 HITL 思路时注意这套裁剪策略未必适配我们。
- **坑5（跑起来重）**：依赖 Postgres + 一堆 key（OpenAI/Together/FAL/Tavily/Unsplash/UploadThing/Google OAuth，`.env.example`）。本次结论全部基于**亲读源码**，未实跑（建空 presentation→出片需完整环境）。
- **坑6（文档对不上）**：README 的「Project Structure」说生成流在 `components/notebook/`，实际编排中枢在 `components/notebook/presentation/components/PresentationGenerationManager.tsx`，且 README 写的 `src/ai/agents/presentation/` 目录确实存在但只放后修图——**以源码为准，别信 README 的目录树**。
