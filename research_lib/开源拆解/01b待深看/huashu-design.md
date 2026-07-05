# 开源拆解 · huashu-design（花叔Design）

> 日期：2026-06-30 · 方法：克隆仓库 `ls -R` + 全文读 SKILL.md(62KB) + README中英 + references/(slide-decks / editable-pptx / critique-guide / verification / design-styles) + scripts/ + package.json/.env/test-prompts。保真带出处，中英文都读。
> 对象：`alchaincyf/huashu-design`（~19k★·MIT·Claude Code skill 形态·和我们最像）。作者花叔（花生），代表作女娲.skill(12k★)、《一本书玩转 DeepSeek》。
> 一句话最值得偷：**「选择无效铁律」——需求模糊时绝不抛文字单选题让用户盲选风格，而是并行 spawn 3 个独立-context subagent 各产出一版真实视觉，让用户在「看得见的东西」里选。** 这把"问 vs 做"的死结直接解开，是咨询级 deck 策略层最该抄的交互范式。

---

## 0. 三个最重要的判断（先读）

1. **它是「制作工作流」的天花板级参照，不是策略层竞品**。huashu-design 全部能量在「把视觉做到大厂水准 + 反 AI slop」，**没有 brief 解读 / 判目的 / 市场调研 / 反复推敲**那一层——和开源生态调研的总结论一致（99% 卡在制造）。但它把"制造"做到了别人没做到的深度：**HTML-first 单一真相源 + 一键派生 PDF/可编辑PPTX，且把"为什么这样做"写进每条规则**。对我们「制作工作流」是可直接搬的成熟蓝本。
2. **它已经把"咨询级 deck 风格"显式编码进风格库**。`design-styles.md` 的「PPT 20 种」直接点名 McKinsey/BCG 双字体咨询版、Sequoia/Airbnb 极简 pitch、断言-证据(Tufte)、Bento、Big-Number Stage、Sparkline 叙事(Duarte)、图谱箭头企业版——**这正是我们收窄的高 stakes 段**。每种都带「参考案例 + 视觉DNA + 纯HTML还原度% + 开源字体替代」，是现成的"咨询 deck 视觉语法表"，可拆进我们的 04制作/05图表 层。
3. **它的"防假绿"是靠规则里嵌入的真实踩坑代价 + 硬 checkpoint，不是靠 LLM 自评分**。每条铁律都挂一个带日期的事故记录（"2026-04-20 DJI Pocket 4 实测翻车，返工 2 小时"），并用 🛑 STOP/检查点把流程卡死（"清单里有一个没取到 logo = STOP 补齐"）。这是「fail-closed 出关闸」在 prompt-only skill 里的实现样板——和我们七铁律 §2 防假绿同构，且做法更"叙事化、可被 agent 内化"。

---

## ① 是什么 + 定位

- **一句话**：在 agent 里打一句话，拿回一份"看起来像大厂设计团队做的"可交付设计。3–30 分钟产出：交互原型(App/Web) / HTML deck + 可编辑 PPTX / 时间轴动画(MP4+GIF+BGM) / 信息图 / 设计变体。
- **形态**：纯 markdown skill（`SKILL.md` + `references/` + `assets/` + `scripts/`），**agent-agnostic**——Claude Code/Cursor/Codex/OpenClaw/Hermes 都能装（`npx skills add alchaincyf/huashu-design`，skills.sh 兼容）。这点和我们形态完全一致。
- **起源**：作者拆解 Anthropic 的 Claude Design（含社区流传系统提示词 + 品牌资产协议 + 组件机制），蒸馏成结构化 spec 再写成 skill。**核心思想偷自 Claude Design 那句"好的 hi-fi 设计不是从白纸开始，而是从已有设计上下文长出来"**——作者称这是 65 分作品和 90 分作品的分水岭。
- **自我定位诚实**：README 明写"这是一个 80 分的 skill，不是 100 分的产品"；Limitations 列了不支持图层级可编辑到 Figma、不支持 Framer Motion 级复杂动画、完全空白品牌从零设计会掉到 60-65 分。**这种"标清楚边界、不吹"的态度本身值得抄进我们的交付说明。**

---

## ② 作为 Claude skill 怎么组织（最该精读的维度）

### 2.1 文件架构：薄主文档 + 路由表 + 厚 references + 可执行 scripts + starter assets

