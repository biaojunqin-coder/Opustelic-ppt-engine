# 拆解：ppt-master（AI 原生可编辑 PPTX）

> 拆解时间：2026-06-30 · 拆解对象本地路径：`01_AI端到端应用/ppt-master`
> 资源地图定位：34.3k★ · 「灵感源 · 原生可编辑 PPTX · SVG→DrawingML · 跑在 agent 里 · 同我们形态」
> 作者：Hugo He（金融背景 CPA/CPV/投资咨询工程师，自述「常年审改 deck，想要 AI 出的稿子在 PowerPoint 里还能改，而不是拍平成图」）· MIT · v2.11.0
> 出处约定：本笔记每条结论都带文件名；凡未标出处的判断会显式写「（拆解者判断）」。

---

## ① 是什么 + 定位

**一句话**：把任意源文档（PDF/DOCX/XLSX/PPTX/URL/Markdown/纯主题）转成**真·可编辑的 .pptx**——每个元素都是原生 DrawingML 形状/文本框/图表，能在 PowerPoint 里点开逐个改色改形，而非一页一张图。（出处 `README.md` §"AI presentation tools roughly fall into four categories"表 + `docs/technical-design.md` §Stage 3）

**形态 = 一个 Claude/Agent Skill**，不是独立 app。核心全在 `skills/ppt-master/SKILL.md`（728 行）+ `references/` + `scripts/`，跑在 Claude Code / Cursor / VS Code+Copilot / Codex CLI 等任何"能读写文件 + 执行命令 + 多轮对话"的 agent 里。装法三种：clone、`npx skills add hugohe3/ppt-master`、Claude Code 插件市场 `/plugin install`。（出处 `README.md` §"Pick an Agent" + §3 Set Up + `.claude-plugin/marketplace.json`）

**它对自己的定位（关键心智）**：
- "**harness + model = agent**"——工具拥有工作流，模型决定天花板。明说"PPT Master 是 harness 不是完整 agent"，最佳质量要 Claude（~1M 上下文）+ `gpt-image-2`，模型差就活儿多。（出处 `README.md` 第 100 行 ⚠️ 框）
- "**a tool, not a wishing well**"——产出是**设计草稿**不是成品，类比建筑师渲染图；定位"消灭 90% 空白页苦工，不替代最后一公里的人类判断"。（出处 `README.md` 顶部 IMPORTANT 框 + `docs/technical-design.md` §Design Philosophy）
- 四类 AI PPT 工具（模板填充 / 整页图片 / HTML 演示 / **原生可编辑**），它只做最后一类。（`README.md` 四象限表）

**定位与 PPT Engine 的契合度**：形态完全一致（跑在 agent 里、原生 pptx、本地化、fail-closed 有质检门）。差异：它是**通用美学 deck 引擎**（杂志/数据新闻/瑞士网格/玻璃拟态/孟菲斯等 19 种视觉风格），不专攻咨询/投资人高 stakes 段；但它的图表库里**已经备齐了咨询级武器**（见 ③⑤）。

---

## ② 它怎么做 deck（核心机制·最该看的部分）

### 底座：原生 PPTX，中间格式选 SVG（不是 HTML）

**管线一句话**：`AI 生成 SVG → 后处理脚本把 SVG 翻译成 DrawingML（PPTX）`。（`docs/technical-design.md` §Technical Pipeline）

**为什么选 SVG 当中间层（淘汰法选出，`docs/technical-design.md` §"Why SVG?"——这段是整个项目的设计魂，强烈建议原文精读）**：
- **直接生 DrawingML**：太啰嗦，一个圆角矩形要几十行嵌套 XML，AI 训练数据少、产出不稳、肉眼没法 debug。
- **HTML/CSS**：AI 最熟，但 HTML 是"文档"世界观（元素位置由内容流决定），PowerPoint 是"画布"世界观（每个元素绝对定位、无流无上下文）——**结构性失配**，不只是布局计算问题；HTML `<table>` 根本没法自然映射成一组独立形状。
- **WMF/EMF**：微软自家矢量格式、和 DrawingML 同源、转换损失最小，但 AI 几乎没训练数据，死在起跑线（"连微软自家格式都输给 SVG"）。
- **SVG 作为图片嵌入**：最简单但彻底毁掉可编辑性，等于截图。
- **SVG 胜出**：和 DrawingML 同世界观（都是绝对坐标 2D 矢量），转换是"同一概念的两种方言互译"。给了一张精确对照表：`<path d>`↔`<a:custGeom>`、`<rect rx>`↔`<a:prstGeom prst="roundRect">`、`linearGradient`↔`gradFill`、`fill-opacity`↔`alpha` 等。且 SVG 三方都满足：**AI 可靠生成 + 人在浏览器预览/debug + 脚本精确转换**。

