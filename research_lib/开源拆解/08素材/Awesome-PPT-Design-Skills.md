# 开源拆解 · Awesome-PPT-Design-Skills（software-ai-life · 繁中友好 · 资源地图归在「08 素材库 / 聚合表」）

> 日期：2026-06-30 · 方法（轻拆·保真带出处）：`ls -R` 全树 + 读 README.md（繁中，已含完整 Style Gallery / Repository Structure / PPT Master Workflow 章节）+ 完整精读 `futuristic-tech-editorial` 一支 skill 的全部 5 个文件（SKILL.md / style-system / slide-patterns / ppt-master-integration / qa-checklist + agents/openai.yaml + 封面 SVG 头部）+ 批量 grep 其余 5 支 skill 的页型清单与字数 + 查 git remote/log/LICENSE。代码即真相，不靠 README 宣称掺料。
> 仓库本地路径：`/Users/qinbiaojuan/Documents/PPT开源参考/08_素材库/Awesome-PPT-Design-Skills` · 上游：[github.com/software-ai-life/Awesome-PPT-Design-Skills](https://github.com/software-ai-life/Awesome-PPT-Design-Skills) · 最近 commit 2026-04-28（README 微调）。
> **一句话最值得偷的**：它把「一种美学风格」做成一支**自包含 skill 包**——`SKILL.md`(触发+硬约束) + `references/{style-system, slide-patterns, ppt-master-integration, qa-checklist}.md` 四件套，**6 支 skill 严格同构、只换风格内容**；这套「风格层 = 可插拔 skill 包、骨架固定」的封装范式，正是我们做制作工作流「换皮不换骨」最干净的目录级模板。**但它全是消费向编辑设计风（日系/黏土/手绘/精品），零咨询级图表（无 waterfall/Mekko/Gantt），且它的核心依赖 `ppt-master` 我们 40 项目里早已收录——所以本表对我们几乎无「新资源」增量，价值在「skill 封装结构」这一个范式点。**

---

## 0. 最重要的判断（先说结论）

1. **它不是「awesome 资源清单/链接聚合表」，是一个含 6 支实体 skill 的代码仓库**。名字里的 "Awesome" 有误导——它不索引外部项目，而是自带 6 套**风格化 PPT design skill**（每套是一整个目录的 markdown 规范 + 一张封面 SVG + 一个 template.html）。资源地图把它归在「08 素材库」是按「范本/风格素材」定位，准确。
2. **它对我们的「新资源增量」基本为 0**。它唯一的外部依赖是 `ppt-master`（README 第 7、135 行反复指向），而 **`ppt-master` 我们早已收录在 `01_AI端到端应用/ppt-master`**（40 项目索引原话：「34.3k star · 灵感源 · 原生可编辑 PPTX · SVG→DrawingML · 跑在 agent 里（同我们形态）」）。除此之外它不聚合任何我们 40 项目之外的新资源/新 skill。→ **不存在「遗漏的好资源该补纳」。**
3. **真正可偷的是「skill 封装结构」，不是内容**。6 支 skill 共用同一套五文件骨架（见 §2），证明「美学风格」可被抽成**目录级可插拔单元**——这对我们制作工作流的风格层组织有直接借鉴（§3.1）。
4. **零咨询级范本**。6 支风格全是消费/品牌/编辑向（日系生活杂志、黏土 3D、手绘、精品 branding、现代插画、未来科技杂志），页型里**没有任何** waterfall / Mekko / Gantt / 竞品矩阵这类高 stakes 咨询图。→ 对我们「收窄高 stakes 段」**无直接范本可用**，只可借结构与 QA 门思路。
5. **无 LICENSE 文件**（根目录无 LICENSE/COPYING）——若要复用其规范文本须先确权（§5 坑1）。

---

## 1. 是什么 + 定位 + license

- **一句话**：一组 **agent-agnostic 的风格化 PPT design skill**（繁体中文友好），让支持本地 skills 的 coding agent（README 列：Codex / Claude Code / Cursor / OpenCode / OpenClaw / Hermes）用一句 prompt 按指定美学产出高质感 deck，**搭配外部 `ppt-master` 流程把 SVG 页面转成可编辑 .pptx**。
- **形态**：纯 markdown + 静态资产仓库，**没有可执行代码、没有引擎**。每支 skill = 一个目录：`SKILL.md` + `agents/openai.yaml`（给 OpenAI 风格 agent 的等价指令）+ `assets/{template.html, examples/01_cover.svg}` + `references/` 四件套。它**本身不生成 PPT**，只是「风格层规范」，真正产物由调用它的 agent + ppt-master 产。
- **定位**：风格/范本素材包。**不是模板**——README §Limits 明说「这些 skills 是风格与流程规范，不是固定模板」。
- **license**：⚠️ **仓库根目录无 LICENSE 文件**（已 `ls` 确认）。上游 org `software-ai-life`。复用前须确权。
- **活跃度**：最近 commit 2026-04-28（README 微调），非高频维护。
- **和我们关系**：①产物链路（SVG→可编辑 PPTX via ppt-master）**与我们同形态、同灵感源**；②但风格全消费向、**无咨询图**；③核心增量是「skill 目录封装范式」一个点，不是资源。

---

## 2. ⭐ 它聚合了哪些（分类 · 有没有 40 项目之外的新资源值得补）

### 2.A 6 支 skill 一览（这就是它「聚合」的全部内容——都是自带风格，非外链）

| Skill 目录 | 风格 | 必用色板（节选） | 适用场景（README 原话） |
| --- | --- | --- | --- |
| `japanese-style-ppt-skill` | 日系编辑（**含 2 套 house style**：Washi Paper & Soft Glow / Japanese Lifestyle Editorial） | 和纸米白 / 纯白 + 焦橙 #?? + 深炭灰 | 品牌故事、商务提案、产品叙事、杂志感专业简报 |
| `soft-3d-clay-ppt-skill` | 柔和 3D / 黏土感 | 暖米 `#FDF5E6` + 鼠尾草绿 `#B2AC88` + 莫兰迪粉 `#DBADAD` | 轻盈科技、友善产品说明、活泼但专业 |
| `futuristic-tech-editorial-ppt-skill` | 未来科技杂志 | 纯白 `#FFFFFF` + 电光蓝 `#2F6BFF` + 石墨灰 `#2B2B2B` | AI / 平台 / 工程 / 技术策略 / 数据导向商务（**最贴我们科技 deck**） |
| `minimalist-luxury-branding-ppt-skill` | 高端品牌提案 | 暖米 `#F5EFE6` + 柔棕 `#A68A64` + 深灰 `#3A3A3A` | 高端品牌提案、公司简介、创办人简报 |
| `modern-illustration-editorial-ppt-skill` | 现代插画编辑 | 柔米 `#F7F3EE` + 雾蓝 `#A7C7E7` + 灰橘 `#E8A87C` | 产品故事、策略解释、工作流程、概念插画 |
| `japanese-hand-drawn-editorial-ppt-skill` | 日系手绘 | 暖白 `#F8F6F2` + 墨黑 `#2B2B2B` + 低彩靛蓝 `#6C7A89` | 人文品牌、生活风格、创意流程、安静细腻概念 |

### 2.B 每支 skill 的内部骨架（亲读 futuristic 一支全文 + grep 其余 5 支验证同构）

5 个文件，职责分层非常清晰（**与我们方法论「分层规范」高度同构**）：

```
SKILL.md                              触发条件(description 含大量风格关键词供 agent 匹配) + Style Intent + Non-Negotiables(硬禁项) + Workflow
references/style-system.md            色板/字号(精确到 px 与字重)/12 列网格/几何/图表/图标 的精确数字规范
references/slide-patterns.md          7~10 个可复用页型(每个 = 用途 + 3~5 条排版约束)
references/ppt-master-integration.md  Deck Defaults + 「SVG Spec Lock」(viewBox/真文字非栅格/明确 fill·stroke/禁 filter·blur·渐变·外链图) + 文字密度 + Forbidden Treatments
references/qa-checklist.md            交付前自检(Style Fit / Layout / Typography / Content / PPT Production 五组勾选项)
agents/openai.yaml                    给 OpenAI 风格 agent 的等价 instructions(name/version/description/instructions)
assets/{template.html, examples/01_cover.svg}   HTML 预览参考 + 一张矢量封面示意(实测真 <rect>/<path>/<text> 原语)
```

各 skill 字数：japanese-style 最厚 3291 词（双 house style），其余 5 支 1471~1978 词，**厚度一致 = 标准模板化产出**。

### 2.C 7 个页型骨架（以 futuristic 为例，其余 5 支命名随风格变但骨架同构）

futuristic 的 7 页型：`Editorial Tech Cover → Asymmetric Thesis → Data Signal → System Map → Editorial Comparison → Timeline Rail → Closing Signal`。
对照其余：所有 skill 都是 **Cover → Thesis/Statement → 若干结构页 → Comparison → Closing** 的同一叙事弧，只换风格皮（clay 的结构页叫 "Floating Concept Object"，日系叫 "Paper Bento"，luxury 叫 "Brand Pillars"）。→ **证明「页型骨架可固定、风格可换皮」。**

### 2.D 有无 40 项目之外的新资源？

- **唯一外部依赖 `ppt-master` → 已收录**（`01_AI端到端应用/ppt-master`，已 grep 确认本机存在该目录 + 40 索引已列）。
- 无其它外链项目、无外部 skill 索引、无外部范本库。
- → **结论：本表对「补新资源」无增量。**

---

## 3. 对 PPT Engine 落点（有无遗漏好资源该纳 · 有无咨询级范本）

### 3.1 ⭐ 最值得跟进：「风格层 = 可插拔 skill 目录包」的封装范式（结构借鉴，非内容）

6 支 skill 同构异风，给出一个干净的目录级模板：把每种「视觉风格」封成 `SKILL.md(触发+硬禁) + style-system(精确数字) + slide-patterns(页型) + ppt-master-integration(SVG spec-lock) + qa-checklist(交付门)` 的自包含包。这正契合我们硬纪律「PPT 收窄高 stakes 段」下做**多套咨询风格皮**时的组织方式——骨架（waterfall/Mekko 的页型与数据校验）固定在引擎层，风格（McKinsey 蓝 / Bain 红 / BCG 绿）做成可换的 skill 包。**可偷其目录分层与「Non-Negotiables + qa-checklist 一对」的 fail 思路，不可偷其消费向内容。**

### 3.2 与我们方法论的同构点（可互相印证，强化既有「强候选」）

- 它的 `qa-checklist.md`「PPT Production」组明确写 "Text remains editable where the workflow supports it"、"SVG viewBox is 1280×720"、"No filters/blur/shadows"——这与我们方法论里「产物须可编辑、矢量优先」的方向一致，可作**第三方佐证**（但仍属「方法论编码非真实 deck」级别，不足以升格铁律）。
- 它的「一页一个清楚讯息 / 留白要有意图 / 色彩是系统不是装饰 / 产 PPT 前先过 QA」(README Design Principles) 与我们已落的 00/01/03 强候选**重合度高**——印证这些是行业共识，但**仍非高 stakes 真实 deck 实证**。

### 3.3 与 `ppt-master` 的关系（提示去那支主拆里挖真链路）

本表反复指向 `ppt-master` 做 SVG→可编辑 PPTX。**真正的技术增量在 ppt-master 主拆里**（SVG→DrawingML 怎么转、可编辑性怎么保），本表只是它的「风格层适配示例」。→ 行动项：深拆 ppt-master 时重点验证「SVG 真文字 → PPTX 文本框」是否如宣称可编辑（这是我们和 pptmaker「死图」路线的关键分水岭）。

### 3.4 有无咨询级范本？

**无。** 6 支风格 0 咨询图、0 高 stakes 页型。对「升格铁律的唯一路径 = 拆真实高 stakes deck」**无贡献**。

---

## 4. 一句话定性

「**一个把视觉风格封装成可插拔 skill 目录包的优秀范式样本**，但内容全是消费向编辑设计、核心依赖 ppt-master 我们已有——对我们是『**结构可借、资源无增量、范本不可用**』。」

---

## 5. 坑

1. **无 LICENSE**（根目录已确认无 LICENSE/COPYING 文件）：要复用其规范文本/封面 SVG 须先向上游 `software-ai-life` 确权，别直接搬。
2. **名字误导**："Awesome-…" 让人以为是资源聚合清单，实为 6 支自带 skill 的代码仓；**它不索引任何外部项目**，别指望从里面捞到新资源链接。
3. **两个不同 org 易混**：本仓上游 = `software-ai-life/Awesome-PPT-Design-Skills`；它依赖的 ppt-master = README 内部链到 `hugohe3/ppt-master`（与 40 项目里收录的 ppt-master 同名，需核对是否同一上游再引用）。
4. **它不产 PPT**：纯风格规范，离开 `ppt-master` + 一个支持 skills 的 agent 就是一堆 markdown，**不能单独跑出 deck**——评估其「能不能产可编辑 PPTX」必须连带评估 ppt-master，不能只看本表。
5. **全消费向、无数据校验**：页型只管排版美学，**无任何「数字对不对/逻辑通不通」的内容质检**（qa-checklist 的 Content 组只查「标签简洁/无填充文本」，不校验数据真伪）——与我们 fail-closed 质量门要求的方向相反，**不可把它的 QA 当内容正确性门**。