```
SKILL.md          # 主文档(给 agent 读)。前置 frontmatter 塞满触发词；正文是"核心哲学+工作流+异常处理+路由表"
references/*.md    # 24 篇按任务深入读的子文档(slide-decks/editable-pptx/critique/动画/音频/风格库…)
assets/*.jsx/.html # starter 组件(ios_frame/deck_index/animations/design_canvas…)+ 24 个预制 showcase 截图 + 6 首 BGM + 37 个 SFX
scripts/*.mjs/.js/.py/.sh  # 导出工具链(html→pdf / html→可编辑pptx / 录视频 / 加BGM / 取图 / verify)
```

**关键机制 = "References 路由表"**：SKILL.md 末尾有一张大表「任务类型 → 读哪个 reference」。主文档只放哲学和流程骨架，**具体操作细节按需加载**——这是把 62KB 主文档 + 24 篇子文档组织成"渐进披露"的核心。对我们启示：主 skill 别堆死知识，用路由表把"高 stakes 图表怎么画""可编辑 PPTX 4 约束"等重型知识拆成按需读的 reference。

### 2.2 frontmatter description = 触发词军火库

`description` 一整段塞满中英触发词（"做原型/交互原型/HTML演示/做个可视化/iOS原型/导出MP4/设计风格/推荐风格/做个好看的/评审/好不好看/review this design…"）+ 一句话流程摘要。**这是 skill 被正确唤起的命门**——我们的 PPT skill 同样要把"做咨询 deck/投资人 PPT/waterfall/Mekko/路演"等高 stakes 触发词铺满。

### 2.3 分步流程：编号工作流 + 嵌入式 🛑 检查点（fail-closed 的 prompt 实现）

主工作流 10 步（理解需求→探索资源抽资产→先答四问再规划系统→建文件夹→Junior pass→Full pass→验证→总结→导视频→可选评审），**每个关键节点插一个 🛑 检查点**，且明写检查点原则：

> "碰到 🛑 就停下，明确告诉用户'我做了X，下一步打算Y，你确认吗？'然后**真的等**。不要说完自己就开始做。"

这就是 fail-closed 出关闸在对话式 skill 里的形态——**不靠代码闸门，靠把"停下等人"写成承重墙规则**。对我们"纪律分阶段 fail-closed"是直接同构的参照。

### 2.4 质检：三层

- **核心原则 #0 事实验证先于假设**（优先级凌驾所有流程）：涉及具体产品/版本/规格的事实断言，第一步必须 WebSearch，禁止凭训练语料断言。列了**禁止句式**("我记得X还没发布""X目前是vN版本")+ 真实反例(DJI Pocket 4)+ 代价对比("WebSearch 10秒 << 返工2小时")。
- **Playwright 验证**（`scripts/verify.py` + `references/verification.md`）：打开 HTML→截图→抓 console error→报 status。多 viewport、逐页截 deck。理念："验证=设计师的第二双眼，最后1分钟验证省1小时返工。"
- **5 维度专家评审**（见 ④/⑤ 详述）：可选的结构化打分。

### 2.5 跨 runtime 适配 + 隐私护栏（工程细节）

- 专门一节「跨 Agent 环境适配」：没有内置 fork-verifier 就用 verify.py；不支持 spawn subagent 的 runtime(Codex/Cursor) 改**串行跑三套逻辑**、用三个 anchor 物理隔离防趋同。**所有路径用相对本 skill 根目录的形式，不依赖绝对路径**。
- 隐私：`personal-asset-index.json`(用户真实数据) 和 `.env`(API key) 都只进 `.example` 模板、`.gitignore` 排除真文件，"真实数据文件不要放在 skill 目录内避免随分发泄露隐私"。

---

## ③ 做 deck / 设计的方法（可直接搬的手法）

### 3.1 六条核心哲学（优先级从高到低）

1. **从 existing context 出发，不凭空画**——先问有没有 design system/UI kit/Figma/截图/品牌；凭空做 hi-fi 是 last resort，一定 generic。
2. **Junior Designer 模式**：不闷头做大招，HTML 开头先写 assumptions + reasoning + placeholders，尽早 show，再迭代。底层逻辑"理解错了早改比晚改便宜 100 倍"。
3. **给 variations 不给最终答案**：3+ 个变体跨不同维度，从 by-the-book 到 novel 逐级递进，让用户 mix and match。
4. **Placeholder > 烂实现**：没图标留灰块+标签别画烂 SVG，没数据写注释别编假数据。"一个诚实的 placeholder 比拙劣的真实尝试好 10 倍。"
5. **系统优先不填充**："Don't add filler. One thousand no's for every yes." 警惕 data slop / iconography slop / gradient slop。
6. **反 AI slop**（最硬，必读）——见 3.3。