**viewBox 用像素不用绝对单位**：像素空间让 AI 布局推理无歧义（`x="100"`=左+100px），浏览器可检视；EMU 转换只在导出时发生一次，管线其余环节（Strategist/Executor/质检/后处理）永不碰 EMU。（`docs/technical-design.md` §Canvas Format System）

### SVG→DrawingML 怎么转（技术核心·11390 行的转换引擎）

`scripts/svg_to_pptx.py` 只是 20 行薄包装，真身是两个 Python 包（纯 Python，核心仅依赖 `python-pptx`）：

- **`scripts/svg_to_pptx/`**（导出引擎，~6900 行）：
  - `drawingml_converter.py`（589 行）：核心 dispatcher，**逐元素分派**——`convert_rect/circle/ellipse/line/path/polygon/polyline/text/image/nested_svg` 各有独立翻译器。设计理由：SVG 层级模型干净映射到 DrawingML group/shape/picture，**不需要重排整页的整体优化器**；每个形状种类一个窄翻译器，能单独 debug + 单测。"一页质量 = 各局部独立转换之和"，这性质在整文件翻译下脆弱、在逐元素分派下稳健。（`docs/technical-design.md` §Native PPTX Conversion Internals）
  - `drawingml_elements.py`（**2440 行，最大模块**）：各元素→DrawingML 的实际翻译。
  - `drawingml_paths.py`（429 行）：`<path>`→`<a:custGeom>`（最复杂的几何翻译）。
  - `drawingml_styles.py`（656 行）：渐变/描边/效果/阴影。
  - `drawingml_context.py` / `drawingml_utils.py`：`transform` 解析（composes 每个 translate/scale/rotate/matrix，处理"绕非原点翻转"这类 idiom，见 `drawingml_converter.py` `parse_transform` 注释）、EMU 换算、url 引用解析。
  - `pptx_builder.py`（1215 行）：组装 .pptx。
  - `pptx_media.py` / `pptx_notes.py` / `pptx_narration.py` / `animation_config.py`：媒体嵌入、演讲备注嵌入、录制旁白、动画。
  - `use_expander.py` / `tspan_flattener.py`：见下「双消费者」。
- **`scripts/svg_finalize/`**（后处理，~2900 行）：`embed_icons`（图标内联）、`align_embed_images`+`crop_images`+`embed_images`+`fix_image_aspect`（图片裁剪/嵌入/宽高比修复）、`flatten_tspan`（818 行，文本展平）、`svg_rect_to_path`（圆角矩形转 path）。

**「svg_finalize 包有两个消费者」——容易漏看的关键设计**（`docs/technical-design.md` §"The svg_finalize package has TWO consumers"）：
- **磁盘消费者**：`finalize_svg.py` 把 `svg_output/`→`svg_final/`（Base64 内联图片，自包含，喂 IDE 预览 + 预览版 pptx）。
- **内存消费者**：原生 pptx 生成直接读 `svg_output/`（不落盘），但 DrawingML 处理不了两个 SVG 特性，于是转换器**在内存里**调 svg_finalize 模块：`use_expander.py`→`embed_icons`（否则每个 `<use data-icon>` 图标静默丢失）、`tspan_flattener.py`→`flatten_tspan`（否则 dy 堆叠的多行文本会塌成一行/x 锚定 tspan 渲染错列）。

**两种图片嵌入策略分叉**（`docs/technical-design.md` §Image Acquisition & Embedding）：开发期 `svg_output/` 用外部文件引用（快迭代、单一真相源替换）；交付时 `svg_final/` Base64 内联（自包含但体积涨 3-4×），原生 pptx 则把位图拷进 PPTX media 文件夹 + 用 `<a:srcRect>` 表达裁剪（PowerPoint 原生裁剪元数据，仍可编辑）。两边方向反了都会牺牲可编辑性或体积。

