# 开源拆解 · gpt-researcher（自主深度研究 agent）

> 拆解对象：`06_调研agent/gpt-researcher`
> 仓库：`github.com/assafelovic/gpt-researcher`（28k★ 级 · 作者 Assaf Elovic）
> 拆解时仓库版本：`pyproject.toml` version = **0.14.7**；HEAD commit `18d4051`（2026-06-28，PR #1820「security/content-hardening」）
> **保真说明**：本笔记结论全部来自源码/README，标了文件:行号或方法名；凡引申到「PPT Engine 怎么用」的地方明确标【落点·我的推断】，与原仓库事实分开。

---

## ① 是什么 + 定位

README 原话（`README.md` 顶部）：**"the first open deep research agent designed for both web and local research on any given task"**——产出「detailed, factual, and unbiased research reports with citations」。

- 设计血统：README 自述受 **Plan-and-Solve（arXiv 2305.04091）+ RAG（arXiv 2005.11401）** 两篇论文启发，针对「misinformation, speed, determinism, reliability」做工程化。
- 核心架构思想（README「Architecture」节原文）：**planner agent 生成研究问题，execution agents 去搜信息，publisher 把发现聚合成报告**。靠「parallelized agent work」提速。
- 解决的痛点（README「Why」节）：人工调研要数周；LLM 训练数据过期会幻觉；token 上限写不长报告；现成服务源太窄→片面/有偏。
- 形态丰富：PIP 包（`from gpt_researcher import GPTResearcher`）、FastAPI server（`main.py`，:8000）、CLI（`cli.py`）、两套前端（轻量 HTML/CSS/JS + 生产级 NextJS）、Docker、**还官方发布成 Claude Skill**（`npx skills add assafelovic/gpt-researcher`，README「Install as Claude Skill」节）、自带 `mcp-server/` 把自己暴露成 MCP server。

定位一句话：**它不是「搜一下给答案」，而是「planner 拆问题 → 多 execution agent 并行搜+爬+压 → curator 评源 → writer 出带引用长报告」的一整套自主深度研究流水线**，且高度可配置/可嵌入。

---

## ② 自主深度研究流程（重点·拆透）

仓库里其实有**两条研究流水线**，要分清：

### A. 标准流水线（`gpt_researcher/skills/researcher.py` 的 `ResearchConductor`）—— 默认主线

一次「广度优先、一层」的研究，是 PIP 包 `conduct_research()` 走的路径：

1. **建研究 agent 角色**（`actions/agent_creator.py: choose_agent`）：先用 LLM 按 query 生成一个「你是 X 领域分析师」的 agent + role prompt（`researcher.py:120-128`），后续所有 LLM 调用带这个角色。
2. **先搜一把垫底 → 再规划子问题**（`researcher.py: plan_research`，:49-88）：
   - 先用**第一个 retriever** 对原 query 搜一轮拿 `search_results` 当「实时上下文」（:63）；
   - 再调 `actions/query_processing.py: plan_research_outline → generate_sub_queries`，用 **strategic LLM**（默认 `o4-mini`，见 default.py:9）+ `generate_search_queries_prompt` 生成 N 条 google 搜索式子问题（N=`MAX_ITERATIONS`，默认 3，default.py:22）。
   - **关键：子问题不是凭空拆，是「拿初搜结果喂回去」再拆**——prompt 原文（prompts.py:213-254）："Write {max_iterations} google search queries to **form an objective opinion** from the following task"，并把 `context`（初搜结果）塞进去要求「consider current events / recent developments」。
   - 子问题生成有**三级容错链**（query_processing.py:71-110）：strategic LLM →（报错）带 token_limit 重试 →（再报错）fallback 到 smart LLM。鲁棒。
   - 非 subtopic 报告时，会把**原始 query 也追加进子问题列表**一起搜（researcher.py:335-336），保证主问题不被拆丢。
3. **每条子问题并行执行**（`asyncio.gather`，researcher.py:348-355；`_process_sub_query`）：
   - 对每个 retriever 搜 URL（`_search_relevant_source_urls`，:752）→ 去重 + `random.shuffle`（:796，避免总爬同样的头部源）；
   - **优化点**：有些 retriever（如 PubMed Central）自带全文 `raw_content`，直接透传不再爬；只有 snippet 的才进 scraper（:778-790 注释明说「body 是 snippet 还得爬，只有 raw_content 才算抓全了」）。
   - 爬完用 **RAG 压缩**留相关段（见下「RAG 怎么综合」）。
