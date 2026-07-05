# open_deep_research 深拆笔记（简版 · 主 agent 异常未自动落盘 · 据返回料补）

> 项目：`../PPT开源参考/06_调研agent/open_deep_research`（11.8k★ · MIT · LangChain/LangGraph）
> ⚠️ 拆解 agent 中途"等 gpt-researcher 对照"没落盘，本笔记据其返回摘要 + gpt-researcher 对照 agent 补。**源码级细节待下个账户深化。**

## 一、是什么 + 定位
LangChain/LangGraph 的**可配置深度研究骨架**。版本很新（2026-06-26 主干）。auth 是 Supabase JWT 中间件（给 Open Agent Platform 多租户部署用，**与研究骨架本身无关**，别误读）。

## 二、研究骨架（vs gpt-researcher 的关键差异）
据 gpt-researcher 对照 agent 的结论：
- **open_deep_research**：更明确的**多 agent 分工 / Tree-of-Thoughts**，agent 角色更细分（Editor 规划 + Researcher 执行 + Reviser 质控类），编排更**显式**（LangGraph 状态图）。
- **gpt-researcher**：单一"主规划 agent + 并发多路搜索"扁平架构 + 深度研究靠**递归套娃**（每条子查询起新实例跑完整流水线、breadth 逐层砍半）。

## 三、对 PPT Engine 落点
- 接策略工作流的"主动调研"环节，两者都候选。**初判**：gpt-researcher 的"深度研究=递归套娃、把论点挖到可溯源数据"更贴 PPT 高 stakes 段的需求；open_deep_research 的 LangGraph 显式编排更适合"要强可控/可插自定义节点"时。
- ⚠️ 与 gpt-researcher 同坑：质控若是 LLM 自评，**不能当 🟢 硬信号**（防假绿）。

## 四、license + 待办
- License = **MIT**（可商用可闭源）。
- **待下个账户深化**：读 `src/` 的 LangGraph 节点/状态定义、配置项、与 gpt-researcher 逐项对照（检索源/迭代预算/fact-check）。
