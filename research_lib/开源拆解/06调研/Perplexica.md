---
status: progress
type: 开源拆解
target: Perplexica（仓库内已改名 Vane，作者 ItzCrazyKns）
repo: https://github.com/ItzCrazyKns/Perplexica （仓库当前自称 https://github.com/ItzCrazyKns/Vane）
license: MIT
star: ~35k（用户口径；本地仓库不含 star 数据，以 GitHub 为准）
本地路径: 06_调研agent/Perplexica
版本: package.json name=vane, version=1.12.2
拆解日期: 2026-06-30
拆解人: Claude (Opus 4.8)
和我们的相似度: ★★★☆☆（它是「答案引擎」不是「PPT 引擎」，但它的"调研/搜索环节"正是我们策略工作流缺的那一段；可整段移植的是它的搜索-重排-提炼管线，不是它的产品形态）
---

# Perplexica / Vane 深度拆解

> 一句话：**它是一个本地优先、隐私优先的「AI 答案引擎」——元结构 = `分类(classify) → (调研循环 ∥ 小组件) → 带引用写作(writer)` 三段式；最值钱的是中间那个 ReAct 式调研循环，它用同一套「动作注册表 + 逐轮 LLM 选工具」的骨架，靠三套 prompt（speed/balanced/quality）把"轻搜索"和"深研究"调成同一引擎的三档。** 对 PPT Engine 而言，它给的不是产品参照，而是一个可直接搬的"调研环节"内核。

保真说明：以下结论全部来自本地仓库实读，关键处带文件路径与行号（行号以本次实读为准）。⚠️ **重要事实**：这个目录名叫 Perplexica，但仓库已整体改名为 **Vane**（README.md、`package.json` 的 `name: "vane"`、LICENSE 版权年 2026 都印证），且代码是较新的"agentic 重写版"——和网上流传的老版 Perplexica（每个 focusMode 写死一条 LangChain chain）已经是两套架构。star=35k 是用户口径，仓库本身不含 star 数据。

---

## ① 是什么 + 定位

- **一句定义**（README.md:11）：「a **privacy-focused AI answering engine** that runs entirely on your own hardware. It combines knowledge from the vast internet with support for **local LLMs** (Ollama) and cloud providers (OpenAI, Claude, Groq), delivering accurate answers with **cited sources** while keeping your searches completely private.」
- **定位坐标**：开源的 **Perplexity 平替**——你问一句话，它去网上搜、读、提炼，然后给你一段**带 `[1][2]` 内联引用的博客式答案 + 来源列表**。不是聊天机器人，是"问→答+出处"。
- **三档速度旋钮**（README.md:21；代码 `optimizationMode`）：Speed（快答）/ Balanced（日常）/ Quality（深研究）。**这是整个产品的核心交互——同一个问题，用户自己挑要多深。**
- **隐私是第一卖点**：默认用自建的 **SearXNG**（元搜索引擎，聚合 Google/Bing/Reddit/arXiv 等但不暴露你的身份）做搜索后端；LLM 可全用本地 Ollama → **整条链路能完全离线/自托管**，搜索词不出本机。
- **形态**：单体 **Next.js 16 应用**（前端 + API routes 一体），SQLite（better-sqlite3 + drizzle-orm）存历史，Docker 一键起（自带 SearXNG）。不是库，是产品。
- **能力面**（README.md:17-41）：网页/学术/讨论三类源可选、图片/视频搜索、文件上传问答（PDF/Word/纯文本，走 embedding 语义检索）、限定域名搜索、Widgets（天气/股票/计算卡片）、Discover（每日推荐流）、搜索历史。
- **关键边界（和我们的根本不同）**：它的产出是**一段文字答案 + 引用**，**完全不碰任何可视化/文档产物**。它是"调研+回答"的终点，我们的调研只是"做 deck"的一个中途环节。**所以它对我们是"零件供应商"不是"竞品"。**

---

## ② 搜索 + 回答怎么做（★ 本次最核心的料）

整条主链在 `src/lib/agents/search/index.ts`（SearchAgent.searchAsync）。三步：

### 2.0 总骨架：classify → (research ∥ widgets) → writer

```
用户问题
  → classify()            分类 + 把问题改写成"独立问题"
  → Promise.all([
        researcher.research()   ← ReAct 调研循环（除非 classify 说 skipSearch）
        WidgetExecutor          ← 天气/股票/计算卡，和调研并行跑
     ])
  → getWriterPrompt()       把搜索结果塞进 context
  → llm.streamText()        流式吐出带 [n] 引用的答案
```
（`index.ts:55-140`）

