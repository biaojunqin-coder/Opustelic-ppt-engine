# 开源拆解 · guizang-ppt-skill（歸藏 PPT Skill）

> 日期：2026-06-30 · 方法：亲读 `ls -R` 全树 + README(中文) + SKILL.md + checklist.md + 校验脚本 + swiss-layout-lock.md + components.md + layouts.md + image-prompts.md（中文为主，保真带行号出处）。
> 源仓库：https://github.com/op7418/guizang-ppt-skill （~18k★ · 作者 [歸藏 op7418]）· 本地：`/Users/qinbiaojuan/Documents/PPT开源参考/01b_待深看skill/guizang-ppt-skill`
> 一句话结论：**它把"Claude skill 怎么做 deck"工程化到了极致——但走的是 HTML 网页 PPT + 偏设计/分享场景，和我们"原生可编辑 PPTX + 咨询级高 stakes"是两条路。最值得偷的不是它的产物，是它的「纪律工程」：约束换稳定 + 可 grep 自检 + 纯静态校验门（零 LLM 打分）。**

---

## 0. 三个最重要的判断（先看这个）

1. **形态高度同构、赛道完全不同 → 是「方法论镜子」不是「竞品」**。同样是 Claude Code skill、同样 SKILL.md 驱动、同样"分步 + 自检"，但它做的是 **单文件 HTML 横向翻页 deck**（演讲/分享/发布会/封面），明确写"❌ 不适合大段表格数据、需要协作编辑"（README:88）。我们做 **原生可编辑 PPTX + 咨询级（waterfall/Mekko/Gantt）**。所以它对我们的价值在「skill 怎么组织 + prompt 工程 + 质量门」，不在产物或图表能力。

2. **它的护城河逻辑和我们一字不差：「约束换稳定」**。CONTRIBUTING 原话：*"This Skill is opinionated by design. It prefers constrained layout systems over unlimited customization, because constraints make AI-generated decks more reliable."*（约束让 AI 生成的 deck 更可靠）。具体落地成两条硬规矩：**不允许自定义颜色**（只能从 5/4 套预设里选，README:265「保护美学比给自由更重要」）、**不允许自创版式**（Swiss 模式只能从 22 个登记版式 S01–S22 里选，发明 P23/P24 直接被校验拦死）。这正是铁律4「收窄高 stakes 段」的同款思路——**收窄自由度，是质量的来源，不是缺陷。**

3. **质量门是「纯静态正则校验 + 可 grep 自检清单」，零 LLM 打分** → 直接印证我们的防假绿铁律。它的 `validate-swiss-deck.mjs` 是一个 110 行的纯文本正则检查器，`process.exit(1)` 真 fail-closed；checklist.md 每条坑都配一行 `grep`/`rg` 自检命令。**全程没有"让模型给自己打分说做好了"这种假绿信号**——和铁律2（不让自动判定/LLM 打分当"做好了"的硬信号）完全一致。这是最值得我们抄的工程范式。

---

## 1. 是什么 + 定位

- **产物**：单文件 `index.html` 横向翻页网页 PPT（键盘 ←→ / 滚轮 / 触屏 / 底部圆点 / ESC 索引 / `B` 键切静态低功耗）。浏览器直接打开，无需构建、无需服务器。
- **两套视觉系统**（核心卖点）：
  - **Style A 电子杂志 × 电子墨水**：衬线标题（Noto Serif SC + Playfair）+ WebGL 流体背景，暖色，"像 Monocle 杂志贴上了代码"。叙事/观点/人文/分享。
  - **Style B 瑞士国际主义（Swiss）**：全程无衬线（Inter/Helvetica/Noto Sans SC）+ 网格点阵 + 单一高饱和锚点色（克莱因蓝 IKB / 柠檬黄 / 柠檬绿 / 安全橙四选一）+ 极致字号对比。事实/产品/数据/方法论。锚点：Vignelli + Helvetica Forever + Müller-Brockmann 网格系统。
- **附带能力**：Codex 环境下用 GPT-Image/GPT-M 生成配图（纪实照片/信息图/流程图/UI 情景图）；多平台封面（公众号 21:9、1:1 分享卡、小红书 3:4、视频号 16:9）；截图美化（CleanShot X 式背景画布适配）。
- **平台**：Claude Code（原生 skill）/ Codex（含配图）/ Cursor 等本地 agent。明确写「普通 Chatbot 不推荐」——因为没有文件系统和浏览器预览，没法稳定产出。
- **支持方**：360 安全龙虾（金牌赞助）+ 真格 Token Grant。

---

## 2. ⭐ 作为 Claude skill 怎么组织（对我们最有用）

