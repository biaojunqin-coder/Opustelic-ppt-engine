# 开源拆解 · pptmaker（jorben · 中文 · 资源地图称「明确 outline 步」）

> 日期：2026-06-30 · 方法：`ls -R` + 读 README(中英)/AGENTS.md/LICENSE + 亲读 `lib/prompts.ts`(prompt 全文)、`lib/api.ts`(两模式两协议)、`app/api/plan|gen/route.ts`(中转端)、`lib/types.ts`、`lib/themes.ts`、`PlanningReviewStep.tsx`/`EditorStep.tsx`(人审与导出)、`lib/utils.ts`。保真·带文件行号出处·代码即真相，不靠 README 宣称掺料。
> 仓库本地路径：`01_AI端到端应用/pptmaker` · 上游：[github.com/jorben/pptmaker](https://github.com/jorben/pptmaker)。
> **一句话最值得偷的**：它把整张幻灯片当**一张 AI 生图**来产（outline 只产「标题+要点+一段极详尽的 visualDescription 画面描述」，再逐页喂图像模型出 16:9 图），于是**「美术风格」被抽成一个可插拔的纯文本 prompt 槽**（`themes.ts` 11 套主题各一段 prompt 字符串）——这套「视觉风格 = 一段可替换的描述文本、与内容生成解耦」的拆法，是我们做制作工作流「换皮不换骨」时最干净的解耦范式。**但它也正因此踩了致命坑：产物是死图、文字不可编辑（见 §5 坑1），与我们咨询级 deck 的要求正相反——是反面教材。**

---

## 0. 最重要的判断（先说结论）

1. **它不是「生成可编辑 PPT」，是「生成一叠图片」**。每页最终产物 = 图像模型吐的一张 base64 图（`api.ts:418` `images[0].image_url.url` / `api.ts:259` `data:${mime};base64,`），编辑器里那张图**就是幻灯片本体**。所谓「导出 PDF」= 把这叠图塞进打印视图、调浏览器 `window.print()`（`EditorStep.tsx:98-106` `downloadPDF`→`window.print()`）。**没有 PPTX、没有矢量、没有可改的文本框。**
2. **它有「明确的 outline 步」+「人审闸」，但 outline 只是给画图当 prompt 的，不是终态产物**。outline 步产结构化 JSON（`title` + `slides[]{title,bulletPoints,visualDescription}`，`prompts.ts:80-100` schema），人可在 `PlanningReviewStep` 增删改三个字段（`PlanningReviewStep.tsx:41-82`），确认后逐页生图。**这一步对我们有借鉴价值（见 §2、§4）。**
3. **全程零质检 / 零返工闸**。生图失败只标 `status:"failed"`、跳过、可手动单页重试（`PlanningReviewStep.tsx:126-129`、`EditorStep.tsx:71-96`），**没有任何「内容对不对 / 数字准不准 / 逻辑通不通」的校验**。唯一的「把关」是人在 outline 步肉眼看一眼。→ 对我们「fail-closed 质量门」**无可借的闸**，只可借「outline→人审→再生成」的**流程骨架**。
4. **「内容生成」与「视觉风格」彻底解耦**，是它最干净的设计：内容靠 `contentModel`(文本模型)产 JSON，画面靠 `imageModel`(图像模型)产图，风格靠一段可替换 prompt 注入（`themes.ts`）。**这条解耦思路可借（§4.1）。**

---

## 1. 是什么 + 定位

- **一句话**：粘贴文本 / 传 PDF·Word·MD·TXT → 文本模型规划大纲(JSON·流式) → 人审改大纲 → 图像模型**逐页生成 16:9 图片** → 浏览器打印导出 PDF 的**「素材 → 一叠配图幻灯片」**生成器。中文项目。
- **形态**：Next.js 15 + React 19 + TS + Tailwind 纯前端 App（`package.json`），部署 Cloudflare Workers(OpenNext)。**配置存浏览器 localStorage**（API key/base/双模型 ID），无后端持久化；历史记录存 IndexedDB(`lib/db.ts`)。
- **底座模型**：双协议——**VertexAI 兼容**(Gemini，`gemini-2.5-flash` 内容 + `gemini-2.5-flash-image` 出图) 或 **OpenAI 兼容**(`gpt-4.1` 等 + 任意 OpenAI 兼容图像模型)。两种请求模式：**前端直连**(浏览器直打你配的 apiBase) 或 **服务端中转**(走 `/api/plan`、`/api/gen` 代理，`api.ts:583-597`)。
- **和我们差异极大**：①产物是**死图非 PPTX**；②面向**通用 PPT**（演讲、教学、卡通风），README 12 个示例主题全是哆啦A梦/赛博朋克/水彩这类**消费向美术风**，无 waterfall/Mekko/Gantt 这类咨询图；③**无 brief 解读、无策略层、无数据校验**。→ 它在资源地图里被标「明确 outline 步 · 同样无策略层」，本次确认属实。
- **对我们的相关性**：**不在产物形态，在两点解耦设计**——(a)「outline 步显式化 + 人审拍板」的 UX 流程；(b)「视觉风格 = 一段可插拔 prompt、与内容解耦」的工程拆法。其余（生图当幻灯片、打印当导出）是**反面教材**。

---

## 2. ⭐ 它怎么做 deck（重点：outline 步 / 底座 / 分几步 / 有无质检）

### 2.A 全管线（7 步，对应 `AppStep` 枚举 `types.ts:14-22`）

```
API_KEY_CHECK(配 key/模型) → INPUT(粘文本/传文件) → CONFIG(页数/语言/风格/附加要求)
  → PLANNING(文本模型流式产大纲 JSON) → PLANNING_REVIEW(★人审改大纲)
  → GENERATING(逐页生图) → EDITOR(预览/单页重绘/改文字/打印导出)
```

### 2.B outline 步怎么做（这是资源地图点名的「明确 outline 步」，亲读 `prompts.ts`）

- **系统 prompt**（`buildPlanningSystemPrompt` `prompts.ts:47-68`）："You are an expert presentation designer"，要求**按内容复杂度自动定页数或拆成指定 N 页**、保持**跨页风格一致（配色/主题/角色）**，输出一个 JSON：deck 级 `title` + `slides[]`，每页三字段：
  1. `title`：页面大标题；
  2. `bulletPoints`：**3-5 个要点（纯文本）**；
  3. `visualDescription`：**「一段高度详尽、艺术化的画面应当长什么样的描述」**——原文明令「用 infographics、layered diagrams、structural diagrams、comparison charts、storyboard frames、maps、timelines、charts 等图形元素生动诠释内容」(`prompts.ts:67`)。**这第 3 个字段是全项目的灵魂**：它不是「这页讲啥」，是「这页画成啥样」，直接当下游生图 prompt 的主体。
- **用户输入**：`buildPlanningUserPrompt` 把素材**截断到 128000 字符**塞进去（`prompts.ts:73-75`，`document.substring(0,128000)`）。
- **结构化约束按协议分两路**：VertexAI 用 `responseSchema`(JSON Schema，`prompts.ts:80-100`) + `responseMimeType:"application/json"` 强约束；OpenAI 用 `response_format:{type:"json_object"}` + 在 system prompt 尾部追加一段**手写的 output format 示例**(`getPlanningOutputFormatHint` `prompts.ts:105-118`)。→ **可借的小工程点**：同一套 prompt，对「原生支持 schema 的模型」用 schema、对「只认 json_object 的模型」补一段格式示例 few-shot，做协议兼容。
- **流式**：plan 步全程 SSE 流式回吐（`api.ts:296-327` 解析 `data: ` 行取 `delta.content`/Vertex 取 `parts[0].text`），前端进度条边收边显（plan 占 0→30%，`PlanningReviewStep.tsx:87` 注释「Start from 30% as planning is done」）。
- **JSON 兜底**：流式拼完整文本后过 `cleanJsonString`（`utils.ts:26-37`，正则剥 ` ```json ``` ` 代码块包裹）再 `JSON.parse`。**仅此一道容错**，解析失败直接抛错，无重试。

### 2.C 人审闸（`PlanningReviewStep.tsx`，唯一的「质检」）

- 人可对每页**改标题 / 改要点(textarea 按换行 split) / 改 visualDescription**（`tsx:41-55`、`211-253`）、**加页 / 删页 / 重排页码**（`tsx:57-82`）。
- 改完点「确认并生成」→ 进入逐页生图。**这是全流程唯一的把关点，纯靠人肉眼**，无任何机检。

### 2.D 生图步怎么做（`buildImageGenerationPrompt` `prompts.ts:123-152` + `api.ts`）

- 每页拼一个 prompt：`Slide Title` + `Bullet Points`(逗号连) + `Style Guide`(风格上下文) + `Visual Instructions`(就是那段 visualDescription) + 设计硬约束（**16:9**、高质量、「设计生动图形/匹配场景/恰当结构来补足简化文字」）。
- **关键文本渲染规则**：prompt 明令**别把 "Presentation Title"/"Slide Title"/"Bullet Points" 这种标签字样画进图里**（`prompts.ts:145-146`）——因为图像模型会把 prompt 里的标签词当文字渲染上去，这是生图做幻灯片的经典坑，它用一句负向指令规避。
- **逐页串行生图**（`PlanningReviewStep.tsx:107-152` for 循环 `await` 一页一页来），每页生成后**立即写 IndexedDB 历史**（`tsx:138-148`），进度 30%→100% 按页均摊（`tsx:150-151`）。某页失败只标 `failed` 跳过，不中断整批。
- **出图提取**：Vertex 从 `candidates[0].content.parts[]` 找 `inlineData.data` 拼成 `data:image/png;base64,...`（`api.ts:256-264`）；OpenAI 从 `choices[0].message.images[0].image_url.url` 取（`api.ts:413-418`）。**最终落到 `slide.imageUrl` 一张图。**

### 2.E 有无质检？——**没有**

- 全流程零自动校验：不验数字、不验内容覆盖、不验逻辑、不验图里文字对不对（图像模型常把文字画错/画乱码，它完全不查）。失败的唯一定义 = 「图像模型没吐出图」(`api.ts` 抛 `"No image generated"`)。把关 100% 外包给人在 outline 步看一眼 + 编辑器里手动单页重绘。

---

## 3. 关键实现 / 文件位（速查）

| 关心点 | 文件:行 |
|---|---|
| ⭐ outline 系统 prompt（三字段·visualDescription 是灵魂） | `lib/prompts.ts:47-68` |
| outline JSON Schema（Vertex 用） | `lib/prompts.ts:80-100` |
| OpenAI 协议补的 output format few-shot | `lib/prompts.ts:105-118` |
| 素材截断 128000 字符 | `lib/prompts.ts:73-75` |
| ⭐ 生图 prompt 拼装 + 「别画标签字样」负向指令 | `lib/prompts.ts:123-152` |
| ⭐ 视觉风格 = 可插拔 prompt（极简/详细/自定义） | `lib/prompts.ts:8-42` |
| ⭐ 11 套美术主题（各一段 prompt 字符串） | `lib/themes.ts:10-110` |
| 双协议双模式总入口 | `lib/api.ts:571-628` |
| plan 流式 SSE 解析（直连） | `lib/api.ts:296-389` |
| 生图出图提取（Vertex base64 / OpenAI url） | `lib/api.ts:256-264, 413-418` |
| 服务端中转 plan（TransformStream 再吐 SSE） | `app/api/plan/route.ts:162-311` |
| 服务端中转 gen（一次性返 imageData） | `app/api/gen/route.ts:146-226` |
| ⭐ 唯一人审闸（改大纲三字段/增删页） | `components/PlanningReviewStep.tsx:41-82` |
| 逐页串行生图 + 每页写历史 | `components/PlanningReviewStep.tsx:107-152` |
| 单页重绘 | `components/EditorStep.tsx:71-96` |
| ⭐「导出 PDF」= window.print() | `components/EditorStep.tsx:98-106` |
| JSON 兜底（剥 markdown 代码块） | `lib/utils.ts:26-37` |
| 配置存 localStorage / 历史存 IndexedDB | `lib/config.ts` / `lib/db.ts` |

---

## 4. ⭐ 对 PPT Engine 的落点（能借什么 / 反面教材）

1. **【直接偷·制作工作流的换皮解耦】「视觉风格 = 一段可插拔的纯文本 prompt、与内容生成解耦」**。它把内容（contentModel 产 JSON）和美术（imageModel + 一段 theme prompt 出图）拆成两个正交维度，11 套主题就是 11 段 prompt 字符串（`themes.ts`）、换主题 = 换一段文本、内容生成代码一行不动。→ 我们制作工作流做「同一份 deck 内容 × 多套视觉模板」时，可借这个**「风格层抽成可替换描述、与内容层正交」**的拆法（哪怕我们落地不是生图、是模板/主题 token，解耦的边界划法可直接搬）。**这条最值得记。**
2. **【可借·流程骨架】「显式 outline 步 + 人审拍板 + 再生成」**。它把「先出大纲 JSON → 摆给人增删改三字段确认 → 才进入下一步重活」做成独立一步（`PLANNING_REVIEW`），正中我们要的「每步用户拍板」。→ 我们策略/制作工作流的「大纲闸」可参照这个 UX：**重活（生图/渲染）之前，必有一道结构化、可逐字段编辑、人点确认才放行的中间态**。但我们要在这道闸上**加机检**（它没有），让它从「纯人审」升级成「机检 🟡 + 人确认 🟢」。
3. **【可借·小工程点】协议兼容的 prompt 双写**：对支持 JSON Schema 的模型走 `responseSchema` 强约束、对只认 `json_object` 的走「format 示例 few-shot」（`prompts.ts:80-118`）。我们若要多模型兼容产结构化大纲，这个「同一意图两种约束写法」可直接用。
4. **【可借·一句坑规避】生图当幻灯片时，prompt 必须显式负向指令「别把字段标签词画进图」**（`prompts.ts:145-146`）。我们若在任何环节用图像模型出配图/封面，照抄这条「DO NOT render labels」防乱码标签。
5. **【反面教材·产物形态绝不学】生图当幻灯片 = 死图、文字不可编辑、不可改数字、不可换字体、矢量丢失**。咨询级 deck 要求**每个数字可改、每个图表数据驱动、可二次编辑交付**——生图路线根本满足不了。→ **明确划界：我们走原生可编辑(PPTX/结构化)路线，不碰「整页生图」**（这也与铁律4「产物可交付」一致：客户拿到一叠 PNG 没法改是不可接受的）。
6. **【反面教材·导出别学】`window.print()` 当「导出 PDF」**：清晰度受屏幕/打印机驱动、分页靠 CSS `print-slide`、无法保证 16:9 精确、不可后期编辑。我们的导出必须是**程序化生成真 PPTX/PDF**。
7. **【反面教材·零质检正是我们的反面】** 它把质量 100% 外包给人肉眼看 outline，无任何 fail-closed 闸。→ 印证我们方向：**机检质量门是咨询级 deck 区别于通用 PPT 工具的护城河**，这类工具恰恰因为「没有质检、生图不可控」做不出高 stakes 段。

---

## 5. License + 坑

- **License = Apache-2.0**（`LICENSE` 标准全文，无附加商业条款）。→ **比 MIT 更友好商业借鉴**：可商用、可改、可闭源分发，仅需保留版权声明 + 标注修改 + 附 LICENSE/NOTICE。**借代码/借思路都合规**（我们主要借「解耦设计/流程骨架」思想，无版权顾虑）。
- **坑1（最致命，也是它与我们最根本的分歧）**：**整页是一张 AI 生图，文字不可编辑**。编辑器里那三个 textarea（标题/要点/visualDescription，`EditorStep.tsx:286-331`）**改的是「下次重绘的 prompt」，不是当前这张图**——你改了文字，屏幕上的图纹丝不动，**必须点「重新生成视觉」整页重画**(`EditorStep.tsx:71-96`)才会变，且重画结果不可控（图像模型每次出图都不同、文字可能画错）。**这是「生图做幻灯片」的根本死穴，咨询级 deck 绝不可接受。**
- **坑2**：**图里的文字靠图像模型「画」出来**，会糊、会错字、会中英混排乱掉、会无视 bulletPoints 原文——它只用一句「别画标签词」防护，**无任何「图里文字 = 原文」的校验**。高信息密度/精确数字的页（正是咨询 deck 的核心）会翻车。
- **坑3**：**素材硬截断 128000 字符**（`prompts.ts:74`），长文档/大 PDF 后半段直接丢，无分段/摘要/map-reduce 兜底。
- **坑4**：**API key 存浏览器 localStorage + 支持「前端直连」模式**（`config.ts`/`api.ts:583`），key 直接暴露在前端、打到第三方 apiBase。自用 demo 可以，**当产品有密钥泄露风险**。
- **坑5**：**逐页串行生图**（`PlanningReviewStep.tsx:107` for+await），N 页就 N 次串行图像调用，慢且贵；中途某页失败只跳过不阻断，最终可能交付一叠「有破洞」的 deck。
- **坑6**：plan 的 JSON 兜底只有「剥 markdown 代码块」一招（`utils.ts`），模型若吐半截/带解释文字/格式跑偏，直接 `JSON.parse` 抛错、无重试无修复，plan 步整体失败。
