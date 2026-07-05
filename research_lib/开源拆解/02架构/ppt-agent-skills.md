# 开源拆解 · ppt-agent-skills（sunbigfly）

> 资源地图定位：「状态机多 agent·几乎是我们蓝本」。本次深拆结论：**确实是目前最贴 PPT Engine 哲学的开源参照**——它把"分阶段 fail-closed + 防假绿 + 上下文隔离"全部落成了可运行的 Claude Code Skill。每条结论带出处文件，未掺常识。
>
> ⚠️ **[2026-07-01 勘误·D6 决策记录]**：本篇写的是"读了它的代码觉得设计精巧"，**不代表这些设计后来真的被移植进了 PPT Engine**——同日利用率审计核实：本篇④「对 PPT Engine 的落点」列的 5 条（状态机多agent/上下文隔离/像素级Visual QA/断点续跑/`svg2pptx.py`）**全部未落地**，详见价值评估结论（`research_lib/开源生态调研_两工作流资源地图.md` 对应条目的勘误注）。「哲学呼应」和「代码移植」是两件事，本篇的"目前最贴PPT Engine哲学"评价指前者，读者别误当成后者的证据。
>
> - 仓库：`https://github.com/sunbigfly/ppt-agent-skills`（本机：`/Users/qinbiaojuan/Documents/PPT开源参考/02_Agentic架构/ppt-agent-skills`）
> - 版本：`SKILL.md` 自述 v4.1 / `WORKFLOW_VERSION = 2026.04.09-v4.1`（`scripts/workflow_versions.py`）；本机 git HEAD `13e3537`（2026-06-08）
> - License：**MIT**（`LICENSE`，Copyright 2025 sunbigfly）——可放心借鉴/改写/搬代码
> - 体量：105 个 .md + 15 个 .py，**无业务后端、无服务**，纯 Skill（`SKILL.md` 38KB 主控合同 + `references/` 知识源 + `scripts/` 黑盒工具）

---

## ① 项目是什么 + 定位（对哪个工作流）

**一句话**：一个"以软件工程理念组织的 PPT 全自动生成 Skill"，把"一句话需求 → 专业级 PPTX"拆成 7 阶段状态机，每阶段开独立子代理、落盘产物、过 Gate 才放行（README.md 24 行、`SKILL.md` §4）。

**它的工作流（README.md 57–77 行 + `SKILL.md` §4 Canonical Plan）**：
```
P0 采访 → P1 分支确认 → (P2A 联网检索 | P2B 本地资料压缩)
→ P3 叙事大纲 → P3.5 全局风格锁定
→ P4 逐页并行生产（Planning → HTML → Visual QA）→ P5 Preview + 双 PPTX 导出
```
产物链（`SKILL.md` §3.3）：
`interview-qa.txt → requirements-interview.txt → search/source-brief → outline.txt → style.json → planningN.json → slide-N.html → slide-N.png → preview.html → presentation-{png,svg}.pptx → delivery-manifest.json`

**对我们哪个工作流**：**两条都覆盖，但分量倒挂**。
- **策略工作流（我们的①）**：P0→P3.5 基本一一对应我们"解读 brief→判目的→调研→叙事→质量门"。它的 P0 采访、P1 research/非research 分叉、P2A 检索、P3 大纲、P3.5 风格，就是策略链。**可直接对标**。
- **制作工作流（我们的②）**：这里是**最大分歧点**——它**不走 python-pptx 原生出可编辑 pptx**，而是 **HTML/CSS 渲染 → 截图/矢量化 → 灌进 pptx**（详见④）。所以它的 P4/P5 对我们是"另一条技术路线的参照"，不是直接复用对象。
- **关键收窄缺口**：它做"通用专业 PPT"，**没有**我们要的咨询级高 stakes 图表（waterfall / Mekko / Gantt）。它的 `references/charts/` 只有 13 种轻量图表（kpi/funnel/radar/treemap/waffle/stacked_bar 等，见 `planning_validator.py` `VALID_CHART_TYPES`），**没有 waterfall/Mekko/Gantt**。`references/layouts/waterfall.md` 是"瀑布式版式"不是瀑布图。→ 印证我们铁律 4 的护城河：它够不到的那段正是我们要做的。

