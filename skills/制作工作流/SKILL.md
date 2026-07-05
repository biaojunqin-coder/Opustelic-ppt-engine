---
name: makedeck
description: PPT「制作工作流」技能——把策略定稿的大纲做成原生可编辑 .pptx 成品。分阶段 fail-closed：搭大纲(校验关闸)→设计定稿(风格光谱三档拍板+spec_lock 完整设计契约：风格/字号角色槽/图标/图像清单/每页视觉概念)→逐页(模板映射声明→生成 SVG→渲染→硬门·写一页渲一页检一页)→vendor 引擎导出(零栅格化验证关闸)→交付(人审清单勾完才 publish+只读锁+入 git)。当用户说「做 deck / 做 PPT / 做幻灯片 / 把大纲做成 PPT / 生成 deck / 制作演示稿 / 出成品」，或要产出行业惯例=PPT 形态的交付物（结案报告/复盘报告/提案/比稿方案/营销方案/汇报材料/月报季报等）时触发（还没有策略定稿则先走策略工作流）。接「策略工作流」出口（intent + 大纲骨架 + 两轴 + 每页 chart）为入口。每页过硬门才进下一页，导出必验证非图片化，交付即上只读锁。绝不跳页硬门、绝不把栅格化图片当成品交付、绝不回改已交付 deck；停点白名单（设计定稿/人审清单/缺用户素材）外绝不停顿等"继续"，逐页推进播报不请示；策略侧直通档单子全程零停顿（设计自动锁+人审 waiver 留痕+交付摊假设台账）。只负责把定稿大纲做成 pptx，不负责策略推导（那是策略工作流）、不负责拆 deck 入库（那是 chaideck）。
---

# /makedeck —— 制作工作流 · 定稿大纲 → 原生可编辑 .pptx 成品

> 串起五层一条链：State(大纲) + Prompt(逐页拼范本) + RAG(范本卡·在 Prompt 内) + 规则(硬门) + vendor 引擎(导出)。
> 引擎实现见 `engine/pipeline.py::build_deck`；端到端 demo 见 `examples/demo_deck.py`；制作底座决策见 `specs/决策记录.md` D1。

## 🔥 灵魂：高 stakes deck 的制作操盘手
做的是**咨询级 / 投资人 deck**——waterfall / Mekko / Gantt 这类通用 agent 和大厂 skill 做不出的段（收窄边界见 CLAUDE.md 硬纪律 4）。
核心交付物两条死线：① **action title**（每页标题是论断不是主题）② **原生可编辑**（PowerPoint 里能直接改数字/改色，绝非截图贴图）。

> 🧭 **以人为主 · 全程引导对齐（CLAUDE.md 第 0 条 · 最高铁律）**：制作过程也**一轮一轮跟用户确认**——不是策略定稿后我闷头把 PPT 做完。页面方向 / 视觉风格 / 关键页都摊给用户拍板，绝不批处理。人做主、AI 是手。
> 🖱 **拍板类问题必须用 AskUserQuestion 工具呈现（D19 FR2.1·第二轮实测用户点名："手动打字回复拍板题是体验硬伤"）**：风格光谱三档、关键页方向确认、交付确认这类"从明确候选里选一个"的题，一律用工具摊选项——每个候选一个 option（label=选项名，description=这一项的理由+权衡），推荐项 description 开头标「推荐：」；摊功课的叙述照旧先在正文给足，工具只承载"选"这个动作。**开放性讨论（问细节/请用户补素材）仍用文字对话**——问答工具管收敛不管发散。
> 🚀 **停点白名单 · 白名单外绝不停（D21·2026-07-03 用户拍板："除了必要的发散性确认以外，让它按最佳方案推进"）**：上一条的"都摊给用户拍板" = 拍板点**集中约定**，≠ 逐页请示。制作全程**只有**这些停点：① 设计定稿（风格光谱三档拍板 → spec_lock·硬停 ack）——**关键页（首页/高潮页/决策页）的方向也在这一轮一并约定**，不逐页停；② 用户在策略阶段选的确认粒度若含制作节点，按档执行；③ 人审清单（用户勾完才 publish·硬闸）+ 交付确认；④ 缺**只有用户才有**的输入（素材/API key/品牌规范）。
> 白名单外——每页过硬门、机检修复、渲染自检、导出验证、图像获取——**播报进展后直接做下一页/下一步**：40 页 deck 绝不做一页停一页。**策略侧选了 `direct_through` 直通档的单子，①②③全部不停**（设计自动定稿+人审走 `publish_deck(direct_through_waiver=根授权原话)` 豁免+交付摊假设台账），只剩④·D21。**播报 ≠ 停顿**（说完立刻继续，禁"需要我继续吗 / 我先做 X 好吗"这类征求推进许可的收尾）；**机检不过 = 自己返工修到过**，不是问用户怎么办（fail-closed 的"停"指返工循环不指等人）；**回合自查**：要结束回合先自问"我停在白名单上吗？"——不是，就继续干。

## 🗣 播报纪律三条（D19 FR2.2·对用户说的每一句话·全程生效）

第二轮实测确诊两类播报事故：对用户说程序语言（"跑 run_text_gate"）+ 跨项目串场（"和上一轮某品牌…"）。三条纪律覆盖制作全程每一次对用户的叙述：

**① 机制名翻译成用户语言**——机制名/文档编号/函数名不出现在对用户的叙述里：说"做了什么"，不说"调了什么"。五组正反例：

| ❌ 程序语言 | ✅ 用户语言 |
|---|---|
| 「spec_lock 校验通过，设计契约已锁定」 | 「设计规范定稿了：整份 deck 的色板、字号、图标从此统一，不会页页漂移」 |
| 「run_text_gate 报 error：page 5 数字无 source」 | 「第 5 页有个数字还没带出处，我先补上来源再往下做」 |
| 「check_svg_compat 拦了 rgba() 写法」 | 「这页有个视觉效果导出到 PowerPoint 会损坏，我换成等效的安全写法」 |
| 「publish_deck 上只读锁，assert_editable 会拦重做」 | 「这版交付后就封存不改了，之后的修改走新版本，旧版永远可回溯」 |
| 「acquire_image 返回 handoff_to_human」 | 「这个视觉位免费图库没找到合适的图，我标了'真人接管'，不影响整份 deck 先出」 |

**② 跨项目提及只限 `data/decks/` 内存在的项目**——该目录就是**这个用户的项目史**，天然的可见性边界：提别的单子之前先确认它的 deck 在 `data/decks/` 里（拿不准就 `ls data/decks/`），并且**用用户自己的叫法**称呼（"你之前 059 那单"✓；"上一轮某品牌"仅当某品牌的 deck 真在该目录内才可说✓）。目录里没有的项目**一个字不提**——哪怕范本库/知识库里有它沉淀的手法。

**③ 知识库/范本库引用不透品牌**——说"行业知识库有一条 XX（来源 XX 报道）""范本库里有张同页型的手法卡"，**不带其他品牌名、不提来自哪个客户单**——除非该品牌的 deck 就在这个用户的 `data/decks/` 内（用户自己的项目当然可以点名）。

> ⚠️ 单机单用户下 `data/decks/` 天然=该用户的可见边界，这三条是**工序纪律**；多租户真隔离（账户体系/每用户一仓库）挂 D3 C 端待办，届时边界判定自动继承租户目录，纪律本身不变。

## ⛔ 铁律（fail-closed·任一不满足 = 没做完）
1. **大纲先过校验**：`validate_outline` 不绿不开做（缺必填 / 页号重复 / 坏依赖 → 拒做）。
2. **每页过硬门才进下一页**：`run_text_gate` 有 error（数字无 source）→ 返工，不带病推进
   （2026-07-01 用户拍板：数据溯源是100%红线，`check_source` 从 warn 升级 error——编造/无据数字
   比此前移除的"AI 味"更该是能拦截的硬伤）。D18 FR1.4 起节拍固定为
   **写一页→渲染一页→机检一页→有问题当页返工**（机检前移·别攒到完稿才发现，见阶段2）。
3. **导出必验证非图片化**：解包查 `<p:pic>=0` + `<a:t>` 有原生文字——栅格化图片**不是成品**，重做（D1 质量基准）。
4. **交付即只读**：`publish_deck` 收尾上锁（登记 + 交接卡一步到位）；已交付 deck 绝不回改（铁律 4），改需新
   deck_id 走新版本——2026-07-02 起 `build_deck` 开工前会 `assert_editable` **代码硬拦**已交付 deck 的重做
   （此前只读锁全仓零生产调用、全靠自觉，同 spec_lock 那次"文档喊强制、代码可绕过"一种病）。
