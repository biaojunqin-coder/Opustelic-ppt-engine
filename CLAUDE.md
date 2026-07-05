# CLAUDE.md · PPT Engine

给在本仓库工作的 AI 的常驻指令。

## 项目是什么

PPT Engine：把模糊 brief 做成咨询级/投资人级 deck 的引擎。两条工作流——**策略工作流**（brief → storyline 定稿）和**制作工作流**（大纲 → 原生可编辑 .pptx），外加 **chaideck**（拆真实 deck 入库 + 盲拆进化的自成长飞轮）。技能在 `skills/` 下。

## 结构

- `engine/` —— 确定性引擎：图表几何（`chart_shapes.py`）、财务模型（`financial_models.py`）、SVG→pptx vendor 导出（`svg2pptx/`）、图像/图标/演讲稿管线。
- `reinforce/` —— 规则机检与状态：数字溯源/元叙述/对客调性等机检（`deck_rules/`）、设计契约锁（`spec_lock.py`）、deck 工作目录与状态、多角色策划团队、检索、自成长飞轮（`evolution/`）。
- `skills/` —— 策略工作流 / 制作工作流 / chaideck 的 SKILL.md。
- `specs/PPT方法论/` —— PPT 方法论（顶级 deck 共因、页型手法、场景叙事、质量门、演讲版 vs 阅读版等）。
- `exemplars/` `research_lib/` —— 卡库与方法论知识（开箱为方法论骨架，事实/品牌库随使用自行填充）。
- `tests/` —— 测试。

## 硬纪律

1. **以人为主 · 全程引导对齐**：从 brief 解读到最终 deck，一轮一轮跟用户确认，不批处理、不一次性产出。人做决策，AI 做参谋。
2. **fail-closed / 防假绿**：每阶段/每页过硬门才进下一步；机检不过就返工，绝不带病推进；自动判定/LLM 打分不能当"做好了"的硬信号。
3. **数字溯源**：上页的数字要能追到来源，无源硬拦。
4. **原生可编辑**：导出即验证非图片化，绝不把栅格图当成品。

## 常用命令

```bash
.venv/bin/pip install -e ".[dev]"    # 装能力包 + 测试依赖
.venv/bin/python -m pytest           # 测试
git config core.hooksPath .githooks  # 启用卡库改动留痕钩子（每次新 clone 各跑一次）
```
