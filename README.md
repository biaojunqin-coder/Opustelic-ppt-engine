# PPT Engine

[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

中文 | [English](README_EN.md)

> **AI 不是帮你填模板，是帮你把 deck 想清楚。** PPT Engine 把"AI 一次成稿"拆成三段可控流程——**策略先想清楚 → 逐页硬门验收 → 原生可编辑导出**——专攻 waterfall / Mekko / Gantt 这类结构化图表、数字必须溯源、绝不栅格化的**咨询级 / 投资人级**高 stakes deck。

## 你是不是也遇到过

- 找 AI 生成 PPT，出来是一张张栅格图，打开 PowerPoint 改不动一个字，也挪不动一个框；
- 让 AI 自己"编"数据，汇报时被问一句"这个数字哪来的"，答不上来；
- 瀑布图 / 甘特图 / 波士顿矩阵这类结构化图，AI 画出来的条形对不齐、占比加起来不是 100%，细看就穿帮；
- 一次性甩出 40 页，通篇是 AI 自己的叙事逻辑，不是你想讲的那个故事，改起来比重写还累。

PPT Engine 就是奔着这几件事去的——原生可编辑、数字必须有来源可查、结构化图表用代码算而不是让 AI"照猫画虎"、逐页跟你对齐而不是一次性甩全套。

## 核心亮点

- **原生可编辑，不是图片**：每个元素——文本框、形状、图表——在 PowerPoint 里都能单独点开改颜色改文字改位置，不是一张栅格图拍平了事。
- **结构化图表用代码算，不靠 AI 目测**：waterfall 的柱子必须数学连接、甘特图的条位必须对齐日期、占比必须求和 = 100%，几何和数据由确定性引擎计算，不是让模型现场画。
- **数字溯源硬门**：deck 上出现的每一个数字都要求能点回源头，查无来源直接拦下重做，不是"大概率没错"就放行。
- **一轮一轮跟你对齐，不批处理**：从解读 brief 到逐页定稿，全程跟你确认，不会一次性甩出一整份让你自己去挑错。
- **chaideck 自成长飞轮**：持续拆解真实成品 deck 入库进化方法论，用得越多，范本库 / 语感库越准，不是一套写死不变的模板。

## 六个 demo，看效果

三个场景 × 中英双语，虚构品牌（不涉及真实客户），下载 `.pptx` 到 PowerPoint 里逐个元素点开改——这才是"原生可编辑"的意思。

<table>
<tr>
<td align="center" width="33%" valign="top">
<a href="examples/01_fmcg_growth_strategy/"><img src="examples/01_fmcg_growth_strategy/preview/cover.png" alt="元气浆 2027 全国化增长战略" width="100%"/></a>
<br/>
<sub><b>快消品增长战略</b> — 元气浆 2027 全国化增长战略 · 39 页<br/>
<a href="examples/01_fmcg_growth_strategy/元气浆_2027全国化增长战略.pptx">下载中文版</a> · <a href="examples/01_fmcg_growth_strategy/YuanQiJiang_2027_National_Growth_Strategy.pptx">Download EN</a></sub>
</td>
<td align="center" width="33%" valign="top">
<a href="examples/02_enterprise_ai_roadmap/"><img src="examples/02_enterprise_ai_roadmap/preview/cover.png" alt="云枢重工 AI 转型路线图 2027-2029" width="100%"/></a>
<br/>
<sub><b>制造业 AI 转型路线图</b> — 云枢重工 2027-2029 · 39 页<br/>
<a href="examples/02_enterprise_ai_roadmap/云枢重工_AI转型路线图2027-2029.pptx">下载中文版</a> · <a href="examples/02_enterprise_ai_roadmap/Yunshu_Heavy_Industries_AI_Transformation_Roadmap_2027-2029.pptx">Download EN</a></sub>
</td>
<td align="center" width="33%" valign="top">
<a href="examples/03_hospitality_brand_launch/"><img src="examples/03_hospitality_brand_launch/preview/cover.png" alt="隐山 品牌启动与运营战略" width="100%"/></a>
<br/>
<sub><b>文旅品牌启动战略</b> — 隐山 品牌启动与运营战略 · 38 页<br/>
<a href="examples/03_hospitality_brand_launch/隐山_品牌启动与运营战略.pptx">下载中文版</a> · <a href="examples/03_hospitality_brand_launch/YINSHAN_Brand_Launch_and_Operations_Strategy.pptx">Download EN</a></sub>
</td>
</tr>
</table>

每份 deck 里都少不了 2×2 矩阵和甘特图这类"通用工具画不好"的结构化图表：

<table>
<tr>
<td align="center" width="50%" valign="top">
<img src="examples/02_enterprise_ai_roadmap/preview/matrix.png" alt="核心痛点诊断四象限矩阵" width="100%"/>
<br/>
<sub>2×2 定位矩阵 —— 云枢重工核心痛点诊断</sub>
</td>
<td align="center" width="50%" valign="top">
<img src="examples/03_hospitality_brand_launch/preview/gantt.png" alt="执行路线图甘特图" width="100%"/>
<br/>
<sub>甘特图 —— 隐山三年拓店节奏</sub>
</td>
</tr>
</table>

## 致谢：站在 ppt-master 肩上做的迭代

PPT Engine 的制作工作流不是从零造轮子，而是参考、迭代自 [ppt-master](https://github.com/hugohe3/ppt-master)（34k★）——它第一个把"AI 生成 SVG → 翻译成原生 DrawingML pptx"这条路验证到大规模可用，PPT Engine 制作层的 SVG→pptx 导出引擎就直接 vendor 自它（MIT，见 [engine/ppt_master/LICENSE.ppt-master](engine/ppt_master/LICENSE.ppt-master)）。在此向原作者 Hugo He 和 ppt-master 社区表示感谢。

ppt-master 本身定位是通用美学 deck 引擎（19 种视觉风格：杂志/数据新闻/瑞士网格/玻璃拟态/孟菲斯…），把"好看的 deck"这件事做得很完整。PPT Engine 站在这套引擎之上，往"咨询级/投资人级高 stakes deck"这个更窄但更深的方向做了几层进化：

1. **确定性图表几何引擎**：ppt-master 的 71 个图表模板已经备齐 waterfall/Gantt/Mekko 雏形等咨询级武器，我们在此基础上加了一层数据保真校验——bridge 必须数学闭合、占比必须求和 = 100%，图表不是 AI 目测画出来的，是代码算出来的。
2. **数字溯源硬门**：每页每个数字都要求能追溯到来源，无源硬拦——这是在 ppt-master "发散但不发明事实"的软规则之上，加了一道更严格的硬性质检。
3. **双层质检门**：在 ppt-master 已有的 SVG 语法层质检（禁用元素黑名单 / spec_lock 漂移检测）之外，加了一层内容层机检（元叙述 / 对客调性等），语法 + 内容两道 fail-closed。
4. **策略工作流的五阶段引导对齐**：把 ppt-master "八项确认"这套人机协商的 UX 骨架，延展成一整套面向咨询叙事的策略工作流——议题树 / 假设树（MECE）、storyline 论点证据结构、三道审查质量门。
5. **chaideck 自成长飞轮**：持续拆解真实成品 deck 入六类资产库 + 盲拆进化，让方法论随使用越积越准——这是 ppt-master 没有的、我们新长出来的能力。

## 架构

**两条工作流 + 一个飞轮**：

- **策略工作流**——把模糊 brief 做成 storyline 定稿。五阶段 fail-closed：判目的（演讲 / 阅读 / 预读讲解三态）→ 议题树 / 假设树（MECE）→ 调研（数字溯源 + 来源分类）→ storyline（论点 + 证据 + framing + 节奏 + Part 章结构）→ 三道审查质量门。
- **制作工作流**——把定稿大纲做成原生可编辑 `.pptx`。搭大纲 → 设计定稿（风格光谱 + spec_lock 完整设计契约）→ 逐页（模板映射 → 生成 SVG → 渲染 → 硬门，写一页渲一页检一页）→ vendor 引擎导出（零栅格化验证）→ 交付。
- **chaideck**——拆解真实成品 deck 入六类资产库 + 盲拆进化，让范本库 / 语感库越用越准。

**代码结构**：

- `engine/` —— 确定性引擎：图表几何（`chart_shapes.py`）、财务模型（DCF/LBO/可比公司，`financial_models.py`）、SVG→pptx vendor 导出引擎（`svg2pptx/`）、图像 / 图标 / 演讲稿生成管线。
- `reinforce/` —— 规则机检与状态：数字溯源 / 元叙述 / 对客调性等机检（`deck_rules/`）、设计契约锁（`spec_lock.py`）、deck 工作目录与状态、多角色策划团队、检索、chaideck 自成长飞轮（`evolution/`）。
- `skills/` —— 三条工作流对应的 SKILL.md，设计为在支持 Agent Skills 的编码助手（如 Claude Code）里加载使用。
- `specs/PPT方法论/` —— 沉淀下来的 PPT 方法论：顶级 deck 共因、页型手法、场景叙事、质量门标准、演讲版 vs 阅读版等。
- `exemplars/` `research_lib/` —— 卡库骨架（页型卡 / 表达手法卡 / 分析框架卡）与方法论调研知识，开箱即用，事实 / 品牌库随使用自行填充。

## Skill 说明

- **策略工作流**：brief → storyline 定稿。五阶段引导对齐：判目的 → 议题树/假设树 → 数字溯源调研 → storyline（论点+证据）→ 三道质检门。
- **制作工作流**：定稿大纲 → 原生可编辑 `.pptx`。逐页生成 → 渲染 → 硬门，vendor 引擎零栅格化导出。
- **chaideck**：拆真实成品 deck 入六类资产库 + 盲拆进化，方法论自成长飞轮。

## 快速开始

```bash
python3 -m venv .venv
.venv/bin/pip install -e .            # 装 engine + reinforce 两个能力包
.venv/bin/pip install -e ".[preview]" # 可选：渲染自检（另需 playwright install chromium）
.venv/bin/pip install -e ".[docling]" # 可选：PDF 版面分析增强
.venv/bin/python -m pytest            # 跑测试
```

技能（`skills/` 下的 SKILL.md）设计为在支持 Agent Skills 的编码助手里加载使用。

## 依赖与许可

- 内置 vendor 的 SVG→pptx 导出引擎（来自 [ppt-master](https://github.com/hugohe3/ppt-master)，MIT）与 [simple-icons](https://simpleicons.org) 图标集（CC0），许可见各自目录。
- 本项目以 **Apache-2.0** 授权，见 [LICENSE](LICENSE) 与 [NOTICE](NOTICE)。
