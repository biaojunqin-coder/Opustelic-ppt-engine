# PPT Engine

把一份模糊的 brief，做成**咨询级 / 投资人级**的演示 deck——不是套模板，而是先想清楚叙事与逻辑，再逐页生成原生可编辑的 `.pptx`。

主攻通用工具做不好的高 stakes 段：waterfall / Mekko / Gantt 这类结构化图表、有论点有证据的叙事、fail-closed 的质量门。

## 两条工作流

1. **策略工作流**：把模糊 brief 解读成 storyline 定稿（叙事 + 逻辑 + 质量门）。五阶段 fail-closed：判目的（演讲/阅读/预读讲解三态）→ 议题树/假设树（MECE）→ 调研（数字溯源 + 来源分类）→ storyline（论点 + 一组证据 + framing + 节奏 + Part 章结构）→ 三道审查质量门。全程引导式对齐——一轮一轮跟人确认，不批处理。
2. **制作工作流**：把定稿大纲做成原生可编辑 `.pptx`。搭大纲 → 设计定稿（风格光谱 + spec_lock 完整设计契约）→ 逐页（模板映射 → 生成 SVG → 渲染 → 硬门，写一页渲一页检一页）→ vendor 引擎导出（零栅格化验证）→ 交付。

另有 **chaideck**（拆解真实成品 deck 入六类资产库 + 盲拆进化）的自成长飞轮。

## 核心设计

- **fail-closed 质量门**：每阶段/每页过硬门才进下一步，机检不过就返工，绝不带病推进。
- **确定性引擎**：图表几何（`chart_shapes.py`）、财务模型（DCF/LBO/可比公司，`financial_models.py`）是确定性计算，不靠模型即兴。
- **数字溯源**：每个上页的数字都要能追到来源，无源硬拦。
- **原生可编辑**：vendor SVG→pptx 引擎导出，导出即验证非图片化，绝不把栅格图当成品。

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

- 内置 vendor 的 SVG→pptx 导出引擎与 [simple-icons](https://simpleicons.org) 图标集，许可见各自目录。
- 本项目以 **Apache-2.0** 授权，见 [LICENSE](LICENSE) 与 [NOTICE](NOTICE)。