### 3.2 ⭐ 品牌资产协议（skill 里最硬的一段，"稳定性的稳定性"=真护城河）

涉及具体品牌时强制 5 步：①问全资产清单 ②搜官方品牌页(`<brand>.com/brand`、`/press`) ③下载资产(SVG→官网HTML全文→产品截图取色，三条兜底前一条失败立刻下一条) ④grep 提取色值(从资产抓 `#xxxxxx` 按频率排序过滤黑白灰，**绝不从记忆猜品牌色**) ⑤固化为 `brand-spec.md` + CSS 变量。

- **核心理念"资产 > 规范"**：logo/产品图/UI 截图比品牌色值更重要（"除了品牌色，显然该用上 logo 和产品图，否则我们在表达什么呢"）。
- **铁律**：设计里只要出现一个能被认出的产品/品牌名，它的官方 logo 就是必需资产；对比/榜单/评测 deck 把多个产品并列时尤其常漏（"只抽了品牌色就开做"= 2026-06-06 五大 Coding Agent PPT 实测翻车）。这对我们做**竞品对比页 / 市场地图 deck** 是关键护栏。
- **A/B 实测**：v2(带资产协议) vs v1，各跑 6 agent，**v2 稳定性方差比 v1 低 5 倍**。作者结论："稳定性的稳定性，才是 skill 真正的护城河。" ← 这句对我们"fail-closed 质量门"是最强背书。

### 3.3 反 AI slop：带"为什么"的清单，不是审美洁癖

逻辑链很硬：用户请你做设计是要他的品牌被认出来 → AI 默认产出=训练语料平均=所有品牌混合=没有任何品牌被认出来 → 所以反 slop 是**替用户保护品牌识别度**。要规避（每条带"为什么"+"什么情况可破例"）：激进紫渐变 / emoji 当图标 / 圆角卡+左 border accent / SVG 画人脸 / **CSS 剪影代替真实产品图** / Inter 当 display / GitHub-dark 偷懒解(`#0D1117`+通用霓虹)。**唯一合法破例理由="品牌本身就这么用"**。还专门提醒"别把整片暗色大胆派一起误杀"——要禁的只是偷懒解，电影级光影/暖色赛博是有作者意图的暗色。演示反例时用"诚实的 bad-sample 容器"(虚线框+"反例·不要这样做"角标)隔离，别整页堆 slop。

### 3.4 ⭐ HTML-first 单一真相源 + 派生 PDF/PPTX（对我们"制作底座"最直接）

> 与开源生态调研的判断②呼应：质量基准=原生可编辑 PPTX。huashu-design 给出了 HTML→可编辑 PPTX 的完整工程路径。

- **HTML 聚合演示版永远是默认基础产物**，PDF/PPTX 是从 HTML 一行命令导出的衍生物。开工**绝不问**用户要 PDF/PPTX，直接做 HTML deck。
- **deck 架构二选一**：默认**多文件**(每页独立 HTML + `deck_index.html` 拼接器，iframe 天然隔离 CSS/可并行开发/单页双击可验)；仅 ≤5 页极简 pitch 才用单文件 `deck_stage.js`。附了单文件架构连踩四坑的真实事故（CSS 特异性覆盖 / shadow DOM slot / localStorage 竞态 / 验证成本高）。
- **可编辑 PPTX 走 `html2pptx.js`**：读 DOM computedStyle 逐元素翻译成 PowerPoint 对象(text frame/shape/picture)，**导出真文本框双击可编辑**。代价是 HTML 必须从第一行按 **4 条硬约束**写：①body 固定 960×540pt(匹配 LAYOUT_WIDE) ②所有文字包在 `<p>/<h1-6>`(禁裸 div 文字) ③文字标签自身不能有 background/border/shadow(放外层 div) ④div 不用 background-image(用 `<img>`)；外加不用 CSS 渐变/web component/复杂 SVG。
- **关键 doctrine（我们要照搬的取舍纪律）**：**绝不为了能转 PPTX 而牺牲 HTML 设计质量**。视觉自由优先就出 PDF；要可编辑 PPTX 就从头按 4 约束写。"实测视觉驱动 HTML 直接上 html2pptx，pass 率 <30%"——所以事后补救会触发 2-3 小时返工，必须开工前就和用户确认交付格式（这是比"单文件 vs 多文件"更先的 checkpoint）。
- **`data-pptx-merge="true"`** 把容器内多个 `<p>` 合并成一个可编辑文本框（否则 PPT 里多个文本框摞着，没法整段编辑）——做"同事会改文字"的交付件时是关键细节。