### 叙事怎么处理（Strategist 角色 + 两层风格锁 + 八项确认）

**不是一个 mega prompt，而是「单 agent 内角色切换」**（`docs/technical-design.md` §Role System）：Strategist / Image_Generator / Executor 是**按需加载的指令域**（`references/<role>.md`），不是并行 sub-agent。理由三条：①页面设计依赖完整上游上下文（Strategist 选的色、实际拿到的图 vs 失败替换的图、前页视觉节奏），sub-agent 拿到的是过期快照→视觉漂移；②Strategist 是"和用户协商"模式（开放、可回退），Executor 是"产出严格 XML"模式（不许即兴、不许缺属性），混进一个 prompt 逼模型同turn持两套不兼容纪律；③角色切换前强制 read 对应 reference 文件 = 把新角色指令压进上下文盖掉漂移 + 留审计轨迹。

**叙事骨架 = 两层独立锁**（`references/strategist.md` §d）：
- **Layer 1 通信模式（mode）**：deck 的叙事+说服骨架，锁一个 `pyramid`/`narrative`/`instructional`/`showcase`/`briefing`（闭集，文件在 `references/modes/`）或 `custom`（写 `mode_behavior` 段落描述多幕融合/正反合/苏格拉底式等）。
- **Layer 2 视觉风格（visual_style）**：锁一个 `references/visual-styles/` 里的预设（19 种：`swiss-minimal`/`brutalist`/`editorial`/`dark-tech`/`data-journalism`/`glassmorphism`/`memphis`/`ink-wash`/`zine`/`vintage-poster`…）或 `custom`。它**锁的是 HEX 怎么用，不锁用哪些色**。

**八项确认（Eight Confirmations）= 全管线唯一阻塞门**（`SKILL.md` Step 4，约 400 行篇幅，是 SKILL 最重的一节）：画布/页数/受众/风格目标/配色/图标/字体（含公式渲染策略）/图片。**两层 tier 确认**（默认通过本地网页 Confirm UI，端口 5050，chat 是永久 fallback）：
- **Tier 1 锚点**（由源+用户意图驱动）：画布 · 受众+核心信息+`content_divergence`+`delivery_purpose` · `mode`+`visual_style`。
- **Tier 2 实现层**（从用户**实际**确认的 Tier 1 重新推导）：页数 · 配色 · 字体 · 图标 · 公式策略 · 图片用法。
- **为什么两层**：每个实现字段都被那几个锚点决定（`visual_style` 锚定色/图标/字体/图片；`delivery_purpose` 定正文字号+页密度+**页数推荐**）。先锁锚点再推导，Tier 2 候选就贴用户真实锚点而非 AI 原始建议。页数是**派生字段**（内容量×delivery_purpose），所以在 Tier 2 不在最前。
- Tier 1→Tier 2→等最终确认是**一个不间断的 turn**，中间不许停下汇报（页面在转 spinner 等你写 Tier 2，停下=把页面晾住=bug）。（`SKILL.md` Step 4 ⛔ 框）

**material divergence（源材料发散度）**：自由文本字段，用户自己说"贴源 vs 自由重塑"。硬规则：**无论多自由，事实必须来自源材料**——发散是"发展源里已有的"（重组/重构/扩写/连接），绝非发明事实（发明是 `topic-research` 的活）。（`references/strategist.md` §c "Hard rule — facts stay sourced"）

**防视觉同质化的杠杆**：无用户指定风格时，**给≥3 种风格人格光谱**（safe 行业norm → shifted 更外放一档 → bold 挑战默认如 brutalist/zine/memphis），每个带一句"脾气标签+现实类比"（像"经济学人特稿"），而非一个安全选项。创意类字段（配色 palette、字体、生成图风格）一律≥3 候选，硬规则。（`references/strategist.md` §d Layer 2 + §"诚实不足例外"）

### 有无质检（有·fail-closed·这是和 PPT Engine 最对味的一点）

