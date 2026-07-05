---
name: 策略工作流
description: PPT Engine 策略层——把模糊 brief 解读成咨询级/投资人 deck 的「storyline 定稿（叙事+逻辑+质量门）」，交制作工作流出 pptx。五阶段 fail-closed：判目的(delivery_purpose 演讲/阅读/预读讲解三态 + mode 论证 + 美学倾向三轴)→议题树/假设树(MECE)→调研(数字溯源+来源分类+逐议题进展播报)→storyline(论点+一组证据+framing+节奏+Part 章结构·按 Part 编写节拍：每写完一个 Part 摊给用户确认留痕再写下一个)→三道审查质量门+用户拍板。全程确认粒度开场问（四档含 direct_through 直通档：问完全程零停顿直到成品·AI 代拍进假设台账）、每角色收工摊结论、发散点方向卡硬停、关键节点 ack 留痕缺失拒交棒，停点白名单外绝不停顿等"继续"（播报≠停顿·机检不过自己返工）；结构性文案按六槽位真提案范式写（禁元叙述/工序时态），收尾 Read-Through 通读自查+文案候选回灌。触发：需要产出内容交付物且行业惯例=PPT 形态时——咨询诊断/投资融资/战略汇报/尽调 deck，以及结案报告/复盘报告/提案/比稿方案/营销方案/汇报材料/月报季报/BP/pitch/roadshow/拿 Excel·数据做分析汇报等变体（判断依据='要不要产出一份内容交付物'，不是交付物叫什么名字，别按通用常识做成 Word）；简单需求同样走（leader 配轻角色组合）；吃不准先问一轮交付形态。
---

# 策略工作流 · SKILL（五阶段做实版）

> **定位**：策略层 = PPT Engine 的护城河（开源界 99% 空白）。本 skill 只搭「storyline 定稿（叙事 + 逻辑 + 质量门）」，**不出 pptx**（那是制作工作流）。
> **铁律**：分阶段 fail-closed——每阶段出关闸，闸内任一项不过就停在本阶段返工到全过，**绝不带病推进**（对照 Novel xieshu 节拍闸）。
> **可信度**：方法论 00–07（07 双模式**真样本背书**·D19 FR3 起扩展第三态「预读讲解版」[用户真实场景背书]·余为强候选）。生产中边用边验，按 [修订日志](../../specs/PPT方法论/_修订日志.md) 升格。

## 何时触发
用户要做任何 deck/PPT 类交付物都从这里进——高 stakes（咨询诊断/投资融资/战略汇报/尽调估值）是火力聚焦段，**简单需求同样走本管线**（leader 按需配轻角色组合，可能就 1-2 个角色——精品优先≠拒绝简单需求·CLAUDE.md 硬纪律 4·D14 澄清，本节旧措辞"通用 PPT 不走"已废）。
⚠️ **行业交付物名称许多默认就是 PPT 形态**：结案报告/复盘/提案/比稿方案/营销方案/月报季报/BP/pitch/roadshow/汇报材料——用户说这些词=要 PPT，别按通用常识写成 Word 文档（第四轮实测确诊的截胡事故："根据 Excel 写个结案报告"被做成 docx）；真吃不准形态，引导对齐第一轮问清。**绝不因需求"看起来简单/通用"绕开管线用原生能力直接写。**

---

## 五阶段（每阶段一道 fail-closed 关闸 · 调真实模块）

> 🔁 **引导式·非批处理（铁律）**：**绝不读完 brief 就一次性吐 storyline**——必有理解偏差。每阶段产出"我的理解"后，**摊给用户逐项确认对齐，对齐了才出关闸进下一阶**。大型 brief（几十上百页）信息量巨大、偏差致命，光 brief 解读就可能十几二十轮对话。尤其阶段 1：「我理解客户主线是 X，对吗？这下面还该包含哪些？线上线下？」的引导对齐，不是闷头读完就定。**策略的价值一大半在"对齐"。** 每阶段的关闸都隐含一道「用户确认对齐」——对齐不是我说了算。
>
> **引导对齐怎么问（每一轮·别再做成问卷）**：① **一次只问一个点**（绝不批量把几个选择题一股脑丢过去）② 问之前先花篇幅摊功课：**brief 里看到什么（带原文/证据）→ 我的理解/分析 → 我的推荐 + 理由（+ 权衡风险）** ③ 用户决定（确认/纠正）④ 定了这一点再进下一轮。对齐顺序由粗到细：**主线 → 场地/范围 → 各模块 → 细节**。
>
> 🖱 **拍板类问题必须用 AskUserQuestion 工具呈现（D19 FR2.1·第二轮实测用户点名："手动打字回复拍板题是体验硬伤"）**：凡"从几个明确候选里选一个"的收敛拍板——**确认粒度四档 / 方向卡收敛 / 三轴选型（delivery_purpose、mode、framework 各一轮）/ 关键节点 ack（定稿？还要改？）**——一律用 AskUserQuestion 摊选项：每个候选一个 option（label=选项名，description=这一项的理由+权衡），**推荐项在 description 开头标「推荐：」+一句为什么**；摊功课的叙述（材料里看到什么[带证据]→我的理解→推荐+权衡）照旧先在正文铺完，工具只承载"选"这个动作。**开放性讨论（脑暴/追问细节/请用户补材料）仍用文字对话**——问答工具管收敛不管发散，别把"你还有什么想法"也做成选择题。
>
> ⚠️ **「方向对齐」≠「做完策略」（易错坑·真实踩过）**：brief 阶段把主线/场地/范围等方向逐项对齐完，**只是定了约束条件，不是策略本身**。绝不能对齐完方向就直接跳去拼一份成稿 storyline——那仍是变相批处理（只是把批处理的时点往后挪了一步），会跳过「策略研究」整个板块。
>
> 🚀 **停点白名单 · 白名单外绝不停（D21·2026-07-03 用户拍板："除了必要的发散性确认以外，让它按最佳方案推进——用户的核心目标是从最初需求变成落地的 PPT"）**：引导对齐 = 在**拍板点**深度对齐，**≠ 步步请示**——把"要不要继续"抛回给用户，是把推进成本转嫁给操盘手（第四轮实测点名的体验硬伤：非拍板点也停下来等"继续"）。本 skill 全程**只有**这些地方允许停下等用户输入（停点白名单）：
> ① brief 引导对齐的每一轮问题（阶段 1 的主业）；② 发散点方向卡收敛（两默认点 + leader 加点·硬停）；③ 确认粒度开场问 + 用户所选档位对应的关键节点 ack（`key_nodes` 五类 / `every_role` 逐角色）；④ Part 定稿节拍（`minimal` 档除外）；⑤ storyline 定稿拍板；⑥ 缺了**只有用户才有**的关键信息（材料/预算/品牌红线/资质）。**`direct_through` 直通档下白名单收缩到只剩①（brief 对齐）和⑥**——②③④⑤全部由 AI 代拍并记假设台账，见下方第 4 档（D21 用户拍板）。
> 白名单外的一切——阶段出关、角色收工（非 every_role 档）、调研完成、机检通过——**播报一句进展就直接做下一步**。三条执行细则：
> - **播报 ≠ 停顿**：摊结论、报进度不构成等待理由——说完立刻继续，绝不以"如果没问题我就… / 需要我继续吗 / 我先做 X 好吗"这类**征求推进许可**的话收尾（推进不需要许可，**方向**才需要许可）。
> - **机检不过 = 自己返工修到过**，不是停下来问用户怎么办——fail-closed 的"停在本阶段"指返工循环，不指等人；除非返工缺的恰是⑥的用户独有信息。
> - **回合自查**：每次要结束回合，先自问"我停在白名单停点上吗？"——不是，就继续干。多个可行做法而无用户偏好依据时：选最佳方案推进 + 一句为什么；除非它构成真发散点（那走②，是方向不是执行）。

### 播报纪律三条（D19 FR2.2·全程生效·对用户说的每一句话）

第二轮实测确诊两类播报事故：对用户说"SKILL 08 方法论自动选型"（程序语言）、"和上一轮某品牌一样…"（跨项目串场）。三条纪律覆盖策略全程每一次对用户的叙述：

**① 机制名翻译成用户语言**——内部机制名/文档编号/函数名是给开发者看的，对用户的叙述里**一律不出现**：说"做了什么"，不说"调了什么"。五组正反例：

| ❌ 程序语言 | ✅ 用户语言 |
|---|---|
| 「按 SKILL 08 方法论自动选型，建议 mode=pyramid」 | 「按这份 deck 的论证方式——要说服董事会拍板、结论得先行——我推荐金字塔式讲法」 |
| 「跑了 run_storyline_gate，全过」 | 「我把整份故事线过了一遍质量检查，逻辑闭环、数字溯源都通过了」 |
| 「市场策划已 complete_role，user_summary 已落盘」 | 「市场研究这块收工了：一句话结论是……，三条关键发现给你摊开」 |
| 「这里要 record_divergence，请提供 user_quote」 | 「这里需要你拍板选一个方向；你的原话我会记进决策留痕，往后的推荐会越来越贴你的偏好」 |
| 「按 FR2.1 这题得用问答工具」 | （什么都不解释，直接把选项摊出来）——机制自己生效，不需要向用户报机制编号 |

**② 跨项目提及只限 `data/decks/` 内存在的项目**——该目录就是**这个用户的项目史**，天然的可见性边界：提别的单子之前先确认它的 deck 在 `data/decks/` 里（拿不准就 `ls data/decks/`），并且**用用户自己的叫法**称呼（"你之前 059 那单"✓；"上一轮某品牌"仅当某品牌的 deck 真在该目录内才可说✓）。目录里没有的项目**一个字不提**——哪怕知识库里有它沉淀的知识。