### 2.1 文件结构 = SKILL.md 主控 + references 分文件 + assets 模板种子 + scripts 校验
```
SKILL.md                  ← 主控：工作流 6 步 + 原则 + 常见错误（541 行，frontmatter 含 name/description/触发词）
assets/
  template.html           ← Style A 种子文件（完整可运行：CSS+WebGL shader+翻页JS+CDN 全预设，只留 <!-- SLIDES_HERE --> 占位）
  template-swiss.html     ← Style B 种子文件
  motion.min.js           ← Motion One 本地副本（离线兜底 64KB）
  screenshot-backgrounds/ ← 截图美化内置背景 WebP（A 5 套 / B 4 套）
scripts/
  validate-swiss-deck.mjs ← Swiss 静态校验器（真 fail-closed）
references/               ← 「按需加载」的知识分文件，SKILL.md 里明确给了加载顺序
  components.md / layouts.md（A 10 版式）/ layouts-swiss.md（B 22 版式）/
  swiss-layout-lock.md（版式锁硬约束）/ swiss-map-component.md /
  themes.md（A 5 主题）/ themes-swiss.md（B 4 主题）/
  image-prompts.md / screenshot-framing.md / checklist.md（P0–P3 质检）
```
**借鉴点**：和 Anthropic 官方 skill 的「SKILL.md 瘦主控 + references/ 渐进披露」范式一模一样。SKILL.md 末尾「加载顺序建议」8 条（先读哪个、动手前必读哪个、生成后跑哪个）= 一份显式的 **上下文预算管理脚本**，避免一次性灌爆 context。我们的 skill 也该这么排。

### 2.2 frontmatter description = 触发词工程
SKILL.md:3 的 description 把「做什么 + 两种风格各自特征 + 触发关键词」全塞进一句（"杂志风 PPT"/"瑞士风 PPT"/"Swiss Style"/"horizontal swipe deck"）。这是 skill 被正确唤起的关键——**描述里要带用户会说的原话**。

### 2.3 工作流 = 6 步，且「需求澄清」是动手前的强制闸
- **Step 1 需求澄清（动手前必做）**：给了 **7 问清单**（①A/B 风格 ②受众/场景 ③时长→页数映射 15min≈10页/30min≈20页 ④原始素材 ⑤图片截图处理 ⑥主题色 ⑦硬约束）。明确写「**一旦结构定错，后期翻修代价很高**」「不要基于猜测就开始写 slide」。**这就是我们「策略工作流第一关」的同款 fail-closed 闸——先对齐再动手。** 还区分运行环境：Claude Code 用 `ask_question` 逐项问，Codex 用普通对话一次最多问 1–3 个。
- **Step 2 拷贝模板** + 必改占位符（拷完立刻 grep `[必填]` 确认 title 换掉）。
- **Step 3 填充内容**，含三个子闸：
  - **3.0 类名预检（最重要）**：写任何 slide 前先 Read 模板的 `<style>` 块，确认要用的每个 class 都已定义——"**这是所有生成问题的源头**"，缺类会 fallback 成默认样式（大标题字体错/卡片挤成团/图片堆底）。**根因防御思路：把"最常出错的根因"提前到动手前拦掉。**
  - **3.0.5 主题节奏规划**：动手前先列每页主题（hero dark/hero light/light/dark）写进草稿。硬规则：连续≥3 页同主题不允许；8 页以上必须 ≥1 hero dark + ≥1 hero light。
  - **3.1 挑布局**：不要从零写，从 layouts 里粘现成骨架改文案。
- **Step 4 对照 checklist 自检**（见 §3.3）。
- **Step 5 浏览器预览** / **Step 6 迭代**（90% 调整是改 inline `font-size`/`height`/`gap`）。

---

## 3. ⭐ 质量门怎么做（防假绿的现成范式）

### 3.1 纯静态校验器 `validate-swiss-deck.mjs`（零 LLM，真 fail-closed）
110 行 Node 脚本，正则扫 HTML，命中即 `errors.push`，有 error 就 `process.exit(1)`。拦截 9 类：
1. `<section class="slide">` 缺 `data-layout` → 未登记版式
2. `data-layout` 不在白名单（S01–S22 + SWISS-COVER-ASCII/SWISS-CLOSING-ASCII）
3. 用了实验结构 P23/P24 / Swiss Image Split / Evidence Grid（除非 `--allow-experimental`）
4. 顶部标题区 `text-align:center`（Swiss 正文标题必须左对齐；statement 版式 S03/S09/S10 例外）
5. SVG 里出现 `<text>`（可见文字必须走 HTML，SVG 只画几何）
6. 本地 `<img src="images/">` 缺 `data-image-slot`（每张图必须绑版式槽位）
7. S15/S16 重生成图用了 `fit-contain` 或没用 `.r-21x9` 或写了固定 vh 高度
8. S22 缺 `data-image-slot="s22-hero-21x9"`
9. S22 照片用 `object-position:top center`（会裁脸）

