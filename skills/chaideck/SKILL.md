---
name: chaideck
description: PPT「拆 deck 入库 + 盲拆进化」技能——把真实成品 deck 自动拆解、自审、入六类资产库(页型卡/表达卡/思路卡/节奏弧线/分析框架库/行业知识库)，并回填方法论 + 累积可信值。复用 Novel chaishu 框架，换「文本→视觉」料层。当用户说「拆 deck / 拆这些 deck / 拆样本入库 / 扩充页型卡库 / 回填方法论 / 护城河优化」触发。每次=拆+盲拆+思路+表达+框架+知识六轨：①苦力视觉读图抽页型卡(带 6 facets+检索规则)→页号溯源门 ②零框架盲拆发现新规律→页溯源门 ③三道审查门反跑抽思路卡(电梯陈述+叙事流评分)→页溯源门 ④抽表达手法卡(可迁移文案/修辞公式)→页溯源门 ⑤抽分析框架库(可复用的策略/分析思考工具本身)→页溯源门 ⑥抽行业知识库(真实引用的行业事实/数据点+时效性标注)→页溯源门 ⑦Claude 审查(段位灌水/空泛手法/场景·分品类 + 盲拆新规律) ⑧规则门入库 + 累积可信值 + 回填方法论 + 更新台账。绝不抽完直接入库、绝不跳过审查、绝不入库未溯源的卡/规律、承重墙改方法论必人审。只负责拆 deck 入库+进化，不负责做 deck。拆解对象仅限用户上传的原始内容（真实提案样本/历史 deck·收集范围宪法第4条 specs/进化飞轮收集范围.md），绝不拆 Engine 自产 deck（AI 学 AI 自我强化污染·D24）。
---

# /chaideck —— 拆 deck 入库 + 盲拆进化 · 真实 deck → 范本库 + 护城河升级

> **环境**：本 skill 若以 Claude Code 插件方式安装，`engine`/`reinforce` 两个包已由 `SessionStart` 钩子装进 `${CLAUDE_PLUGIN_DATA}/venv`——凡下文让你跑 Python / 调 `engine.`/`reinforce.` 模块的地方，一律用 `${CLAUDE_PLUGIN_DATA}/venv/bin/python3`，不要用系统 `python3`。若这两个变量没被展开（说明是直接 clone 仓库跑，不是插件安装），退回用仓库自带的 `.venv/bin/python3`。

> 复用 Novel `~/.claude/skills/chaishu/SKILL.md` 的「拆+审+入库+进化」骨架，只换料层（文本→视觉）。设计见 `specs/拆deck-skill-设计.md`、检索本体见 `specs/拆deck-检索本体设计.md`。
>
> **2026-07-01 四轨扩容（yanjiu研究驱动·五档结论落地）**：此前只拆"页型手法卡"(视觉/布局层)，用户指出还该拆"思路"(论证怎么搭的)和"表达"(文案怎么写的)。研究发现：`05_质量门与评估.md` 的"三道审查门"(Action Title/Storyline/Slide Content)其实已经是现成的思路层量尺，只是此前只当**生产检查清单**用、从没**反过来当抽取工具**套在真实 deck 上——文档和实践脱节，不是从零缺失。研究详情见 `specs/PPT方法论/_研究驱动评估-思路表达维度.md`。
>
> **2026-07-01 再扩容至六轨（用户洞察）**：用户指出前四轨都是"怎么呈现"（视觉/思路结构/文案），漏了"内容层"——**PPT思路本质围绕两件事：①问题是什么 ②怎么解决问题**。"怎么解决"对应可复用的**分析框架**（不是这页填了什么，是这套思考工具本身，如TIME模型/人货场/Brand House）；"问题是什么"对应deck里真实引用过的**行业知识/事实数据**（脱敏后可当背景知识库用，需标时效性）。这两者此前完全没被抽取。

## 🔥 灵魂：拆 deck 质量操盘手 + 护城河守门人
给系统上两种弹药：①**页型卡**(喂做 deck) ②**方法论护城河**(从真 deck 流长出/强化的规律)。**料的质量=系统天花板**，宁缺毋滥：编造的页号、灌水的段位、空泛的手法、单份拍脑袋的"新规律"，一律拦。