**`scripts/svg_quality_checker.py`（2106 行）是强制门**，跑在后处理**之前**（针对 `svg_output/` 而非 finalize 后——因为 finalize 会重写 SVG 掩盖源级违规）。Executor 生成完所有 SVG 后必跑，**任何 error 必须修完才能继续**（回 Visual Construction 重生成那一页、重跑检查）。（`SKILL.md` Step 6 "Quality Check Gate"）

**禁用特性黑名单（不是白名单）**，error 级直接 block（`svg_quality_checker.py` `_check_forbidden_elements`，行 376-470）：`<mask>`、`<style>`、`class` 属性、CSS 选择器/外部 CSS（`xml-stylesheet`/`<link rel=stylesheet>`/`@import`）、`<foreignObject>`、`<symbol>`+复杂 `<use>`、`<textPath>`、`@font-face`、SMIL 动画（`<animate*>`/`<set>`）、`<script>`/事件属性（onclick/onload）、`rgba()` 色（必须用 fill-opacity/stroke-opacity）、`<g opacity>`、`<image opacity>`。还查：viewBox 缺失/不匹配、width/height 与 viewBox 不一致。

**spec_lock 漂移检测**（`_check_spec_lock_drift`，行 811+）：扫 SVG 里实际用的 `fill`/`stroke`/`stop-color`/`font-family`/`font-size`，凡落在 `spec_lock.md` 允许集之外的=漂移，按文件汇总告警。字号有"ramp 包络"上下界检测（poster/showcase 模式去掉上界，因为巨型 hero 字号是设计不是漂移）。

**为什么黑名单 + 经验式 + 无 auto-fix**（`docs/technical-design.md` §"SVG Constraints" + §Quality Gate）：
- 黑名单不白名单——SVG 规格太宽，枚举允许项要常维护；黑名单只抓"语义上 DrawingML 无法表达"的窄集，其余隐式可用。
- 经验式不推导自规格——清单是从真实 PPT 导出失败长出来的，不是读 OOXML 规格；有些特性（如 `<mask>`）理论上 DrawingML 能表达但跨 PowerPoint 版本实际不可靠。
- **故意无 auto-fix**：error 要求 Executor 在上下文里**重新创作**那一页——一个被禁的 `<style>` 不是机械补丁，Executor 当初用它有设计意图，替代方案（内联属性）要重新施加同样意图；auto-fix 会静默丢意图、出更丑的页。
- 价值：把"PowerPoint 第 14 页导出失败"变成"Executor 在第 14 页用了 `<style>`，重生成那页"——快一个数量级的诊断回路，这才让长 deck 迭代经济可行。

### 分几步（七步串行管线 + 三命令后处理）

`SKILL.md` 核心 pipeline：`源文档 → 建工程 → [模板可选] → Strategist → [图片获取] → Executor 实时预览 → 质检 → 后处理 → 导出`。

七步：
1. **源内容处理**：非 Markdown 立即转（`source_to_md/` 下 pdf/doc/excel/ppt/web 各转换器）。
2. **工程初始化**：`project_manager.py init <name> --format <fmt>`（默认 `ppt169`=1280×720）；`import-sources --move`（强制 move 不 copy，保证工作根干净可复现可审计）。
3. **模板选项**：**默认自由设计**，只在用户给**显式模板目录路径**（含 `design_spec.md` 且 frontmatter `kind: brand/layout/deck`）时触发——**机械触发不语义匹配**：裸名字"academic_defense"、风格词"麦肯锡风"、品牌提及都**不**触发（这些流进 Strategist 八项确认当风格简报）。三种 kind 拥有设计契约的不同段（brand=身份段/layout=结构段/deck=全包），多路径按**段级整数替换**融合。
4. **Strategist**：八项确认（唯一阻塞门）→ 产出 `design_spec.md`（人读叙事）+ `spec_lock.md`（机读执行契约）。
5. **图片获取**（条件触发）：只在有 `Acquire Via: ai/web/slice` 行时跑。ai 走 manifest 契约（`image_prompts.json`）、web 批量搜（`image_search.py --batch`）、slice 切一张 AI 大图成多个同族小插画（风格凝聚）。
6. **Executor**：实时预览自启（浏览器编辑器，端口 5050，全程常驻）→ **逐页顺序手写 SVG**（绝不批量/不脚本生成/不派 sub-agent）→ 质检门 → 生成演讲备注 `notes/total.md`。
7. **后处理与导出**（三命令**逐个**跑、绝不合并）：`total_md_split.py`（拆备注）→ `finalize_svg.py`（图标/图片嵌入、文本展平、圆角转 path）→ `svg_to_pptx.py`（导出 pptx，默认嵌备注）。