### 2.1 第一步 · 分类器（classifier）——决定"要不要搜、搜哪、怎么问"

- 入口 `researcher/../classifier.ts` + prompt `prompts/search/classifier.ts`。**一次 LLM 调用（`generateObject` 结构化输出）**同时产出 7 个布尔 + 1 个改写后的独立问题：
  - `skipSearch`：能不能不搜直接答（基础常识/写作/问候/能被 widget 完全满足 → true）。**关键护栏（classifier.ts:14）：「不确定 / 含糊 / 拿不准时，一律 skipSearch=false」——即"拿不准就去搜"，把幻觉风险压到搜索这一层。**
  - `personalSearch / academicSearch / discussionSearch`：要不要查上传文件 / 学术库 / 论坛。
  - `showWeatherWidget / showStockWidget / showCalculationWidget`：要不要弹卡片。
  - `standaloneFollowUp`：把"它们怎么工作"这种依赖上下文的话，改写成"汽车怎么工作"这种自包含问题（classifier.ts:40-47）——**这是多轮对话里搜索能搜准的前提**。

### 2.2 第二步 · 调研循环（researcher）——一个 ReAct agent，不是写死的 chain

核心在 `researcher/index.ts`，是本仓库**最该偷的一段**：

- **迭代预算随档位变**（index.ts:15-20）：`speed=2, balanced=6, quality=25` 轮。
- **动作注册表 Registry**（`actions/registry.ts` + `actions/index.ts`）：把 7 个动作注册进一个 Map——`web_search / academic_search / social_search / scrape_url / uploads_search / __reasoning_preamble(plan) / done`。每个动作自带 `enabled(config)` 谓词，**按"当前档位 + 分类结果 + 有没有上传文件 + 用户选了哪些源"动态决定这一轮把哪些工具暴露给 LLM**（registry.ts:22-46）。例如 `academic_search` 只在 `sources 含 academic 且 classify.academicSearch=true` 时才出现（academicSearch.ts:28-31）。
- **每轮循环**（index.ts:59-183）：
  1. 按档位生成 researcher prompt（见 2.5）；
  2. `llm.streamText({ messages, tools })` → 让模型流式吐工具调用；
  3. 收齐这一轮的 `toolCalls`；若为空 / 最后一个是 `done` → 跳出；
  4. `ActionRegistry.executeAll()` **并行执行**本轮所有工具调用（registry.ts:82-104 用 `Promise.all`）；
  5. 把结果以 `role: 'tool'` 塞回 `agentMessageHistory`，进下一轮。
- **强制"先想后做"**（`actions/plan.ts`）：有个特殊动作 `__reasoning_preamble`，schema 只有一个 `plan` 字符串。prompt 硬性要求 **balanced/quality 档每次调工具前必须先调它**（speed 档禁用，`enabled: mode !== 'speed'`）。它的产出被实时 emit 成 UI 上"思考过程"气泡（index.ts:86-135）。**等于把 CoT 显式化成一个工具调用，既给用户看进度，又强制模型规划。**
- **done 的巧思**（`actions/done.ts`）：done 是显式终止信号，prompt 反复强调"绝不直接对用户输出文字，必须靠工具"；且 done 的描述里写明"到达最大迭代会自动触发，所以迭代快用完时别浪费一轮去调 done，先抢着搜"。

### 2.3 第三步（也是引用机制核心）· 写作器（writer）

- prompt 在 `prompts/search/writer.ts`。把搜索结果包成 `<result index=N title=...>...</result>` 列表塞进 `<context>`（index.ts:106-120）。
- **引用是纯 prompt 约束**（writer.ts:24-30，没有任何代码层校验）：「**每一句话都必须带至少一个 `[number]` 引用**，对应 context 里的来源；多来源用 `[1][2]`；找不到来源支撑的话要明说局限、不许编」。前端 `MessageRenderer/Citation.tsx` 再把 `[n]` 渲染成可点链接。
- **widget 结果单独隔离**（index.ts:120）：context 里 widget 区块特意标注「**已展示给用户、可用来答题但不许当来源 cite**」——避免模型把"天气卡"当引用源。
- quality 档强塞一条全大写硬指令（writer.ts:36）：「**答案不得少于 2000 字，像研究报告一样铺开**」。

### 2.4 ★ "搜索 vs 深研究"的真正分水岭：`baseSearch.ts` 的两条路径

`actions/search/baseSearch.ts` 是 web/academic/social 三个搜索动作**共用的底座**，但它内部按档位走两条**完全不同**的管线——这就是"它到底是搜索还是深研究"的答案：