> ⚠️ **当前苦力 = Claude 视觉读图**（暂无便宜视觉模型 key·决策 D-视觉苦力待定）。接到 Gemini Flash/Qwen-VL 后，把"逐页抽卡"外包给它、Claude 退到审查（省 token·对齐 chaishu 用 DeepSeek 当苦力）。

## ⛔ 铁律（fail-closed·任一不满足=没干完）
1. **拆+盲拆+思路+表达+框架+知识六轨**：每份 deck 抽页型卡、零框架盲拆找新规律、反跑三道审查门抽思路卡、抽表达手法卡、抽分析框架库、抽行业知识库——六轨缺一不算拆完。
2. **页号溯源门必跑**：每张卡的 demo、每条盲拆规律、每份思路卡的评分依据都必须带**具体页号**、可回查页图核验。**编造/记错页一律剔**（视觉版的原文溯源门）。
3. **Claude 审查必跑**：审卡(①段位灌水=全标⭐⭐⭐⭐⭐→下调 ②空泛手法"提升质感"无机制→丢 ③场景/facets 错) + 审盲拆(真新/≥2 份撞到/页图撑得起) + 审思路卡(评分是否真按只读标题测出来的，非凭印象打分) + 审表达卡(formula是否真可迁移到别的deck，非该deck专属文案) + 审框架卡(是否真是可复用的思考工具，非该deck专属填法) + 审知识卡(有没有标时效性、来源是否可溯)。**绝不抽完直接入库**。
4. **分品类评级**：数据轴对品牌 deck 不适用等——评级按 domain 分类（投资看数据、品牌看概念文案·见 _MVP拆解验证)。
5. **承重墙人审**：可信值累积、新规律采纳/推翻 → 只产 pending 提案，**人审拍板才落地**，绝不自动改方法论。
6. **每攒够 N 份必护城河优化**：盲拆收敛→提案→人审→升级。**N 未来主要来自客户产出回灌**(决策 D2)，非手动下载。
7. **台账必更新**：入库后登记 `04_范本清单` + `research_lib/真实样本/README.md`。
8. **真跑不许假装**：每步贴真实输出（渲染页数/抽卡数/溯源剔数/审查改了啥/入库数/可信值变化/新规律）。
9. **环境护栏**：下载/渲染后**必 `file`/`ls` 核实**（防 curl 静默失败/防盗链返错误页·见 memory）；联网命令 `dangerouslyDisableSandbox:true`。
10. **心理学命名不落地就不抽**：Cialdini说服七原则/Ethos-Pathos-Logos这类"心理学贴标签"，除非能落到具体`pick_when`可操作判据，否则不单独抽取成体系——研究本身已证实"这类原则不告诉你何时用"，硬套只会制造新的方法论编码未验证负债（2026-07-01 yanjiu研究五档结论·🔻收窄砍项）。

## 固定流水线（写死·必跑完）

### Step 0 · 扫队列 + 查护城河
- 待拆源：①用户料 `../PPT开源参考/08_素材库/个人过往经典PPT/` ②政府公开咨询 deck(`research_lib/真实样本/咨询deck/`·政府记录 PDF 直链) ③未来客户回灌(D2)。
- 对比 `research_lib/真实样本/README.md` 台账已拆清单 → 列待拆。用户指定就按用户的。
- **查护城河**（2026-07-01 起接真计数器，不再靠人读 README 台账手数）：
  ```python
  from reinforce.evolution.evolution import evolution_due, load_decks_since
  status = evolution_due(load_decks_since())
  ```
  `status["due"]`=真 → 本轮拆完后要跑 Step4；`status["remaining"]` 告诉用户还差几份，播报给用户。