---

## ② Agent 流程：分阶段 / 编排 / 防上下文污染 / Visual QA 闭环

### 2.1 角色切分 = 主 agent 只当"调度器"，内容全外包（`SKILL.md` §1）
- 主 agent **只做**：维护计划、调 harness、管 subagent 生命周期、校验 Gate、与用户交互。
- 主 agent **不做**：代写任何正式产物、手写 subagent prompt、内联生产内容、用口头判断替代 validator。
- **"内容生产全量外包红线"**：search/outline/style/planning/html 等正式产物 **必须且只能** 由对应 subagent 生成；主 agent 自己写 = 合同违规；即使 subagent 失败，主 agent 也只能重建子代理重跑，不能"补写"（§1、§2.2 红线）。
  - → **对我们最直接的纪律启发**：把"编排"和"生产"在角色层就切干净，是防假绿的结构性前提。

### 2.2 编排 = 统一子代理调度骨架（`SKILL.md` §5.1 + cli-cheatsheet）
每个业务节点（P2A/P2B/P3/P3.5/P4）共用一套骨架：
1. 查 cheatsheet → `prompt_harness.py` 从模板生成阶段 prompt（phase1 + phase2 [+ phase3]）
2. harness 生成 **orchestrator prompt**（轻量调度，只含各阶段路径 + 渐进式执行协议）
3. 按《Subagent 操作手册》创建 subagent（**强制传 `--model SUBAGENT_MODEL`**，禁止默认回退）
4. 发 `RUN`（只发 orchestrator 路径，一行，不发正文）→ 子代理内部自主渐进 → 收 `FINALIZE`
5. 主 agent 跑同一 validator **复检**（§2.5 双保险：子代理自审 ≠ 主链放行）
- 通信协议（§2.4）只三条指令、只里程碑通信：`RUN`（主→子，发路径）/ `STATUS`（子→主）/ `FINALIZE`（子→主，发产物路径列表）。多阶段非末阶段只准发 `--- STAGE n COMPLETE: {path} ---`，**只有末阶段能发 FINALIZE**。

### 2.3 防上下文污染（最值得抄的一块，四道机制叠加）
1. **子代理强制隔离运行**（`SKILL.md` §2.2"上下文隔离"）：无论 CLI 默认是否继承，本 skill 要求子代理唯一可见上下文 = 主 agent 通过 prompt 文件**显式传递**的内容。主 agent 的对话历史、SKILL.md 正文、环境变量**都不准泄露**给子代理。若 CLI 支持隔离参数（`--no-context`/沙箱）必须用上。
2. **orchestrator 渐进式披露 = 把一页拆成三份自包含 prompt 文件**（`references/prompts/step4/tpl-page-orchestrator.md`）。系统级强制指令原文：
   - "你必须逐阶段读取并执行——完成当前阶段后才能读下一个阶段的文件"
   - "**严格禁止调用工具去读取外层的 `SKILL.md` 或主控全局规则文件**"
   - 禁止行为清单："禁止一次性读取全部三份 prompt 文件 / 禁止在 Planning 阶段预读 Review 的评判标准或 HTML 的实现细节 / 禁止在 HTML 阶段预读 Review 的 Failure Modes"
   - → **设计意图明确写出**（`SKILL.md` §6.8）："为防止大模型在一次 prompt 中同时兼顾排版、图文推演与 HTML 编码导致『注意力塌陷』，本阶段每个单页任务被拆散成三级 prompt（4A Planning → 4B HTML → 4C Review）"。**这就是"上下文卫生 = 质量"的工程化。**
3. **阅读隔离边界**（`SKILL.md` §2.6）：主 agent 未到对应步骤禁止读对应阶段文件；可读内容**只限** `OUTPUT_DIR/**` + 用户资料 + `cli-cheatsheet.md`。
4. **脚本当黑盒**（§2.6）：`scripts/*.py` 只准 `python3` 执行，**严禁 `cat` 源码、严禁 `--help` 摸参数**（参数全在 cheatsheet）——防主 agent 把一堆实现细节读进上下文。

