# 08 · deck mode 叙事骨架体系（怎么论证 ≠ 长什么样）

> **可信度定级：方法论编码强候选**——来自 ppt-master `references/modes/`（vendor 进 `engine/ppt_master/`，MIT），
> 多轮真实生产打磨出的角色分工文档（非凭空候选），但**非拆真实 deck 验证**，与 00-06 同档。
> pyramid 一节因为和我们 [01 共因](01_顶级deck共因与翻车雷区.md)/[03 场景叙事](03_场景叙事结构.md) 高度吻合
> （"Data never stands alone, every figure pairs with a comparison" 直接印证用户洞察"一组数据论证一个观点"），
> 可信度可视为**交叉印证**，比单纯"编码候选"更硬一档。
> **源头**：用户问"怎么提升 ppt-master 利用率"，深挖出这条比"多用几个图表模板"价值高得多的方法论级发现。

---

## 〇 核心原则：mode 和 visual_style 是两个独立锁定的轴

> **「Mode = 你怎么论证；visual_style = 长什么样。」两者正交——任意 mode 可配任意 visual_style，不是 2×2 粗糙矩阵。**

此前我们的 `deck_type`(论证型/创意提案型) + `deck_mode`(演讲版/阅读版) 是把"叙事骨架"和"呈现风格"两件独立的事**捆在一起**的 2×2 矩阵——这次重构拆开成两条独立的轴：

- **`mode`**（本文档）：叙事骨架、标题语态、页面结构倾向、讲解词 register。一个 deck 锁一个 mode。
- **`visual_style`**（[07 双模式](07_演讲版vs阅读版.md)）：留白/节奏/密度。演讲版的 `narrative` deck 和阅读版的 `narrative` deck，论证骨架一样，呈现完全不同。

两轴在策略工作流阶段 1 **分开问**（一次一个问题，不合并成一轮）。

---

## 一、四种 mode（收窄到 4 种·CLAUDE.md 硬纪律4）

> ppt-master 原有 5 种，**排除 `instructional`**（培训/教程拆解场景——不是我们"咨询级/投资人 deck"的收窄定位，CLAUDE.md 硬纪律4 明确不做通用 PPT）。

| mode | 一句话 | 适用 | 对应我们原概念 |
|---|---|---|---|
| **pyramid** | 结论先行；MECE 论据；每个数字配 comparison | 决策支持/分析/战略/董事会汇报 | ≈ 原"论证型" |
| **narrative** | 情景→张力→解决的故事弧 | pitch/案例/品牌故事/融资 | ≈ 原"创意提案型" |
| **briefing** | 中性完整、可扫读、不预设立场 | 状态汇报/参考资料/周报/会议材料 | 新增（原"阅读版"里没拆出来的部分） |
| **showcase** | 视觉主导、大图大数字、情绪节奏 | 发布会/品牌揭幕/活动开场 | 新增 |

### 1.1 pyramid（与 01/03 强交叉印证）
- **塔顶 Lead**：标题就是结论，不是标签。
- **SCQA 开篇**：Situation(共识)→Complication(张力)→Question(待解问题)→Answer(MECE展开的建议)。
- **论断式标题**：写发现不写主题（"市场概览" ✗ → "国内市场同比+23%，跑赢全球均值" ✓）——和 01 共因1 一字不差。
- **数据不孤立站着**：每个数字配对照(同比/对标/竞品/目标/排名)+so-what——和我们"一组证据合围"用户洞察直接印证。
- **MECE**：拆分(驱动因素/细分/选项)时互斥穷尽，分支求和等于整体。
- → 硬门：`mode in {pyramid, briefing}` 才查数字溯源（陈述事实导向，narrative/showcase 的方案数字不强制）。

### 1.2 narrative
- 情景→张力→解决的故事弧（呼应 [03 SCR 三段式](03_场景叙事结构.md)）。
- 塔顶是 **big idea**（创意主张），不是"决策指向"——`check_horizontal_logic` 对 narrative/showcase 跳过这条查。
- 适合 pitch/案例/品牌故事/融资——我们 Descente 26FW 实战正是这个 mode。

### 1.3 briefing
- 中性、完整、可扫读，主题式标题可以接受（不强求论断式），不预设立场，等重展开。
- 适合状态汇报/参考资料/周报/会议材料——和 visual_style="阅读版" 天然搭配（但不是强制绑定）。

### 1.4 showcase
- 视觉主导，一页一个大冲击（大图/大数字），情绪节奏，文案克制。
- 适合发布会/品牌揭幕/活动开场——和 visual_style="演讲版" 天然搭配（但不是强制绑定）。

---

## 二、自动选型信号表（策略阶段1 判 mode 用·来自 ppt-master 编码）

| 内容/受众信号 | 推荐 mode | 备选 |
|---|---|---|
| 战略决策/分析/董事会/投资人 | `pyramid` | `narrative` |
| Pitch/案例/起源故事/campaign | `narrative` | `showcase` |
| 状态更新/参考资料/目录/FAQ/周报 | `briefing` | `pyramid` |
| 产品发布/品牌揭幕/活动开场/主题演讲 | `showcase` | `narrative` |

**易混淆对**（信号不强时怎么判）：
- `pyramid` / `briefing`：必须落到一个推荐结论(论断式标题、每数字配对照) → pyramid；只需完整呈现不论证(主题式标题、等重) → briefing。
- `narrative` / `pyramid`：论点靠故事弧落地(张力→解决) → narrative；论点是开篇即给结论再支撑 → pyramid。

> **mode 是透镜不是强制令**：用户自带大纲时，大纲是权威——mode 只管标题语态/讲解词 register，绝不重排用户的页序、不改用户给定的标题。这条和我们"以人为主"铁律同源。

---

## 三、和既有方法论的接口
- **07 双模式**(visual_style 轴)：正交关系，见〇节。
- **01 共因/03 场景叙事**：pyramid 一节交叉印证，可信度借力升级。
- **deck_rules/storyline.py**：`check_evidence_source` 按 mode 分流；`check_horizontal_logic` 对 narrative/showcase 跳过决策指向查。

> **待补/待验证**：① 0 份真实 deck 按 mode 分类验证过（虽 pyramid 有方法论交叉印证，仍未实拆样本核实）② briefing/showcase 两个新增 mode 还没有真实 demo 跑过，待制作层补 ③ instructional 被收窄排除，若未来产品定位扩展需重新评估。