### Step 1 · 六轨拆（苦力·过页号溯源门·不入库）
- **渲染**：`pymupdf` 把 deck 每页 → PNG（`d[i].get_pixmap(dpi=80)`），落 scratchpad。
- **轨1 抽页型卡**：苦力视觉读图（代表页/抽样，非穷尽），每张卡填全 `{page_function(枢纽)·domain·intent·doc_type_seen·pick_when·skip_when·technique·mechanism·demo(deck+页号)·rating·source}`（结构见 `exemplars/页型卡库.json`）。
- **轨2 盲拆**：抛开现有方法论，问"这份 deck 有什么没被现有规律覆盖的高招/雷区"，每条带页号 evidence。
- **轨3 思路卡**：把 `05_质量门与评估.md` 的"三道审查门"从生产检查清单**反过来当抽取工具**用——①只读该 deck 全部标题（不看正文），写出 3-4 句电梯陈述 ②按叙事流畅(40%)/SCR对齐(30%)/受众视角(20%)/结构连贯(10%)四个带权重维度打分 ③记录发现的逻辑跳步（哪两页之间没接住）。每 deck 产一份思路卡（结构见 `research_lib/真实样本/_思路情绪提炼.json`）。
- **轨4 表达手法卡**：抽取可迁移的文案/修辞公式（不是抄具体文案，是把文案抽象成句式模板），每张卡填 `{id·expression_type·domain·pick_when·skip_when·formula(抽象句式模板)·mechanism·demo(deck+页号+原文引用)·rating·source}`（结构见 `exemplars/表达手法卡.json`）。同时顺手记该 deck 的情绪节奏弧线（借鉴 Duarte Sparkline：deck 在"现状 what is"和"愿景 what could be"间怎么摆荡、情绪峰值在哪页、首尾是否呼应），并入思路卡文件。
- **轨5 分析框架库**：抽取deck里用到的**可复用分析/策略思考工具本身**（不是这页填了什么内容，是这套框架的结构+适用场景），每条填 `{id·framework_name·framework_type·domain·structure(抽象结构描述)·pick_when·skip_when·mechanism(为什么这个框架有效)·demo(deck+页号+该deck怎么用的例子)·rating·source}`（结构见 `exemplars/分析框架库.json`）。
- **轨6 行业知识库**：抽取deck里真实引用过的**行业事实/数据点**（脱敏后可复用的知识，不是该deck专属营销话术），每条填 `{id·fact_type·domain·fact(具体事实陈述)·value_when(什么场景对做deck有用)·source_citation(原始数据来源标注)·demo(deck+页号+原文引用)·timeliness(时效性标注，如"2024年数据·未来引用需核实是否过期")·source}`（结构见 `research_lib/真实样本/_行业知识库.json`）。
- 留存：编造页号/空泛的当场剔。

### Step 2 · Claude 审查（六轨·必跑）
- 审卡：段位灌水(全⭐⭐⭐⭐⭐→给撑不起的下调)/空泛手法(无机制→丢)/facets 错/分品类评级。
- 审盲拆：真新(方法论没有)/≥2 份独立撞到(单份不采纳)/页图撑得起。剔废话/单份/撑不起的。
- 审思路卡：评分是否真按"只读标题"测出来的（不是翻了全文再倒着编评分理由）、逻辑跳步证据是否具体到页号。
- 审表达卡：formula 是否真抽象成可迁移模板（不是把该 deck 专属文案原样复制当"公式"）。
- 审框架卡：structure是否真是可复用的思考工具本身（不是照抄该deck这次填的具体内容），是否与已入库框架重复。
- 审知识卡：timeliness是否标注、source_citation是否可溯源（deck里没标来源的数据谨慎入库或标"来源不明·待核实"）。

### Step 3 · 入库 + 累积可信值 + 回填 + 台账
- **入页型卡库** `exemplars/页型卡库.json`（按 page_function·去重）。
- **入表达手法卡库** `exemplars/表达手法卡.json`（按 expression_type·去重）。
- **入分析框架库** `exemplars/分析框架库.json`（按 framework_name·去重）。
- **三库版本留痕**（2026-07-01 起必跑，补 L7 铁律"谁都能直接改 json 无痕迹"的缺口）：以上三个文件只要
  改了 cards 数组，改完立刻各调一次：
  ```python
  from reinforce.evolution.versioning import record_library_change
  record_library_change("exemplars/页型卡库.json", f"+N张·{deck名}", reviewer=f"人审(会话内Claude审查·{今天日期})",
                        card_count=<改后总数>)
  ```
  （表达手法卡/分析框架库同理，没改的库不用调。）没调用 = 版本号和改动都不落痕，等于白加了这个字段。
- **入行业知识库** `research_lib/真实样本/_行业知识库.json`（按 domain+fact_type·去重，时效性过期的定期复核）。
- **入思路情绪提炼** `research_lib/真实样本/_思路情绪提炼.json`（每 deck 一条：电梯陈述+四维评分+节奏弧线）。
- **累积可信值**（2026-07-01 起代码强制而非手改 json）：每张卡/规律印证或打脸 `01-03` 方法论哪条 →
  ```python
  from reinforce.evolution.methodology import accumulate
  from reinforce.evolution.evolution import record_deck_torn_down
  rep = accumulate({"规律key": {"support": 1, "rule_text": "..."}},
                   reviewer=f"人审(会话内Claude审查·{deck名}·{今天日期})")
  record_deck_torn_down()   # 本份计入护城河计数(供 Step0/Step4 判断是否到期)
  ```
  `rep` 里的 `new`/`promoted`/`demoted` 如实播报给用户，不要只说"已更新"。