**③ 知识库引用不透品牌**——行业知识库条目是脱敏后的公开知识，引用时说"行业知识库有一条 XX（来源 XX 报道）"，**不带其他品牌名、不提知识来自哪个客户单**——除非该品牌的 deck 就在这个用户的 `data/decks/` 内（用户自己的项目当然可以点名）。例：✅「行业知识库有一条：网红城市热度一年腰斩的先例（来源：新华网报道）」；❌「某品牌那单沉淀的经验说……」（仅当某品牌 deck 在该用户目录内才合规）。

> ⚠️ 单机单用户下 `data/decks/` 天然=该用户的可见边界，这三条是**工序纪律**；多租户真隔离（账户体系/每用户一仓库）挂 D3 C 端待办，届时边界判定自动继承租户目录，纪律本身不变。

### 一个完整策略的真实骨架：三大板块（每块都要像 brief 对齐一样多轮深挖）

对照真实办公室的策略产出（用户定性·非简化流程），一份策略从来不是「方向对齐 + 一份十几页大纲」，而是三大板块依次铺开，**每块都独立经过多轮对齐**、**每块成稿都可能是十几二十页**（不是一带而过的一两页）：

1. **策略研究 / 诊断**：市场数据 + 用户/受众分析 + 痛点与背景铺垫。**必须是真材实料**（联网调研·见 `engine/research.py` claude-websearch provider），不能凭 brief 词句反推。这是后面一切的地基——大 idea 没有研究支撑就是空中楼阁。
   > **两档研究深度（2026-07-01 用户拍板：把 `/yanjiu` 的研究纪律赋予各角色）**：日常单点数据/
   > 事实查证走 `claude-websearch`（WebSearch/WebFetch·快·免费）；遇到**consequential 的关键
   > 判断、本 deck 没有框架卡背书的陌生方法论、或需要多源交叉验证才敢下结论的论断**时，直接
   > 调用 `/yanjiu` 技能——不是随手搜一次就采信，是按它的保真度铁律（核实原始证据·别只抄名字
   > 丢机制·对照这份 deck 已有的结论看是否站得住）产出更扎实的判断，不必等 leader 或用户特别
   > 要求，角色自己判断"这个论断够不够 consequential 值得多花一轮"。这条纪律覆盖研究板块全部
   > 角色，不是给某几个角色单独加的能力。
2. **核心 Idea**：围绕研究里找到的关键洞察，提炼大 idea——**可能有多种表达形式/角度**，要拿出来和用户反复论，不是想到一个就定一个。
3. **执行**：围绕定下的 idea，铺开非常具体的执行内容（落到模块、页面、细节）。

**纪律**：① 板块按顺序推进，**前一板块没和用户对齐完，不开始下一板块**（研究没扎实，idea 提炼也立不住）。② 每板块内部也是「一个问题 + 摊功课 + 用户定」的多轮对齐，不是一板块一轮就过。③ 板块产出量级要匹配真实工作（一份认真的策略研究本身可以是十几页：市场数据页 + 受众洞察页 + 痛点页…），**不要因为"这是 demo/测试"就自动缩水成一页一句话**——除非用户明确说要简化。④ 当前阶段做实/创意提案型 deck 也适用本骨架（议题树里"怎么赢"对应执行板块的验证逻辑，但研究板块 = 市场/竞品/受众洞察，idea 板块 = big idea，不可省略）。
> ⑤ **一个论点 ≠ 一页（写死·"一组证据合围"原则在页面尺度的延伸）**：研究板块每条**承重论点**（少了它整个论证就垮）不能压成一页一句话——该拆成 **2–3 页从不同角度**（宏观数据 / 具体案例或事件 / 对比或调研）把它做实，再过渡到下一个论点。判断标准：**单页扛不扛得住"凭什么信这个"的追问**——扛不住就拆页补证据，不能因为是 demo/测试就自动收窄。同一原则也适用 idea / 执行板块的承重页。

**多角色策划团队（2026-07-01 用户拍板+同日追加三处·`reinforce/planning_team.py`）**：三大板块
不是一个人从头包到尾——`ROLE_CATALOG` 按板块分组了策划角色：
- **研究板块**（7个·2选，按 deck 类型挑）：广告campaign向——市场策划/人群策划；
  **咨询/投行/尽调向**（`/yanjiu` 四路联网调研 McKinsey/BCG/Bain、IB/PE、企业战略、pitch deck
  服务后新增，每条带真实来源见 `specs/决策记录.md` D10）——行业专家策划/商业尽调策划/
  财务尽调策划/法务尽调策划/数据建模策划。
- **Idea板块**：创意策划。
- **执行板块**（**广告campaign专属，咨询/投行/企业战略类deck通常整个跳过**——四路调研独立一致
  显示这类deck根本不经过"媒介执行"环节）：媒介策划/线上推广策划/线下推广策划。
- **整合收尾板块**：叙事策划——读全部角色产出，把内容顺成一份连贯 storyline，桥接到阶段4，
  永远排接力链最后一个（真实企业里 Chief of Staff 承担同一职能，见D10）。

**单会话换人设执行，不是独立多 agent**——Claude 明确切人设框定视角推进该板块的引导对齐，底层
机制不变（还是一次一个问题+摊功课+推荐+用户拍板），人设只改变"问什么/看什么信号"。角色
**严格接力**（不并行）：`start_role` 会拒绝"前面角色还没 `complete_role`就想开工"的插队。

> **刻意不做的边界**：McKinsey/Bain/JPMorgan/RBC 四家独立证实"内容定稿"和"视觉呈现"是两个不同
> 角色（甚至 McKinsey 有专职1000+人的子公司做视觉排版）——但这属于**制作工作流**的职责
> （逐页手写+chart_shapes.py+渲染自检，见 [makedeck](../制作工作流/SKILL.md)），`planning_team.py`
> 不加"视觉呈现策划"这个角色，策略层只锁 storyline 不碰视觉执行，两层边界不重复。
>
> **角色重叠二次核实（2026-07-01·D11）**：12 个角色查完不是互相独立平行的——有几对看似重叠、
> 实际是**递进关系**：`商业尽调策划` 建立在 `市场策划` 的基础研究之上（多一层投资决策级压力测试，
> 不是替代）；`线上推广策划`/`线下推广策划` 建立在 `媒介策划` 已分配的渠道之上做具体执行。这类
> 关系记在 `ROLE_CATALOG` 的 `builds_on` 字段里，`validate_planning_team` 会在漏带前置角色/顺序
> 反了的时候给 warn（不阻断——允许有意跳过，比如市场研究已经在别处做过）。`数据建模策划` vs
> `财务尽调策划`、`市场策划` vs `行业专家策划` 这两对二次核实后确认边界清晰（前瞻建模内部亲自做 vs
> 回溯验证常外包；调研产出的事实 vs 从业经验带来的判断），维持独立不合并。
>
> 🧮 **数据建模策划的确定性算数工序（D26 接线·此前 `engine/financial_models.py` 零调用是孤岛）**：
> 做估值/融资/尽调类 deck 需要 DCF/LBO/可比公司分析时，**数字必须来自确定性引擎，不许模型口算**
> （同 `chart_shapes.py` 一个设计原则——LLM 定叙事、代码算数字）：
> ```python
> from engine.financial_models import dcf_enterprise_value, dcf_terminal_value_gordon_growth
> tv = dcf_terminal_value_gordon_growth(final_year_fcf=1420, wacc=0.11, perpetuity_growth=0.025)
> ev = dcf_enterprise_value(fcf_by_year=[820, 990, 1150, 1300, 1420], wacc=0.11, terminal_value=tv)
> # 结果进 storyline evidence（source 标"内部测算·DCF模型"·client_provided 口径不上页脚注）；
> # LBO 用 lbo_returns_summary、可比公司用 comps_implied_valuation_range——签名见模块 docstring
> ```
> 非估值类 deck 用不到就不用——这是工具不是必经步骤（简单需求轻角色组合口径不变）。

**交接四段式（结构化，不是自由文本一段话·D18 FR1.1 起 user_summary 必填）**：`complete_role(team,
role_id, key_findings=[...], decisions=[{"question":..,"answer":..}], open_questions=[...],
user_summary={"conclusion":.., "highlights":[...], "next_step":..})`——`key_findings` 扫读友好的关键
产出清单；**`decisions` 是这个角色引导对齐过程中用户已经拍板的事，下一个角色开工前必须先读
`all_decisions_so_far(team)`，不能对同一件事再问用户一遍**（用户原话"防止...交接角色的时候导致
原角色信息丢失"，这条字段专门堵这个漏洞）；`user_summary` 是**摊给用户看的**（一句话结论+3-5条
关键发现+建议下一步·为空拒绝 complete·工序见阶段1结尾"每角色收工工序"）——前三段给下一个角色读，
这一段给人读，别混着写；`handoff_briefs_for(team, role_id)` 给的是**全部**
前序角色的交接，不是只给上一个角色的——"1+1累积"，越往后角色看到的上下文越完整。

**落盘防丢失**：交接内容不能只指望对话记忆——本会话可能被自动压缩，早前角色的细节会被压没。
每个角色 `complete_role` 后应 `save_team(team, path)` 落盘（校验通过才写·fail-closed），新角色
开工前先 `load_team(path)` 读回，不是纯靠"记得住"。哪些角色参与、什么顺序，是阶段1"leader拍板"
这一步定的，见下方阶段1结尾。

### 发散工序：方向卡制（D18 FR1.3·策略不许单主线一条道走到黑）