4. **评源/筛源**（`skills/curator.py: SourceCurator`，可配 `curate_sources`，researcher.py:196-198）：
   - 用 **smart LLM**（temperature=0.2）按 `curate_sources` prompt（prompts.py:315-347）对所有抓到的源打分排序，**只保留 top-N（默认 10）**。
   - prompt 的取向很明确——**"err on the side of inclusion"**（宁可多留），但**强烈偏好含统计/数字/可验证事实的源**（"Give higher priority to sources with statistics, numbers, or concrete data"），且**禁止改写/总结源内容**（"DO NOT rewrite, summarize, or condense"），只清垃圾。→ 这是「保数据保真」的设计取向。
5. **写报告**（`skills/writer.py` + `actions/report_generation.py` + `generate_report_prompt`）：见 ④/下文。

### B. 深度递归流水线（`gpt_researcher/skills/deep_research.py` 的 `DeepResearchSkill`）—— "Deep Research" 模式

真正体现「深度研究」四个字、且**最值得学**的部分。是一棵 **depth × breadth 的研究树**（默认 breadth=4, depth=2, concurrency=2，deep_research.py:`__init__`）：

1. **先生成澄清问题**（`generate_research_plan`，用 strategic LLM + **High reasoning effort**）：基于初搜结果生成 N 个「探索不同侧面/时间段」的追问，且 prompt 显式塞当前时间要求「考虑到 {current_time} 的最新进展」。
   - ⚠️ 注意：这些追问在自动模式下**不真问人**——`run()` 里直接 `answers = ["Automatically proceeding with research"] * len(...)`（deep_research.py:`run`）。即「假装做了 clarification 这一步」，把问题拼进 combined_query 继续。（多智能体版才有真·human-in-the-loop，见 `multi_agents/agents/human.py`、`plan_review.py`。）
2. **生成带「研究目标」的搜索查询**（`generate_search_queries`）：每条查询不只给 query 字符串，还要 LLM 给 `researchGoal`（schema：`[{"query":..., "researchGoal":...}]`）——目标用于决定「往哪深挖」。
3. **每条查询 = 起一个全新子 `GPTResearcher` 实例跑完整标准流水线 A**（deep_research.py: `process_query` 内 `from .. import GPTResearcher; researcher = GPTResearcher(...); await researcher.conduct_research()`）。即**深度研究 = 标准研究的递归套娃**。MCP 配置会向下传播给子 researcher。
4. **抽提「learnings + 追问 + 引用」**（`process_research_results`，strategic LLM + High effort）：把每条查询的 context 提炼成结构化 `{"learnings":[{"insight":..., "sourceUrl":...}], "followUpQuestions":[...]}`。**learning 级别就带 sourceUrl 引用**（不是最后才挂引用）。
5. **递归下钻**（`deep_research` 里 `if depth > 1`）：用上一层的 `researchGoal + followUpQuestions` 拼成 `next_query`，**breadth 砍半**（`new_breadth = max(2, breadth // 2)`）、depth-1，带着已有 learnings 继续递归。→ 越往深越聚焦、越窄。
6. **全程控字数**（`trim_context_to_word_limit`，上限 `MAX_CONTEXT_WORDS = 25000`）：reverse 遍历保最新的，防爆 context。
7. 解析极其防御性：`_load_repaired_json` + 一堆正则（`QUERY_LINE_PATTERN` / `LEARNING_LINE_PATTERN` 等）兜底——LLM 不吐合法 JSON 也能从 Markdown 行里抠出 query/goal/learning/citation。**这套「JSON 优先 + 正则兜底」的解析很值得抄。**

### RAG 怎么「综合」（`gpt_researcher/context/compression.py`，两条流水线共用）

- 核心类 `ContextCompressor.async_get_context`：用 LangChain 的 `RecursiveCharacterTextSplitter(chunk_size=1000, overlap=100)` 切块 → `EmbeddingsFilter(similarity_threshold)` 按**与子问题的 embedding 相似度**过滤 → 只留相关块。默认 embedding `openai:text-embedding-3-small`，阈值 `SIMILARITY_THRESHOLD=0.42`（default.py:5-6；compression.py 内默认 0.35，可被环境变量覆盖）。
- **小文档快路径**：总字符 < `COMPRESSION_THRESHOLD`（默认 8000）时**跳过整套 embedding 压缩**直接用原文（compression.py: `async_get_context` 头部注释 + 逻辑）——省钱省时。
- 即「综合」= 切块→向量相似度筛→拼成 context，本质是**对子问题的定向 RAG**，不是让 LLM 漫读全文。

### 有没有 fact-check？（重点·别被名字骗）

分两层，**结论：标准 PIP 流水线没有独立的运行时 fact-check 闸；只有多智能体版才有**：

