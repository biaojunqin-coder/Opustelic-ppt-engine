# 开源拆解 · LandPPT（AI 端到端 PPT 生成平台 · sligter/LandPPT · Apache-2.0）

> 日期：2026-06-30 · 方法：`ls -R` + 读 README/README_EN/LICENSE + 亲读 SKILL.md+endpoints.md（自带自动化技能，最权威的工作流真相源）+ 核心服务源码（outline/slide/research/template/prompts/config）。保真带文件:行号出处，代码与 SKILL 即真相，不掺论文/营销宣称。
> 仓库本地路径：`/Users/qinbiaojuan/Documents/PPT开源参考/01_AI端到端应用/LandPPT` · 上游：[github.com/sligter/LandPPT](https://github.com/sligter/LandPPT)。
> **一句话最值得偷的**：它把工作流的"出关闸"做成**两道人工确认硬门 + 一道结构化页数自愈门**——大纲必须 `confirm-outline` 才放行、自由模板必须 `free-template/confirm` 才允许出页（没确认就调出页流会立刻 emit error），且页数不达标会自动扩/缩/强制对齐；这套「**人确认是闸、机器只在结构层自愈、内容质量不设闸**」的取舍边界，正是我们划"哪些环节该 fail-closed、闸放在哪"时最现成的对照样本。

---

## 0. 最重要的判断（先说结论）

1. **README 说"四阶段"，但代码里真实管线是 5 步、且 README 的四阶段名不对应实现**。README 写「需求确认 → 大纲生成 → TODO追踪 → PPT生成」（README.md:112-113），但 TODO 板里**实际只有 2 个 AI 执行阶段**：`outline_generation` + `ppt_creation`（`project_workflow_stage_service.py:460-477` `_get_default_todo_structure`，加一个已完成的 `requirements_confirmation` 占位），"TODO追踪"不是一个生成阶段而是**贯穿全程的看板/进度对象**。而自动化技能 SKILL.md 揭示的**真实端到端顺序是 5 步**：需求确认 → 大纲 → **选模板(free) → 生成模板 → 确认模板** → 出页（`SKILL.md:209-219`、`endpoints.md` 步骤 1-10）。→ **"四阶段"是 UI 叙事，真实工作流多一段"模板生成+确认"，且这段是带硬闸的**。这点对我们最重要：它的阶段切分**确认门**比大厂 skill 细。
2. **它有两道真·fail-closed 人工确认门，但内容质量层不设闸**。两道硬门都是"人点确认才放行"：① 大纲确认（`confirm_project_outline` 把 `ppt_creation` 从锁定转 pending，`project_workflow_stage_service.py:347-434`）；② 自由模板确认（SKILL.md:57-62 "Hard gate"：模板没 confirm，调 `slides/stream` **会立即 emit error**）。但**单页 HTML 生成失败不阻断**——直接塞一个红字"生成失败" div 当该页内容继续往下（`slide_generation_service.py:520、608`），整册照样标 completed。→ **它的闸是"流程节点闸（人确认）+ 结构闸（页数）"，不是"内容质量闸"**。对我们是清晰的分界参照：我们要补的恰是它没有的**内容/数字质量 fail-closed**。
3. **页数是唯一的"机器自愈闸"，且是三级兜底**：生成大纲后若页数不在用户区间 → `_adjust_outline_page_count`（扩/缩）→ 仍不达标 → `_force_page_count` 强制对齐到区间中点（`project_outline_page_count_service.py:114-128`）。**这是它把"用户硬约束"落成确定性自愈的范式**，可借。
4. **最值钱的工程结构是"角色级模型路由"+"三层创意设计缓存"**（见 §3、§4）：12 个功能角色各自可配不同模型/provider（`config.py:118-137`）；单页 HTML 生成前先建"全局视觉宪法→页面类型指导→单页创意指导"三层、且并行生成时共享缓存（`creative_design_service.py`）。这两套是"控成本 + 保全册一致性"的成熟做法。

---

## 1. 是什么 + 定位

- **一句话**：文档/主题 → 结构化大纲(JSON) → AI 自由模板(HTML) → 逐页 HTML 幻灯片 → 多格式导出（PDF/PPTX/图片/DOCX/讲解视频）的**通用 AI PPT 端到端平台**，带 Web UI + OpenAI 兼容 API + 自动化 Skill。
- **形态**：FastAPI + SQLite/PostgreSQL + Valkey；产物是 **HTML 幻灯片**（1280×720 画布），PPTX 靠 Apryse 转或截图嵌入。多 AI provider（OpenAI/Claude/Gemini/Ollama/DeepSeek 等兼容）。规模大（单 `pyppeteer_pdf_converter.py` 143KB、`ppt_image_processor.py` 99KB、`global_master_template_service.py` 114KB），是**重型成品**不是 demo。
- **和我们差异**：它是**通用 PPT**（market 全覆盖：旅游/教育/商业/技术…），不收窄高 stakes 段；产物是 HTML 不是原生可编辑 PPTX；**没有 waterfall/Mekko/Gantt 这类咨询图表的专门生成**（chart_config 只在大纲里给 bar/pie/line/scatter/radar 的泛型建议，`outline_prompts.py:116`，无咨询级图表语义）。→ **正是我们铁律4 说的"通用 agent/大厂 skill 做不出的段"它也做不出**，可作为"通用基线"对照，反衬我们收窄段的价值。
- **对我们的相关性**：**不在产物，在"分阶段 + 出关闸"的工作流骨架**——它是资源地图里点名的"四阶段+看板"样本，本次就是来挖它每阶段做什么、闸放哪、能借多少阶段切分思路。

---

## 2. ⭐ 它的"四阶段/五步"各做什么 + 有无出关闸（重点）

> 真实管线（以 SKILL.md + endpoints.md 的 API 顺序为准，比 README 四阶段更可信）：

| # | 阶段 | 做什么（源码/SKILL 出处） | **出关闸？是否 fail-closed** |
|---|---|---|---|
| 1 | **需求确认** requirements_confirmation | 用户定主题/受众/页数模式(fixed/range/ai_decide)/风格/场景；可上传文件抽大纲。确认后存 `confirmed_requirements`、`ppt_creation` 仍锁定。`project_workflow_stage_service.py:544-609` | **软门**：未确认则整个工作流 `return` 不往下（`:98-100`）。是"前置条件"不是质检。 |
| 2 | **大纲生成** outline_generation | 按 `confirmed_requirements` 生成 JSON 大纲：固定页面结构（第1页 title／第2页 agenda／中间 content／末页 conclusion/thankyou），每要点≤50字，给 chart_config 泛型建议。`outline_prompts.py:67-153` | **结构闸（机器自愈）**：页数不在区间 → 自动扩/缩 → 强制对齐中点（`page_count_service.py:114-128`）。JSON 解析失败 → **fail-OPEN**：塞 3 页兜底大纲照样存（`:174-192`）。 |
| 2.5 | **大纲确认**（人工） confirm-outline | 用户审完点确认；把 `outline.confirmed=True`、`outline_generation→completed`、**`ppt_creation→pending`（解锁出页）**。`project_workflow_stage_service.py:347-434` | **✅ 真·fail-closed 人工门**：不确认，PPT 制作阶段保持锁定。 |
| 3 | **选模板 + 生成自由模板**（free 模式） | `select-template{mode:free}` → `free-template/generate`（streaming-first，先吐 preview HTML 再持久化）。AI 生成整册风格基准 HTML 模板。`template_selection_service.py:93-146`、`endpoints.md:69-113` | 生成本身**有锁**（`asyncio.Lock` 防并发重复生成，`:100`）；已有 ready 模板且 `force=false` 会复用不重生。 |
| 3.5 | **确认自由模板**（人工） free-template/confirm | 把生成的模板标为"已批准项目模板态"，`confirmed=true`。`endpoints.md:135-150` | **✅ 真·fail-closed 硬门（最关键）**：SKILL.md:57-62 明示——free 模式下模板**没 confirm，调 `slides/stream` 会立即 emit error**，不是软提示。"确认才是改 confirmed 的闸，生成本身不给权限"（`endpoints.md:148-150`）。 |
| 4 | **出页** ppt_creation（slides/stream SSE） | 逐页生成 HTML：支持**并行批量**（用户配 parallel_count）、**已存在则跳过**（按页查 DB，含尊重用户手改的页）、生成前预热三层创意缓存。`slide_generation_service.py:360-631` | **❌ 内容层 fail-OPEN**：单页失败 → 写红字"生成失败"div 当该页内容、存库、继续（`:518-528、602-628`）。整册仍 status=completed。 |
| 终 | **完成校验**（仅自动化技能强调） | SKILL 要求：流的 complete 事件**不算成功**，必须最终轮询 `status==completed` 且 `slides_count≥target` 且 `slides-data total≥target` 三条全真才算过。`SKILL.md:44-51、93-100` | **✅ 这是 SKILL 层补的"事后核验门"**（程序事实判过，不信流的自报）——**思路可借**（见 §4.2）。 |

**两个最值得记的设计取向：**
- **A. 闸都设在"人确认 / 用户硬约束(页数)"上，不设在"内容好不好"上**。作者明显选择"机器只保证结构与流程节点正确，内容质量交给人在 UI 里看着办（侧栏 AI 对话编辑）"。→ 与我们要的"内容/数字 fail-closed"是**互补而非重叠**：它替我们验证了"流程闸+结构闸"够用且好实现，但**高 stakes 的内容质量闸是它的空白、是我们的主场**。
- **B. "生成 ≠ 批准"被刻意做成两步**（generate 之后必须单独 confirm）。无论大纲还是模板，**生成只是产出草稿，确认才是状态跃迁的闸**。这条"产出与放行分离"对我们划阶段极有参考价值。

---

## 3. 能借什么（成熟工程结构）

1. **⭐ 角色级模型路由（`config.py:118-137, 223-257`）**：把 LLM 调用按 **12 个功能角色**分别配 provider+model——outline / creative / image_prompt / slide_generation / editor_assistant / template_generation / speech_script / vision_analysis / polish / default 等，每个角色一对 `*_MODEL_PROVIDER` + `*_MODEL_NAME` 环境变量，`get_model_config_for_role(role)` 统一取。**意图明确：贵活（出页/创意）用强模型，便宜活（大纲/讲稿）用 mini 控成本**。→ 直接可借的成本控制架构，比"全程一个模型"工程上成熟得多。
2. **⭐ 三层创意设计 + 共享缓存（`creative_design_service.py`）**：出页前分层建设计规则——
   - **Layer 1 全局视觉宪法**（`get_global_visual_constitution_prompt`，`design_prompts.py:242-283`）：**只定整册规则不碰具体页**（整册气质/色彩策略/1280×720 锚点预算/页码规则/给单页生成器的执行原则）；
   - **Layer 2 页面类型指导**（按 title/agenda/content/… 归纳，`design_prompts.py:289+`）；
   - **Layer 2.5 单页创意指导**（逐页细化，`creative_design_service.py:755-787`）。
   - 并行生成时**共享 style-genes 缓存**、剩余页指导**后台异步预热不阻塞首屏**（`:301-531`）。→ **"先立全局宪法再逐页推导"正是保证整册一致性的范式**，对我们多页 deck 的风格统一直接可借。
3. **页数硬约束的确定性自愈（`page_count_service.py:200-239`）**：扩页时保留首尾页、在中间插 content；缩页 `_condense`；仍不达标 `_force_page_count` 兜底。**把"用户给的硬数字约束"落成程序自愈而非求 LLM 自觉**——可借作"结构层约束"的实现参照。
4. **页级幂等 + 尊重用户手改（`slide_generation_service.py:411-461、541`）**：出页前**先查 DB 单页是否已有 html**，有则跳过；`is_user_edited` 的页**永不重生**（`save_single_slide(skip_if_user_edited=True)`）。→ 中断可续、重跑不毁人工成果，与我们"scaffold 幂等不覆盖已填的肉"同构。
5. **DEEP 研究方法论（`deep_research_service.py:104-111`）**：研究阶段命名为 **D**efine-**E**xplore-**E**valuate-**P**resent，跑成 **ReAct agent 循环**（`_run_react_research_agent`，max_iterations 上限、逐轮选工具观测，`:466-509`），双引擎 Tavily+SearXNG。→ 我们做"策略工作流"的调研环节时，这套"有命名方法论骨架 + ReAct 有限轮 + 多源"可作结构参照（但它是通用研究，非咨询尽调）。
6. **自带自动化 Skill（`skills/landppt-ppt-generation/`）**：把 API 工作流封装成可被 n8n/CLI/curl 驱动的技能，**SKILL.md 写得比 README 更准**（含 Hard gate、State-first 诊断决策树、"流不算成功必须轮询三条"的成功判据）。→ **"给端到端流程配一份带闸与决策树的执行规约"本身就是好范式**，我们的命令/skill 可学这种"出关判据写死在 skill 里"。

---

## 4. ⭐ 对 PPT Engine 的落点（阶段划分 + 出关闸能借什么）

1. **【直接借·阶段切分】"生成"与"批准"分两步，每个关键产出后插人工确认门**。LandPPT 把"大纲生成→大纲确认""模板生成→模板确认"刻意拆成两个 API、确认才解锁下游——这正是我们"分阶段 fail-closed"在**流程节点**上的落地形态。我们的策略工作流（如：研究→判断标尺→deck 骨架）与制作工作流（骨架→逐页→图表）之间，**每个阶段出口都该有"产出 vs 放行"的分离**，放行可以是人工确认，也可以是程序判据，但**绝不能"生成完即默认进入下一阶段"**。
2. **【直接借·补它的空白】内容/数字质量闸是它的盲区、是我们的主场**。LandPPT 证明了"流程闸+页数结构闸"好实现且够撑通用 PPT，但**它对内容真假、数字勾稽完全不设闸**（单页失败都只塞红字 div 放行）。我们做投资人 deck 恰恰要在这一层 fail-closed：waterfall 首尾数字是否对得上、Mekko 宽度和是否=100%、引用数据是否在 source 里、Gantt 时间线是否自洽——**这些是它结构里完全缺的硬门，是我们收窄高 stakes 段的核心差异**。
3. **【直接借·成功判据写死在 skill】"流的完成事件不算成功，必须轮询客观状态三条全真"**（SKILL.md:93-100）。这套"**不信过程自报、只认事后程序事实**"完美对应我们铁律2 防假绿——把"做没做好"的判定建在**可程序核验的客观字段**上（status==completed AND count≥target AND data_total≥target），LLM/流的自我宣称至多当过程信号。我们每道阶段闸都该有这种"轮询式硬判据"。
4. **【可借·控成本架构】角色级模型路由**。我们的多阶段引擎里，调研/判断/出页/图表/讲稿对模型能力需求差异大，照 `config.py` 那套"每角色一对 provider+model 环境变量 + `get_model_config_for_role`"做，**便宜活降配、贵活升配**，是干净的成本规约。
5. **【可借·整册一致性】先立"全局视觉宪法"再逐页推导**。做多页 deck 时，先生成一份"只定规则不碰具体页"的整册宪法（色彩/锚点预算/页眉页脚/页码规则），再让单页生成器在宪法约束下出页——这是 LandPPT 保证 N 页风格统一的范式，对我们咨询级 deck 的视觉一致性直接可借（且其 1280×720 + overflow:hidden + 三段式骨架 + flex/grid min-height:0 的"防溢出"工程约束，`design_prompts.py:55-58`，是现成的版式护栏）。
6. **【可借·幂等续跑】页级"已有则跳过 + 用户手改永不重生"**，与我们 scaffold 幂等同构，可作"返工/重跑只补缺、不毁已交付/已人工确认产物"的实现参照（呼应铁律4 产物只读）。
7. **【反面警示·别学它的内容 fail-open】** 单页失败塞红字 div 照样标 completed = 整册"假完成"。我们绝不能让"某页/某图表生成失败"被吞成"项目完成"——**任一关键件不过，整体不得标 🟢**。
8. **形态层不借**：通用 PPT 全场景覆盖、HTML 幻灯片产物、Apryse/截图转 PPTX、讲解视频/TTS/积分/OAuth 这些重外围，都与"咨询级原生 deck 收窄段"无关，不引入。

---

## 5. License + 坑

- **License = Apache-2.0**（LICENSE 标准全文，11KB）。**比 MIT 更宽松友好商用**：明确授予专利许可、要求保留 NOTICE/变更声明，**无"商用需授权"附加条款**（与上次拆的 Auto-Slides 那种 MIT+商用授权附注不同）。借**架构思路/方法论**无版权问题（思想不受版权保护）；即便借鉴代码，Apache-2.0 也允许商用，**保留版权声明与 NOTICE 即可**。
- **坑1（最大·别被文档误导）**：README 的"四阶段"（含"TODO追踪"作为一个阶段）与代码实现**不一致**——真实 AI 执行阶段只有 outline+ppt_creation 两个，且真实端到端多一段"模板生成+确认"。**以 SKILL.md/endpoints.md 和代码为准，别照 README 四阶段名去理解工作流**。
- **坑2**：名为端到端"自动化"，但**关键两道门是人工确认**（大纲确认、模板确认）。SKILL 里专门处理"自由模板没确认就调出页流会 emit error"这个高频踩坑（`SKILL.md:57-62`），说明**这条非阻断不了**——纯无人值守跑要先把 confirm 步骤显式接上。
- **坑3**：**工作流非幂等**——`POST /api/projects` 成功后若中断重跑，会**创建重复项目**（同 topic 多条，`SKILL.md:117-131`）。续跑必须先 `GET /api/projects` 找回 project_id 复用，不能盲目重建。
- **坑4**：大纲 JSON 解析失败时**fail-open 塞 3 页兜底大纲**（`page_count_service.py:174-192`），且页数自愈用的是**模板化补页**（标题"补充内容N"、要点"补充要点1/2/3"，`:230-232`）——**自愈保的是"页数对"，不保"内容好"**，扩出来的页是占位级。借页数自愈思路时要清楚它的内容质量代价。
- **坑5（重）**：依赖面广——PDF/视频导出靠 pyppeteer(Chromium)+ffmpeg，标准 PPTX 靠 Apryse 商业 license key，TTS 靠 Edge-TTS/ComfyUI，研究靠 Tavily key/SearXNG 实例。**很多功能要外部 key/服务才跑得起**，本次拆解全部基于源码+SKILL 事实，未实跑（也无需实跑即可得出工作流与闸的结论）。