第一轮实测确诊：策略从头到尾单主线推进、用户全程没见过"还有哪些方向可选"——发散环节现在是
**机制**不是自觉。**两个默认发散点**（缺一不可·都是硬停点）+ leader 按单加点：
1. **研究群收工后·策略方向发散**：全部研究角色 `complete_role` 完、进 Idea 板块之前——基于研究
   `key_findings` 发散出 N 个可选策略方向；
2. **创意概念前·创意发散**：策略方向定稿后、创意策划产出概念之前——同一个策略方向下发散 N 个
   创意概念方向。
其余发散点 leader 在分配角色时按单规划（**每个研究角色出口都挂发散能力**，认为值得就提议加点），
用户也可随时喊"这里给我发散一下"。

**工序（每个发散点跑一遍）**：
```python
from reinforce.strategy_prompts import prompt_divergence     # prompt_divergence(node, findings_digest, n_cards=3, history=None)
from reinforce.planning_team import new_direction_card, record_divergence, divergence_history
# ① 用 prompt_divergence("策略方向", findings_digest=各角色 key_findings 摘要,
#                        history=divergence_history()) 引导自己发散——divergence_history() 跨 deck
#    扫 data/decks/*/team_state.json（含已 published·无需传参），把用户历史收敛理由**原话**注入
#    prompt（D19 FR4.2·只回原话不做画像——2 条样本抽象必歪，等 5+ 条再人工评估），别再推用户
#    明说过不要的方向；每张卡必须实评执行难度（团队能力/预算/周期/供应链依赖四维·结果由 fit
#    字段承载）且 N 张卡难度**拉开梯度**（D19 FR4.1·不许全是高难炫技——059 实测三张卡两张被
#    用户拍回"执行难度太高"）。
#    产出 N 张方向卡（默认 N=3·七参数全必传，validate_direction_cards 组级校验 ≥2 张且不重名）
cards = [new_direction_card("社媒声量突袭",                        # name 方向名
                            "一句话核心逻辑",                       # core_logic
                            ["精酿品类 CAGR 12%…"],                # supporting_findings·引用已收工角色 key_findings 原文
                            "打法概要",                             # play_summary
                            "为什么可能赢",                         # why_win
                            "主要风险",                             # risks
                            "适配度：预算/周期/品牌调性怎么匹配"),   # fit
         ...]
# ② 把 N 张卡**摊给用户**（每张：方向名+核心逻辑+为什么可能赢+风险+执行难度——不是只报名字
#    让用户盲选）；收敛动作用 AskUserQuestion 工具呈现（D19 FR2.1·用法示意见本节末）
# ③ 硬停等用户收敛拍板（发散点=硬停点·record_divergence 的 user_quote 必填——唯一例外是
#    direct_through 直通档：AI 按推荐代拍 auto_decided=True，进假设台账不硬停·D21）
# ④ 留痕：选了哪个+为什么（FR6.4 选择偏好内化·divergence_ledger 精简台账供回灌飞轮消费）
record_divergence(team, "策略方向", cards, chosen="社媒声量突袭",
                  reason="预算撑不起双线，声量阵地已经在小红书",   # 用户为什么选它·飞轮最金贵的知识
                  user_quote="用户拍板原话")
# 直通档代拍（D21）：record_divergence(team, "策略方向", cards, chosen="社媒声量突袭",
#                  reason="AI 代选理由：三卡中唯一有竞品不可复制的护城河", auto_decided=True)
# ——user_quote 必须留空（绝不编造用户原话），条目自动带根授权原话；不回灌偏好、不进历史注入
# ↑ 收敛即确认：record_divergence 自动 record_user_ack(team, "方向收敛:策略方向", ...)，
#   发散点的 ack 不用再手记一遍；chosen 也可以是 "混合:要A的打法+B的渠道"（不硬逼二选一）
```
**纪律**：① 方向卡的 `supporting_findings` 必须引用已收工角色的 key_findings（发散不是凭空脑暴，是研究
支撑的分叉）；② 用户拍板前**绝不带着某个方向继续推进**（发散点=硬停点；`direct_through` 直通档
除外——那是用户亲选的代拍授权，AI 选定即推进+记假设台账·D21）；③ "为什么选它"跟
"选了哪个"同等重要——不记 reason 的收敛对飞轮是废数据（直通档 reason=AI 为什么代选，同样必填）。

**方向卡收敛的 AskUserQuestion 用法示意（D19 FR2.1·工序描述·不是可执行代码）**：
- **正文先摊满功课**：N 张卡逐张贴完整（方向名/核心逻辑/为什么可能赢/风险/执行难度档位）——
  工具的 option 是"选择动作"的载体，不是功课本体的载体，别把整张卡塞进 description 就算摊过了；
- **question**：「三个方向的完整功课都在上面了，这单走哪个？」；
- **options 每张卡一项**：label=方向名（如「社媒声量突袭」），description=一句核心逻辑+执行难度档
  +主要权衡（如「声量阵地已在小红书·执行难度：低·风险：品类噪音大」）；推荐项 description 开头
  标「推荐：」+一句理由；
- **额外加一项兜底**：label=「要混合或都不满意」，description=「说说想怎么组合、或哪里不对，我再
  发散一轮」——明示不硬逼 N 选一（`record_divergence` 的 chosen 本就允许"混合:要A的打法+B的渠道"）；
- **收敛后补一问"为什么选它"**：工具收的是选择，`record_divergence` 的 reason/user_quote 要的是
  **用户原话**——别拿选项 label 充当 reason（那对飞轮是废数据）。

### 阶段 1 · 判目的 + 定模式 ｜闸：目的卡填全 + delivery_purpose/mode 两轴锁定（visual_style 美学轴记倾向）
解析 brief（PDF/Word/PPT → LLM-ready；PDF 复杂版式/表格推荐 `parse_brief(prefer_docling=True)`，
2026-07-01 起 docling 是验证过能用的增强路径，MinerU 因 Python 3.14 硬不兼容暂不可用，见 D13）。判：① 推动什么决策 ② 受众 ③ 场景 ④⑤⑥ **三个独立的轴**（D18 FR7.1·分开问·**一次一个问题**，别合并成一轮；每轴都是拍板题→用 AskUserQuestion 摊选项·D19 FR2.1）：
- **delivery_purpose**（密度轴·本阶段锁定）：**三选一**——演讲版 / 阅读版 / **预读讲解版**（07 总开关·决定密度/节奏/留白·双模式真样本背书，第三态用户真实场景背书·D19 FR3）。
  **预读讲解版**（D19 新增第三态）="先发客户自读、看完再开会由我们讲"的交付形态（第二轮实测用户
  真实场景·此前在两态间没有归宿）：密度取中（比阅读版略疏、比演讲版满）/subtitle 导读保留（支持
  自读）/备注按现场讲写（支持后讲）/节奏要转场不强制情绪页（`check_rhythm` 柔化分流）。问询时
  **三态都摊**（信号与边界判法见 07 方法论〇节和四节），别只给两个旧选项。
  ⚠️ 2026-07-02 前这个轴借宿在 `visual_style` 字段里——D18 FR7.1 改名归位，旧落盘数据兼容读
  （`delivery_purpose_of(sl)` 统一读口），**新代码/新示例一律写 `delivery_purpose`，别再把密度值塞给 visual_style**。
- **mode**（论证轴·本阶段锁定）：pyramid/narrative/briefing/showcase 四选一（08 方法论·决定怎么论证/标题语态·来自 ppt-master·强候选）。
  自动选型信号（08 方法论详表）：决策支持/分析/董事会 → `pyramid`；pitch/案例/融资 → `narrative`；
  状态汇报/参考资料/周报 → `briefing`；发布会/品牌揭幕 → `showcase`。两个信号都强时，正常推荐+权衡，用户拍板。
- **visual_style**（美学轴·本阶段只记倾向，不锁）：deck 长什么样——18 份风格手册
  （`engine/ppt_master/references/visual-styles/*.md`：swiss-minimal/editorial/dark-tech/zine…）之一。
  **锁定动作发生在制作工作流的「设计定稿」（阶段 1.5·FR7.2 三档风格人格光谱·用户拍板后进 spec_lock）**，
  策略阶段若 brief/用户已流露倾向（"要杂志感""别做成咨询灰"），记进 decisions 传下去，别当场锁死。
  「mode = 怎么论证，delivery_purpose = 交付密度，visual_style = 长什么样」——三轴正交，任意组合。
```python
from reinforce.storyline_state import new_storyline
sl = new_storyline(brief, purpose="说服董事会批专项", intent="说服决策",
                   audience=["董事会"], decision_ask="今日批准", domain="财务",
                   delivery_purpose="演讲版", mode="pyramid",   # ← 两轴都要动手前跟用户确认·分两轮问
                   brand="客户品牌本名")   # D19 FR5.1：brand 在交棒时自动生成 outline.brand_terms
                                           # 品牌名豁免表——"059"类含数字品牌名不再被文字机检当统计数字
```
🚪 **闸**：目的卡（purpose/intent/audience/decision_ask）填全 + `delivery_purpose` ∈ {演讲版, 阅读版, 预读讲解版}（D19 FR3 三值）+ `mode` ∈ {pyramid, narrative, briefing, showcase}。缺则追问，绝不凭空开做。美学倾向有则记录、无则留给设计定稿，不闸。