**A) speed / balanced 档 —— 纯"轻搜索 + 嵌入重排"，不抓正文**（baseSearch.ts:37-171）
  1. 多 query 并行打 SearXNG，**只拿搜索引擎返回的 snippet/title**，不进任何网页；
  2. **嵌入重排**：对 query 和每条结果分别算 embedding，`computeSimilarity`（余弦）算分，**< 0.5 直接丢**（baseSearch.ts:72）；
  3. **去重**：两两算结果间 embedding 相似度，**> 0.75 视为重复剔掉**（baseSearch.ts:149）；
  4. 按相似度排序，**取前 20 条**（baseSearch.ts:169）→ 交给 writer。
  → 全程不读网页正文，靠 snippet + 向量排序，所以快。**这是"搜索引擎"行为。**

**B) quality 档 —— "选→抓→提炼"的两段式深挖**（baseSearch.ts:172-419）
  1. 多 query 打 SearXNG 拿到一批结果（**不做嵌入过滤**，全保留）；
  2. **LLM picker**（baseSearch.ts:240-289）：一次 `generateObject`，让模型按"相关性/质量/优先权威源/多样性/避免雷同/最多 3 条"的成文标准，**从一堆结果里只挑 2-3 条最值得读的**，输出选中下标 `[0,2,4]`；
  3. **真正 scrape 正文**：对选中的 URL 用 Playwright 抓全文（见 2.6），按 4000 token / 500 overlap 切块；
  4. **LLM extractor 逐块提炼**（baseSearch.ts:323-417）：每个 chunk 过一遍提炼 prompt，抽成**电报体要点**。这个 extractor prompt 写得极硬核，值得整段抄（baseSearch.ts:323-355）：
     - 「按 query 意图动态调粒度：问"是什么"就抽定义，问"规格/特性"就抽到每一个技术细节」；
     - 「**数字完整性铁律：绝不概括/泛化数字、基准、表格——原值照抄**。别说'提升了编码分'，要说'LiveCodeBench v6: 80.0%'」；
     - 「砍营销废话（best-in-class/seamless）、砍 UI 噪声（Subscribe now）、合并重复事实、删填充词（'重 1.2kg' 而非 'features a weight of only 1.2kg'）」。
  → 选 + 抓 + 逐块提炼，这是**"深研究"行为**。

> 一句话定性：**它本质偏"搜索"，但在 quality 档接上了一条轻量的"深研究尾巴"。**和 gpt-researcher / open_deep_research 比，它**没有**多智能体编排、没有 outline-先行 / 分节并行写作、没有研究计划文档、没有迭代式"研究→反思→补搜→再写"的长程闭环。它的 quality 档约等于"加了正文抓取和事实提炼的一次性深搜"，深度档次明显低于专职 deep-research 框架。详见 ④。

### 2.5 三套 prompt = 三种"研究人格"（`prompts/search/researcher.ts`）

同一个 ReAct 循环，靠换 system prompt 调出三种行为，**这套"一引擎三档"的写法本身就值得偷**：

- **speed**（researcher.ts:4-87）："action orchestrator"，禁用 reasoning，鼓励"一把搜完就 done"，web_search 描述里直接告诉它"speed 模式你只能调一次，把最重要的 query 一次打满"。
- **balanced**（:89-188）：强制 `__reasoning_preamble → tool → ... → done` 交替；硬性预算"最多 6 个工具调用 = 2 reasoning + 2-3 搜索 + 1 done"；要求"至少两次信息收集，除非问题极简"。
- **quality**（:190-318）："deep-research orchestrator"，塞了一段固定的 **`<research_strategy>` 七维清单**（researcher.ts:271-280，对 PPT 调研极有参考价值）：
  > 1.核心定义 2.特性/能力 3.对比/替代 4.最新动态 5.评价/专家观点 6.用例 7.局限/批评
  并反复施压"非穷尽不许 done"「never settle for surface-level」「never stop before 5-6 iterations」。
- 三档都共享一组 **`<mistakes_to_avoid>`**（researcher.ts:55-67 等）很值得借：「别假设存在与否、直接查；别浪费工具调用去'验证存在性'；2-3 次搜不到就是没有、报告后 move on；别过度思考」。

### 2.6 SearXNG + Playwright 抓取（基础设施层）

