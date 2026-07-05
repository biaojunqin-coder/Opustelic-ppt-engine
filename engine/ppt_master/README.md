# engine/ppt_master/ —— ppt-master 设计资产 + 方法论纪律（D1 补 vendor）

> 来源：[hugohe3/ppt-master](https://github.com/hugohe3/ppt-master)（MIT，见 `LICENSE.ppt-master`）。
> 背景：用户验收 Descente 成品后追问"是不是没用到当时下载的引擎"——核查发现 D1 当初只 vendor 了
> ppt-master 最底层的「SVG→DrawingML 转换引擎」（在 `engine/svg2pptx/`），把它真正值钱的**设计资产库**
> 和**方法论纪律**全漏了。这是补课，见 `../Engine/PPT开发实录/`（待补对应篇）。

## 和 engine/svg2pptx/ 的关系
`engine/svg2pptx/` = ppt-master 的 `scripts/svg_to_pptx/` + `scripts/svg_finalize/`（已在生产链路跑通+有测试，不动）。
本目录 = ppt-master 剩下的部分，按它原始结构搬：

```
engine/ppt_master/
├── templates/   # 设计资产：图表(71张svg) / 版式体系(7套：government_blue/red·academic_defense·ai_ops·
│                #          medical_university·pixel_retro·psychology_attachment) / 真实客户deck案例
│                #          (5套·每套5页+design_spec.md：某品牌/某品牌/某品牌/某品牌/某品牌)
│                #          / 品牌预设(4个：anthropic/google/某品牌/某品牌) / 图标(11631 svg·5库)
├── references/  # 设计方法论：视觉风格体系 / 配色方案 / deck模式(5：briefing/instructional/narrative/pyramid/showcase)
│                #            / shared-standards.md(SVG 技术规范) / strategist.md+executor-base.md+template-designer.md(角色方法论)
├── scripts/     # 配套脚本：svg_position_calculator.py(坐标预算防溢出) / svg_quality_checker.py / batch_validate.py
│                #          / native_narration_pptx.py(原生旁白) / pptx_intake.py(反向解析) / icon_sync.py 等
└── SKILL.md     # ppt-master 原始完整工作流文档（Strategist→Executor 多角色协作·供我们对照学习，不直接套用）
```

> ⚠️ **2026-07-01 勘误**：上面这版数字是查实据（`ls`+`wc`+读 `*_index.json`）后改的。
> 最早 vendor 时这里写的是"图表74/版式45/deck案例52/品牌17"——**45/52/17 这三个数字是错的**，
> 真实只有 7/5/4（图表 74→71 基本对，差 3 是把 README/index.json 也数进去了）。错误来源：
> 大概率是照抄了上游仓库 README 里"原仓库总规模"的表述，没有逐目录核对**实际 vendor 进我们仓库的子集**。
> 教训：vendor 资产清单这种"一写就可能被当真相用很久"的记录，必须现查、不能凭印象/抄来源文档写。

## 过滤了什么（收窄边界·CLAUDE.md 硬纪律4）
原始仓库还有 `image_gen.py`/`image_search.py`（AI 配图）、`references/image-renderings/`+`image-palettes/`
（水彩/像素艺术/蒸汽波等渲染风格）、`pptx_animations.py`/动画定制、`create-brand.md`（品牌创建）——
这些是通用 PPT 工具特性，咨询/投资人 deck 不靠配图和动画加分，按收窄定位**没拿**。
`references/ai-image-comparison/{rendering,palette}/` 下的渲染风格对比 PNG（~36M）同理排除，只留了文字规范。

## 关键发现：方法论纪律（比设计资产更该学）
ppt-master 的 `SKILL.md` 写死一条用血泪教训换来的铁律：

> **"SVG MUST BE HAND-WRITTEN, NOT SCRIPT-GENERATED"** —— 每页 SVG 必须主 agent 逐页手写，
> 禁止脚本批量生成（哪怕模板化数据生成）。"脚本生成路径试过、放弃了——跨页视觉一致性依赖逐页带着
> 完整上游上下文的手写创作，脚本生成器做不到。"

我们的 `examples/demo_descente_deck.py` 正是这个反模式（Python 脚本批量生成 21 页 SVG）。
还有 `spec_lock.md` 机制——颜色/字体/图标/图片锁在一个文件里，每页生成前强制重读，不许凭记忆现编。
这两条比图表模板本身更值钱，是接下来该落进我们 `制作工作流` SKILL 的东西（待办，见开发实录）。

## 怎么用（当前阶段：参考/适配，非直接套用）
- 做图表页时先查 `templates/charts/charts_index.json` 有没有现成版式可适配，不要从零手画。
- 配色/视觉调性先查 `references/visual-styles/`，别凭手感定十六进制色值。
- 高 stakes（金融/国企）deck 可参考 `templates/decks/某品牌/` 等真实客户案例的版式语言。
- SVG 排版坐标先用 `scripts/svg_position_calculator.py` 算，别手算字号（我们 `engine/svg_layout.py`
  的 `hero_text` 自动缩放是简化版，这个脚本更完整，待评估是否替换/整合）。