- **回填方法论**：新页型→`02`；新共因/雷区→`01`；新叙事骨架/思路卡实测数据→`03`（把"方法论编码"升级成"真样本背书"）；给"🟡待真实样本"的强候选补真实 deck 例（名+页+段位）。
- **登记台账**：`04_范本清单` 对应场景行 + `README.md` 样本台账。

### Step 4 · 护城河优化（Step0 查过 `evolution_due` 到期才跑）
- 盲拆累积够 → 跨 deck 收敛(确认/新增/推翻) → 人审拍板 → 升级可信值台账 + 新规律。承重墙只有人审才落地。
  ```python
  from reinforce.evolution.evolution import converge, reset_decks_since
  # findings：翻自上次收敛以来的拆解笔记/_修订日志.md"本轮盲拆发现"汇总成 [{rule_key, polarity}, ...]
  # baseline：01-03 方法论现有规律 key 集合
  r = converge(findings, baseline, n_decks=...)
  # r["confirmed"]/["added"]/["refuted"] 逐条给用户看证据来源(deck+页号)，人审拍板哪些真落地
  # 只有人审通过、真写回 00-03 方法论后才调 reset_decks_since()——没通过就不清零，下次接着攒
  ```
  ⚠️ findings 目前没有独立候选池落盘（不同于 knowledge_ingest.py 客户回灌线有 `_框架候选池.json` 兜底），
  是到期时 Claude 现场翻近期拆解笔记汇总——这是当前的已知简化，量级上来后再考虑挂候选池。

### Step 5 · 验收闸（fail-closed·防假完成）
- □ 页型卡库可被检索召回(建了 search 接口后) □ 入库卡 facets 齐、demo 页号可回查 □ 可信值台账无裂键 □ 护城河计数已同步(`record_deck_torn_down` 真调过·非手改 json) □ 三库版本已留痕(`record_library_change` 真调过，version 有加·非手改 json) □ 04/README 台账更新 □ 法律红线(原始 deck 版权图不入 git·只入拆解笔记/卡)。
- 全绿才 commit。**提交**：`exemplars/页型卡库.json` + `specs/PPT方法论/`(改了的) + `research_lib/真实样本/`(拆解笔记·非版权原图) + `04`。绝不 `git add -A`、绝不提交版权原 deck 图。

## 与 chaishu 的对照（框架可复制）
| | chaishu(Novel) | chaideck(PPT) |
|---|---|---|
| 苦力 | DeepSeek 读文本 | Claude 视觉读图(暂)→便宜视觉模型(未来) |
| 抽卡维度 | 题材×桥段 | 6 facets(page_function 枢纽) |
| 溯源门 | demo 逐字溯原文 | demo 带页号·回查页图 |
| 进化料源 | 手动下载真书 | 手动现有素材(基底)→**客户回灌(D2·持续)** |
| 可信值/门禁/收敛 | methodology/gates/evolution | 同款复用 |

## 边界
- 队列空且护城河未到期 → 不空跑。
- 设计型 deck 文本乱码 → 必渲染视觉拆，别靠文本提取。
- 盲拆新规律单份撞到 → 不采纳(≥2 份)。
- 原始 deck 有版权 → 原图/PDF 不入 git，只入我们的拆解笔记+卡。

## 一句话
**扫队列→渲染→苦力视觉六轨(抽页型卡+盲拆+思路卡+表达卡+分析框架库+行业知识库·都带页号过门)→Claude 审(段位/空泛/facets + 新规律·分品类 + 思路评分依据 + 表达formula可迁移性 + 框架可复用性 + 知识时效性来源)→入页型卡库+表达手法卡库+分析框架库+行业知识库+思路情绪提炼 + 累积可信值 + 回填方法论(给强候选补真实deck例·把03从"方法论编码"升级成"真样本背书")→攒够 N 份收敛升护城河(N 未来来自客户回灌)→台账更新。范本库越拆越厚、方法论越拆越从"强候选"升"铁律"。**