- **SearXNG 适配**（`searxng.ts`，仅 67 行）：就是拼 `?format=json&q=...&engines=...&categories=...` 打自建 SearXNG 的 HTTP 接口，10s 超时。**学术源 = `engines: ['arxiv','google scholar','pubmed']`（academicSearch.ts:51），讨论源 = `engines: ['reddit']`（socialSearch.ts:51）——"换源"本质只是换 SearXNG 的 engines 参数，零额外集成成本。**
- **正文抓取**（`scraper.ts`，117 行）：单例 Playwright（chromium-headless-shell）+ `@mozilla/readability` 抽正文 + 30s 空闲自动关浏览器省内存；带反检测（伪造 userAgent、抹掉 `navigator.webdriver`）。
- **切块**（`utils/splitText.ts`）：用 `js-tiktoken`（cl100k_base）按真实 token 数切，正则在句末/换行/列表符处断句，带 overlap。

---

## ③ 能借什么（对 PPT Engine）

按"可直接搬 → 可借范式 → 仅作参照"排序：

1. **★★★ quality 档的"选→抓→逐块提炼"三段管线**（baseSearch.ts:240-419）——这正是策略调研环节缺的内核。我们的调研不该停在"搜到 snippet"，而要：LLM picker 挑权威源 → 抓正文 → extractor 抽成**带原值数字的事实卡**。那段 **extractor "数字完整性铁律"prompt 可几乎原样复用**——做咨询 deck 最怕把"$1.2B 市场"糊成"很大的市场"，这条 prompt 正是对症的。
2. **★★★ "动作注册表 + enabled 谓词 + 逐轮选工具"的 ReAct 骨架**（researcher/index.ts + registry.ts）——比写死的 chain 灵活得多。PPT 调研可照搬：注册 `web_search / scrape_url / 财报库检索 / 行业数据库检索 / done` 等动作，按"做哪一页/哪类图表"动态开关可用工具。
3. **★★★ "一引擎三档 prompt"模式**——同一循环，speed/balanced/quality 三套 prompt + 三档迭代预算。映射到我们：做一页观点页 vs 做一张要数据支撑的 waterfall/Mekko，调研深度天差地别，正好用档位区分，不必各写一套。
4. **★★ classifier 先行 + "不确定就去搜"护栏**（classifier.ts:14）——契合我们 fail-closed 纪律：拿不准的事实，强制走调研、不让模型凭记忆编。`standaloneFollowUp` 改写也该抄（多轮里搜准的前提）。
5. **★★ quality 档的 `<research_strategy>` 七维清单**（researcher.ts:271-280）——可直接长成"策略调研 checklist"的雏形（市场规模/竞争格局/趋势/标杆/风险…按 deck 场景定制）。
6. **★★ widget 隔离思想**（index.ts:120）："这是给你看的、能用但别当来源 cite"——我们若给模型喂"已算好的图表数据"，也该这样标，防止它把自己算的数当外部引用。
7. **★ embedding 重排 + 去重**（baseSearch.ts:72/149）——`> 0.5 留、> 0.75 算重复`两个阈值是现成可调起点；不过对高 stakes 调研，B 路径（抓正文+提炼）比 A 路径（snippet 重排）更该是主力。

---

## ④ 对 PPT Engine 落点：它偏"搜索"还是"深研究"？vs gpt-researcher / open_deep_research

**结论：Vane 本质是「搜索引擎 + 一条轻量深研究尾巴」，整体偏"搜索"；论"深研究"它明显轻于 gpt-researcher / open_deep_research。** 三者在我们工作流里是不同工位：

| 维度 | Vane(Perplexica) | gpt-researcher | open_deep_research |
|---|---|---|---|
| 自我定位 | 答案引擎（problem=即时答+引用） | 研究助手（problem=出一份研究报告） | 深研究框架/范式参照 |
| 长程结构 | **单轮 ReAct 循环**（最多 25 轮工具调用），无"研究计划文档"、无 outline 先行 | planner-executor：先列研究问题 → 分头搜 → 汇总成长报告 | 多阶段/多智能体、迭代 reflect-补搜 |
| "深"在哪 | quality 档：picker 选源 → 抓正文 → 逐块 extractor 提炼 | 并行抓多源 → 按子问题聚合 → 长报告 | 研究→反思→再研究的闭环 |
| 产出 | 一段带 `[n]` 引用的答案（quality≥2000字） | 结构化研究报告（含引用/章节） | 同上量级或更重 |
| 重排/提炼 | 嵌入重排(speed/balanced) + LLM picker&extractor(quality) | 偏向多源聚合 | 偏向迭代质控 |