**leader 开场第一问：确认粒度（D18 FR1.2·分配角色之前先问这个）**：切到"leader"人设后的**第一个
引导对齐问题**不是角色分配，是"这一单你想怎么跟我确认"——四档用 AskUserQuestion 摊给用户（D19 FR2.1·每档一个 option：label=档名，description=理由+权衡，推荐档标「推荐：」；照例先在正文摊功课）。
**开场固定动作：品牌素材收集点提示（D22b·D27 升格为无条件必说·提示不是问题·说完继续不停顿）**
——问粒度的同一段正文里告诉用户：「有品牌素材（VI 手册/logo/KV/品牌字体文件/历史 deck）可以直接
丢进 `data/decks/<deck_id>/brand_assets/` 文件夹（建家时已备好·里面有说明），制作视觉时会优先按
你的品牌资产锚定（比联网查证更准）；没有也不影响，我会联网查证品牌官方色。」
⛔ **这句提示任何情况下不许裁剪**（D27·第七轮某品牌单确诊：会话见目录里有既往月报可延续视觉，就
自作主张"这点比较确定，不单独展开问了"跳过了提示——而用户手里其实有官方 VI 手册+字体文件。
**历史 deck 可延续版式 ≠ 品牌资产全集**：标准色号、官方字体文件、VI 规范只有用户有，目录里翻不
出来。延续历史视觉与提示投素材是两件事，前者不豁免后者）。素材随时可补投——制作阶段 1.5 设计
定稿前放进去都来得及（晚投也有兜底：素材在场而色板来源没用它，build_deck 开工直接 error 拦下·
D27 机检）；直通档用户则在开场配置舱这轮一并提示（起飞后没有交互窗口了）：
1. **`every_role`（逐角色停）**：每个角色收工摊完结论就硬停，等用户回应才开下一个角色（最重·适合第一次合作/高 stakes）；
2. **`key_nodes`（关键节点硬停·默认·用户不选就是它）**：只在关键节点硬停等拍板——**全部发散点 /
   设计定稿（制作阶段 1.5 风格光谱确认）/ 每 Part 定稿（阶段 4 逐 Part 摊面·D20 FR4.2·Part 有几个
   就停几次）/ storyline 定稿 / 交棒制作**五类；角色收工照样摊结论（铁律 0 不豁免），用户不喊停就
   继续推进。⚠️ 口径边界（如实写）：Part 定稿的 ack 是**留痕不进交棒闸**——`handoff_to_production`
   的 ack 闸只查「storyline定稿」一个节点，Part ack 缺了闸不拦（防代填的根本解不在本期）；但工序上
   它跟其他关键节点同一条纪律：user_quote 必须是用户确认原话，不可代填；
3. **`minimal`（少打扰·用户自己选的快进档）**：非关键节点一律不停不追问，**交棒 ack 闸也放行**
   ——之所以敢放，是 `granularity_quote` 留了用户亲口选快进的原话，事后可回放"当初是用户自己要
   快进的"；发散点收敛照样必须 `record_divergence`（它的 user_quote 必填参数天然强制留痕，不随档位豁免）；
4. **`direct_through`（直通档·D21·2026-07-03 用户拍板"直通档就是字面上的直通，问完直接到出成品"）**：
   **开场配置舱问完后全程零停顿直到成品交付**。配置舱（D22·第五轮实测"直通版无法选排版风格"的解
   ——审美是纯偏好不是优劣判断，AI 代拍代不准）=选中直通后紧接的最后一轮 AskUserQuestion，两道视觉
   题一次摊：①**风格大方向三选**（克制专业 / 图文并茂 / 大胆吸睛——制作侧在所选方向内按策略内容
   自动锁定 18 风格之一，不再问）②**视觉丰富度三档**（素雅/标准/浓郁——先调
   `engine.chart_template_map.default_richness_for(目的)` 拿类型默认档+一句为什么，推荐项标出来）。
   两个选择记入 storyline 的 `richness`/美学倾向字段（交棒卡自动透传制作侧）。配置舱之后——
   发散点不再硬停，AI 按推荐方向代拍
   `record_divergence(..., auto_decided=True)`（reason=AI 为什么代选·必填；条目自动带根授权原话；
   **代拍决策不回灌偏好、不进跨 deck 历史注入**——飞轮只学用户亲手拍的，否则学到的是 AI 自己的偏好）；
   storyline 定稿不等 ack **直接交棒进制作工作流**（跨流直通·不等用户说"做 deck"），设计定稿由 AI
   在配置舱选的风格方向内自动锁（含品牌视觉锚定·见制作 SKILL 阶段 1.5），人审闸走
   `publish_deck(direct_through_waiver=根授权原话)` 豁免（如实留痕
   "未经人审·依据哪句授权发布"，不伪造勾选）。**交付时必摊 `assumption_ledger(team)` 假设台账**——
   AI 代拍过哪些方向、为什么，用户从过程操盘换成验收操盘，重点核对代拍项。适合简单需求/不想动脑子
   的场景；开场摊这档时**一句话提示权衡**（brief 解读若偏、全 deck 跟着偏，高 stakes 比稿慎选），
   提示本身在开场那一轮内完成，不新增停顿。唯一还会停的情况：缺**只有用户才有**的关键信息（白名单⑥）。
用户拍板后记入 team_state（user_quote 传用户选择原话·留痕不是走形式）：
```python
from reinforce.planning_team import set_confirm_granularity
set_confirm_granularity(team, "key_nodes", user_quote="按默认来，关键的地方叫我")
# 档位枚举 GRANULARITIES = ("every_role", "key_nodes", "minimal", "direct_through")·非法值直接 ValueError
```
之后每到一个关键节点，拿到用户确认后用 `record_user_ack(team, node, user_quote)` 留痕（node 如
"storyline定稿"/"设计定稿"，user_quote 必须是用户确认原话，不可代填/编造——存原话不存布尔位，
True/False 自己就能悄悄置上，原话才证明用户真说过；交棒 ack 闸只认这里的记录）。

**leader 拍板策划角色（确认粒度定了之后·还没进阶段2前）**：看这份 deck 的
domain/decision_ask/scene，推荐一个角色子集（不是每次 12 个全员出动——比如内部复盘 deck 通常只需要
市场策划+人群策划，不需要创意/媒介/推广/尽调角色），**给推荐+理由+权衡，用户拍板增删**，同 mode/delivery_purpose
一样是引导对齐项不是自动选。**leader 同时按单规划发散点**（两个默认点之外要不要加，见下方"发散工序"）。
拍板后按用户确认的顺序落到 `assign_roles`：
```python
from reinforce.planning_team import assign_roles, new_planning_team
# 例①：品牌campaign提案(mode=narrative)
team = new_planning_team(sl["purpose"])
assign_roles(team, ["市场策划", "人群策划", "创意策划", "媒介策划", "叙事策划"])
# 例②：并购尽调向投委会推荐(mode=pyramid)——不带广告campaign三角色，换成尽调向
assign_roles(team, ["商业尽调策划", "财务尽调策划", "数据建模策划", "叙事策划"])
```
之后每进入一个板块：先切换对应角色人设、`start_role` 开工，工作前先读 `handoff_briefs_for` +
`all_decisions_so_far`（**不重新问用户已经拍板过的事**），收工用 `complete_role` 留结构化交接
（key_findings/decisions/open_questions/user_summary 四段都要给，不是随手写一句话·见下方
"每角色收工工序"），存盘 `save_team`。
**「叙事策划」收工 = 阶段4 storyline 搭建完成**——它的工作就是把 `handoff_briefs_for` 读到的全部
角色 `key_findings` 编织进 `storyline_state.add_line`，按 SCR/框架弧排页序，衔接下方阶段4。

**每角色收工工序（D18 FR1.1·结论强制·fail-closed）**：`complete_role` 增加**必填** `user_summary`
（不填直接拒 complete，第一轮实测确诊"角色闷头收工不摊结论就推进"违铁律 0）：
```python
from reinforce.planning_team import complete_role
complete_role(team, "市场策划",
              key_findings=["精酿品类 CAGR 12%·CNY 档期社媒声量集中在小红书", ...],
              decisions=[{"question": "对标品牌范围", "answer": "只对标国产精酿前 5·用户拍板"}],
              open_questions=["KOL 预算区间 brief 未给·留给媒介策划追问"],
              user_summary={"conclusion": "一句话结论：品类在涨但声量阵地已转移到小红书",
                            "highlights": ["发现1", "发现2", "发现3"],      # 3-5 条关键发现
                            "next_step": "建议下一步：人群策划接手锁定核心人群画像"})
```
收工后**必须把 user_summary 三件套原样贴给用户**（结论 + 关键发现 + 建议下一步——是"贴出来给人看"，
不是存进 JSON 就算摊过了），然后按确认粒度决定停/不停：逐角色停档=硬停等回应；默认档=摊完继续，
用户随时可打断纠偏。

### 阶段 2 · 结构化思维 ｜闸：议题树/假设树 MECE + 可证伪
用 `issue_tree` 把问题空间 MECE 拆解（还不知道什么重要 → 议题树；Day-1 押答案 → 假设树）。
```python
from reinforce.issue_tree import new_tree, add_branch, to_sub_hypotheses
from reinforce.storyline_state import set_hypothesis_tree
t = new_tree("Q3 增长健康吗", mode="假设树", hypothesis="增长是虚假繁荣·需批专项止血")
add_branch(t, "H1", "成本增速>收入增速", "成本50% vs 收入25%", "高")  # test=能杀死它的检验
add_branch(t, "H2", "失控在人力", "人力占比42%→58%+人均-12%", "中")
add_branch(t, "H3", "明年由盈转亏", "净利率外推+敏感性", "低")        # 先打低信心分支
set_hypothesis_tree(sl, "增长是虚假繁荣…建议批专项", to_sub_hypotheses(t))
```
🚪 **闸**：`validate_tree` valid（3 分支法则 + 每末端可证伪 + 假设树有 Day-1 答案）。
⏭ **真实客户项目**：树定稿后记得跳到收尾节「客户回灌知识库」的 `record_issue_tree_fingerprint`
步骤留结构指纹（跨客户复用侦测·只存形状指纹+品牌不存内容）——那节整体虽是"交棒后"跑，这一步
的时点在**阶段2 当下**，别等收尾才想起。
拆分支前用 `reinforce.strategy_prompts.prompt_stage2_tree(purpose, domain=[...])`——传了 domain
会自动检索分析框架库（88 张真实 deck 抽取+联网调研核实的可复用分析/策略思考工具，如双情景分析法/驱动因素归因
乘数法）拼进返回的 prompt 文本，省掉从零现造分析角度的功夫；不传 domain 或无命中就正常现拆，
不强求套现成框架。**⚠️ 这不是像制作层 `build_deck_prompt` 那样的强制编排**——策略层没有自动
pipeline，这个函数要主动调用才生效，别指望"不调用也自动检索"。