### 2.4 Visual QA 闭环（核心——和我们"防假绿"哲学高度同构）
**两层断言 + 一道人眼，三者缺一不可**（`SKILL.md` §6.8 / cli-cheatsheet §4.4 / `page-review-playbook.md` Part G）：

**(a) 子代理内部图审循环**（`references/playbooks/step4/page-review-playbook.md`，是这个项目最硬核的文档）：
- **截图存档协议**（Part A-0）：每轮截图必须存两处——最终位 `PNG_OUTPUT` + 轮次存档 `REVIEW_DIR/roundX/slide-N.png`。理由直说："**LLM 极易产生『我已经修好了』的幻觉。物理存档 + 前后对比是唯一可靠的验证手段。**"
- **三遍扫描协议**（Part A）：第 1 遍边界巡逻（四角/四边/页脚溢出裁切）→ 第 2 遍内容区纵深（标题/焦点/支撑/层叠重叠/图文/装饰层）→ 第 3 遍整体印象（"一秒焦点测试""毛坯房测试""风格一致性"）。
- **P0/P1/P2 严重度分级 + CSS 修复配方**（Part B）：每个症状给根因诊断 + 具体 CSS 配方（如 P0-1 内容超画布 → 加 `max-height:580px; overflow:hidden`；P0-8 破图 → `object-fit:cover`）。
- **铁律：最少 2 轮，第 1 轮禁止 FINALIZE**（Part E + orchestrator 48 行）。理由："LLM 极易在第 1 轮自我放行——『我改了 CSS，应该好了』——第 2 轮是验证这种幻觉的唯一机会。"
- **回退止损硬门**（Part E 新增）：同一 P0/P1 类别连续 2 轮新截图仍存在 → **停止改 HTML，强制回退 planning**，重写 `density_label/density_contract/layout_hint/cards 分配` 至少一项，"禁止只改 5px 边距再回来"。

**(b) 自动化像素断言**（`scripts/visual_qa.py`，纯像素分析、**不依赖 LLM**）：
- 像素层检查：分辨率 16:9（DIM）、大面积空白占比（BLANK，深色主题特判）、疑似竖排单字列（VTXT，WARN）、边缘裁切痕迹（CUT）、低对比块（CONT）、文件大小（SIZE，<10KB=FAIL 疑似空白页）。
- **结构层检查**（v4.1 新增的"双层断言"，README.md 31 行）：对照 planning JSON + HTML 文本——卡片数/图表数超 `density_contract` 上限（DENS）、HTML 是否含统一 `header.slide-header`/`footer.slide-footer`（HTML-01/02）、planning 每张卡片的 `data-card-id` 是否都落地到 HTML（HTML-03）、dashboard 页禁外部图（HTML-04）、字体是否低于 `min_body_font_px`（HTML-06）、装饰节点数是否超 `decoration_budget`（HTML-07）、装饰节点是否带 `aria-hidden`（HTML-08）。
- **退出码语义**：`0` 全过 / `1` FAIL（致命，必须重跑）/ `2` WARN（看图复查）。
- **关键自我设限**（脚本 docstring + cheatsheet §视觉质量断言）："抓明显硬伤……**真正的视觉质量判断由主 agent 亲自看图完成**""`visual_qa.py` 不是人工审美检查的替代品"。

**(c) 主 agent 亲自看图 = 最终防线**（cli-cheatsheet §4.4 第 3 步）：
- 原文："这是整个质量体系的最终防线。`visual_qa.py` 只能抓硬伤，排版质量、内容完整性、视觉和谐度必须由主 agent 亲眼确认。"
- 判定规则：`visual_qa exit=1` **或** 主 agent 看图发现明显问题 → 整页重跑。
- → **这正是我们"绝不让自动判定/LLM 打分当『做好了』硬信号"的同款立场**，只是它把"人眼"换成了"主 agent 的眼"。**差异见④。**