- **标准流水线（A/B）**：**无独立事实核查 agent**。「事实性」靠三件事兜：(1) RAG 强制基于抓到的源、(2) curator 偏好数字源 + 禁改写、(3) 报告 prompt 强制**逐句内联引用**（见 ④）。即「靠 grounding + 引用约束」而非「靠一个核查器复核」。
- **多智能体版（`multi_agents/agents/`，LangGraph 编排）才有真·质量闸**，这是全仓**最像 fail-closed 的部分**：
  - `fact_checker.py: FactCheckerAgent`：把 intro+sections+conclusion 拼成 draft 丢给 LLM，prompt 是「找出 factual inaccuracies / hallucinations / inconsistencies；**没问题就严格只回字符串 'None'，有问题就列错误送回 writer 改**」。
  - `reviewer.py` ↔ `reviser.py` **审-改循环**：reviewer 按 `guidelines` 评 draft，「达标返回 None，否则给修改意见」；reviser 据意见重写；reviewer 二轮「除非 critical 否则尽量返回 None」。→ **典型的「不达标就打回、达标才放行」闸门，且'None=通过'是硬信号**。
  - `editor.py: EditorAgent`：先 `plan_research` 规划报告大纲分 sections，再 `run_parallel_research` **每个 section 起一条 LangGraph chain 并行**写（`asyncio.gather`），最后 `human.py`/`plan_review.py` 支持人审大纲。
- ⚠️ **保真提醒**：这里的「fact check / review」全是 **LLM 自评自批**（`call_model`），没有外部权威库交叉核验。对照 PPT Engine 铁律 2「防假绿」——**这正是「让 LLM 打分当通过信号」的典型，照搬会踩坑**（见 ⑤）。

### 离线评测（不是运行时闸，但说明它在乎事实性）

`evals/` 下两套 benchmark（README 说明这些日志**故意进 git** 留历史）：
- `simple_evals/`：移植 **OpenAI SimpleQA**，三档判定 CORRECT / INCORRECT / NOT_ATTEMPTED，GPT-4 当 grader，测短答事实准确率（出 accuracy/F1/cost/latency）。
- `hallucination_eval/evaluate.py`：用 `judges` 库的 `HaluEvalDocumentSummaryNonFactual`，**拿源文档核查输出是否幻觉**（offline LLM-judge）。→ 即「事实性是离线 benchmark 出来的指标」，不是每次研究都跑的在线 gate。

---

## ③ 能借什么（架构 / 可复用 / MCP）

### 架构上最干净的可复用点

- **「planner / execution / publisher 三段 + 子问题并行」这个骨架本身**就是策略调研环节的现成蓝本。
- **`skills/` 单一职责切分**极清晰，可逐块抄：`researcher`(编排) / `deep_research`(递归树) / `curator`(评源) / `context_manager`(RAG) / `writer`(出报告) / `browser`(爬) / `image_generator`。每个 skill 只持有 `researcher` 引用、互不耦合 → **照搬成 PPT Engine 调研层的子组件零阻力**。
- **`prompts.py` 的 `PromptFamily` 类**：所有 prompt 收口成静态方法，且支持按模型切「prompt family」（`get_prompt_family`，针对 granite 等有专门子类）——**prompt 工程集中管理**的好范式。
- **retriever 抽象**：`gpt_researcher/retrievers/` 下 **20+ 检索源**统一接口（`tavily/google/bing/brave/exa/serper/arxiv/pubmed_central/semantic_scholar/openalex/searx/duckduckgo/...` + `custom` + `mcp`），全是 `retriever(query, query_domains).search(max_results=...)` 同签名。换源只改 `RETRIEVER` 环境变量。**这套「一堆源一个接口、配置切换」直接可偷。**
- **防御性 JSON 解析**（deep_research.py 的 `_load_repaired_json` + 正则兜底、用 `json_repair` 库）——任何让 LLM 出结构化结果的地方都该有这层。
- **成本全程回传**（`cost_callback` / `add_costs` 贯穿每次 LLM 调用，deep_research 还分段记 research_costs）——可观测性范本。

### 可配置「深度档位」（很适合 PPT 的高/低 stakes 分档）

- MCP 有 `fast / deep / disabled` 三档策略（researcher.py: `_get_mcp_strategy`，默认 fast）：fast=只用原 query 跑一次缓存复用；deep=每条子问题都跑；disabled=跳过。
- deep research 的 `breadth/depth/concurrency` 全可配。→ **「按 stakes 调研究深度」的现成旋钮**。

### MCP 接口怎么暴露（双向，重点）

gpt-researcher 与 MCP 是**双向**关系，两边都值得看：