输出：`exports/<name>_<ts>.pptx`（原生·读 `svg_output/` 保高保真）+ `backup/<ts>/svg_output/`（永远快照，可不跑 LLM 重导出）；`--svg-snapshot` 才额外出 SVG 预览版 pptx。

---

## ③ 能借什么（架构 / 技术 / 可复用代码）

**A. 整套 SVG→DrawingML 转换引擎（最大金矿·MIT 可直接用）**
- `scripts/svg_to_pptx/` + `scripts/svg_finalize/` 共 11390 行纯 Python，核心只依赖 `python-pptx`。PPT Engine 走"python-pptx 原生"路线——这套是现成的、经 34k★ 验证的、能把矢量图精确翻译成原生形状的轮子。逐元素分派架构（`drawingml_converter.py`）让每个翻译器可单测、好维护。
- 特别是 `drawingml_paths.py`（path→custGeom）、`drawingml_styles.py`（渐变/阴影→gradFill/alpha）、`transform` 矩阵分解（`drawingml_converter.py parse_transform`）——这些是自己从零写最费时、最容易出 bug 的部分。

**B. fail-closed 质检门的设计哲学（直接对标 PPT Engine 的「防假绿」铁律）**
- `svg_quality_checker.py` 的"**黑名单 error 级 block + 经验式增长 + 故意无 auto-fix + 跑在后处理前**"四原则，可整体移植成 PPT Engine 的质检门设计准则。尤其"无 auto-fix、强制 LLM 带上下文重做"= PPT Engine "🟢必须人工自测、绝不让自动判定当做好了"的同构思想，只是它在更细的页级。
- "把导出失败翻译成可定位的源级诊断"这个价值主张，正是 fail-closed 门的存在理由。

**C. spec_lock.md 防漂移机制（长 deck 一致性的核心解法）**
- 两文件分离：`design_spec.md`（人读"为什么"）vs `spec_lock.md`（机读"是什么"，Executor **每页生成前必 re-read**）。理由：没有 lock，Executor 长 deck 逐页重读 design_spec 会因上下文压缩漂移、色/字逐渐变异。（`docs/technical-design.md` §Spec Propagation）
- lock 还是**每页路由表**：除全局色/字，带 `page_rhythm`(anchor/dense/breathing)、`page_layouts`（继承哪个布局模板）、`page_charts`（适配哪个图表模板）、图片行带放置/裁剪契约。**空条目是有意信号**（无模板/无图表/无图常是设计决策不是缺数据）。
- `update_spec.py`：后期改色/字体两步传播（写 lock + 跨所有 `svg_output/*.svg` 字面替换），但**故意窄范围**（只 `colors.*` 和 `typography.font_family`），其余字段要语义感知不做批量传播。

**D. 图表/可视化模板库（71 个 SVG·`templates/charts/`·见 ⑤ 详列）**
- 命名按**视觉结构**不按业务模型名（SWOT/BCG/PEST/OKR/波特五力/价值链经由 `summary` 关键词匹配）。
- **`summaryGrammar` 是神来之笔**（`charts/charts_index.json` meta）：每个图表的 `summary` 是**选择规则不是描述**，格式固定 `"Pick for <内容形状+规模>. Skip if <原因→替代>"`。例：bar_chart="Pick for 单系列类别值比较 3-8 类。Skip for >12 长标签项(用 horizontal_bar)或多系列(用 grouped_bar)"。Strategist 拿每页内容形状去全读 71 条 summary 匹配——**无类别/关键词索引，全读是有意的**。这套"互斥选择规则 + 显式 Skip 跳转"可直接借给 PPT Engine 的图表选型逻辑。