### 2.5 无状态断点恢复（README.md 47 行 + `SKILL.md` §7）
- **不依赖任何进度状态文件**。中断后靠扫描磁盘已有产物（`outline.txt`/`style.json`/`slide-N.png` 等）**自动推断恢复点**。
- 探测器 `scripts/milestone_check.py`：从高到低跑 validator，第一个 `exit=0` 即最高自动通过点（P5→P4→P3.5→P3→P2→P0/P1）。
- 原则一句话（§7）："**只信文件与 Gate 校验，不信口头记忆或 session 状态。**" 子代理死亡 = 上下文全无 = 整页打回重跑，旧 session 一律不可续接。
- → 和我们"换会话/换账号无缝接手·进度在文件里不在账号里"（项目 CLAUDE.md §🔄）**理念完全一致**，可直接抄它的"磁盘探针式恢复"。

---

## ③ 关键实现 / 文件位（要搬代码看这里）

| 能力 | 文件 | 一句话 |
|---|---|---|
| **主控状态机合同** | `SKILL.md` | 8 节：角色红线 / 全局规则 / 环境感知 / Canonical Plan / 调度骨架 / 状态机 / 重试恢复 |
| **逐步命令手册** | `references/cli-cheatsheet.md` | 每个 Step 的 harness/validator 命令全集；主 agent 入口靠它，**不读脚本源码** |
| **prompt 模板填充器** | `scripts/prompt_harness.py` | 纯文本变换：`{{VAR}}` 填充 + `--inject-file` 注入正文；**残留未填变量直接 exit 1**（防带病 prompt）|
| **大纲/采访/交付合同校验** | `scripts/contract_validator.py` | 11 种 contract-type；正则抠字段 + 锚点字段必填 + 密度节奏跨页规则 |
| **Step4 planning schema 校验** | `scripts/planning_validator.py` | 单页 + 跨页双层校验；密度合同/卡片角色/anchor 唯一/资源引用存在性 |
| **像素+结构双层视觉断言** | `scripts/visual_qa.py` | 见 ②(b)；唯一外部依赖 Pillow |
| **资源动态路由** | `scripts/resource_loader.py` | `menu`（标题+引用层喂 planning）/ `resolve`（按 planning 字段加载正文喂 html）/ `images`（本地图清单）|
| **HTML→PNG 引擎** | `scripts/html2png.py` | Puppeteer headless；`await document.fonts.ready` + 等所有 `<img>` onload 再截图（0 丢字体的真实现）|
| **HTML→SVG** | `scripts/html2svg.py` | 952 行，矢量化管线 |
| **SVG→可编辑 PPTX** | `scripts/svg2pptx.py` | **最值钱的代码**：把 SVG 元素解析成 OOXML 原生形状，详见④ |
| **PNG→PPTX** | `scripts/png2pptx.py` | 整图灌 slide，跨平台 100% 还原（文字变像素不可编辑）|
| **子代理日志** | `scripts/subagent_logger.py` | 记录每页 PageAgent/PagePatchAgent 阶段命令，供断点审计回放 |
| **里程碑探针** | `scripts/milestone_check.py` | 无状态恢复的核心：磁盘产物探测 |
| **知识源（按需挂载）** | `references/{playbooks,prompts,styles,layouts,charts,blocks,principles,page-templates,design-runtime}/` | 105 个 md，全部"`# 标题` + `> 一句话引用层` + 正文层"三段结构，供双层消费 |

**资源双层消费机制**（`SKILL.md` §2.7，巧思）：每个资源文件 = `# 标题` + `> 引用层` + 正文。planning 阶段只加载"标题+引用层"组菜单（省 token）；html 阶段按 planning JSON 字段（`layout_hint→layouts/`、`card_type→blocks/`、`chart_type→charts/`）**动态 resolve 正文层**。→ 即"先给目录、用到才给正文"的上下文节流。

---

## ④ 对 PPT Engine 的落点（能借鉴 / 能复用 / 哲学异同）