5. **数字必溯源**：每个数字带 source 标记，硬门 warn 也要人审补全（咨询 deck 的命）。收尾自动汇集
   `asset_ledger.json` 溯源台账（每个数字从哪来的 deck 级汇总·给客户答疑/法务复核用）。

## 🔗 入口：接策略工作流出口
「策略工作流」(`skills/策略工作流/`) 定稿后经 `handoff_to_production(sl, team=team)` 交出：**intent**(7 类真枢纽：说服决策/同步进展/复盘总结/陈述分析/推导策略/展示介绍/传递教学) + **大纲骨架**(每页论点 + 建议页型) + **delivery_purpose/mode 两轴** + 策略层声明的每页 chart（设计定稿建 spec_lock 后调 `seed_per_page_from_outline(spec, o)` 播种进 per_page·FR3.4）。
交接卡能到手 = 关键节点 ack 闸 + Part 结构硬门都已过（D18 FR1.2/FR2.2·缺 ack/缺目录转场小结在策略侧就被拦了）。
本 skill 从这里接手。若用户直接给定稿大纲，跳过策略阶段直接进阶段 1（**阶段 1.5 设计定稿不可跳**——没有策略交接卡更要从头对齐设计锚点）。

## 🚦 阶段流（每阶段出关闸·产物落盘才进下一阶）

### 阶段 0 · 安家（④数据产物层·一份 deck 一个家）
```python
from reinforce.deck_workspace import new_workspace
ws = new_workspace("descente_y26_proposal")   # data/decks/<deck_id>/ 全套产物路径映射·幂等不覆盖已填的肉
```
本 deck 全部状态产物落这个家：`outline.json`(页状态活文件) / `spec_lock.json` / `asset_ledger.json`
(D18 FR4.4 起含图像生成台账段) / `handoff_card.json` / `pages/`(逐页 SVG·PNG) / `images/`(D18 FR7.4·
acquire_image 获取的图像资产) / `brand_assets/`(D22b 品牌素材收集点·建家自带引导说明——用户没走
策略层直接进制作的，安家后顺带提示一句"有品牌素材丢这里，设计定稿前放进去都来得及"·提示不停顿) /
`deck.pptx`；策略工作流的 `team_state.json` / `storyline.json` /
`handoff.json` 也约定落同一目录——**跨会话接手读这个目录 = 全局图**（策略走到哪个角色、制作做到哪页、交付没有）。
别再把状态文件散落 `examples/out*/` 各处（2026-07-02 前的旧疾：CFO demo 只落了 storyline、Descente 只落了
spec_lock，没有一份 deck 有完整产物套装）。

### 阶段 1 · 搭大纲（State 关闸）
把策略骨架结构化成 `deck_outline`，每页定 **page_function**(页型) + **claim**(action title 论断) + **depends_on**(叙事依赖)。
```python
from reinforce.deck_state import new_outline, add_page, validate_outline, save_outline
o = new_outline("标题", doc_type="数据报告", intent="复盘总结", domain="财务", audience=["管理层"],
                brand_terms=["059", "059某品牌精酿公社"])
# ↑ brand_terms（D19 FR5.1）品牌名豁免表：含数字品牌名（"059"）不再被文字机检当统计数字。
#   从策略交棒来的 outline 已自动带（new_storyline(brand=...) 派生）——只有"用户直接给大纲、
#   跳过策略层"的路径才需要在这手填
add_page(o, 1, "title_cover", "收入增25%但成本翻倍，增长质量亮红灯")
add_page(o, 2, "waterfall", "成本增长吃掉全部收入增量，净利反降20%", depends_on=[1])
# … 逐页。claim 必须是论断（带数字/方向），不是主题词（如「财务概况」）
```
**关闸**：`validate_outline(o)["valid"]` 必须 True。`save_outline(o, ws["outline"])` 落盘到家（内部 fail-closed·非法拒写）。
page_function 选型查范本库，用 `reinforce.retrieval.search.search_deck_cards(page_function=..., domain=[...])`
（按 page_function 精确/模糊匹配 + domain 交集打分，返回按分数降序的候选卡，含 pick_when/skip_when 检索规则；
不传参数则按 rating 兜底浏览全库）——**别直接手翻 JSON**，检索函数会把最相关的范本卡排到前面。

### 阶段 1.5 · 设计定稿（D18 FR7.2·spec_lock 扩容为完整设计契约·两轮确认工序）

> **这是"设计"整层，不是填个色板**（D18 机制考古：ppt-master 的质感在这个阶段被设计出来——我们
> vendor 时把这层按"咨询 deck 不靠配图"的旧判断过滤掉了，第一轮实测 24 页单色卡片网格实锤证伪）。
> 工序 = **两轮确认**，全程贴引导对齐范式（一次一个点·摊功课+推荐+权衡·用户拍板）。