> **对我们的直接落点**：这就是「机检质量门」的最小可行实现——**纯文本规则、可独立运行、退出码真 fail**，不依赖任何模型判断。我们的 `deck_rules` 硬门（原生可编辑 PPTX？三图表存在？一页一论点？）完全可以照这个模式写成 Python 静态校验器，作为 fail-closed 的硬信号源，绝不让 LLM 自评当绿灯。

### 3.2 Golden Source 还原度守卫
checklist 0-E：原始参考 PPT 文件被定为 "golden source"，生成页要对照它的实际字重/间距/密度，"越迭代越偏离参考"被当成 bug。配套 `compare-swiss-base.mjs` 校验 `missing in template: 0`。**思路**：用一份"标准答案产物"当回归基准，防漂移——对应我们可以拿真实咨询 deck 当 golden 样本。

### 3.3 checklist.md = 分级 + 四段式 + 可 grep 自检（最值得抄的清单结构）
- **分级 P0/P1/P2/P3**：P0「一定不能犯」（emoji 当图标、图片撑破、标题 1 字 1 行、字体分工错、Swiss 版式违规…）必须全过；往下递减。**= 我们铁律分级 + 准入项的同构物。**
- **每条坑四段式**：`现象 → 根因 → 做法 → 自检命令`。例：
  - 0-S-4 字号下限：自检 `rg -n "font-size:(10px|11px|12px|13px)" index.html`
  - 0-A 画布对齐：自检 `grep "padding:.*5vw" index.html`
  - 0-B-2 封面色彩闭环：自检 `grep -c "ascii-bg" index.html` 应 ≥2
  - 动效覆盖：`grep -c 'data-anim' index.html` 应 ≥ 页数×3
- **来源是真实迭代**：开篇写「这个清单来自"一人公司"分享 PPT 的真实迭代过程，每一条都是踩过坑之后总结的」。**= 我们「开发实录沉淀方法论」的同款机制**——坑→清单条目，可执行、可验证。
- **末尾总自检清单**：分「预检/内容/排版/视觉/交互/动效」六组 checkbox，"全勾完才是合格的 PPT"。

### 3.4 视觉 + 代码双核对（checklist 0-F）
明确写「代码只能证明类名和结构存在，不能证明版式舒服」→ 生成后必须打开浏览器逐页看（等动效稳定 1–2 秒再判断），再回代码核版式选型。**对应我们：机检过 ≠ 人验过，🟢 必须人工自测。**

---

## 4. 它做 deck 的方法（底座 / 叙事 / 设计）

- **底座**：HTML/CSS 单文件 + WebGL shader 背景 + Motion One 动效。理由（README:101）：HTML 是文本，**agent 能直接读/改/验证**；表现力比 Markdown 高；交付轻（单文件）；**容易做质量控制**（可脚本校验）。
  - ⚠️ 这恰好印证我们的反向选择：HTML 路线导出 PPTX 是图片不可编辑（我们已定 python-pptx 原生路）。它的 FAQ 也承认「当前核心交付是 HTML，需要 PPTX 建议把 HTML 当视觉稿再转」——**它主动放弃了 PPTX，正是我们的差异化空间。**
- **叙事**：没大纲时给「叙事弧」模板搭骨架——**钩子 Hook(1页) → 定调 Context(1–2) → 主体 Core(3–5) → 转折 Shift(1) → 收束 Takeaway(1–2)**。要求"叙事弧 + 页数规划 + 主题节奏表"三张表对齐后才动手。
- **设计（量化成可执行规则，不是感性形容）**：
  - **字号越大越细**（Swiss 灵魂）：≥8vw→weight 200，13–15px→weight 500–600，且"同页字号小的字重必须 ≥ 字号大的"。16px 小字禁用 weight 300。
  - **大字双约束限高** `font-size:min(Xvw, Yvh)` 且 **Y ≥ X×1.6**（因 1vw:1vh≈1.78，只用 vw 在 16:9 屏会溢出）——给了推荐数值速查表。
  - **中文大标题分档降字号**（中文方块字视觉面积大，不能直接套英文 hero 的 6.8vw）：按字数行数四档。
  - 单一 accent 色 / 直角纯色（禁渐变阴影圆角，hairline 除外）/ 网格至上 / Lucide 图标禁 emoji / 图片只裁底部不裁顶左右、网格图用固定 `height:Nvh` 不用 `aspect-ratio`（会撑破）。