### A. 哪个阶段可借鉴（策略工作流，几乎平移）
- **P0 强制结构化采访**（`SKILL.md` §6.2）："即使第一句话信息极多也严禁跳过采访"；必问维度含 场景/受众/核心目标/页数密度/风格/品牌/配图/资料范围 + **subagent 模型与思考深度 + 人工审计参与方式**。→ 我们策略工作流"解读 brief→判目的"可直接借这套必填维度清单（`contract_validator.py` `REQUIRED_INTERVIEW_DIMENSIONS` 是现成的 17 维 checklist）。
- **P1 research/非research 二选一分叉 + 互斥锁**（"进入 P2A 后绝不可再跑 P2B"）。→ 对应我们"判目的后选调研路径"。
- **P2A 搜索深度预估**（§6.4）：按主题复杂度定 `MAX_SEARCH_ROUNDS`（简单 2/中等 3/高复杂 4），每轮自评覆盖率，硬上限收敛——**防"内容单薄"和"无限烧 token"两个极端**。`search-brief.txt` 强制含 ≥3 种数据类型（指标/对标/时间线）。→ 我们调研阶段可抄这套"丰富度优先 + 硬轮次上限"。
- **P3 大纲"内部自审闭环"**（§6.6）：主 agent **不显式开审查轮**，Outline 子代理自带"草稿→自查缺陷→覆盖修复"死循环，只有完美才交 FINALIZE。→ 把"自审"下沉到子代理内部，主链只验收，是干净的分工。

### B. 哪段能复用（拿代码/拿数据结构）
1. **`scripts/svg2pptx.py`（强烈建议偷）**——这是它最稀缺、和我们②"原生可编辑 pptx"目标最接近的资产：把 SVG 的 rect/text+tspan/circle/ellipse/line/path/polygon/image + linearGradient/radialGradient/transform **解析成 OOXML 原生形状**（`p:sp` / `a:custGeom` / `a:gradFill`），含：path d→`cubicBezTo` 贝塞尔转换、环形图 `fill=none+stroke+dasharray`→`arc` 预设+粗描边、`object-fit:cover`→`a:srcRect` 源裁剪、字体回退链（PingFang SC→Microsoft YaHei）。**它走的是"HTML→SVG→OOXML 形状"，我们走"python-pptx 直出"——但这份 SVG→OOXML 映射表（颜色/渐变/路径/图片裁剪）对我们做高 stakes 矢量图表是直接可移植的轮子。** MIT，可搬。
2. **三个 validator 的"fail-closed 字段合同"思路**：`planning_validator.py` 的密度合同（`density_contract` 必含 `max_cards/max_charts/min_body_font_px/max_lines_per_card/image_policy/decoration_budget/overflow_strategy`）、跨页规则（禁连续 3 页 high/dashboard、dashboard 前后必须有过渡页、anchor 卡唯一）。→ 我们的"质量门"可照此把"页面预算"做成机器可校验的 JSON 合同，而不是靠文字描述。
3. **`visual_qa.py` 的双层断言模式**：像素硬伤 + 结构合同（planning↔html 一致性，如"planning 列了 N 张卡片 → HTML 必须有 N 个 `data-card-id`"）。→ 这是把"产物自洽性"做成自动门的范本，可直接迁到我们的制作工作流出关闸。
4. **`prompt_harness.py` 的"未填变量即 exit 1"**：模板化 prompt + 残留 `{{VAR}}` 直接失败。→ 防"半成品 prompt 喂给子代理"，轻量可抄。
5. **资源文件"标题+引用层+正文层"三段结构 + 双层消费**：上下文节流的好范式，我们 `research_lib`/`specs` 的知识源可照此组织（菜单态 vs 正文态）。

### C. 和我们 fail-closed 哲学的异同（重点）
**同（可放心对标）**：
- **分阶段 + 落盘 + Gate 才放行**：和我们"分阶段 fail-closed"骨架同构（`SKILL.md` §2.1"前序 Gate 必须通过才进下个 Step""失败只许 RETRY 或 ROLLBACK，严禁跳到后续步试试看"）。
- **双保险校验**（§2.5）：子代理自审 ≠ 主链放行，主 agent 必复检——和我们"防假绿"同源。
- **拒绝自动判定当『做好了』**：它明确"`visual_qa.py` 只抓硬伤，最终靠主 agent 亲眼看图"——精神上 = 我们"🟢必须人工自测过才标"。
- **无状态恢复 / 进度在文件**：和我们"换会话无缝接手"一模一样。

