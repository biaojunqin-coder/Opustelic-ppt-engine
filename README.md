# PPT Engine

[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

中文 | [English](README_EN.md)

> **AI 不是帮你填模板，是帮你把 deck 想清楚。** PPT Engine 把"AI 一次成稿"拆成三段可控流程——**策略先想清楚 → 逐页硬门验收 → 原生可编辑导出**——专攻 waterfall / Mekko / Gantt 这类结构化图表、数字必须溯源、绝不栅格化的**咨询级 / 投资人级**高 stakes deck。

## 六个 demo，看效果

三个场景 × 中英双语，虚构品牌（不涉及真实客户），下载 `.pptx` 到 PowerPoint 里逐个元素点开改——这才是"原生可编辑"的意思。

<table>
<tr>
<td align="center" width="33%">
<a href="examples/01_fmcg_growth_strategy/"><img src="examples/01_fmcg_growth_strategy/preview/cover.png" alt="元气浆 2027 全国化增长战略"/></a><br/>
<sub><b>快消品增长战略</b> — 元气浆 2027 全国化增长战略 · 39 页<br/>
<a href="examples/01_fmcg_growth_strategy/元气浆_2027全国化增长战略.pptx">下载中文版</a> · <a href="examples/01_fmcg_growth_strategy/YuanQiJiang_2027_National_Growth_Strategy.pptx">Download EN</a></sub>
</td>
<td align="center" width="33%">
<a href="examples/02_enterprise_ai_roadmap/"><img src="examples/02_enterprise_ai_roadmap/preview/cover.png" alt="云枢重工 AI 转型路线图 2027-2029"/></a><br/>
<sub><b>制造业 AI 转型路线图</b> — 云枢重工 2027-2029 · 39 页<br/>
<a href="examples/02_enterprise_ai_roadmap/云枢重工_AI转型路线图2027-2029.pptx">下载中文版</a> · <a href="examples/02_enterprise_ai_roadmap/Yunshu_Heavy_Industries_AI_Transformation_Roadmap_2027-2029.pptx">Download EN</a></sub>
</td>
<td align="center" width="33%">
<a href="examples/03_hospitality_brand_launch/"><img src="examples/03_hospitality_brand_launch/preview/cover.png" alt="隐山 品牌启动与运营战略"/></a><br/>
<sub><b>文旅品牌启动战略</b> — 隐山 品牌启动与运营战略 · 38 页<br/>
<a href="examples/03_hospitality_brand_launch/隐山_品牌启动与运营战略.pptx">下载中文版</a> · <a href="examples/03_hospitality_brand_launch/YINSHAN_Brand_Launch_and_Operations_Strategy.pptx">Download EN</a></sub>
</td>
</tr>
</table>

每份 deck 里都少不了 2×2 矩阵和甘特图这类"通用工具画不好"的结构化图表：

<table>
<tr>
<td align="center" width="50%"><img src="examples/02_enterprise_ai_roadmap/preview/matrix.png" alt="核心痛点诊断四象限矩阵"/><br/><sub>2×2 定位矩阵 —— 云枢重工核心痛点诊断</sub></td>
<td align="center" width="50%"><img src="examples/03_hospitality_brand_launch/preview/gantt.png" alt="执行路线图甘特图"/><br/><sub>甘特图 —— 隐山三年拓店节奏</sub></td>
</tr>
</table>

## 和同类开源项目的区别

同类项目里形态最接近的是 [ppt-master](https://github.com/hugohe3/ppt-master)（34k★，同样跑在 Claude Code 这类 agent 里、同样导出原生 DrawingML pptx，是 PPT Engine 制作层导出引擎的 vendor 来源，见下方许可说明）。但两者定位不同：

| 维度 | ppt-master | PPT Engine |
|---|---|---|
| 定位 | 通用美学 deck 引擎——19 种视觉风格（杂志/数据新闻/瑞士网格/玻璃拟态/孟菲斯…），面向"好看的 deck" | 专攻咨询级/投资人级高 stakes deck，面向"经得起论证的 deck" |
| 叙事把关 | Strategist 角色 + 八项确认（画布/受众/风格/配色等实现层锚点），偏视觉与体验 | 五阶段策略工作流（判目的 → 议题树/假设树 MECE → 数字溯源调研 → storyline 论点证据 → 三道审查门），偏逻辑与论证 |
| 图表 | 71 个通用图表模板（waterfall/Gantt/Mekko 雏形等已备齐，当作通用素材使用） | 在同类图表上加**确定性几何引擎**计算（不是 AI 目测画），外加数据保真校验（bridge 必须闭合、占比必须求和 = 100%） |
| 质检门 | SVG 语法层质检（禁用元素黑名单 / spec_lock 漂移检测） | 语法层质检 + 内容层机检（数字溯源 / 元叙述 / 对客调性），双层 fail-closed |
| 数字与事实 | "发散但不发明事实"的软规则，校验偏格式 | 每个数字必须硬性可追溯到来源，无源硬拦——不是软规则是硬门 |
| 生成节奏 | 一次性生成整份 deck（单 pass，中途不许停下汇报） | 一轮一轮跟人确认，从解读 brief 到逐页定稿全程引导对齐，不批处理、不一次性产出 |
| 方法论沉淀 | 无持续学习机制，风格/图表模板人工维护 | **chaideck 自成长飞轮**：持续拆解真实成品 deck 入六类资产库 + 盲拆进化，方法论随使用越积越准 |

两者不是竞品关系——PPT Engine 制作工作流的 SVG→DrawingML 导出层直接 vendor 自 ppt-master（MIT，见 [engine/ppt_master/LICENSE.ppt-master](engine/ppt_master/LICENSE.ppt-master)），PPT Engine 是站在这套引擎之上，往"咨询级高 stakes 段"继续做深：确定性图表几何 + 财务模型、数字溯源硬门、双层质检、以及一轮一轮对齐的策略工作流。

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