**第一轮 · 锁锚点（delivery_purpose / 受众 / visual_style）**：
- `delivery_purpose`（密度轴·D19 FR3 起三值：演讲版/阅读版/**预读讲解版**）与受众从策略交接卡
  读回（阶段1已锁），跟用户核对一句即可。三态在制作层的落法：演讲版=极简大留白+情绪节奏、
  阅读版=三段式高密度自洽（07 规范不变）；**预读讲解版**（"先发客户自读、看完再开会讲"·用户
  真实场景·D19 FR3）=**密度取中**（比阅读版略疏、比演讲版满——自读要自洽、现场讲要留讲述
  空间）+ **subtitle 导读保留**（支持自读·机检同阅读版口径查）+ **备注按现场讲写**（支持后讲·
  见阶段5）+ 节奏要转场不强制情绪页（策略侧 `check_rhythm` 已柔化分流）；
- **visual_style（美学轴）= 本轮主戏**：给 **≥3 档风格人格光谱**——`safe`（行业惯例）→ `shifted`
  （外放一档）→ `bold`（挑战默认），**每档带脾气标签 + 现实类比**，不是报三个风格名让用户盲选。
  策略阶段 decisions 里记过美学倾向的，光谱围绕倾向出。例（精酿啤酒 CNY campaign 比稿）：
  - safe = `editorial`（杂志编辑部脾气：栏线+衬线标题，克制但有出版物质感——像《第一财经》专题页）；
  - shifted = `photo-editorial`（摄影画册脾气：满版大图说话、文字退成图注——像 Kinfolk）；
  - bold = `zine`（地下刊物脾气：高密度拼贴、胶带贴纸、故意不对齐——像先锋买手店的季册）。
  18 风格目录见 `engine/ppt_master/references/visual-styles/_index.md`（按行业/气质挑三档，不许永远拿同三个）。
  **推荐纪律（D22·第五轮实测"总推荐特别素"确诊）：三档必须真横跨 safe→shifted→bold 光谱——禁止三档
  全是 editorial/swiss-minimal 这类素面孔**（18 风格里 zine/memphis/vintage-poster/glassmorphism/
  photo-editorial 这些浓的存在就是拿来推荐的）；推荐档按 deck 类型定——比稿/创意/营销类推荐档位
  应落在 shifted 或 bold（客户买的是感染力），别拿 LLM 保守天性替客户做决定，"素"必须是用户选的。
  三档光谱是拍板题→用 AskUserQuestion 摊（D19 FR2.1·每档一个 option：label=风格名+脾气标签，
  description=现实类比+一句权衡，推荐档 description 开头标「推荐：」；摊功课的完整叙述先在正文贴完）。
- **视觉丰富度档（D22·与风格光谱同轮拍板·进 spec_lock 成为设计契约）**：先调
  `engine.chart_template_map.default_richness_for(目的)` 拿类型默认档+一句为什么（比稿/创意/营销
  默认浓郁·尽调/董事会默认素雅·其余标准），作为推荐项与另两档一起摊给用户选；锁进
  `spec_lock(richness=…)` 后逐页 prompt 简报自动带档位准绳，**浓郁档 images 清单不达下限
  （max(3, 页数//8)）build_deck 直接 error 拒做**（fail-closed·直通档下 warn 整批架空[人审已
  waiver]，用户拍板的浓郁承诺必须有 error 兜底）。直通档不再问——用开场配置舱选好的值。
- **用户拍板后硬停 ack**（D18 FR1.2·设计定稿是关键节点，唯一例外是 `direct_through` 直通档
  ——用户开场配置舱已选风格大方向+丰富度档，AI 在该方向内按策略内容自动锁定具体风格，不停不 ack、
  选型理由进假设台账·D21/D22）：
  ```python
  from reinforce.planning_team import record_user_ack
  record_user_ack(team, "设计定稿", user_quote="用户确认原话")   # 存原话不存布尔位·补不出原话=没真确认
  ```

**第二轮 · 从锁定风格手册派生实现层（保证整套互相咬合·不是自由拼配）**：
读 `engine/ppt_master/references/visual-styles/<锁定风格>.md`（**只读锁定那一份**，别 glob 全目录），
按手册各节派生推荐、打包摊给用户过目：
- **§2 Typography character（字体性格）** → `typography` 角色槽：body 锚点按 delivery_purpose 定
  （演讲版大/阅读版小/**预读讲解版取中**·D19 FR3），title/subtitle/lead/annotation/footnote/hero **各锁一值**（同角色跨页漂字号=
  不专业·FR7.6）；`title_font` 承载风格字体性格（editorial=衬线、dark-tech=几何 sans……正文可中性，
  **标题不许默认中性 sans**）；
- **§3 Using the deck's colors（色彩纪律）** → `palette` 怎么用（手册刻意不含 HEX——色值按品牌/brief
  现场锁，手册只管"这些颜色怎么使"）；旧版"一个高亮色其余灰"的写死规范已随 FR7.1 删除，色彩纪律
  以锁定风格手册为准。**色值从哪来=品牌视觉锚定工序（D22·第五轮实测"不贴品牌视觉"的解——
  风格手册管版式骨架，品牌管色板皮肤，两者正交）**，按优先级三源取一：
  ① **brand_vi**：第一步扫品牌素材收集点（D22b·leader 开场已提示用户投放，建家自带
    `brand_assets/` 目录+引导说明）。⚠️ **素材是异步投放的（D27·第七轮某品牌单：用户开场问"怎么
    给"、中途才放入，扫描只做一次就会漏）——spec_lock 落盘前、逐页生成前，各再扫一次收集点**；
    机制兜底：素材在场而 palette_source 不是 brand_vi 且无 assets_reviewed 豁免 → `build_deck`
    开工 error 拒做（把"做完 13 页才发现素材"的整单返工提前到开工前·改 spec_lock 重跑即可）。
    确认弃用素材（如只有历史 deck、无标准色号）→ `palette_source` 里加 `"assets_reviewed": True`
    + 弃用理由，如实留痕。——`reinforce.deck_workspace.list_brand_assets(ws)` 返回
    {fonts, images, docs, others} 分组：**docs**（VI 手册 PDF / 历史 deck）→ docling 提取色板与
    字体规范（锚定最高优先级）；**images**（logo/KV/官网截图）→ 视觉读图提取品牌主色+辅色；
    **fonts**（ttf/otf/woff 品牌字体文件）→ 先过 `reinforce.deck_rules.font_embed` 可嵌入性检查
    （fsType 受限的如实告知用户、换开源近似体），过了才锁进 `typography` 的 title_font/body_font。
    evidence 填素材路径；也兼容用户在 brief 里直接附素材的口径。收集点空
    （`any(list_brand_assets(ws).values())` 为 False）且 brief 无素材 → 走②；
  ② **web_verified**：没给素材 → 联网查证品牌官方色（官网/品牌指南公开页），**evidence 必须填来源
    URL**——不许凭模型常识写品牌色（"某品牌 绿记成蓝"就翻车·validate_spec_lock 缺 evidence 直接 error）；
  ③ **neutral**：查不到（小品牌/内部项目）→ 用风格手册气质的中性色板并如实标注。
  锚定结果锁进 `spec_lock(palette_source={"kind":…, "brand":…, "evidence":…})`——品牌色默认做
  `accent` 主导色+关键页（封面/高潮/收尾）可品牌色铺场，铺多铺少听锁定风格手册的；来源留痕后
  逐页 prompt 简报自动带"色板来源=品牌官方"锚点。直通档自动跑这条链，来源与色值进假设台账。
- **§5 Paired image-rendering + §6 Illustration propensity** → `image_rendering` / 图像与插画用法倾向；
- **icons**：5 库锁 1（11631 个图标·`icons={"library":…, "inventory":[…]}`），inventory 只列本 deck
  允许用的名字——Executor 只准用清单内图标，`icon_sync` 存在性验证缺名强制重选（FR7.5）。

**图像规划工序（D18 FR7.4·设计定稿时排完 images 清单，不是逐页临时找图）**：
- 每行**强制填 `pattern_id`**（81 模式图文版式库 `engine/ppt_master/references/image-layout-patterns.md`
  ——选版式先读库，防"永远左右分栏"）；`acquire_via` 六源：`web`（四个免 key 免费图库·pixabay/
  pexels/wikimedia/openverse）/`ai`（FR4.2 BYO key）/`user`/`placeholder`；`slice`/`formula`
  本期返回 `not_implemented`（诚实标注·二期），排清单时别指望这两源；
- **真实图库 vs AI 生图的分工（D19 FR6.5·31 次检索调研实证）**：**地标/城市/建筑找真实图库**
  （`acquire_via="web"`）——Pexels 福建类内容 4.7K 张、Wikimedia Commons 土楼 3 万+/骑楼 7.6 万张，
  覆盖够用；**食物特写/摆拍/品牌场景合成走 AI 生图**（`acquire_via="ai"`）——"沙茶面"这类长尾
  题材真实图库就是缺，别硬搜（搜不到还耗额度，搜到也不对味）。排清单前配好 Pexels/Pixabay 免费
  key（环境变量 `PEXELS_API_KEY`/`PIXABAY_API_KEY`·注册即时发放·.env 方式配置见 FR6.1[该文件
  必须在 .gitignore 内，key 绝不入库]）——**缺 key 时管线 deck 级 warn 一次**（D19 FR6.1·"四库
  只有两库在跑"曾是第二轮'搜不到福建'的误诊主因），看到这条 warn 先补 key，再下"图库没图"的结论；
- **图像合规三条（D19 FR6.6·调研背书：民法典肖像权/著作权法 24 条/CC 条款）**：
  ① **可识别人脸只用带 model release（模特授权）的图**——Pexels/Pixabay 级图库有此保障；
  Flickr/Wikimedia Commons 的 CC 图**带清晰人脸一律避开**：CC 许可只解决著作权、不解决肖像权，
  民法典下商用可识别肖像需本人同意，图库条款替代不了；
  ② **历史建筑（土楼/骑楼）零风险**放心用；**现代地标**做背景可、当主视觉需谨慎（著作权法
  24 条"合理使用"有判例边界），且留意画面里的**商标/店招**（放大成主视觉前先查一眼）；
  ③ **CC BY / BY-SA 必须署名**：`acquire_image` 返回 `attribution_required=True` 时，
  `attribution_text` **交付前必须贴上页面或尾页 credit 区**——`image_sources.json` 溯源台账
  管线已自动落，**credit 渲染由做页面的这一步承接，别断链**（署名断链=违反许可条款）；
  Pixabay 按其 API 条款**强制 24h 缓存**（禁热链·别对同一查询反复直连刷 API，管线下载落盘
  即合规形态）；
- **≥4 图的 deck 至少 1 页用 #38-46「图像当画布」族**（Image-as-Canvas + 原生叠加·最被低估的一族·硬门）；
- deck 级 `image_rendering × image_palette` 一起锁——多张图（尤其 AI 生成）读起来像同一份 deck；
- 清单定稿后逐行获取（可在阶段2开工前一次跑完）：
  ```python
  from engine.image_pipeline import acquire_image, load_image_api_keys
  keys = load_image_api_keys()          # 用户自备生图 key(FR4.2 BYO)·返回 None=未开启生图
  for row in spec["images"]:
      r = acquire_image(row, "data/decks/<deck_id>/images", api_keys=keys,
                        rendering=spec["image_rendering"], palette=spec["image_palette"])
      # r["status"]∈{ok, handoff_to_human, pending_user, not_implemented}：
      # 无 key / 生图失败 / web 无结果 → handoff_to_human"真人接管"标注，不阻塞 deck 产出（需求§六）；
      # web 成功附 provider/license/attribution_text，ai 成功附 model/prompt/cost_estimate（喂图像台账）
  ```
- **AI 生图工程铁律（FR4.3）**：AI 只出**无字底图**，中文 slogan 与 logo 由 SVG 排版层用真字体/真 logo
  贴合成（绕开中文渲染与 logo 两大硬点）；prompt/迭代次数/参考图/模型/时间自动进 `asset_ledger`
  图像段（FR4.4 生成台账·客户维权证据链），投放物料记得提示"AI 生成"标识义务（2025-09-01 施行）。

**每页视觉概念（D18 FR7.3·问题A核心件·per_page 逐页填 `visual_concept`）**：设计定稿阶段就把
每页"先想后画"契约写完——`layout`（版式声明：版式库选/组合/破格）+ `core_message`（一句断言
"本页凭什么存在"·**说不出就砍页**）+ `blocks`（内容块按语体 prose/bullet/keyword **预写真句子**，
用对客语域写[FR5.3]——是"春节档声量阵地已转移至小红书"这种真句子，不是"这里放洞察"的骨架占位）。
`per_page[n]["layout"]` 同时路由到 `engine/ppt_master/templates/layouts/` 7 套骨架 SVG（FR7.7·cover/chapter/toc/content/
ending·供结构不供皮肤）。策略层声明的 chart 用 `from reinforce.spec_lock import seed_per_page_from_outline; seed_per_page_from_outline(spec, o)` 一步播种进 `per_page[n]["chart"]`（FR3.4·已有人工声明不覆盖·别手抄一遍大纲）。

**Part 级视觉配额（D18 FR3.5）**：每 Part 至少 1-2 页强视觉页（真图表/框架图/巨字页/视觉主体页）
——设计定稿时逐 Part 点名哪几页扛视觉（机检数配额 warn），对齐真样本节奏感；**不要求每页有视觉
主体**（防装饰性噱头）。

**new_spec_lock 全参数示例（真实签名·D18 扩容后）**：
```python
from reinforce.spec_lock import new_spec_lock
spec = new_spec_lock(
    palette={"bg": "#FFFFFF", "ink": "#1A1A1A", "accent": "#C8102E", "grey": "#8A8A8A"},
    font_family="Noto Sans SC",
    zones={"header": {"y": 0, "h": 100}, "content": {"y": 100, "h": 560}, "footer": {"y": 660, "h": 60}},
    visual_style="editorial",                      # 美学轴·三档光谱用户拍板后的锁定值（18 风格之一）
    richness="浓郁",                                # D22 丰富度档·用户拍板（浓郁档 images 不达下限拒做）
    palette_source={"kind": "web_verified", "brand": "示例品牌",   # D22 品牌锚定留痕：色板从哪来
                    "evidence": "https://brand.example.com/guidelines"},  # web_verified 必须带来源 URL
    typography={"body": 16, "title": 28, "subtitle": 20, "lead": 22,
                "annotation": 12, "footnote": 9, "hero": 130,
                "title_font": "Noto Serif SC",     # 标题字体承载风格字体性格·不许默认中性 sans
                "body_font": "Noto Sans SC"},
    icons={"library": "lucide", "inventory": ["trending-up", "users", "target"]},
    images=[{"filename": "cover_hero.png", "purpose": "封面情绪主视觉",
             "pattern_id": 40, "acquire_via": "web",
             "intent": "春节餐桌碰杯的精酿·暖光", "size": "1280x720", "text_policy": "no_text"}],
    image_rendering="editorial", image_palette="brand-tinted",
    per_page={1: {"rhythm": "anchor", "layout": "cover",
                  "hero": {"hook": "春节声量翻盘", "composition": "满版图像+左下标题块"},
                  "visual_concept": {"layout": "#40 图像画布+原生标题叠加",
                                     "core_message": "开场 3 秒让评审记住'翻盘'这个词",
                                     "blocks": [{"type": "keyword", "text": "春节声量翻盘"}]}},
              5: {"chart": "waterfall_chart", "rhythm": "dense",
                  "visual_concept": {"layout": "上图下文·瀑布拆解",
                                     "core_message": "成本增量吃掉全部收入增量·净利反降两成",
                                     "blocks": [{"type": "prose", "text": "收入涨出来的 1.2 亿，被三项成本原地吃光。"}]}}})
```
**关闸**：`validate_spec_lock` valid——palette/font_family 必填；`rhythm` ∈ {anchor,dense,breathing}；
`richness` ∈ {素雅,标准,浓郁}；`palette_source.kind` ∈ {brand_vi,web_verified,neutral} 且非 neutral 必带 evidence（D22）；
`hero`/`visual_concept`/`typography`/`icons`/`images` 都是"可不填，**填了必须合法完整**"（visual_concept
缺 core_message、icons 缺 inventory、images 行缺 pattern_id 都是 error——填一半比不填更危险）。
**全 deck 只锁一次，N 页都用同一份**——逐页另定颜色/字号 = 跨页风格漂。对应 ppt-master `spec_lock.md`
机制：逐页生成前强制重读（`build_deck_prompt` 自动把当页 per_page 项+锁定风格手册段拼进 prompt，
图表项附"模板供结构不供皮肤"换色提醒），不许凭记忆现编。门面页钩子写得好不好是人审
（`review.py` slide_content 清单），spec_lock 只管"有没有先想清楚再画"。

#### 三档视觉边界（D18 FR4.1·创意不越能力边界硬做）
视觉位在设计定稿时逐个定档，三档工序不同：
1. **概念示意级**（页面配图/氛围底图）：AI 生图随用（走上面 images 清单）；
2. **mood board / KV demo 级**：AI 生图当主力（4A 当前真实用法："AI 出概念、真人出成片"）；
3. **成品 KV 级**：**不承诺 AI 产出**（版权确权/logo/标识义务四重结构风险·调研结论）——页面标注
   **"真人创意接管"** + 落盘 **brief 三件套**给未来协作的真人创意：①创意阐述 ②mood board
   ③交接规格（尺寸/色值/字体/构图要求，色值字体直接从 spec_lock 抄，不许口头"品牌红"）。
   无生图 key 时（FR4.2 默认态），②的 mood board 位也走"真人接管"标注，deck 照常交付。

#### 对客交付物模板（D18 FR4.5·campaign 比稿 deck 的角色必产出）
- **创意角色必产出**：概念卡 + KV（按上面三档执行）+ **延展应用清单**（逐触点：每个触点写
  "形式 + 视觉要点"，如"电商开屏：KV 竖版裁切+利益点前置"——不是一句"多触点延展"糊过去）；
- **执行角色必产出**：**KOL 矩阵（框架级）**——层级×平台×选择逻辑×预算配比，**不点名不报价**
  （产品边界：不碰客户的利润腹地）+ 排期（gantt_chart 可用）+ 预算分配框架。

### 阶段 2 · 逐页做（Prompt 拼装 + 硬门关闸）

> **🔒 逐页节拍（D18 FR1.4·机检前移·xieshu 同款节拍纪律）**：节拍是
> **写一页 → 渲染一页 → 机检一页 → 有问题当页返工**——绝不"把 N 页全写完再统一渲染机检"
> （第一轮实测的翻车形态：机检假阳性/版式塌方全堆到完稿才发现，返工成本 N 倍）。逐页渲染预览
> **默认开启**（playwright 已装为前提·`build_deck(render_previews=True)` 或逐页 `render_svg_to_png`），
> 当页渲染图当页亲眼看完、硬门当页过完，才进下一页。

对每页四步：**① 输出"模板映射 + 布局策略声明" → ② 拼 prompt 生成 SVG → ③ 渲染亲眼看 → ④ 过硬门**。

**① 模板映射 + 布局策略声明（D18 FR7.3·强制前置·先想后画的当页兑现）**：写 SVG 前必须先输出
一段声明（对话里明说，留痕）：本页用哪张版式/图表模板（或声明破格+理由）、`visual_concept` 的
core_message 是什么、blocks 怎么落位、图像按哪个 pattern_id 摆——**没有这段声明直接开画 = 违工序**
（第二轮实测验收项：每页生成前有模板映射声明留痕）。
`build_deck_prompt` 已自动按 domain 检索表达手法卡拼进 prompt（142 张真实 deck 抽取的可迁移文案/修辞
公式，含 formula/mechanism/pick_when/skip_when——是"公式"不是照抄原句），返回值 `ctx["expression_cards"]`
里能看到具体命中了哪几条；`top_expression_cards=0` 可关闭。**这条不需要手动查，已经是代码强制**。
```python
from engine.prompt_builder import build_deck_prompt
ctx = build_deck_prompt(o, page_n, spec_lock=spec)   # {prompt, page, cards(范本), expression_cards, deps, spec_lock}
# 按 ctx["prompt"] 生成本页 SVG ——见下方"逐页手写"铁律，禁脚本批量
svg = ...                                       # 1280×720 viewBox·action title 在顶·美学按锁定风格走
```
D18 起 `build_deck_prompt` 注入的上下文比旧版厚（都是代码强制，不用手动查，但要**读完再画**）：
- **锁定风格手册段（FR7.1）**：spec_lock 锁了 `visual_style` 时，该风格的形状语言/字体性格/色彩
  纪律/配图倾向段拼进 prompt——旧版写死的"一个高亮色其余灰"已删，美学以锁定风格为准；
- **chart→资产映射（FR3.1）**：当页声明的 chart 强制注入对口模板的结构参考（声明 line_compare 的页
  prompt 里必有 line_chart 模板结构·延续"模板供结构不供皮肤"）；范本卡检索词表已做同义映射
  （FR3.3·"数据论断"↔"数据呈现"，修复 22 页喂错卡）；
- **图标 inventory（FR7.5）**：SVG 里用 `<use data-icon="名字">` 占位（只准用 inventory 清单内的名字，
  `icon_sync` 缺名强制重选），finalize 时转换引擎内嵌真图标。
`pipeline.build_deck` 逐页自动跑文案关（`reinforce.deck_rules.rules.run_text_gate`，内部按
SVG 抽文字，抽取函数是 `pipeline.py` 内部私有实现，不对外暴露，不需要也不能手动调），
结果落在 `res["pages"][n]["gate"]`（`res` 见阶段3 `build_deck` 调用）。
**关闸**：每页 `gate["passed"]` 必须 True（有 error 返工）。warn（数字无 source / 标题过长 / spec_lock 外用色）人审补。
`pipeline.build_deck` 已自动跑 `check_svg_compat`（PPT 导出兼容性机检·提炼自 ppt-master `shared-standards.md`，
779 行黑名单的真实风险补课）——`rgba()`/`<g opacity>`/`<image opacity>`/`<style>`/`class=`/`<mask>`/裸 `&` 等
会导出失败/损坏的写法直接 error 拦截，不用靠人记。

`pipeline.build_deck` 还自动跑 `run_visual_gate`（视觉缺陷结构级机检·提炼自 ppt-master `visual-review.md` 的
H1/H4/H8/S6——出画布/对比度(WCAG真实公式)/图片引用破损/CJK字距过松，全 warn 喂人审，不阻断导出）。
**⚠️ 这不是那套完整的"批量渲染+subagent自动修复"系统**——H4 对比度/隐形文字的背景推断 D18 FR1.5
已从"整页背景"升级为**最近包含矩形**（单层几何包含推断·不做透明度叠加合成，第一轮实测 121 条假
阳性即此病，升级后应 ≤10），文字坐落在多层半透明叠加上时仍可能有残余假阳性，看到 warn 先用
人眼判断是不是真问题再处理；**chart 兑现机检（D18 FR3.2·warn）**：渲染后按"chart 类型→期望元素"
启发式核对（声明折线页无 `<path>` 折线 → warn 喂人审）——第一轮"声明 20 种 chart 兑现 0"就靠这道
兜底逮；**Part 级视觉配额（FR3.5·warn）**：逐 Part 数强视觉页够不够 1-2 页。`review.py` 的
`slide_content` 人审清单列的视觉重心/网格对齐/呼吸感留白
这类项，仍然不做几何近似硬判（误报率比不查还误导人，见 `reinforce/deck_rules/visual_review.py` 范围声明）——
但**不等于没人看**，这一步现在由下面这道"渲染自检"关卡承接（D18 FR1.4 起就是逐页节拍的第③步）。

> **🔒 渲染自检关卡（2026-07-01·D7 路线A拍板·创意层第一版；D18 FR1.4 起=逐页节拍的固定一步）**：
> 每页写完，**在生成这一页的同一个对话里**渲染成图片、亲眼看一遍，连同硬门当页过完、有问题当页返工，
> 才决定进不进下一页——不是另起一个 subagent 或外部视觉模型，是当前主
> agent 自己读图判断。跟前面机检最大的区别：机检抓的是"违反了哪条硬规则"，这一步抓的是"看着舒不舒服"，
> 正是 `slide_content` 人审清单里那些机器判不了的项（视觉重心/留白/对齐/呼吸感）。
> ```python
> from engine.render_preview import render_svg_to_png
> render_svg_to_png(svg, f"{out_dir}/page_{n}_preview.png")   # 或整份deck用 build_deck(render_previews=True)
> ```
> 然后用 Read 工具打开这张 png **亲眼看**，对照 `slide_content` 清单自问："一页一焦点吗？视觉重心清楚吗？
> 强调色是不是控制在 2 种内？留白够不够？同行同列元素对得齐吗？"——挑得出具体毛病就回去改 SVG 重渲一次，
> **最多改 2 轮**（改不完的说明这页设计思路本身有问题，别在同一页死磕，先往下走或跟用户过一遍思路），
> 不是为了"改到我觉得完美"无限循环。
> **诚实边界**：这是 Claude 自己的一次性视觉判断，不是训练过的设计评分模型，也不能替代最终人工验收——
> `render_preview.py` 用 Playwright(Chromium) 渲染（CJK 正确渲染的唯一可靠方案，cairosvg 等轻量方案中文
> 字体无回退链会渲染成方块，已用真实测试验证，见该模块 docstring），playwright 是可选依赖，未装时
> `render_svg_to_png` 会抛清楚的 ImportError（附安装命令），不会静默跳过让你误以为自检发生过。
>
> **🔒 SVG 必须逐页手写，禁脚本批量生成（写死·D1 决策记录 2026-07-01 补记的真实教训）**：
> 每页 SVG 必须当前主 agent（Claude）逐页手写，在带着完整上游上下文（spec_lock + 上一页 + 本页 evidence/claim）的
> 情况下现场创作——**禁止写 Python/Node/Shell 脚本批量生成**（哪怕"数据驱动模板"——遍历 evidence 自动套进固定
> 坑位渲染，看着像手写，本质是生成器）。这条直接抄自 ppt-master `SKILL.md` 的铁律「SVG MUST BE HAND-WRITTEN,
> NOT SCRIPT-GENERATED」——他们在 feature branch 上试过脚本生成路径，放弃了："跨页视觉一致性依赖逐页带着
> 完整上游上下文的手写创作，脚本生成器做不到。"
> **真实踩过的坑**：这条纪律早在 D1 vendor 决策时就被标成"遗留张力·别想当然绕过"，但制作层开工时
> （`examples/demo_cfo_speech.py`/`demo_descente_deck.py`）没回查决策记录、直接写了批量生成脚本，原样踩了。
> 那两个文件里的 `callout_tpl`/`confront_tpl`/`fact_tpl` 等"数据驱动模板"函数**是反模式的活样本，不是该抄的写法**——
> 留着只为给 `pipeline.build_deck` 当回归测试 fixture（验证编排链路本身），**生产路径绝不能照抄这个写法**。
> 一次只问一个点和"逐页手写"同源——都是"以人为主全程引导对齐"那条最高铁律在不同层面的体现：不批处理。
> SVG 生成规范（喂给生成这步·D18 FR7.1/FR7.6 更新）：**色彩纪律按锁定风格手册走**（旧版写死的
> "一个高亮色其余灰"已删——那是把 18 种风格塌缩成单色卡片网格的病根之一），色值只准出自 spec_lock
> palette；**字号走 typography 角色槽**（title/subtitle/lead/body/annotation/footnote/hero 各锁一值，
> 同角色跨页漂字号=不专业；未锁 typography 的旧 deck 兜底 8 级网格 `{44,28,24,22,18,16,14,9}`）；
> 数字带 source；**页面文案=对客语域**（FR5.3·工作定位符/流程自述永不上页，`check_client_facing_tone`
> 兜底——D19 FR1.2 起分级：**标签冒号形态[「聚焦判断：」「立场：」类]与 brief 定位符=error·strict
> 拦导出**，流程自述/白名单外缩写/工作口语仍 warn 喂人审；白名单控误拦——只拦"标签冒号"形态与
> 工作短语，**不拦"我们的立场是与消费者站在一起"这类自然句**）。
> **subtitle=写给客户读的导读句（D19 FR1.4·第二轮实测确诊字段语义直译上页）**：subtitle 的功能是
> 导读，写法必须是**给客户读的真句子**，禁止把工作字段的语义直译上页——
> ❌「聚焦判断：这次要解决的是哪个缺口」→ ✅「三个增长缺口里，情感连接是本案要攻的主阵地」；
> ❌「开场判断：……」→ ✅ 直接给判断本身（判断内容就是导读句，永远不带字段名前缀）。
> 「聚焦判断：」这类**标签冒号形态已进对客文案门 error 清单**（D19 FR1.2·strict 拦导出）；
> subtitle 写完自查一遍：这句话拿给客户读，像方案还是像说明书？
> **⚠️ 页面展示整组证据**：数据论断页要把该页 evidence 的**一组数据都摆上**（焦点数字最大 + 其他证据作支撑），别为"极简"只画一个数——那违背"一组证据合围"（用户验收教训）。
> **⚠️ 页面 ↔ 讲解同源对齐**：页面展示的数据 = 讲解词(narration)念的数据（都从 evidence 出）。**讲解有、页面无 = 不合格**（演讲者讲的，观众得看得到）。
>
> **🔒 SVG 文字渲染必须用 `engine/svg_layout.py`（写死·不准重新发明）**：
> ```python
> from engine.svg_layout import hero_text, text_block, source_card_from_evidence
> ```
> - 焦点数字 / 长文本一律用 `hero_text()` / `text_block()`，**绝不手写裸 `<text>` 塞固定字号**——
>   Descente 实战真出过这 bug：把 18 字长句塞进 130px 巨字号槽，直接撑爆画布。这层是机制防呆，不是凭手感画对。
> - evidence 若带真实来源（用 `engine/research.py::attach_citation` 填的字段），调 `source_card_from_evidence()`
>   渲染引用卡——**不要按页号现开一张硬编码表**（旧 demo 的反模式：`SOURCE_CARDS={7:..., 11:...}`，换个 deck 直接失效）。
> - **判断"按页码索引是不是反模式"的真正标准**：看这段渲染逻辑**打不打算被复用**。
>   `confront_tpl`/`callout_tpl` 这种**通用模板**（设计成喂任意 deck 任意页数据都能渲染）内部认死页码 = 真反模式
>   （通用系统和特定页面强绑定）。但像封面/高潮/创意展示这种**针对某份 deck 手写的独一无二内容**，
>   用页码索引 = 诚实标记"第几页的手写产物"，不是反模式（和文件叫 `page_14.svg` 是同一件事）。
>   **别看见"字典+页码"这个表面形状就套用结论——先确认这段代码是不是真的设计成可复用的通用系统。**
> - 这条铁律的由来：这些工具最早是在某次 demo 脚本里现写的，被用户点破"我们是在改引擎不是改一个 PPT"才回炉提炼成引擎层。
>   **下次发现新的排版/渲染坑，先问「这个修法进的是 demo 文件还是 engine/reinforce 包」，答案必须是后者。**
>
> **🔒 waterfall / Gantt / Mekko 图表几何必须用 `engine/chart_shapes.py`（写死·不准手算）**：
> ```python
> from engine.chart_shapes import waterfall_chart, gantt_chart, mekko_chart
> ```
> - **这条纪律替换旧版**"图表几何手算，生成后 render 自检"——手算浮空柱/列宽占比这类累加/比例算术极易出 bug
>   （见 `specs/PPT方法论/06_高stakes难图实现.md`），跟 `hero_text()` 补漏 `min()` 封顶是同一类教训：能写成确定性
>   函数的几何计算，就不该指望 LLM 逐页心算再肉眼查。
> - 三个函数只画图表本体（返回一个 `<g>` 片段），画布区 `x/y/w/h` 按当页 spec_lock zones 定；标题/action title/
>   来源引用/图例说明仍由本页手写 SVG 现场拼（这层不越界代管内容判断，只管坐标算对）。
> - **颜色必须传 `colors=` 覆盖默认值**：函数默认色取自 `engine/ppt_master/templates/charts/*.svg` 真实模板，
>   只是"起点参考"，正式生成时必须按当次 `spec_lock.palette` 传入锁定色板（"模板供结构不供皮肤"同一条纪律）——
>   不传等于直接把模板色当成品出，`check_against_spec` 会 warn。
> - 三个函数的 `x,y,w,h` 是**无默认值的必填位置参数**（画布区坐标，按当页 spec_lock zones 定，
>   排在数据参数**前面**）——照抄"只传数据参数"的写法会直接 `TypeError: missing 4 required
>   positional arguments`，下面每行都把这四个参数摆出来，别漏抄。
> - `waterfall_chart(x, y, w, h, items=...)`：`items` 每项 `{"label","value","measure":"relative"|"total","display"?}`，
>   `display` 缺省用 `str(value)`——数字格式（要不要加"+"号/单位/千分位）由调用方按当页真实数据决定，
>   函数不做静默格式化（数字溯源铁律：不改写原值）。
> - `gantt_chart(x, y, w, h, tasks=...)`：`tasks` 每项 `{"label","start","end","progress"?}`（日期 `"YYYY-MM-DD"` 或 `date`），
>   `start==end` 自动画里程碑菱形；`dependencies=[{"from":i,"to":j}]` 画依赖箭头（原生 DrawingML 线端，非位图）——
>   frappe-gantt 本身没有依赖箭头，这是咨询级差异化的差异点，别漏画。D18 FR3.6 修复：行标签色已
>   参数化（跟随 `colors=` 传入的 spec_lock 色板，不再写死）、标签定位跟随色条（不再永远停在左缘）。
> - `mekko_chart(x, y, w, h, columns=...)`：`columns` 每项 `{"label","weight","segments":[{"label","share","color"?}]}`，
>   列宽按 `weight` 占比自动铺满整轴——这是三大高 stakes 图表里唯一连 ppt-master 模板都没有的（71 张图表模板
>   grep 零命中），纯自研，没有第二个选项。

**Read-Through 通读自查（D20 FR2.2·阶段 2 收尾：全部页做完、进导出之前·工序纪律）**：把全部页面
的 claim + subtitle **按页序串成一篇文章通读一遍**（出处：McKinsey Read-Through Test——只读每页
标题验证横向逻辑是否成文），自查两问：
1. **哪句在谈论这份 deck 自身而不是客户的生意？**（「这份提案 / 本页 / 后面每一页都在证明它 /
   诊断完毕」式元叙述——第三轮实测 12 页命中全长在目录/转场/章小结/决策前这些结构性文案位置；
   命中的当页改写重渲）；
2. **抽掉页面只读标题，像一篇连贯的商业论证，还是像一份操作手册目录？**（后者=结构性文案在播报
   工序，回策略 SKILL 六槽位速查表对照返工）。
逐页节拍看的是单页，这一步看的是**串起来读**的横向连贯——单页都过门 ≠ 串读成文，所以放收尾补看
一遍。**定位边界（铁律 2·写明不许走样）**：这是**工序纪律 + 人审信号，不是机检**——"像不像论证"
是 LLM/人的语感判断，绝不当自动硬门的信号；确定性形态（文档部件词 × 过程时态词组合）由
`check_client_facing_tone` 的元叙述检测在逐页 gate 里兜底，两层各管各的。

### 阶段 3 · 导出（vendor 引擎关闸）
全页 SVG → 一份原生可编辑 .pptx。**一站式**用 `pipeline.build_deck`（自动跑阶段 1 校验 + 阶段 2 逐页硬门 + 阶段 3 导出）：
```python
from engine.pipeline import build_deck
res = build_deck(o, svg_provider, ws["pages"], strict=True, workspace=ws,
                 spec_lock=spec)   # spec = 阶段1.5 锁定的那份·必传（漏传=设计锁整条链不激活）
# res = {pptx_path, pages:[{n, gate, svg_path, resumed}], all_passed, deck_warnings}
```
> ⚠️ `spec_lock=spec` 别漏（2026-07-02 saopan扫盘揪出：此前本示例没写这个参数——照抄执行则
> 阶段 1.5 辛苦建的 spec 在产线上根本不激活，逐页强制重读/用色机检/色盲检测全部空转，只剩每页
> 一条 warn。"文档喊强制、示例可绕过"第 4 次复发，这次长在示例代码上）。
`workspace=ws` 传入后（④数据产物层接线·2026-07-02）：① 开工前 `assert_editable`——已交付 deck 拒重做
（铁律 4 硬拦）② 每页状态真实流转（生成→`drafted`·硬门全过→`gated`·导出→`done`，没过门的页停在
drafted 供返工；**resume 重检失败的页会降回 drafted 落盘**，不留假绿）并逐页落盘 `outline.json`
（中断不丢进度）③ 收尾自动汇集 `asset_ledger.json` 溯源台账 ④ **成品统一落 `ws["pptx"]`（deck.pptx）**
——2026-07-02 saopan 修复：此前成品写 `pages/<标题>.pptx` 而 `publish_deck` 校验 `deck.pptx`，
两个路径对不上，交付物 checksum 机制在标准链路 100% 空转。
不传 workspace 能跑（旧调用兼容）但 `deck_warnings` 会记一条——无只读锁保护、状态不落盘、不能断点续做。
**关闸**：解包验证质量（绕 python-pptx 3.14 读回 bug，用 zip/XML）：
```bash
unzip -o deck.pptx -d _chk >/dev/null
grep -c '<p:pic>' _chk/ppt/slides/slide1.xml   # 必须 0（非图片）
grep -c '<a:t>'   _chk/ppt/slides/slide1.xml   # >0（有原生文字）
```
`<p:pic>≠0` = 文字被栅格化 → 检查 `export_deck` 是否 `use_native_shapes=True`（封装默认已开）。

### 阶段 4 · 交付（Memory 只读锁 + 人审完成度闸）
交付判断是**人拍板**（铁律 0/2·机器不代判"可以交付"）。**D18 FR6.1 人审完成度闸**：`publish_deck`
前会校验三道人审清单（action_title/storyline/slide_content·`review.py`）**完成度**——第一轮实测
review 视觉 9 项全 null 照样交付，就是这道闸缺位；现在**清单没勾完拒交付**（机器只拦"没做"，
不代判"好坏"——勾没勾是事实，好不好是人的判断）；紧急场景 `force=True` 强行交付 + 留痕。
直通档（D21）：`publish_deck(deck_id, direct_through_waiver="用户开场选直通的原话")` 豁免人审闸——
与 force 是两种语义（force=事中紧急绕行，waiver=开场预授权"问完直接到出成品"），返回值
`review_waiver` 如实记"未经人审·依据哪句授权发布"，不伪造勾选；**交付摊面必带
`assumption_ledger(team)` 假设台账**（AI 代拍过哪些方向+为什么），用户验收操盘重点看这份。
拍板后收尾一步到位：
```python
from reinforce.deck_memory import new_handoff
from reinforce.deck_workspace import publish_deck
publish_deck("descente_y26_proposal",          # 登记只读锁 + 写交接卡·一个入口做完
             handoff_card=new_handoff("Descente Y26 提案", 21, todos=[], next_steps=["等客户反馈"]))
```
**收尾必做②：请用户给一句整体反馈（D24 宪法第 5 条）**：交付后主动问"这单整体感觉如何？
哪里最不满意？"（开放问题·文字对话），答案逐字入反馈池
`knowledge_ingest.queue_feedback(用户原话, context=..., deck_id=..., date=...)`；制作过程中用户
说的任何反馈/纠偏/想法同样随手入池——一句不丢（反馈池无自动入库路径·人审转需求种子/偏好）。
**收尾必做：产物入 git（D18 FR6.3）**：publish 成功后把 `data/decks/<deck_id>/` 按既定 git 策略
提交（**png 唯一忽略**·pptx/svg/json 全进 git，策略见 2026-07-02 拍板记录）——产物闭环的最后一步，
不提交 = 换台机器/换会话就丢真相源。提交动作照例先跟用户确认再执行。
此前这里让人分别手调 `mark_published` / `save_handoff` 两步全靠自觉——漏掉 `mark_published` 则
`assert_editable` 永远拦不住回改（只读锁形同虚设），现在收成一个函数。
**关闸**：交付物只读真相源，改 = 新 deck_id 走新版本，绝不原地覆盖（铁律 4）——上锁后再对同一
deck_id 跑 `build_deck(workspace=ws)` 会被 `PermissionError` 硬拦，这不是提醒是拦截。
`publish_deck` 会自动算 `deck.pptx` 的 sha256 记入登记表（D16 🟢①·npm integrity 同款机制）；
之后随时 `verify_published()` 巡检"已交付产物有没有被绕过只读锁直接改文件"（ok / mismatch /
missing_file / no_checksum 四态·只验本地副本，交付出去的文件在客户手里的变化超出系统边界）。

### 🔁 断点续做（中断的制作会话怎么接·Memory「新会话能续上」的兑现）
`outline.json` 是活文件（`build_deck` 每页落盘状态）。新会话接手：
```python
import json
from reinforce.deck_state import load_outline
from reinforce.deck_workspace import new_workspace
ws = new_workspace("descente_y26_proposal")    # 幂等·拿回路径映射
o = load_outline(ws["outline"])                # 读回真实进度（哪页 done 哪页 drafted 一目了然）
spec = json.loads(ws["spec_lock"].read_text(encoding="utf-8"))   # 读回阶段1.5 落盘的设计锁
res = build_deck(o, svg_provider, ws["pages"], workspace=ws, resume=True,
                 spec_lock=spec)   # spec_lock 必传——输入指纹含它，第一遍带锁、续做不带 = 指纹必不匹配必拒
```
> ⚠️ 续做必须**读回同一份 spec_lock**（2026-07-02 saopan扫盘揪出：此前本示例不传 spec_lock——
> 带锁 deck 照抄续做 100% 被"输入已变"拒掉，报错还误导人去改输入；spec_lock.json 就在 workspace
> 里，读回来传进去即可。per_page 页号键落盘后是字符串，`spec_lock_brief` 已兼容，不用手转）。
`resume=True`：状态已 `gated`/`done` 且 `pages/` 下 SVG 还在的页，跳过重新生成（LLM 逐页手写是贵的
那步），**硬门照样重跑**——规则可能升级过，上次过门不代表这次过（防假绿）；重检没过如实计入
`all_passed`。已过门的页在**非 resume** 场景被重做会直接拒（"拒绝静默重做"·同只读锁一个精神）；
确要返工把该页 `status` 手工改回 `planned`（罕见路径不设机器通道，outline.json 是可编辑 JSON）。
复用前还会比对**输入指纹**（D16 🟡②·Bazel action key 思路）：每页生成时记 claim/facets/spec_lock
的 sha256，resume 时输入变了 → 拒复用过期 SVG（改回原输入，或该页改回 planned 重做）——防"改了
论点却续用旧页面"这种硬门逮不住的漂移。

### 阶段 5 · 备注 + 演讲词 + 语音（备注全版本都写·语音仅演讲版）
演讲版页面是浓缩，**演讲词（narration）把每页观点展开讲透**——不是念页面字。配 TTS = 会自己讲的 deck（发出去无人在场也能讲）。

**预读讲解版的备注（D19 FR3）**：这一态是"先发客户自读、看完再开会讲"——**备注必须按现场讲写**
（下方 FR7.8 承接/位置/展开/落点四环标准原样适用），不是阅读版式的可省项：页面负责自读自洽
（导读副标题在），备注负责"看完之后那场会"的讲述脚本。语音（TTS）默认仍仅演讲版做——预读讲解版
有真人现场讲，用户点名要才配。

**备注写作标准（D18 FR7.8·问题A核心件三·对齐 ppt-master 真样本水准）**：每页 speaker notes 是
**完整讲述逻辑**，不是页面文字复读——验收标尺是两份真样本：pritzker 备注"第七站，阿布扎比…"
（沿叙事线讲，每页知道自己是故事的第几站）、swiss 备注在**推导**设计系统（"基本单位 16px、所有
尺寸由此派生"——讲 why 不是念 what）。落到写法，每页备注要含**叙事推导链**：
1. **承接**：上一页/上一章讲到哪了（转场页用 `bridge_from`，其余页看上一行 claim）；
2. **位置**：本页在 Part/框架弧的哪一站（part + stage）、凭什么存在（sowhat）；
3. **展开**：亮数 → 解读 → 反方会怎么读、拿什么堵回去（framing 的 stance/counter_read/basis）；
4. **落点**：这页讲完听众该带走什么、怎么自然带到下一页。
**机制落点**：备注/讲解词的输入是 **storyline 推演链**（sowhat/framing/bridge_from/part），不是
渲染后的页面文字——`notes_for_storyline`/`narration_for_storyline` 已按此实现（备注头带
`Part·章名`、转场承接 `bridge_from`、数据页收 sowhat 落点、Part 首页报站）；LLM 手写讲解词时
同样从 storyline 行出发按上面四环写，**不许照着 SVG 念**。

**讲解词写作规范（5 原则）**：
1. **展开非复述**——讲解 ≠ 念 claim；讲解词应明显比页面字多（页面浓缩、讲解讲透）。
2. **围绕焦点深度描述**——数据页尤其：亮关键数 → 强调（首次 / 异常）→ 对比参照 → 解读含义 → so-what → 落回论点。
3. **口语化**——短句顺口；念不出的符号转中文（`−20%`→"下滑 20%"、`→`→"降到"）。
4. **有节奏**——情绪页慢 / 留白、高潮页重 / 急、转场一句带过。
5. **时长适中**——每页约 50–150 字（15–45 秒）；太短没展开，太长啰嗦。

**按页型的讲解结构**：
| 页型 | 结构 |
|---|---|
| 数据论断 | 点题 → 亮数 → 强调异常 → 对比 → 解读 → so-what → 落论点 |
| 情绪slogan | 渲染氛围 → 留白停顿（短·慢·不堆数据） |
| 转场 | 收上段 + 一句预告下段 |
| 高潮 | 强调后果 → 制造紧迫 → 加重 |
| 决策 | 重申落点 → 明确 ask → 催促行动 |

**审核清单（如何审核 · 机检 + 人审）**：
- 机检：① 展开度（讲解词 > claim·非纯复述）② 时长 / 字数（50–150 字）③ 口语（无念不出符号 / 书面长句）
- 人审：④ 数据深度（围绕数据·有解读 + 对比 + 推演）⑤ so-what 落点 ⑥ 亮眼度 / 情绪 / 节奏 ⑦ 上下页衔接

**实现**：
```python
from engine.speaker_notes import narration_for_storyline  # 模板(推演链结构对·兜底)·真正亮眼靠 LLM 按上规范写
from engine.narration import narrate_pptx                  # edge-tts→嵌入→autoplay(默认引擎)
# 主路径：LLM 按上面备注标准逐页手写讲解稿（从 storyline 行出发，不照 SVG 念）
narrate_pptx(pptx_path, [narration.get(n, "") for n in page_ns])   # 不传 voice 时用默认 EDGE_VOICE(云希·男声神经语音)
# 兜底路径（D18 FR7.8）：直接喂 storyline，讲解词从推演链生成（sowhat/framing/bridge_from/part 全吃）
narrate_pptx(pptx_path, storyline=sl)   # 与 narration_list 二选一·都传/都不传都拒(fail-closed)
```
> ⚠️ **TTS 引擎**：默认 `edge`（微软 Edge 神经语音·免费无 key·接近真人，`EDGE_VOICE="zh-CN-YunxiNeural"`，
> 女声可传 `voice="zh-CN-XiaoxiaoNeural"`）；`engine="say"` 是 macOS 本地兜底（无网络时用，机器味明显，
> 对应声线 `SAY_VOICE="Tingting"`——**"Tingting" 是 say 专属声线，别当 edge 的 voice 传，两者对不上**）。
> ⚠️ **讲解词「亮眼」是模板天花板**——产品里这步应由 LLM 按本规范生成（同 SVG 生成），模板只保证结构对、可兜底。

## 🧱 当前边界（诚实标注）
- **SVG 生成 = Claude 当 LLM 手写**（无独立视觉模型 key·同 chaideck 苦力待定）。接入视觉/代码模型后，`svg_provider` 换成它，Claude 退到审稿。
  **⚠️ "手写"指对话中逐页现场生成，不是预先写一个 Python 脚本批量产出**——demo 文件违反过这条，已标注反模式见阶段2。
- **创意层第一版已落地（2026-07-01·D7 路线A）**：`engine/render_preview.py` 把每页渲染成 PNG（Playwright，
  CJK 正确渲染已验证），Claude 生成时读图自检（阶段2"渲染自检关卡"），补上机检覆盖不到的"看着舒不舒服"
  这块——**但这仍是 Claude 自己的一次性视觉判断，不是独立训练过的设计评分模型，也不构成"已验证"的🟢信号**，
  最终人工验收仍不可跳过。已知边界：只有当前主 agent 自己看+自己判，没有像 ppt-agent-skills 那样的
  "独立子agent像素级审+自动repair"闭环——路线选择见 `specs/决策记录.md` D7，是刻意取舍非未及做。
- **waterfall/Gantt/Mekko 几何已摘掉手算风险**（2026-07-01）：三者坐标计算落进 `engine/chart_shapes.py`
  （见上方阶段2"🔒 waterfall/Gantt/Mekko 图表几何必须用 chart_shapes.py"），不再手算累积/占比。
  **其余图表几何**（donut 的 dasharray 等未覆盖类型）仍是手算，易出几何 bug，生成后用
  `mcp__visualize__show_widget` 渲 SVG 自检再导出。
  接了 `engine/ppt_master/templates/charts/`（71 个专业图表模板）后，**优先适配现成模板，不再从零手算几何**
  （高 stakes 难图具体哪张模板能用、哪段仍要自研，见方法论 [06](../../specs/PPT方法论/06_高stakes难图实现.md)）。
  >
  > **🔒 模板供结构不供皮肤（写死·抄自 ppt-master `executor-base.md` §1，2026-07-01 补）**：
  > 用 `engine/ppt_master/templates/charts/`、`engine/ppt_master/templates/layouts/` 里的现成模板时，**只继承它的坐标几何/版式结构**
  > （矩形怎么摆、分区怎么分），**模板自带的渐变色/阴影/字号/具体色值一律当占位符丢弃**，必须按当次
  > deck 的 spec_lock 重新蒙皮——禁止直接照搬模板源文件里的 `fill="#10B981"` 这类视觉细节进成品。
  > 真实例子：`waterfall_chart.svg` 自带 emerald/rose 渐变配色，如果当次 deck spec_lock 锁的是品牌红蓝，
  > 抄它的坐标和涨跌逻辑，但颜色必须换成 spec_lock 里锁定的色值——不然就是又一次"跨页风格漂"，
  > 只是这次漂移源头从"凭记忆现编"变成"照抄模板自带值"，性质一样。
- **已做**：演讲者备注（speaker notes）+ 机器语音讲解（narration·edge-tts 默认引擎·autoplay）自动生成
  （阶段 5·D18 FR7.8 起输入=storyline 推演链：sowhat/framing/bridge_from/part，`narrate_pptx(storyline=sl)` 可直喂）；
  spec_lock 机制（`reinforce/spec_lock.py`，颜色/字体/`per_page`（chart/rhythm/hero）锁定 + 用色机检，
  逐页 prompt 自动按页号拼对应锁定项，2026-07-01 接通；`per_page` 由 chart_assign/page_rhythm/hero_pages
  三个平行字段统一重构而来，2026-07-01 补；D18 FR7.2 扩容为完整设计契约——visual_style/typography
  角色槽/icons/images/image_rendering×palette/逐页 layout+visual_concept，见阶段1.5）；补 vendor
  ppt-master 设计资产（`engine/ppt_master/`）；**③ 视觉精修/设计层 D18 FR7 接线**（18 风格手册/81 图文
  版式/7 套 layouts 骨架/5 图标库/图像六源管线——资产早已 vendor 在仓库，D18 补的是接线与流程，见阶段1.5）；
  视觉缺陷结构级机检 `run_visual_gate`（H1出画布/H4对比度/H8图片引用/S6字距，2026-07-01 接通；
  D18 FR1.5 背景推断升级"最近包含矩形"，见阶段2）。
- **未做**：母版/主题系统、动画、多 deck 批量、
  云 TTS（自然语音需 key）、讲解词的 LLM 生成（现为模板+推演链结构兜底·亮眼靠当场手写）、`zones`(spec_lock 页面分区预算字段)的几何越界机检
  （故意没做，代价/收益不成比例，见 `spec_lock.py` 注释）、**像素级渲染视觉审查**（ppt-master 完整版
  visual-review.md 的 H2/H3/H6/H9 精确版 + S1-S5/S7-S10：真要做，需要新依赖 Playwright + 本地 Chromium +
  一套 live-preview 渲染服务，是独立的基础设施投入——**触发条件**：单 deck 页数大到人眼逐页审已经不可靠
  / 同一套版式要批量复用到很多 deck 不再是每页都有人手写盯着时，再启动，不要现在因为"够新潮"就上）。

## 🔁 对应 Novel
`~/.claude/skills/xieshu/SKILL.md`（写书工作流·分章 fail-closed）。本 skill = 视觉版：分页 fail-closed，每页出关闸。