### 3.5 ⭐ 批量前先做 2 页 showcase 定 grammar（防返工 N 次）

> deck ≥ 5 页**绝不能从第 1 页直接写到最后一页**。先做 2 个视觉差异最大的页面类型(如"封面"+"引用/情绪页")→ 截图让用户确认 grammar(masthead/字体/色/间距/结构)→ 方向过了再批量推剩下 N-2 页。

"直接写 13 页到底→用户说方向不对 = 返工 13 次；先做 2 页 showcase→方向错 = 返工 2 次。" **这条对我们做长 deck 的策略→制作衔接极有价值，是"分阶段出关闸"在制作侧的具体落地。** 还给了出版物 grammar 模板(masthead/kicker/H1/英文副/footer 骨架 + 样式约定) + "视觉主角必须差异化"轮换表(封面排版/portrait/时间轴/图谱/before-after/big-quote…一页一类型)。

### 3.6 deck 设计规范零碎但实用

- 先口头 vocalize 设计系统(背景色≤2种/字型 display+body/节奏/图像策略)等用户点头再做。
- Scale：正文最小 24px(理想 28-36)、标题 60-120px、Hero 字 180-240px("幻灯片是给 10 米外看的")。
- 一个 deck 最多 4-5 种 layout；要 intentional variety(颜色/密度/字号节奏)，"不要每张 slide 长一样——那是 PPT 模板不是设计"。
- 信息密度：每页"1 个核心信息 + 3-4 辅助点 + 1 视觉主角"，超了拆新页。列表/矩阵页用主次分层(今天要聊的放大、其余缩小做背景 hint)，"改到留白让你有点不安为止"。
- "位置四问"(每页开工前必答)：叙事角色(hero/过渡/数据/引语/结尾) / 观众距离(10cm/1m/10m) / 视觉温度(安静/兴奋/权威/温柔) / 容量估算(纸笔画 3 个 thumbnail 算塞不塞得下)。"系统要服务于答案，不是先选系统再塞内容。"

---

## ④ 对 PPT Engine 的落点（可借鉴的 skill 形态与设计手法）

### A. 直接可搬的"skill 形态"机制
1. **References 路由表 + 渐进披露**：主 skill 放哲学/流程/铁律，把"高 stakes 图表画法""可编辑 PPTX 约束""咨询风格库"拆成按需读的 reference。我们引擎层八组件可对齐这个组织法。
2. **编号工作流 + 嵌入式 🛑 检查点 + "真的等"原则**：这是 fail-closed 在对话 skill 里的样板。我们策略工作流的"每步用户拍板"可直接用这套写法（说完就停、不自动往下）。
3. **frontmatter 触发词军火库**：把咨询/路演/高 stakes 图表触发词铺满 description。
4. **跨 runtime + 隐私护栏**：相对路径、`.example` 模板 + `.gitignore` 排真实数据，是交付级 skill 的卫生标准。

### B. 直接可搬的"设计/制作手法"
5. **⭐ 选择无效铁律 + 三套逻辑并行 subagent**：需求模糊时不让用户文字盲选，并行出 3 版真实视觉再选——**这是我们"策略层给方向"最该抄的交互**(详见 ⑤ 机制)。
6. **品牌资产协议 5 步 + "资产>规范" + grep 取色不靠记忆**：做品牌 deck / 竞品对比页的硬护栏；尤其"并列多个产品必须各取官方 logo"这条防对比页翻车。
7. **HTML-first 单一真相源 → 派生 PDF + 可编辑 PPTX(html2pptx 4 约束)**：我们"制作工作流"的底座工程路径可直接参考(注意：开源生态调研判断②说 HTML 底座导出 pptx 多是图片堆叠——huashu-design 的 html2pptx 是少数做"真文本框"的，但代价是 4 条硬约束 + pass率<30% 的视觉牺牲，**需评估它和 python-pptx 原生路线谁更适合咨询级图表**)。
8. **批量前 2 页 showcase 定 grammar**：长 deck 防返工，是制作侧的"出关闸"。
9. **反 AI slop 带"为什么"的清单**：可整段移植为我们的视觉下限护栏。
10. **5 维度评审 + Keep/Fix/Quick Wins**：现成的结构化质量门模板（见 ⑤）。