**对我们的落点判断：**
- **PPT 策略工作流的"调研环节"，最该偷 Vane 的"零件"而不是它的"整机"。** 具体：把它 **quality 档的 picker→scrape→extractor 三段**当作"单个调研任务"的执行内核（保真、带数字、出处清晰），但**长程编排要往 gpt-researcher 那侧靠**——因为做一份 deck 不是回答一个问题，而是要按"每页/每图"拆成一串子调研、各自出带出处的事实卡、再喂给制作层。Vane 的单轮 ReAct 撑不起这种"研究计划级"的长程，但它的"单次调研怎么做扎实"做得很到位。
- **一句话分工**：**Vane 教我们"一次搜索怎么搜到能上 deck 的事实"，gpt-researcher 教我们"一份报告怎么编排多次搜索"。** PPT Engine 调研模块 = 用 Vane 的执行内核 + gpt-researcher 的编排骨架。
- **直接可移植清单**（最小起步）：① extractor 数字铁律 prompt；② picker 选源 prompt；③ classifier 的"不确定就搜"护栏；④ SearXNG 换 engines 即换源的极简适配；⑤ researcher.ts 的七维 research_strategy 清单改写成"策略调研 checklist"。

---

## ⑤ License + 坑

- **License：MIT**（LICENSE，版权 2026 ItzCrazyKns）——最宽松，**可商用、可改、可闭源分发，只需保留版权声明**。整段管线/ prompt 拿来改用无授权障碍。
- **坑 1 · 改名混乱**：目录叫 Perplexica，代码已改名 Vane（README/package.json/LICENSE 全是 Vane），README 里还混着 perplexica 的部署链接和赞助商图。**引用时以"仓库即 Vane、对外通称 Perplexica"对待，别被 35k★ 的老 Perplexica 文章误导——那是旧 LangChain 架构，和这份代码不是一回事。**
- **坑 2 · 强依赖 SearXNG**：搜索后端硬绑自建 SearXNG（README 要求开 JSON 格式 + 启用 Wolfram Alpha 引擎）。好处是 engines 参数即换源、零额外 API 集成；坏处是**得自己运维一个 SearXNG**（Docker 镜像虽自带，但生产环境 SearXNG 被各搜索引擎限流/封 IP 是常见运维痛点）。README 也提到 Tavily/Exa "coming soon" 但**当前代码里没有**——别以为现成支持商业搜索 API。
- **坑 3 · 引用零代码校验**：每句带 `[n]` 引用**纯靠 writer prompt 约束**（writer.ts:24-30），没有任何后处理去验证"这句话是否真出自被引来源"。对高 stakes deck，**引用可信度不能依赖这层**——我们若复用，必须自己加"引用↔事实"的校验门（fail-closed），否则就是把幻觉风险藏进看起来很可信的 `[1]` 里。
- **坑 4 · quality 档很贵很慢**：25 轮迭代 × 每轮多 query × 每个选中 URL 抓正文 × 每个 chunk 一次 extractor LLM 调用——token 与时延成本都高，且强制"≥2000 字 / ≥5-6 轮"。生产要做成本护栏。
- **坑 5 · Playwright 抓取脆**：单例 headless chromium，反爬只到"伪造 UA + 抹 webdriver"级别，遇到强反爬/登录墙/JS 重渲染站点会抓空（scraper.ts 失败兜底返回 "Error scraping content"，**失败是静默降级、不报错**——复用时要把"抓取失败"显式上报，否则事实卡会悄悄缺料）。

---

## 附:关键文件地图（复用时直接定位）

- 主链编排：`src/lib/agents/search/index.ts`
- ReAct 调研循环：`src/lib/agents/search/researcher/index.ts`
- 动作注册表：`src/lib/agents/search/researcher/actions/registry.ts` + `.../actions/index.ts`
- ★ 搜索两路径(轻搜/深挖) + picker + extractor：`src/lib/agents/search/researcher/actions/search/baseSearch.ts`
- 三档 researcher prompt（含七维 research_strategy）：`src/lib/prompts/search/researcher.ts`
- 分类器 prompt（含"不确定就搜"护栏）：`src/lib/prompts/search/classifier.ts`
- 写作器 prompt（含引用铁律）：`src/lib/prompts/search/writer.ts`
- 强制先想后做：`.../actions/plan.ts`（动作名 `__reasoning_preamble`）
- SearXNG 适配（换源=换 engines）：`src/lib/searxng.ts`；学术/讨论源：`.../actions/search/academicSearch.ts`、`socialSearch.ts`
- Playwright 抓取：`src/lib/scraper.ts`；切块：`src/lib/utils/splitText.ts`
- 对外 Search API 契约：`docs/API/SEARCH.md`（POST /api/search，支持 stream SSE）