**页数区间引导对齐（2026-07-01·假设树定了才问篇幅，不是阶段1一上来瞎猜）**：假设树校验通过后，
用 `reinforce.strategy_prompts.prompt_stage2_page_scope(governing_thought, sub_hypotheses, scene=...)`
生成内容感知的推荐——不是甩给用户一个抽象数字，是基于已拆的 N 个分支算出"最少 N+2 页讲完覆盖什么"
+"可扩展项覆盖什么"，摊功课给用户拍板一个 `expected_pages=(min, max)`，回填进
`new_storyline(..., expected_pages=(min, max))`。阶段4 storyline 定稿时
`deck_rules/storyline.py::check_page_count_consistency` 会核对实际页数有没有跟这里定的差太多。

### 阶段 3 · 调研 + 数字溯源 ｜闸：关键数字可溯源
用 `reinforce.strategy_prompts.prompt_stage3_research(claim, domain=[...], current_year=当前年份)`——
传了 domain 会自动检索行业知识库（79 条真实 deck 抽取+实测回灌的行业事实，含 source_citation/timeliness）
拼进返回的 prompt，能直接用的就省一趟外部调研；传了 current_year 会自动用 `flag_stale_facts` 标出
候选里明显过期（timeliness 年份距今 ≥2 年）的条目，标了"⚠️疑似过期"的要么去联网换最新数据，
要么在页面上明确标注"历史参考"。**引用前仍必读 timeliness 字段**——过期标记只覆盖能抽出年份的
条目，"无具体年份标注"这类不参与自动判断，得人眼判断。

**知识库没覆盖的论断，Claude 当场用 WebSearch/WebFetch 挖**（`provider="claude-websearch"`——
2026-07-01 用户确认：本项目自己就是这么调研出商业尽调/财务尽调等 44 张框架卡的，免费、不需要
额外 key，不是没验证过的空想）。`provider="gpt-researcher"`（第三方包+独立 LLM/搜索 key）是
**🧭能力边界·待用户愿意为调研深度多花钱再启**（`specs/决策记录.md` D6），不是当前默认路径，
示例代码不要再写它——历史上这里错写过 gpt-researcher，写代码/教下一个人时留意别抄旧例子。
```python
from engine.research import research, attach_citation
r = research("人力成本占比趋势", provider="claude-websearch", today="2026-07-01")
# ↑ 只是记一笔"这条走了免费路"；真正挖数据是 Claude 当场调 WebSearch/WebFetch，查到后用
# attach_citation 带全 source_title/outlet/date/quote/url（quote 必须是真实网页原文摘录，不可编造）：
ev = attach_citation({"dim": "人力占比", "data": "42%→58%"}, title="...", outlet="...",
                      date="2026-...", quote="原文摘录", url="https://...",
                      source_type="external")   # D18 FR5.1·来源分类，决定对客呈现方式，见下
```
**溯源分类（D18 FR5.1·每条 evidence 都要标 `source_type`·决定"页面上怎么呈现"）**：
- `external`（外部公开数据·联网调研挖来的）：制作层会给页内脚注（来源名+日期）+ 尾页 references
  完整 URL——**客户能点开验证**，这是"外部数据可信"的呈现方式；
- `client_provided`（客户内部资料·brief/客户报表里来的）：**页面不标任何来源**（客户自己的数
  据标"来源：brief P3"是把工作定位符暴露给客户看·第一轮实测确诊的对客语言事故），内部
  `asset_ledger` 溯源台账照记不误——"页面不标"≠"不溯源"。
- "brief P3-4"这类**工作定位符永不上页**，它们只许活在 sowhat/speaker_notes/工作档案里（FR5.3 语域建模，详见阶段4）。
🚪 **闸**：`check_evidence_source` 无报错——每个带数字的 evidence 有 source（防编造·01 雷区7）。⚠️ 调研工具 fact-check 是 LLM 自评，**不当 🟢 硬信号**。
⚠️ **时间锚定（真实踩过的坑）**：搜索前先确认当前日期，**"某年预计"一旦那年已过去必须换成实际数**——否则会在客户面前露怯"调研没做新鲜"。

**两层防假阳（2026-07-01·Auto-Slides 启发；2026-07-02 真接线）**：evidence 用 `attach_citation()` 带了
`source_quote`（原文摘录）时，`check_facts_grounded` 核验 evidence["data"] 里的数字是否在原文里字面
出现过（如 LLM 引用时悄悄把 42% 写成 45% 会 warn）；`check_evidence_directions` 查方向词与数字增减
是否矛盾（写"提升"但 58%→42%）。**两条都已接进 `run_storyline_gate`，阶段 4 闸和交棒时自动跑，
不用手动调**（2026-07-02 saopan扫盘揪出：此前这段用"会核验"的自动语态、实际全仓零调用点——文档
喊自动、代码没人调，孤岛第 4 次复发；现在接线了这句话才是真话）。warn 喂人审。只在带了
`source_quote` 的 evidence 上生效，不强制所有 evidence 都要有原文摘录。

**调研进展播报（D20 FR4.1·不停但可见）**：调研深化是全流程最长的静默段（第三轮实测：从页数确认到
storyline 之间用户在输出流里零参与感）——**每个研究议题查完，给用户一行进展播报**：一行结论式
（「✓ 竞品定价已查：3 家均价 15-25 元，比客户高 30%」），不贴全文、不硬停、不追问（停不停是确认
粒度管的事），只保证用户看得见调研走到哪了、随时可打断纠偏。逐议题播报，不是全部查完才冒一句。

### 阶段 4 · Storyline（按 Part 编写·D20 FR4.1）｜闸：validate + run_storyline_gate 全过（含 Part 结构硬门）
每行=一页：论点（claim）+ **一组证据合围**（evidence·覆盖反驳角度）+ **framing**（立场 + 反方）+ page_type（节奏角色）+ subtitle（阅读版/预读讲解版导读·D19 FR3）+ **part（章归属·D18 FR2.1）**。

**🔒 Part 级编写节拍（D20 FR4.1·阶段 4 的编写顺序就是这个，不是可选项）**：第三轮实测确诊
「中后段零交互」——前段问答工具用了 4 次，但从页数确认到完整 storyline 之间（全流程最重的段落）
没有任何设计的交互点，7 个角色收工"贴完就走"，用户无参与感、无法中途纠偏。解法对齐制作层
"写一页渲一页检一页"与小说引擎"5 章节拍"的同款纪律——**绝不逐行闷头写完 40 页再让用户第一次看见**：
1. **先出 Part 骨架摊给用户确认**：几个 Part、各自一句话主张、页数怎么分——这一摊在动笔写任何行
   之前（骨架错了逐页返工是 N 倍成本）；
2. **逐 Part 写，每写完一个 Part 摊给用户**：写完该 Part 全部行（章封面/转场 → 洞察陈述 → 证据展开
   → 章小结）后，把 **Part 主张 + 页序 + 每页一句话 claim** 摊成人能扫读的清单（不是甩 JSON），用
   AskUserQuestion 确认/纠偏（D19 FR2.1 拍板题工具化·选项如「这个 Part 定稿，写下一个」/「哪页要调
   （选这项后说哪页）」），拿到确认当场留痕，再写下一个 Part：
   ```python
   record_user_ack(team, f"Part定稿:{part名}", user_quote="用户确认原话")   # node 约定：Part定稿:市场诊断
   ```
   ⚠️ 边界（如实写）：Part ack 是**留痕不进交棒闸**——交棒 ack 闸只查「storyline定稿」，Part ack
   缺了闸不拦（防代填的根本解不在本期）；user_quote 照样必须是用户原话，不可代填。
   `minimal`/`direct_through` 两档快进不逐 Part 停（用户亲口选的），`key_nodes`（默认）/`every_role` 档逐 Part 摊面是硬工序；
3. **全部 Part 写完才走下方既有定稿闸**（validate + run_storyline_gate + 阶段 5 三道审查 + 用户拍板）
   ——Part 级确认不替代整体定稿：Part 管"这章内容对不对"，定稿闸管"整份叙事连不连贯 + 机检全过"，
   两层各管各的。40 页 deck ≈ 4-6 个 Part = 4-6 次确认，这正是用户要的参与感（需求 §五）。

**Part 结构工序（D18 FR2·storyline 必须按章规划，不是 24 页平铺）**：真实 4A deck 是
"封面→目录→[Part×N]→收尾"的章节结构（某品牌/Lulu/某品牌/MTA 四真样本交叉实证）。规划时**先定 Part
再填页**，每个 Part 内按范式走：**章封面/转场 → 洞察陈述（含来源）→ 证据展开（2-3 页合围）→
章小结（结论先行 + 抛下章钩子）**。落到 `add_line`：
- 每页填 `part="市场诊断"`（章归属·封面/目录/收尾这类 deck 级页可不填）——**页数 ≥12 的 deck 必须
  分 Part**（一个 part 都没填直接 error；<12 页的短简报允许无章节，硬纪律 4：简单需求不加锁）；