### C. 我们和它的根本差异（别照抄错地方）
- **它没有策略层**——brief 解读/判目的/市场调研/反复推敲是我们的护城河，huashu-design 完全空白。它的"设计方向顾问"只解决"没风格参考时给 3 个视觉方向"，**不等于"判断这个 deck 该说什么、给谁看、达成什么"**。
- **它收口在"通用高质量视觉"，我们收窄"高 stakes 咨询/投资人段"**(waterfall/Mekko/Gantt 这类它的风格库也只是"图谱箭头/Sparkline"层面提了叙事，没给这三种硬图表的画法)——这恰好是我们 05图表 层要啃的硬骨头，huashu-design 帮不上，是真差异化。
- **它的"防假绿"靠规则叙事 + 人工 checkpoint，没有机检质量门**——和我们铁律 §2"绝不让自动判定/LLM 打分当做好了的硬信号"方向一致(都强调人审)；但我们仪表盘/conformance 的"机检+人工自测双轨"比它更系统，可反哺它没有的部分。

---

## ⑤ 关键机制原文细节（供落地时查）

### ⭐ 选择无效铁律 + 三套逻辑并行（最值得偷的一件事，完整版）

**触发**：需求模糊("做个好看的""帮我设计""做个XX"没具体参考) / 用户主动要"推荐风格/给几个方向" / 项目无任何 design context。**Skip**：已给明确风格参考、已说清要什么、小修小补工具调用。

**7 Phase 流程**：①对话澄清需求 + **主动索要参考**(项目叫什么/有没有 logo品牌色VI/有没有喜欢的参考站；这步最容易跳过却最该问) ②顾问式重述(≥200字嚼透需求，以"我直接做 3 个方向给你看"结尾，**❌不以"你想选哪个方向"结尾**) ③固化 ≥500字详尽 design spec(三个 subagent 唯一共同输入，**必含输出格式与尺寸**否则三版无法横向对比) ③.5🔴**CHECKPOINT 图片素材前置**(先判断图片是不是内容必需→必需则先取齐真图再 spawn，三个 subagent 共用同一批真图只换设计) ④**三套逻辑并行 subagent** ⑤用户基于看到的真实视觉选 ⑥进主干 Junior 流程深化。

**三套互补逻辑(每个 subagent 独立 context、只看 spec、互不参考防趋同)**：
- **逻辑一·🎲 秒数轮盘**：跑 `date +%S` 取秒，`秒数 % 20 + 1` 从 `design-styles.md` 对应半区(网页20/PPT20)取那一号风格。作用=**用时间掷骰子强制打破模型"每次都偷选安全极简"的确定性偏好**。
- **逻辑二·🏆 现实参照**：选一个和用户需求最相关、且明确知道设计极出色(最好获奖 Awwwards/Apple Design Award)的真实网站/PPT 模板，先 WebSearch 核实存在再拆解配色/字体/布局迁移。
- **逻辑三·🧠 最佳设计师**：深呼吸想"假如预算无上限，世界上最适合为这个用户/产品做设计的工作室是谁"(Pentagram/Collins/IDEO/Jony Ive/原研哉/Stripe团队)，启用其设计哲学从头设计。

**为什么是铁律**(花叔 2026-06 实测确认)："绝不让用户在只有文字、没看到视觉时选风格——用户没依据。" **不支持 spawn 的 runtime 改串行，但也必须出三版，不许偷懒并成一版。** 产出自检：`design-demos/` 下真有 3 个 .html 才能往下。

> 对我们落点：**这套"不抛文字单选题、并行出真实候选、独立 context 防趋同"完全可移植到策略层**——比如"判断 deck 方向"时，不问用户"你要数据驱动还是叙事驱动"，而是并行出 2-3 个真实文字大纲 demo + 解读让用户选(正好对上开源生态调研里"文字 demo + 解读"的策略层构想)。

### 5 维度专家评审（现成质量门模板）