**E. 角色切换 + 两层风格锁 + 两 tier 确认（叙事架构）**
- "单 agent 内按需加载角色指令域"对抗"一个 mega prompt 逼模型持多套纪律"——PPT Engine 的策略/制作两工作流可借此组织。
- mode（叙事骨架闭集）× visual_style（视觉风格闭集）正交分层 + 各锁一个 catalog 项，是把"deck 长啥样"拆成可控维度的好范式。
- 两 tier 确认（先锚点后从真实锚点推导实现层）解决了"AI 先建议一套、用户改了锚点、实现层还是旧的→不连贯"的经典问题。

**F. 工程纪律（十条全局执行纪律·`SKILL.md` 顶部）**
- 串行执行 / BLOCKING 硬停 / 禁跨阶段捆绑 / GATE 前置 / 禁投机预备 / 禁 sub-agent 生 SVG / 只许逐页顺序生成 / 每页 re-read spec_lock / **SVG 必须手写禁脚本批量生成** / 确定性路由。作者明说这些"看着官僚"，但每条都堵一个实战反复出现的失败模式（LLM 默认"这turn解决整个问题"恰是串行管线的错误形状）。PPT Engine 的七铁律可对照吸收。

---

## ④ 对 PPT Engine 的落点（最重要）

**契合判断**：ppt-master 是 PPT Engine 的**最近邻参照系**——同形态（agent skill）、同底座（原生 pptx）、同质量观（fail-closed 门）。它已经把"AI 生 SVG → 翻译成 DrawingML"这条路走通到 34k★，PPT Engine 不必重新论证这条路，应当**站在它肩上 + 在高 stakes 段做深**。

**直接可落的四件事**：

1. **转换引擎：评估直接复用 `svg_to_pptx/`+`svg_finalize/`（MIT）**。PPT Engine 走 python-pptx 原生路线，这 11390 行是现成、经验证、覆盖 path/渐变/阴影/transform/图标/裁剪的轮子。落点：把它当 PPT Engine "制作工作流"的导出层底座，或至少抄其逐元素分派架构 + 关键几何翻译（path→custGeom、transform 矩阵分解）。**（拆解者判断：这是本次拆解最大的可复用资产，复用它能直接拉高 PPT Engine 的"复用率≥50%"框架验证指标。）**

2. **质检门：把它的四原则写进 PPT Engine 的 fail-closed 门**。"黑名单 block + 无 auto-fix 强制带上下文重做 + 跑在后处理前 + 经验式增长"——和 PPT Engine "防假绿/铁律2（绝不让自动判定当做好了）"同构。PPT Engine 可把"高 stakes 图表的几何正确性"（waterfall 柱子是否数学连接、Gantt 条位是否对齐数据）做成同款 error 级门（ppt-master 的 `verify-charts` workflow 已经在做"AI 映射数据到像素常引入 10-50px 误差"的校准，可借）。

3. **高 stakes 段在它的图表库基础上做深**。它的 `templates/charts/` 已备 waterfall/Gantt/funnel/bullet/butterfly(可当 Mekko 雏形)/sankey/pareto/treemap/matrix_2x2/quadrant/consulting_table/financial_statement_table/pyramid——**正是 PPT Engine 收窄的"咨询级/投资人 deck、通用 agent 做不出的段"**。但 ppt-master 把它们当通用模板用，**没有针对"投资人/咨询"场景的叙事编排 + 数据校验深度**。PPT Engine 的差异化落点：在这些图表上叠"高 stakes 专用"的数据保真校验（数字必须对得上源、bridge 必须闭合、占比必须求和=100%）+ 咨询叙事模式（pyramid/MECE 的硬约束化）。

4. **借 spec_lock 防漂移 + summaryGrammar 选型 + 两 tier 确认**。这三个机制可几乎原样移植：①`spec_lock.md`（机读契约 + 每页 re-read）当 PPT Engine 长 deck 一致性的标准件；②图表 `summary` 写成"Pick for…/Skip if…→替代"互斥规则当选型逻辑；③两 tier 确认（锚点→推导实现层）当 PPT Engine 策略工作流的确认范式。

**要避开的坑（拆解者判断）**：ppt-master 自我定位"工具不是许愿池、出草稿不出成品"——PPT Engine 若要做"咨询级一次到位"，等于在它放弃的"最后一公里"上加码，难度更高，必须靠 fail-closed 门 + 数据校验把质量兜住，不能学它"剩下交给人"。

---

## ⑤ license + 坑