- 转场页（page_type="转场"）必填 `bridge_from="承接上章结论的一句话"`（某品牌 章封面淡灰副标机制——
  空转场只是换个背景色，没有承接价值）；**首个 Part 的转场豁免 bridge_from**（前面没有章可承接，
  硬要一句反而逼人编造）；
  **bridge_from 写作指引（D20 FR1.1·本 SKILL 旧示例的"锁定体"正是三轮实测确诊的元叙述源头）**：
  承接的是**内容**不是**工序**——只有两条合法通道，都用内容实体词承接（Minto referencing backward：
  用上章结论里的业务实体承接，不用文档部件词）：
  ① **内容实体词接力**：上章末句立起的实体，下章开头接着用（真样本：某品牌 2025 IMC p7「生活的乐趣
  在减少」→ p8「城市里不再被人使用的电话亭……就像生活的乐趣也并没有消失」）；
  ② **内容设问**：回顾上章内容成果一句，把下章要回答的问题抛出来（真样本：thoughtbox 某品牌 p63
  「某品牌的电音派对、多元宇宙、CLUB 联动…——该如何占据暑期社交场的一席之地？」）。
  **禁工序完成时态词**：「已锁定 / 已定位 / 诊断完毕 / 定案 / 收口 / 进入下一部分」是在播报工作
  流程不是在讲客户的生意——落进 bridge_from 一律重写（这类"文档部件词 × 过程时态词"组合也会被
  对客文案门的元叙述检测拦，见语域规范）；
- 每个 Part 必须有**章小结**行——约定写法：`add_line(..., role="章小结", ...)` 或 page_function 含
  "小结"（机检按这两个字段判定，别只在 claim 里写"小结"二字）；
- **页数 ≥12 必排目录页**：`add_line(sl, 2, ..., page_type="目录", toc_items=["市场诊断", "人群洞察", ...])`，
  toc_items 会被 `check_toc_matches_chapters` 核对与后续转场页标题逐字一致；
- Part 首页（转场后第一页）是洞察陈述——先说"这章看出了什么"再堆证据（机检只查 claim 空不空
  [warn]，"是不是真洞察"留人审，别拿空标题混过去）；
- 结构件选型优先用库内结构卡（FR2.3·转场页/议程页/阶段总览卡已在 101 张卡内）：
  `search_deck_cards(page_function="转场页")` 检索后把卡名填进 `add_line(page_function=...)`。
⚠️ **这些不是建议是硬门**：`check_part_structure`（error 级）已接进 `run_storyline_gate`
——≥12 页无目录/无 Part 分章/某 Part 缺转场缺章小结，**交棒 `handoff_to_production` 时直接被拦**
（存量 storyline 重跑被拦是预期行为·需求 §七），不要等制作层才发现结构塌了。

**语域规范（D18 FR5.3 + FR5.1·写 storyline 时就分好两个语域，不是制作层再洗稿）**：
- **页面文案（claim/subtitle/evidence 的对客呈现）= 对客语域**：写成营销公司对客的**真句子**
  （"春节档声量阵地已从双微转移至小红书"），不是内部推演话术（"对齐 brief 理解·确保方向不跑偏"
  这类流程自述、GD/GX 类内部缩写、"brief P3-4"定位符——全是第一轮实测真实泄漏过的坏例子）；
  subtitle 尤其要写成**"给客户读的导读句"**，禁止字段语义直译（"聚焦判断：""开场判断："类
  标签冒号形态是第二轮实测确诊的新坏例——正反例与文案门 error 说明见制作 SKILL「subtitle=写给
  客户读的导读句」·D19 FR1.4）；
- **工作推演 = 内部语域**：放 `sowhat`（叙事作用）和 speaker_notes/工作档案，永不上页；
- evidence 逐条标 `source_type`（见阶段3：external 页内脚注+尾页 URL；client_provided 页面不标）；
- 机检兜底：`check_client_facing_tone`（D19 FR1.2 起分级——**标签冒号形态[「聚焦判断：」「立场：」
  类字段名直译]与 brief 定位符 = error·strict 拦导出**；流程自述句式/白名单外内部缩写/工作口语仍
  warn 喂人审。白名单机制控误拦：只拦"标签冒号"形态与工作短语，**不拦"我们的立场是与消费者站在
  一起"这类自然句**。坏例子清单从两轮实测起步、飞轮积累）已由 `run_client_tone_gate` 接进制作层
  `pipeline.build_deck` 逐页 gate（对渲染出的页面文字查）——但它只逮得住模式清单里的，且到制作层
  才报就晚了一个板块：**storyline 写作时就用对客语域才是本分**，机检是网不是笔。

**结构性文案写作规范（D20 FR2.2·六槽位正反速查·写目录/转场/小结/ask 行之前先读这张表）**：
第三轮实测全 40 页扫描，12 页元叙述**全部**长在结构性文案位置（目录/转场/章小结/决策前）——D18 建
的 Part 结构件成了元叙述温床。15 条真提案例句（某品牌 8x8/thoughtbox 某品牌/某品牌/LuluMP/某品牌130·
5 份真样本逐字提取）的语料结论一句话：**每句话都在讲客户的生意，不讲这份 deck 自己——结构信息走
版式组件（tracker/Part 编号/目录高亮），不写成句子**。最锋利的判据是**承接词性**：真提案用内容
实体词承接（社交场/电话亭/钱包/渠道），AI 用文档部件词承接（判断/部分/方向/页）——每写完一句结构
性文案，看一眼承接词是哪类。

| 槽位 | ✅ 真提案范式（带出处） | ❌ AI 腔禁形态（实测坏例） |
|---|---|---|
| 目录命名 | 内容词命名各章 + 句式同构（某品牌 p13「立形象，造就重庆精神骄傲 / 现场景，造就重庆生活骄傲…」）；结构导航交给 tracker 组件（McKinsey×MTA 同一 Contents 页当前章加粗，p5/p18/p29 重现） | 「这份提案想说清楚三件事：先诊断，再给方向…」（论文摘要腔·某品牌 p2） |
| 章间桥 | 内容实体词接力（某品牌「生活的乐趣」跨页接力）或内容设问（某品牌「该如何占据暑期社交场的一席之地？」）；纯章名+Part 编号+留白也合法（某品牌130「Part Background」） | 「这是这份提案的第一个判断，后面每一页都在证明它」（元叙述·某品牌 p4） |
| 章小结 | **升维再陈述、从不自称"小结"**：宣言句（某品牌 MANIFESTO「人造就越来越好的城市……致敬每个坚持创造的人」）/ 编号 A-but-B 结论（LuluMP「High on asset quality, low on creative presenting format」） | 「三条线诊断完毕：✓认知模糊是真病根…」（工序时态+打勾自查腔·某品牌 p13） |
| 诊断收束 | 一步给判断：对比定位（某品牌「相比某品牌的『彰显真我』…核心 TA 已不再需要向外索求认同」）/ 设问自答（某品牌「是什么造就重庆的骄傲？——某品牌」） | 「聚焦判断锁定：这次任务是解决情感连接缺口」（"锁定"工序时态+字段名句首·059 p7） |
| ask收尾 | SOW 清单：范围栏 × 交付物（LuluMP p35「SOW OF PROPOSAL」Strategy/UX-UI/Content 三栏）——**祈使请求句留给口头** | 「请某品牌批准，由我们担任…代理」（完整祈使请求句写上页·某品牌 p39） |
| 落幕 | 人格化告别（某品牌「回见！」）/ 呼应开篇实体（某品牌130「See you at 某品牌 WORLD」） | 「以上就是我们的完整方案」（文档自指收尾） |

写这些行之前**先检索槽位卡**（真提案槽位卡已入表达手法卡库·每张带句式公式+真实 demo 出处+禁形态对照）：
```python
from reinforce.retrieval.search import search_expression_cards
hits = search_expression_cards(slot="章间桥", top=3)   # slot ∈ {目录命名, 章间桥, 章小结, 诊断收束, ask收尾, 落幕}
```
谱系提醒（语料调研结论）：营销 deck 标题本就容忍主题词级（「巷子里的福建」合格）——别把咨询长结论
句范式套到每一页，密度过载本身就是说明书感的一部分。

**故事框架（`framework`·2026-07-01 补·出处 gist_AI-Presentation-Coach）**：`new_storyline(framework=...)` 缺省
`"SCR"`（本项目默认骨架），可选 `reinforce.storyline_state.FRAMEWORK_STAGES` 里其余 13 个（SCQA/金字塔/
Before-Change-After/ABT/Golden Circle/三幕/英雄之旅/Pixar Spine/JTBD/Challenger Sale/嵌套循环/山形/Freytag五段）。
**跟 mode/delivery_purpose 同一条纪律——引导对齐不是自动选**：按 `FRAMEWORK_PICK_WHEN[候选]` 给用户一句推荐
理由（如"案例/ROI展示 → Before-Change-After"、"电梯陈述 → ABT"），用户拍板才定，不要看关键词自动套。
每行的第二个位置参数（原叫 `scr`，现叫 `stage`）取值范围随声明的 framework 变——SCR 是 S/C/R，
before_change_after 是 Before/Change/After，以此类推，`validate_storyline` 按声明的 framework 校验弧完整+不回头。