哲学一致性 / 视觉层级 / 细节执行(craft) / 功能性 / 创新性，各 0-10 分(每维给了 1-2/3-4/5-6/7-8/9-10 的判分标准 + 评审要点)。**按场景调权重**(PPT/Keynote→视觉层级+功能性最重，创新性可放宽"清晰优先"；PDF/白皮书→细节执行+功能性，"专业优先")。输出 = 总评 + Keep + Fix(分 ⚠️致命/⚡重要/💡优化) + Quick Wins(只有 5 分钟先做哪 3 件)。还附「常见设计问题 Top 10」(AI科技cliché/字号层级<2.5倍/颜色>5种/间距不统一/留白<40%/字体>3种/对齐不一致/装饰大于内容/赛博霓虹滥用/信息密度与载体不匹配)，每条带"为什么是问题"+"修复含数值"。**评审设计不评设计师。** ← 这套可直接做我们 deck 质量门的人审 rubric。

---

## license + 坑

- **License = MIT**(2026-05-14 从"个人免费/商用需授权"改为 MIT)。可自由使用/修改/分发/**商用**(公司内用、客户商单、做成付费产品对外卖都行)，无需事先授权/付费/打招呼，注明出处不强制但欢迎。**借鉴其方法论/手法零法律风险。**
- **依赖**：`playwright`(截图/PDF/录视频，重) + `pptxgenjs`(出 PPTX) + `pdf-lib`(合并 PDF) + `sharp`(缩略图)。可编辑 PPTX/PDF 导出强依赖本机 Playwright Chromium。TTS 走豆包(火山引擎)，需 `.env` 配 key(国内服务)。
- **坑/限制**：
  - **可编辑 PPTX 是 best-effort 衍生物**：4 条硬约束 + 字体回落(Playwright 用 webfont 测量、PowerPoint 用本机字体渲染，不同会溢出/错位，每页要肉眼过) + 视觉驱动 HTML pass率<30%。**对我们=别指望 html2pptx 兼得视觉保真和可编辑，咨询级精确图表可能仍需 python-pptx 原生路线**(开源生态调研判断②)。
  - **不支持图层级可编辑到 Figma/Keynote**(不能拖进 Keynote 改文字位置)；复杂动画(3D/物理/粒子)超边界；空白品牌从零做掉到 60-65 分。
  - **Chromium 默认不渲染彩色 emoji**(`page.pdf/screenshot` 时 emoji 显空方框)→ 用 Unicode 文字符号替代。
  - **ESM 脚本依赖解析坑**：scripts 放 skill 目录会报 `Cannot find package 'playwright'`，需复制到 deck 项目目录跑 `npm install`。
  - **中文 webfont 加载竞态**：Playwright 截图/PDF 前需 `wait-for-timeout≥3500` 否则中文显示系统默认黑体。
  - **它的"研究层"很薄**：风格库是"调研 100 个真实案例反推"，但没给可编辑 PPTX 的咨询级硬图表(waterfall/Mekko/Gantt)实现——这块它帮不上，正是我们的活。

---

## 附：和我们工作流的对应速查

| huashu-design 机制 | 我们的对应 | 借鉴动作 |
|---|---|---|
| References 路由表 + 渐进披露 | 八组件×五层 | 主 skill 瘦身，重知识拆 reference 按需读 |
| 编号工作流 + 🛑检查点 + "真的等" | 纪律分阶段 fail-closed | 策略层每步拍板直接用这套"说完就停"写法 |
| 选择无效铁律 + 三套逻辑并行 | 策略层"文字 demo + 解读" | 移植为"并行出 2-3 个真实大纲候选让用户选" |
| 品牌资产协议 5 步(资产>规范) | 制作工作流·素材层 | 竞品对比页"并列产品各取官方 logo"护栏 |
| HTML-first → html2pptx 可编辑 PPTX | 制作底座(原生 PPTX) | 评估 vs python-pptx；咨询级硬图表可能走原生 |
| 2 页 showcase 定 grammar | 分阶段出关闸(制作侧) | 长 deck 先定视觉语法再批量推 |
| 5 维度评审 + Keep/Fix/Quick Wins | 防假绿·人审 rubric | 直接做 deck 质量门人审清单 |
| 事实验证先于假设(WebSearch) | 保真度铁律 | 策略层市场调研同款"禁凭记忆断言" |