**License：MIT**（`LICENSE`，Copyright 2025-2026 Hugo He）。可自由用/改/商用，唯一条件保留版权与许可声明（attribution required，README 末尾也强调）。对 PPT Engine 复用代码无障碍。

**依赖**（`skills/ppt-master/requirements.txt`）：核心极轻——转换只要 `python-pptx>=0.6.21`；其余按需：`PyMuPDF`(PDF)、`mammoth`/`markdownify`/`ebooklib`/`nbconvert`(文档)、`openpyxl`(Excel)、`Pillow`+`numpy`(图片)、`cairosvg` 或 `svglib`+`reportlab`(SVG→PNG 后备，Office<2019 兼容)、`flask`(预览/确认 UI 服务)、`edge-tts`(旁白)、`curl_cffi`(微信等高安全站 TLS 指纹绕过)、`google-genai`(Gemini 图)。大部分工具仅用标准库。

**高 stakes 相关图表全清单（71 个中筛出，`charts/charts_index.json`）**：
`waterfall_chart`(变量分析/利润桥/预算差异，柱子数学连接)、`gantt_chart`(6-12 任务带工期依赖)、`funnel_chart`(3-5 转化漏斗)、`bullet_chart`(3-7 KPI 带目标+实际)、`butterfly_chart`(两组镜像数据共轴，可当 Mekko/人口金字塔雏形)、`sankey_chart`(分支合并流)、`pareto_chart`、`treemap_chart`、`matrix_2x2`、`quadrant_text_bullets`、`quadrant_bubble_scatter`、`pyramid_chart`/`pyramid_isometric`、`consulting_table`、`financial_statement_table`、`feature_matrix_table`、`heatmap_chart`、`kpi_cards`。

**坑 / 注意（部分拆解者判断）**：
- **它是 harness 不是成品**：明说模型差则产出差、最佳要 Claude Opus + gpt-image-2。PPT Engine 若复用其转换层没问题，但若想"低成本高质量"会撞它同款现实墙。
- **SVG 必须手写、禁脚本批量生成**：这是它的硬纪律（`SKILL.md` 规则 9），说脚本生成路线在 feature 分支试过并放弃——跨页视觉一致性依赖逐页带完整上游上下文创作，生成器脚本复现不了。**这意味着 deck 生成无法靠脚本提速，必然是 LLM 逐页 token 成本**（拆解者判断：PPT Engine 若想批量/降本，需自行验证这个权衡是否在咨询场景成立，别想当然绕过）。
- **EMF/WMF 不转 PNG**：源文档里的 Office 矢量图保留为外部引用、原生导出时按 Office 矢量媒体嵌入（`image/x-emf`），转 PNG 会丢 CJK 字体替换+栅格化损失。浏览器预览渲染不了 EMF（显示空白）是预期，pptx 才是真相源。
- **端口 5050 冲突**：确认 UI 和 Step 6 实时预览共用 5050（不同时跑），被占则自动顺延（5051…），要从启动日志读真实 URL。
- **图片绝不直接读像素**：所有图片信息走 `analyze_images.py` 输出的 `image_analysis.csv`（实时从 `images/` 重新派生，不是持久缓存），Strategist/Executor 不开图看。
- **路由是确定性的**：raw PPTX 模板→`template-fill`；1:1 保形改版→`beautify-pptx`；成品加备注/旁白/动画→`native-enhance-pptx`；这三条**故意不进 SVG 管线**（保形 vs 设计合成是两类操作，明令不许合并）。PPT Engine 若借其路由表，注意这层边界。
- **fork 风险**：作者一人主力维护（README 自陈），活跃靠赞助商。代码可复用，但若深度依赖其上游更新需评估单点维护风险（拆解者判断）。

---

## 最值得偷的 1 件事

**那套「SVG 当中间层、逐元素翻译成 DrawingML」的原生可编辑 pptx 引擎（11390 行 MIT 纯 Python，只依赖 python-pptx）——它用淘汰法论证清楚了"为什么不是 HTML、不是直接 DrawingML、而是 SVG"，并配了一道 fail-closed 黑名单质检门把 LLM 生成的不确定性挡在导出之前；PPT Engine 走原生 pptx 路线，这是可直接站上去的现成轮子 + 可整体移植的质量门哲学。**