**mode×framework 软契合提示（2026-07-01）**：两者独立锁定但不是完全无关——`validate_storyline` 会对
`FRAMEWORK_MODE_AFFINITY` 里标了"不常见搭配"的组合（如 mode=pyramid 结论先行配 framework=hero_journey
先铺垫后揭晓，叙事哲学互相拧着）给一条 warn，不阻断（人可能就是故意要试非常规组合），但生成前要看到
这条提示、确认不是选歪了没人发现。SCR 是项目默认骨架，配任意 mode 都不在检查范围内。

**page_function（页型手法·2026-07-01 补）**：`add_line(..., page_function=...)` 可选——写这一行时若已经
用 `search_deck_cards` 查过范本库、有贴切的真实卡（如"金句主张"/"案例效果against行业中位数柱状对标"），
传进来精确检索；不传时 `to_outline()` 兜底到 `page_type`（节奏角色），**别指望 `chart`（waterfall/line_compare
这类技术词汇）能查到范本卡**——两者是正交维度，chart 只管"要不要调 chart_shapes.py 算图表坐标"，
不代表"这页该长什么排版"（旧版直接拿 chart 当 page_function 检索，命中率为 0，已修复，见
`storyline_state.py` 模块顶部"page_function 怎么来"说明）。
```python
from reinforce.storyline_state import add_line, validate_storyline
from reinforce.deck_rules import storyline as SG
add_line(sl, 5, "R", "失控在人力·占比58%人均产出反降", "stacked_over_time",
         page_type="数据论断", sowhat="定位病灶", part="成本诊断",       # part=章归属(D18 FR2.1)
         evidence=[{"dim": "结构", "data": "42%→58%", "source": "报表"},
                   {"dim": "效率", "data": "人均-12%", "source": "报表"}],   # ≥2 维合围
         framing={"stance": "效率失控", "counter_read": "战略储备", "basis": "人均产出降+投向非创收"})
# 转场页示例（page_type="转场" 必带 bridge_from·写法见上方"bridge_from 写作指引"——内容设问式承接）：
add_line(sl, 8, "R", "把人力的钱从养人头挪到买产出", "none",
         page_type="转场", part="解法", bridge_from="人力占比 58% 且人均产出反降——钱到底花去哪了？")
# ⚠️ D20 FR1.1：此例旧版写的是 claim="成本病灶已定位·本章看解法"、bridge_from="…失控点已锁定"——
# "已定位/已锁定"这类工序完成时态被第三轮实测确诊为元叙述源头（059/某品牌 满屏"锁定/定案/诊断
# 完毕"与旧示例形态完全一致·一边教一边罚），别再照旧形态写：承接用内容实体词或内容设问，见指引。
v = validate_storyline(sl); g = SG.run_storyline_gate(sl)
```

**Read-Through 通读自查（D20 FR2.2·全部 Part 写完、跑闸之前·工序纪律）**：把全部行的
claim + subtitle **按页序串成一篇文章通读一遍**（出处：McKinsey Read-Through Test——只读每页标题
验证横向逻辑是否成文），自查两问：
1. **哪句在谈论这份 deck 自身而不是客户的生意？**（「这份提案 / 本章 / 第一个判断 / 诊断完毕」——
   命中的句子当场改写成内容句，改法回上方六槽位速查表）；
2. **抽掉页面只读标题，像一篇连贯的商业论证，还是像一份操作手册目录？**（后者=结构性文案在播报
   工序，逐句对照速查表返工）。
**定位边界（铁律 2·写明不许走样）**：这是**工序纪律 + 人审信号，不是机检**——"像不像论证"是
LLM/人的语感判断，绝不当自动硬门的信号；确定性形态（文档部件词 × 过程时态词组合）由
`check_client_facing_tone` 的元叙述检测在机检层兜底，两层各管各的：机检拦得住的形态它去拦，
机检拦不住的语感靠这一步通读。

🚪 **闸**：`validate_storyline` valid + `run_storyline_gate` passed——SCR 弧 / 决策结尾 / 一组证据 / framing 表态 / 三态节奏分流（演讲版全查·预读讲解版要转场不强制情绪页·阅读版不查·D19 FR3）/ 导读副标题（阅读版+预读讲解版都查）/ 数字溯源全过（error 拦·warn 人审）。**2026-07-01 起这道闸已内置进交棒函数 `handoff_to_production()`（见下"交棒"一节）——不调用它就拿不到制作层能吃的 outline，物理上绕不过去，不再只靠这里手动跑一遍自觉。这里手动跑是为了边写边看问题、及早发现，不是唯一防线。**

### 阶段 5 · 质量门 + 文字 demo ｜闸：三道审查 ≥90% + Critic 非 Red + 用户拍板
人审三道审查（机检之外的审美 / 逻辑），输出「文字 demo」给用户拍板。
```python
from reinforce.review import new_review, score_review, critic_light
rv = new_review()                              # 人勾 action_title/storyline/slide_content 各项
# … 人审填 True/False …
sc = score_review(rv); light = critic_light(sc)   # 三道各≥90% + 非 Red
```
🚪 **闸**：三道审查过线 + Critic 非 Red + **用户确认**（🟢 落在人·防假绿）。**生成 ≠ 批准**——先冻结叙事、用户改完点确认，才交制作。
定稿确认是拍板题→用 AskUserQuestion 呈现（D19 FR2.1·选项如「定稿，交制作」/「还要改（选这项后说哪里）」）；拿到用户确认后当场留痕（D18 FR1.2·storyline 定稿是关键节点，交棒 ack 闸硬查这条；user_quote 记用户亲选的选项原文，有自由补充一并记）：
```python
from reinforce.planning_team import record_user_ack
record_user_ack(team, "storyline定稿", user_quote="用户确认原话")
```

---

## 交棒 → 制作工作流
storyline 定稿（五阶段全过 + 用户确认）→ 降解交制作。**2026-07-01 起交棒必须走 `handoff_to_production()`
（不再直接调 `to_outline()`）——它降解前会先跑 `validate_storyline` + `run_storyline_gate`（含 D18 FR2.2
Part 结构硬门），质量机检有 error（如无决策收尾/缺目录/Part 缺转场小结）会直接拒绝交接（fail-closed），
不用等到制作层才发现：**
```python
from reinforce.storyline_state import handoff_to_production
h = handoff_to_production(sl, current_year=2026,   # current_year 传当前年份(查"过期预计")
                          team=team)               # team 必传（真实项目）——见下两道随 team 自动跑的闸
o = h["outline"]   # storyline → deck_outline（page_function=显式指定>page_type兜底>chart垫底，见 storyline_state.py 模块顶部）
# sl 在阶段1填过 brand= 时，outline 自动带 brand_terms 品牌名豁免表（D19 FR5.1·制作层文字机检全吃，
# "059"类含数字品牌名不再被 check_source 当统计数字）——不需要手抄
# quality_warnings 是 warn 级问题（含两层防假阳+遗留问题收口），交接前扫一眼
```
`team=team` 传入后自动跑两道收口（D18 FR1.2）：
1. **ack 闸（error·拦交棒·宁拦勿放）**：`user_acks` 里没有「storyline定稿」节点的 `record_user_ack`
   留痕（用户确认原话）→ **拒交棒**——storyline 定稿是交棒前最硬的关键节点，用户没亲口说定稿就
   交制作 = 替用户做决定。其余关键节点的 ack 由各自工序的必填参数强制（发散点由 `record_divergence`
   自动记"方向收敛:×××"、设计定稿在制作阶段 1.5 `record_user_ack`），不靠这道闸兜底。
   仅 `confirm_granularity="minimal"` 或 `"direct_through"`（都是用户亲口选的快进档·granularity_quote
   有原话·D21）时放行；
   `require_acks=True/False` 可显式覆盖自动判断（旧落盘 team 无粒度字段时默认不查）。
   补不出用户原话就是没真确认过——ack 当场记，不是交棒前突击补；
2. **遗留问题收口（warn）**：`check_open_questions_carried` 查全流程 open_questions 有没有"从头到尾
   没人再提过"的，warn 喂人审。
> ⚠️ **交棒后的制作必须走制作工作流的完整阶段 0→4**（安家 new_workspace → spec_lock → 逐页手写 →
> `build_deck(..., strict=True, workspace=ws, spec_lock=spec)` → publish_deck），见
> [makedeck](../制作工作流/SKILL.md)。2026-07-02 saopan扫盘揪出：此前这里的示例直接
> `build_deck(o, svg_provider, out_dir)` 不传 strict/workspace/spec_lock——照抄则 error 页
> 悄悄进成品（违铁律 2）、无只读锁、状态不落盘（违铁律 4），策略层示例把制作层铁律全绕了。
> 本 SKILL 只负责交出合格的 handoff，制作参数以制作 SKILL 为准，这里不再给能跑的捷径示例。

播报「策略地基已完成·交制作工作流出 pptx」。制作层见 [makedeck](../制作工作流/SKILL.md)。

## 客户回灌知识库（真实客户项目**每单必跑**·D18 FR6.2 激活）

> ⚖️ **一切摄入先对照收集范围宪法 [specs/进化飞轮收集范围.md](../../specs/进化飞轮收集范围.md)（D24·用户拍板 5+1 条）**：
> 核心=只收程序原本没有、也无法自主生成的内容——用户上传的原始数据/文档、**验证过**的公开数据、
> 用户对话反馈。**Engine 自产内容（deck 成品/AI 写的句子/自家分析建议）一律不收**（AI 学 AI 自我
> 强化污染·D24 撤回 6 张自产卡的判例）。