**(a) 作为 MCP 客户端**（`gpt_researcher/mcp/`，把外部 MCP server 当检索源）——这是更相关的方向：
- 开关：`export RETRIEVER=tavily,mcp` 混合检索；代码里传 `mcp_configs=[{...}]`（README「MCP Client」节给了 github server 例子）。
- 四个组件（`mcp/README.md` 列得很清楚）：
  - `client.py: MCPClientManager`——把 gptr config 转 MCP 格式，管 `MultiServerMCPClient`，支持 **stdio / websocket / http** 三种连接（按 URL 前缀 `ws://`、`http://`、无 URL=stdio 自动判定）。
  - `tool_selector.py: MCPToolSelector`——**用 strategic LLM 从 server 暴露的一堆 tool 里挑最相关的 ≤3 个**（`select_relevant_tools`，要 LLM 返回 `{"selected_tools":[{index,name,reason,relevance_score}], "selection_reasoning":...}`），LLM 失败有 pattern-matching fallback。**「先让 LLM 选工具再调」这个两阶段很值得学。**
  - `research.py: MCPResearchSkill`——把选中的 tool **bind 到 LLM**，让 LLM 自己决定怎么调工具拿结果（`conduct_research_with_tools`），结果连同 LLM 分析一起转成标准 `{title, href, body}` 格式。
  - `streaming.py: MCPStreamer`——WebSocket 实时进度。
- 即**「外部数据源（GitHub/DB/自定义 API）→ 包成 MCP server → 当一个检索源插进研究流水线」**，与 web 检索并行融合（`_combine_mcp_and_web_context`）。

**(b) 作为 MCP server**（`mcp-server/`）：把 gpt-researcher 整个能力暴露成 MCP server 给别的 agent（如 Claude）调；仓库根 `.mcp.json` + README 的 Claude Skill 安装都印证它被设计成「被别人当工具用」。

---

## ④ 对 PPT Engine 的落点（策略工作流·调研环节）【含我的推断】

> 背景：PPT Engine 策略工作流需要「判目的后→主动去调研市场/竞品/数据→喂给叙事」。gpt-researcher 是这个**调研层**的强候选。

### 怎么接进「调研环节」

1. **整段当「调研子能力」嵌入，PIP 方式最轻**【落点·推断】：策略工作流判完目的、确定要做哪些 deck 段（如「市场规模 / 竞品格局 / 增长驱动」）后，**每个待论证的论点起一次 `GPTResearcher(query=该论点).conduct_research()`**，拿回带引用的结构化 context，不直接用它的 `write_report()`（那是写文章，不是写 slide）。
   - 关键取舍：**偷它的「研究→context」前半段，丢掉「context→长 Markdown 报告」后半段**。PPT 要的是**结构化 + 带源的事实/数字**喂给排版/叙事层，不是 2000 字散文。
2. **深度按 stakes 分档**【落点·推断】：投资人/咨询级 deck 用 `DeepResearchSkill`（depth=2、breadth=4 的递归树，拿到 `learnings + citations` 列表，天然适合一条 learning → 一个 bullet / 一个数据点）；普通段用标准流水线一层即可。直接复用它的 breadth/depth 旋钮做「高 stakes 深挖、低 stakes 浅挖」。
3. **喂叙事的接口**【落点·推断】：`deep_research.process_research_results` 输出的 **`{"learnings":[{insight, sourceUrl}], "followUpQuestions":[...]}`** 几乎就是理想的「叙事原料包」——每个 insight 自带出处可直接落到 slide 注脚；followUpQuestions 可反哺「这页还缺什么论据」。建议 PPT Engine 在它之上加一层「learning → slide claim（带 source 角标）」的映射。
4. **检索源换成高 stakes 友好的**【落点·推断】：默认 tavily(web)，但它已内置 `arxiv / pubmed_central / semantic_scholar / openalex / serpapi` 等。做投资 deck 可加金融/行研数据源（包成 custom retriever 或 MCP server 插进去），复用那套统一 retriever 接口。
5. **curator 的「偏好数字源 + 禁改写」取向**正好对口咨询 deck【落点·推断】——咨询/投资 deck 命脉是**可溯源的数字**，curator prompt（prompts.py:333「prioritize sources with statistics, numerical data, or verifiable facts」）的取向天然契合，可直接复用并再加码。

### 与 Engine 标准的对照