- **图片纪律**：配图是"嵌入素材不是独立 slide"——禁止图片自带页眉/页脚/标题/页码/角标/边框；先定版式槽位再生成图片（绑 `data-image-slot`）；同组图统一比例高度；图片语言跟随 deck 语言。

---

## 5. ⭐ 对 PPT Engine 的落点（可直接抄的）

| 它的做法 | 我们怎么用 |
|---|---|
| **纯静态正则校验器 + `exit(1)` 真 fail** | 把 `deck_rules` 硬门写成 Python 静态校验脚本（原生 PPTX？三图表？action title？一页一论点？），作为 fail-closed 硬信号源，**绝不让 LLM 自评当绿灯**（铁律2/防假绿）。这是本次最大可抄项。 |
| **checklist 四段式：现象→根因→做法→grep 自检** | 我们的质检清单每条都配一行可执行自检命令，让"自检"从口号变成可跑的东西；坑来自开发实录沉淀。 |
| **「约束换稳定」：禁自定义颜色/版式** | 印证铁律4 收窄思路。我们也该有「不许偏离的硬基线」——配色规范、版式白名单、图表类型白名单，宁可少给自由。 |
| **Step 1 七问澄清 = 动手前强制闸** | 策略工作流第一关：解读 brief 前先对齐目的/受众/约束，对不齐不开工（fail-closed）。它的「时长→页数映射表」也可借。 |
| **3.0 类名预检 = 根因前置防御** | 把"最常出错的根因"提到动手前拦掉（我们对应：动手前先校验 brief 解析、模板/母版是否就位）。 |
| **SKILL.md 瘦主控 + references 按需加载 + 显式加载顺序** | 我们 skill 同样分文件、给 Claude 明确的"先读哪个/动手前必读/生成后跑哪个"，做上下文预算管理。 |
| **frontmatter description 带用户原话触发词** | 我们 skill 的 description 要写进用户会说的话（"投资人 deck"/"咨询级 PPT"/"waterfall"…）。 |
| **Golden Source 回归基准** | 拿真实咨询/投资 deck 当 golden 样本，做还原度/防漂移基准。 |
| **设计规则量化**（字号公式 min(Xvw,Yvh) Y≥X×1.6、字重阶梯、中文降档） | 制作工作流的版式规则也要量化成可校验数值，而非"看起来舒服"。 |

**不抄/不适用**：HTML 底座（我们走 python-pptx 原生）；WebGL/动效/封面/截图美化（偏分享场景，非高 stakes）；它的图表能力很弱（无 waterfall/Mekko/Gantt，正是我们护城河）。

---

## 6. License + 坑

- **License：AGPL-3.0**（强 copyleft + 网络条款）。⚠️ **直接复制它的代码/模板/references 文本进我们仓库 = 触发 AGPL 传染**，要谨慎。但「借鉴方法论/工作流思想/质量门范式」不受 license 约束——**我们偷的是「怎么组织 skill + 怎么做质量门」的思路，不抄它的 HTML/CSS/校验脚本源码**，安全。（与现有调研笔记一致：AGPL 项目谨慎、优先 MIT/Apache/ISC。）
- **真实的坑①——硬编码作者本机绝对路径**：5 处文件把 golden source 写死成 `/Users/guohao/Documents/op7418的仓库/项目/Thin-Harness-Fat-Skills/ppt/index.html`（SKILL.md:398、checklist.md:218、layouts-swiss.md:13/206、swiss-layout-lock.md:9）。**别人装上根本不存在这个文件**，Swiss 还原度守卫对外部用户实际失效。→ 教训：**skill 里引用的路径必须用 `<SKILL_ROOT>` 占位或相对路径，绝不写死开发机绝对路径**（它在别处用了 `<SKILL_ROOT>`，但 golden source 漏了）。我们 scaffold/校验脚本要全用相对路径。
- **坑②——两套风格 class 同名不同义**：Style A 的 `.h-hero` 是衬线、Style B 的 `.h-hero` 是无衬线，同名视觉完全不同，混用即崩。SKILL.md 反复强调"一份 deck 只能选一套，不能混"。→ 教训：**多套模板共存时，命名/隔离要做干净**，否则给 agent 埋雷。
- **坑③——校验是正则不是 DOM**：`validate-swiss-deck.mjs` 用正则切 `<section>`，遇到嵌套/不规范 HTML 可能漏判或误判（它已先 strip 注释规避一部分）。→ 教训：静态校验器要意识到正则的边界，高保真校验最终可能要上真 DOM 解析。

---

## 7. 一句话最值得偷的事

**把质量门做成「纯静态正则校验器（exit 1 真 fail）+ 每条坑配一行 grep 自检命令的分级清单」——零 LLM 打分、可独立跑、退出码即硬信号，这正是我们防假绿铁律最需要的现成工程范式。**