**法务已复核（2026-07-02 用户确认）——"法务复核前默认不触发"的门控措辞就此删除**。第一轮实测
（某品牌）确诊：产物闭环真转、知识内化零转——候选池未建、知识库零增量，根因正是旧门控按设计
拦住了整节。现在的纪律反过来：**真实客户项目 handoff 成功后，本节每单必跑**（素材入候选池→人审
promote 两步，缺一单飞轮就是空转）；仍然只对真实客户项目生效，demo/练习不回灌。
`reinforce/evolution/knowledge_ingest.py` 的安全机制不变：脱敏/公私分流/人审 promote（domain/brand
强制标注、白名单默认 private、原始素材独立归档、sharing_override 操作留痕）——"每单必跑"跑的是
**排队入候选池**，正式入库仍要人审，机器不自动扩库。

handoff 成功后执行（这一步失败不影响制作工作流本身，但**不许静默跳过**——跑失败要播报给用户）：
```python
from reinforce.evolution.knowledge_ingest import fact_candidates_from_storyline, queue_candidates
candidates = fact_candidates_from_storyline(sl, domain=["<已泛化的行业类目，如'精酿啤酒行业'>"],
                                            brand="<客户品牌本名>")
queue_candidates(candidates, pool="fact")   # 只进待审池，不碰正式库；人审 promote() 前不会被任何检索读到
```
**同一收尾工序第二类素材：结构性文案候选（D20 FR3.2·D24 宪法收窄）**：真提案文案语料全网
不存在现成库，语料只能随真实素材生长——但**合法源只有两类**（宪法第 1/3/4 条·D24 撤回 6 张
自产卡的判例）：① 用户上传的历史提案/deck（走 chaideck 拆解或语料提取）；② 本单里**用户亲手
修订过的句子**（用户在对话中直接给过的句子/改写过的标题——那是用户智慧增量）。
**Engine 自产 deck 的句子不提取**——AI 写的句子随时能再生成，收录=AI 学 AI 自我强化。所以
`copy_candidates_from_deck` **默认不跑**；仅当本单文案存在用户逐字修订时，把用户给的原话句子
手动组候选入池（标注 `user_revised: true` + 用户原话出处）：
坏句侧（文案门拦截记录+人审否决的文案）本期不自动提取——拦截记录现状不落盘，等门留痕机制落地
后扩；人审时看到本单被拦/被否的句子，值得当反面教材的手动加进槽位卡的 `anti_pattern` 字段。
**每单闭环第二步：人审 promote（D18 FR6.2 验收项——"候选池有数据且完成一轮人审 promote"）**：
排队完**当场提醒用户过一轮人审**（不是排完队就算回灌了）——用户逐条看候选，值得收编的
`promote(card, pool="fact", reviewer="<真实人名>")` 入正式库，不值得的留池/清掉。这一步做完，
本单的知识内化才算真转。public 事实人审后再跑一次
`sync_public_facts_to_shared_pool(reviewer="<真实人名>")` 把品牌库里 public 条目补同步进共享池
`_行业知识库.json`（幂等·按 id 去重·private 绝不外流），确保跨客户可检索——归档进品牌库
（`file_to_brand_library`）的 public 事实不会自动进共享池，漏这步它就只有该品牌自己的 deck 查得到。
**copy 池 promote 的口径跟 fact 池不同（D20 FR3.2）**：候选池里的裸句**不能直接入库**——值得收编
的句子先由人加工成槽位卡 schema（`slot` ∈ 六槽位 + 句式公式 `formula` + 真实 `demo` 带出处 +
`anti_pattern` 禁形态对照），再 `promote(card, pool="copy", reviewer="<真实人名>")` 入表达手法卡库
（promote 会校验 slot 字段，没加工过的裸句直接拒）。**留痕提醒**：`exemplars/表达手法卡.json` 在
git 钩子监控内（L7 铁律），promote 后必须再跑
`from reinforce.evolution.versioning import record_library_change` →
`record_library_change("exemplars/表达手法卡.json", "<改了什么>", "<真实人名>")` 留痕，
否则 pre-commit 拒提交（framework 池同此纪律）。
**方向卡收敛记录同样是回灌素材（D18 FR6.4）**：发散工序 `record_divergence` 存下的
"N 张方向卡+选了哪个+为什么"已经是结构化 decisions——飞轮后续消费它学用户的选择偏好，
所以发散点收敛时 reason 别偷懒写"用户选了A"，要记真实理由。
**用户投放的品牌素材同样是回灌素材（D27·第七轮确诊缺口：某品牌 VI 手册+字体只被视觉锚定消费了
一次，没进飞轮——按宪法第 1/3 条它们是用户上传的原始文档，正是该收的）**：收尾时检查
`brand_assets/`，有文档类素材（VI 手册/历史 deck）就摊给用户一句：「收集点有 N 份品牌素材，
要不要拆解入库？（VI 手册→docling 提取品牌事实进品牌库+原始归档；历史 deck→chaideck 拆解）」
——**拆解是重工序，用户拍板才跑**（宪法第 4 条：只拆用户上传的原始内容）；用户没空审就先
`archive_raw_fact_context` 原始归档兜底（gitignore 内·不检索·备份语义），素材本体反正在收集点
不会丢。
**第四池：用户反馈/想法（D24 宪法第 5 条·全程随手收）**：用户在对话中给出的反馈、纠偏、想法、
表扬——**逐字原话**当场入池，一句不丢（第六轮教训：'只诊断不解决'这条金子级反馈因为没有回传
通道差点丢失）：
```python
from reinforce.evolution.knowledge_ingest import queue_feedback
queue_feedback("<用户逐字原话>", context="<什么场景说的>", deck_id="<本单id>",
               category="反馈|需求种子|偏好|表扬|纠偏", date="<今天日期>")
```
交付收尾时**主动请用户给一句整体反馈**（"这单整体感觉如何？哪里最不满意？"——开放问题用文字
对话不用问答工具），答案入池。反馈池没有自动入库路径：人审时转需求种子/工作偏好/实录素材。
⛔ **收尾自查硬项（D27c·七轮实测审计确诊：反馈池仅 1 条且是开发侧手动补录——'随手收'工序
没被任何实测会话执行过）**：交付前回看本单全部对话，用户说过的反馈/纠偏/疑问/想法**逐条
queue_feedback 入池**（逐字原话）；真的一条都没有才标注"本单无用户过程反馈"——把"忘了收"
和"真没有"区分开，不许静默跳过这一步。C 端产品化后由会话层自动收集接管（见 C 端部署清单）。
**跨客户结构复用侦测（2026-07-01 补持久化池）**：阶段2 假设树定稿后（真实客户项目），额外调用：
```python
from reinforce.evolution.knowledge_ingest import record_issue_tree_fingerprint, due_framework_candidates
record_issue_tree_fingerprint(tree, brand="<客户品牌本名>")   # 只存结构指纹+品牌，不存 claim/test 内容
due = due_framework_candidates()   # 扫一眼有没有指纹已被 ≥2 个不同品牌独立撞到
```
`due` 非空时播报给用户："这个问题分解形状在 N 个不同客户身上独立出现过，可能是个值得收编的可复用
框架"——候选清单不自动入库，人工看过 `_框架原始归档.json`（`archive_raw_framework_source` 存的完整
原始树，供二次抽象命名）后才 `promote(pool="framework", ...)`。

候选池里的东西**不会自动变成任何人能查到的知识**——`promote()`/`file_to_brand_library()`/
`sync_public_facts_to_shared_pool()` 都要求显式 reviewer 且是分开的人工动作，本节只负责"排队"。

## 引用清单
- 方法论：[00](../../specs/PPT方法论/00_总纲.md) / [01](../../specs/PPT方法论/01_顶级deck共因与翻车雷区.md) / [03](../../specs/PPT方法论/03_场景叙事结构.md) / [05](../../specs/PPT方法论/05_质量门与评估.md) / [07 交付三态（双模式+D19 预读讲解版）](../../specs/PPT方法论/07_演讲版vs阅读版.md)
- 模块：`planning_team`(阶段1.5·D18 新增 `set_confirm_granularity`/`record_user_ack`/`record_divergence`/`new_direction_card`+`complete_role(user_summary=)` 必填；D19 FR4.2 增 `divergence_history()` 跨 deck 历史收敛原话聚合[无需传参·扫 data/decks/]，喂 `prompt_divergence(history=)`；`check_open_questions_carried` 遗留问题收口与关键节点 ack 闸均随 `handoff_to_production(team=...)` 交棒自动跑) · `issue_tree`(阶段2·含页数区间见 `strategy_prompts.prompt_stage2_page_scope`) · `research`(阶段3·`attach_citation(source_type=)` 溯源分类) · `storyline_state`+`deck_rules/storyline`(阶段4·含 `check_counter_addressed`/`check_hypothesis_tested`/`check_page_count_consistency`+两层防假阳 `check_facts_grounded`/`check_evidence_directions`+D18 `check_part_structure` 结构硬门/`check_client_facing_tone` 对客文案门，均在 `run_storyline_gate` 内自动跑) · `review`(阶段5) · `evolution/knowledge_ingest`(交棒后·真实客户项目每单必跑·FR6.2 法务已复核门控解除)
- 工具：`docling`(brief PDF解析·MIT许可·2026-07-01验证可用推荐路径) ·
  `MinerU`(brief解析·⚠️本仓库Python 3.14环境装不上，见D13) ·
  `claude-websearch`(调研·免费默认路·Claude 当场 WebSearch/WebFetch) ·
  `gpt-researcher`(调研·🧭能力边界·第三方包+独立 key·待用户愿意为调研深度多花钱再启)

> ✅ **五阶段已做实**（每阶段调真实模块 + 关闸代码）；端到端 demo 见 `examples/demo_strategy.py`（brief→storyline 定稿）。
> 待打磨：每阶段 prompt 模板、与制作的交接卡 schema 落盘。