- **可复用率角度**（项目首要目标=验证框架可复制、复用率≥50%）：retriever 抽象层、prompts 集中管理、skills 单一职责切分、防御性 JSON 解析、cost 回传——这些是**跨能力通用基建**，对「复用率」叙事是正资产。
- **fail-closed 角度**：标准流水线**没有**满足铁律 2 的硬闸；多智能体版的 `fact_checker`/`reviewer`「None=通过」循环**形似** fail-closed，但**是 LLM 自评**——PPT Engine 若要拿来当质量门，**必须替换成「人工自测过才标 🟢」的真闸，不能让它的 LLM-judge 直接判绿**（否则正中铁律 2/防假绿要避的坑）。可借鉴它「不达标就打回重来」的**控制流结构**，但**判定信号要换成程序化/人工**。

---

## ⑤ License + 坑

### License
- **实际 = Apache License 2.0**（`LICENSE` 文件首行确认：「Apache License / Version 2.0, January 2004」）。商用/改造/闭源分发友好，只需保留版权与 NOTICE。
- ⚠️ **元数据不一致**：`pyproject.toml` 里写的是 `license = "MIT"`（pyproject.toml:6），与根目录 LICENSE（Apache-2.0）**矛盾**。以 LICENSE 文件为准（Apache-2.0），但引用/合规归档时要标注这个不一致点，别被 pyproject 误导。

### 坑（按对 PPT Engine 的杀伤排序）

1. **「fact check / review」是 LLM 自评，不是真核查——直接当质量门会假绿**（最重要）：多智能体版 `fact_checker`/`reviewer` 的「None=通过」全靠 `call_model` 自己判，无外部交叉验证。对照本项目铁律 2/防假绿：**能偷它的控制流，绝不能让它的 LLM 判定当 🟢 信号**。
2. **标准 PIP 流水线根本没有运行时事实核查闸**：只有 grounding+引用约束。若 PPT Engine 默认走 PIP 路径，等于「调研层无质量门」，高 stakes deck 不可接受——要么上多智能体版的闸（但见坑1），要么自建程序化校验（如「每个数字必须能在某个 source URL 文本里命中」）。
3. **引用质量 = prompt 约束的，不保证真**：报告 prompt（prompts.py:305 等）强制逐句内联 `([in-text citation](url))` + 末尾参考表，但 **URL 是 LLM 按 context 填的，可能张冠李戴/挂错源**——内联引用「看起来严谨」但需独立验真，别被格式骗（PR 文件名 `PR_pr_fix-brave-snippet-bypasses-scraper.md` 也印证它修过「snippet 绕过 scraper」类的源质量 bug）。
4. **深度研究的「澄清问题」在自动模式下是假步骤**：`deep_research.run` 直接 `answers = ["Automatically proceeding..."]`，并不真澄清。想要真·human-in-the-loop 得走多智能体版（`human.py`/`plan_review.py`）。PPT Engine 若想「判目的时跟用户确认范围」，这步得自己接。
5. **重依赖外部 API + 强联网**：必须 `OPENAI_API_KEY` + `TAVILY_API_KEY`（或等价检索源 key）；默认 embedding/LLM 全是 OpenAI 系（default.py:5-9：`o4-mini`/`gpt-4.1`/`gpt-4o-mini`/`text-embedding-3-small`）。**本机 git/Clash 代理坑 + 沙箱禁网环境下，它的联网检索会直接跑不动或工具层谎报**——接入前先解决网络/代理，且别信「跑通了」的表面回包。
6. **成本/延迟随 depth×breadth 指数级涨**：deep research 是递归起多个完整子 researcher，每个都爬+压+多次 LLM。高 stakes 深挖一次可能很贵很慢——`run()` 里专门记 `research_costs` 就是因为这容易失控。PPT Engine 要设硬预算上限。
7. **依赖面巨大**：langchain 全家桶（1.0 系）+ langgraph + playwright/PyMuPDF/unstructured 等一大堆（pyproject 几十个依赖）。**只想要「研究→context」核心的话，别整包吞**，挑 `skills/` + `retrievers/` + `context/` + `prompts.py` 子集移植更干净。

---

## 一句话·最值得偷的 1 件事

**偷它的「深度研究 = 标准研究递归套娃」机制**：`DeepResearchSkill` 把一次研究拆成 depth×breadth 的树——每条子查询起一个全新 researcher 跑完整流水线、抽出「带 sourceUrl 的 learning + 追问」、再用追问拼下一层查询且 **breadth 砍半（越深越聚焦）**——这套「自带研究目标 + learning 级就挂引用 + 递归收窄」正是 PPT 高 stakes 段「一个论点深挖到能上 slide 的可溯源数据」最需要的引擎；但**它的 LLM 自评 fact-checker 只偷控制流、判定信号必须换成人工/程序化，否则正踩本项目防假绿铁律**。