**异（必须警惕，别照单全收）**：
1. **"人工自测"的归属不同（最关键差异）**：我们的铁律 3 是 **人（用户）** 亲自验证才给 🟢；它的"最终防线"是 **主 agent（也是 LLM）** 亲自看图。**它没有强制的人类把关点**——除非用户在 P0 显式开 `manual_audit_mode != off`（默认 off）。也就是说：**默认配置下它仍然是"LLM 判 LLM"**，只是用"主 agent 看图 + 两层脚本断言 + 强制 2 轮 + 物理存档对比"把 LLM 自评的可信度往上抬。→ 对我们的启示：**可以抄它全套"抬高 LLM 自评可信度"的工程手段（存档/双层断言/强制多轮/回退止损），但绝不能把"主 agent 看图通过"当成我们的 🟢**；🟢 仍须落在人身上。它正好是"防假绿做到 LLM 层天花板"的样本，而我们要在它之上再加人类闸。
2. **制作技术路线不同**：它 = HTML/CSS→截图/SVG→pptx；我们 = python-pptx 原生直出可编辑 pptx。它的"可编辑"靠 `svg2pptx.py` 把矢量转 OOXML 形状（不完美：path 的弧线 `a` 命令降级为直线、二次贝塞尔近似三次），**文字虽可编辑但布局是"形状拼贴"不是"语义化 pptx 占位符/表格/图表对象"**。→ 高 stakes deck 若需"客户能在 PowerPoint 里改数据联动图表"，它这条路达不到，我们的 python-pptx 路线才行。
3. **图表能力不覆盖我们的高 stakes 段**：它 13 种轻图表无 waterfall/Mekko/Gantt（见①）。→ 不是复用对象，是"留白确认"——证明我们收窄方向有空间。
4. **"密度合同"是它的特色机制、但偏 HTML 排版语境**：`min_body_font_px`/`decoration_budget`/`overflow_strategy` 这些是为"防 HTML 页溢出/塌陷"设计的。→ 概念（页面级机器可校验预算）可借，但具体字段要换成 python-pptx 语境（如形状边界框不重叠、字号下限、单页对象数上限）。

---

## ⑤ License + 坑

- **License：MIT**（`LICENSE`）。可自由 use/copy/modify/merge/distribute/sublicense，只需保留版权与许可声明。**搬 `svg2pptx.py` 等代码合规。**
- **坑 / 注意点**：
  1. **它是 Skill，不是库**：核心价值在 `SKILL.md` 的"合同文"和 playbook 方法论，跑起来依赖宿主 CLI 具备"创建子代理 + 传 `--model` + 结构化提问 UI + web search"等能力（`SKILL.md` §3.1 环境感知）。把它当"运行时框架"会落空；当"方法论 + 几个独立可跑的脚本"才对。
  2. **依赖**：`visual_qa.py` 需 `pip install Pillow`；`html2png.py/html2svg.py` 需 Node + Puppeteer（脚本会自动 `npm install puppeteer`，但**沙箱禁网会失败**——本机记忆里 git/Clash 代理坑同理，离线环境跑不通截图链）；`svg2pptx.py` 需 `python-pptx` + `lxml`。
  3. **svg2pptx 的保真损耗**：弧线 `a`→直线、二次贝塞尔→三次近似、transform 只解析 translate/scale/matrix（无 rotate 矩阵全解）、`<5px` 元素被当装饰丢弃。做精密图表时这些近似会咬人，搬代码要补。
  4. **"默认无人类闸"**：见④C-1，`manual_audit_mode` 默认 off。直接套用它的默认流，就是"全自动 LLM 判 LLM"，与我们铁律 3 冲突——**必须改默认或显式挂人类放行点**。
  5. **README 措辞营销味重**：「阴阳割线设计哲学」「极速底层光栅化引擎」「0 秒白等极速快门」等是包装话术；落到代码就是 `design-specs.md` 的"承重墙 DOM + 内部自由"约束 + `html2png.py` 里 `document.fonts.ready` 等字体那几行。看代码别看形容词。

---

## 附：最值得偷的 1 件事
**把"质量门"做成"两层机器断言（像素硬伤 + planning↔HTML 结构一致性合同）+ 强制多轮带物理截图存档 + 主体亲眼复检"的三段式闭环**——它用这套把"LLM 自评不可信"压到了工程能压的极限（`visual_qa.py` + `page-review-playbook.md`）；我们照搬这套机制、再把最终 🟢 落到人身上，就是"防假绿"的完全体。
