# 开源拆解 · Talk-to-Your-Slides（TYS / pptagent）

> 拆解人：Claude（research 代理）｜日期：2026-06-30
> 仓库本地路径：`02_Agentic架构/Talk-to-Your-Slides`
> 上游：https://github.com/KyuDan1/Talk-to-Your-Slides ｜论文：arXiv:2505.11604（"Talk to Your Slides: Language-Driven Agents for Efficient Slide Editing"，标 ACL）
> **保真声明**：以下结论均出自本地源码 / README / notebook 的直接阅读，关键处标了文件:行号。凡论文宣称但代码未对上的，单独标注。

---

## ① 是什么 + 定位

- **一句话**：一个 LLM 驱动的 agent，**编辑「已经打开的 PowerPoint 活动会话」里的幻灯片**——靠读写 PPT 的**结构化对象信息**（shape 的 Name/Type/位置/字体 run），**绕开截图+点像素的 GUI 操作**。
- **解决的痛点**（README §Overview L25-35）：GUI-based agent（看截图、点坐标，如 UFO/Claude computer-use 那类）做幻灯片编辑**慢、贵、延迟高**。TYS 改成「读对象 → 改对象」，论文自报：**快 34.02% / 指令遵从度高 34.76% / 便宜 87.42%**（相对 GUI baseline；数字来自 README，本地无法复现，当作方向性结论）。
- **核心设计主张**：**hierarchical editing** —— 把「高层语义规划」和「低层对象操作」分两层（README L29）。对应到代码就是 Planner/Processor（语义层）和 Applier（操作层）。
- **跟我们 PPT Engine 的关系**：**强呼应**「操作对象而非图片」这条制作层路线。但有一个**关键技术栈差异**（见 ⑥）：TYS 走的是 **Windows COM（pywin32 / win32com）操作运行中的 PowerPoint.exe**，**不是 python-pptx 原生离线写文件**。它对 python-pptx 只用在「读取 / 转 VBA」的旁支脚本里。**所以 TYS 偷「对象建模 + 分层 + 评测」的思想，不能直接抄它的执行后端。**

---

## ② 5 阶段：各做什么 + 怎么衔接

真相源：`pptagent/main_cli.py`（线性编排）+ `pptagent/classes.py`（五个类）。**整条流水线是严格串行、单向传递一个不断长大的 JSON**（每阶段往同一个 dict 上挂新字段），不是多 agent 互相对话。

| 阶段 | 类 / 文件 | 输入 → 输出 | 用谁 | 关键点 |
|---|---|---|---|---|
| **1. Planner** | `Planner` `classes.py:10` | 自然语言指令 → `{understanding, tasks[]}` JSON | LLM（默认 gemini-1.5-flash，可 GPT-4.1-mini） | 把模糊请求拆成**每页一条 task**（prompt 明令 "write one task for one slide page" `prompt.py:13`），每条带 page number / target / action / contents。**Planner 提示词里直接内联当前 PPT 概况** `get_simple_powerpoint_info()`（只给文件名+页数，`prompt.py:5`）让规划有上下文 |
| **2. Parser** | `Parser` `classes.py:60` | Planner 的 tasks → 给每条 task 挂上该页的**完整对象结构** `task["contents"]` | **纯 COM 读取，无 LLM** | 对每条 task 的 page number 调 `parse_active_slide_objects(page)`（utils.py:692），把那一页所有 shape 解析成结构化 dict。**这是「结构化对象模型」的真相源采集步**——见 ③ |
| **3. Processor** | `Processor` `classes.py:146` | 带对象结构的 task → 挂上 `task["content after edit"]`（改完之后应该长啥样） | LLM（默认 GPT-4.1-mini） | **关键招：让 LLM「输入 JSON → 输出同结构 JSON，只改该改的字段」**（prompt `create_process_prompt` `prompt.py:93-115`，6 条硬规则：保持结构不变 / 只动 action 指定的 / 只改 target 指定的 / 纯 JSON 不要解释 / 保留所有字体格式 / 改完自检 JSON 合法）。即「编辑」被建模成**结构化对象的 diff**，而非自由生成 |
| **4. Applier** | 两套实现，见下 | 带「改前/改后」的 JSON → 真去改 PPT | 规则版无 LLM / LLM 版有 | 把「改前→改后」翻译成对 COM 对象的写操作。**这是把对象 diff 落地的执行层** |
| **5. Reporter** | `Reporter` `classes.py:643` | 处理结果 → 给用户的自然语言总结 | LLM（gemini-1.5-flash） | 总结改了啥、成没成、翻译类要附原文+译文。**注意：`main_cli.py:66-71` 里 Reporter 被注释掉了**，实测主流程不跑它，是可选件 |

**衔接本质**：`用户指令 → [Planner 语义规划] → [Parser 注入对象现状] → [Processor 算出对象应有状态] → [Applier 把差异写回] → (Reporter 汇报)`。串起来的「胶水」是一个 JSON，五阶段只是不断给它加字段（tasks → contents → content after edit）。Parser/Applier 这两步贴着 COM，Planner/Processor/Reporter 这三步是 LLM。

### Applier 的两套实现（重点，且互相打架）

- **A. 规则版 `Applier`**（`classes.py:216`）：**不调 LLM**。`_generate_code()` 用一长串硬编码模板，把 JSON 里的 edit/formatting/images/tables/charts 字段**拼成一大段 win32com Python 代码字符串**，然后 `exec()`。内置 7 个 helper：`modify_text` / `modify_text_formatting`（font/size/bold/italic/underline/color/alignment）/ `modify_shape_fill` / `modify_shape_line` / `replace_image`（删旧 shape 原位加新图，保留 Name）/ `modify_table` / `modify_chart`（要开 Excel 改图表数据）。**找 shape 的策略**：先按 `shape.Name` 精确匹配，找不到再退回「按文本内容 `TextRange.Text.strip()` 匹配」（`classes.py:470-487`）——这个「名字优先、内容兜底」的双重定位很值得借鉴。
- **B. LLM 版 `test_json_Applier`**（`test_Applier.py:465`）：**这是 main_cli 默认实际走的那个**（`main_cli.py:57`）。**让 LLM 现场写 win32com 代码**：`_json_generate_code()` 把（slide 号、改前 contents、改后 content）塞进 prompt，要 LLM 只吐可执行代码，`exec()` 跑。**带 fail-retry 闭环**：执行报错就把 `错误信息 + 出错代码` 当 feedback 回灌给 LLM 让它改 bug，重试 retry 次（`test_Applier.py:529-547`）。这个**「执行→捕获异常→把异常喂回 LLM 修代码→再执行」的自愈循环**是它工程上最实用的一招。
- 还有个 `test_Applier`（`test_Applier.py:238`，非 json 版）思路类似但按 edit_target 逐条改。
- prompt 里给 LLM 的硬约束很有信息量（`test_Applier.py:88-116`）：① 不准新建 PowerPoint 实例、用已开的 ② 文本用 `shape.Name` + `TextFrame.TextRange.Text` 双重定位 ③ **PowerPoint 颜色是 BGR 不是 RGB，要转**（红 RGB(255,0,0) 要写成 RGB(0,0,255)）④ 不准用 `**` 当加粗（Markdown 加粗在 PPT 无效）⑤ 给了 `TextRange.Find()` 循环高亮的范式代码 ⑥ 写备注用 `slide.NotesPage.Shapes.Placeholders(2)`。**这些是「LLM 写 PPT 自动化代码」的踩坑清单，直接可复用成我们的 prompt 护栏。**

---

## ②附 ·「操作结构化对象模型而非像素」到底怎么实现的

核心就是 `parse_active_slide_objects()`（`utils.py:692`）——把一页 PPT 的视觉，**无损降维成一棵结构化 JSON 树**，让 LLM 在「对象空间」而不是「像素空间」里推理。结构（`utils.py:708-745`）：

```
{
  "Presentation_Name", "Total_Slide_Number",
  "Slide_Properties": { 版式码 / CustomLayout 名 / 背景填充类型 / 转场效果 },   # parse_slide_properties
  "Objects_Overview": "Found N objects ...",
  "Objects_Detail": [                        # 每个 shape 一项
    { "Object_number", "Name", "Type"(AutoShape/Picture/Table/Chart/Group/Placeholder…),
      "Position_Left/Top", "Size_Width/Height",
      "More_detail": {  # 按 shape 类型分派：parse_text_frame_debug / parse_table / parse_chart / parse_picture / parse_group_shapes / parse_placeholder_details }
    }, ...
  ],
  "Slide_Notes": { "Has Notes Page", "Notes Content" }   # parse_slide_notes
}
```

**最精的一处：文字按 run 级别拆 + 字符级差分**（`parse_text_frame_debug` `utils.py:333`）。它不是把整段文字当一个字符串，而是：
- 逐字符取 font 快照 `snap(font)` = (Name, Size, Bold, Italic, Underline, RGB, Strikethrough, Sub/Superscript)（`utils.py:274`）；
- **当相邻字符的 font 快照不同就切一个 run**（`utils.py:349-359`），于是「一段里前 3 个字加粗变蓝、后面正常」会被如实拆成 2 个 run，各带自己的 Font dict。
- RGB 还按位拆成 `{R,G,B}`（`utils.py:315`）。

→ 这套「**run 级结构化**」正是它能精确执行「只把这一段里的英文变蓝 / 只加粗关键词」这类指令的底层支撑（对照 README demo："change only English into blue"）。**对我们 python-pptx 路线的直接启发**：python-pptx 里 run = `paragraph.runs[i]`，原生就有 `run.font.bold/size/color`——TYS 用 COM 逐字符重建 run 是因为 COM 没有现成 run 概念；**我们用 python-pptx 反而天然就在 run 层，这个「字体快照差分」的思路可以拿来做「编辑前后 run 级 diff」的校验/最小改动定位**。

执行端（写）对象操作的样子（COM，`classes.py:283-307`）：
```python
shape.TextFrame.TextRange.Text = new_text            # 改文字
text_range.Font.Bold = -1                            # 加粗（COM 用 -1/0）
shape.Fill.ForeColor.RGB = r + g*256 + b*256*256     # 填充色
shape.Line.Weight / .DashStyle / .Transparency       # 边框
```
全是**改对象属性**，没有任何坐标点击 / 截图。这就是「非像素」的实锤。

---

## ③ TSBench 评测思路（对我们「防假绿」最有参照价值）

- **数据集**：人工标注，**379 条指令 × 4 大类**（README L35；本地 `expanded_instruction_379.json` 确为 379 条模板，指令里 `{slide_num}` 占位）。原始种子 55 条（`original_instruction_55.json`），扩写到 379。另有 **TSBench-Hard**（300 条，README L48-72）专攻四种硬骨头：**视觉依赖**（"把文本框对齐到图片左边"，需空间推理）/ **模糊指令**（"让标题页更专业"）/ **多步复杂逻辑**（跨页条件格式）/ **不可能任务**（"改嵌入视频里的内容"——专门测 agent **会不会拒绝无效请求**）。
- **分类法（5 类，注意是 5 不是 README 说的 4）**：`category_map.json` + `evaluation/test_instruction_explain.md`（韩文）：
  1. **TextEditing**（翻译/摘要/改错/生成讲稿/关键词加粗上色）
  2. **VisualFormatting**（字号字体对齐/配色主题/列表样式）
  3. **LayoutAndImageAdjustment**（图片对齐缩放/改双栏/换 logo）
  4. **SlideStructure(AndMetadata)**（页码/排序/转场动画/标题页/SmartArt）
  5. **GlobalPresentationCleanup**（全局批量：统一改演讲者名、删重复页）
  > 这套「按**作用对象 + 作用范围（单页 vs 全篇）**切分编辑任务」的分类法，可直接借给我们做「制作层能力清单」的骨架。
- **判分 = LLM-as-judge + 多模态视觉对比**（`judge_ours.ipynb`，**这点最关键**）：
  - judge 模型用 **GPT-4o**；**把「原幻灯片渲染图 + 原 notes」和「编辑后渲染图 + 编辑后 notes」连同 instruction 一起喂给 GPT-4o**（`build_messages`），让它打分。
  - **评分 prompt（PROMPT_HEADER）**："You are an expert slide-editing judge... Compare the ORIGINAL slide with the EDITED slide. Decide how well the EDITED slide follows the INSTRUCTION and how aesthetically pleasing it is." 输出**严格 JSON 两维**：`{"instruction_adherence": <int 0-5>, "visual_quality": <int 0-5>}`。
  - 即**两个正交维度**：**指令遵从度** + **视觉美观度**，各 0-5。判分带 max_retries=5 重试、结果按 (slide, instruction) 去重续跑、汇总成 CSV。
  - TSBench-Hard 还引入 `ideal_description`（Gemini-2.5-Flash 生成的"理想成品描述"）当 ground truth（README L71）。
- **⚠️ 对 PPT Engine 的「防假绿」警示**：TYS 的质量信号**完全是「渲染成图 → 让另一个 LLM 打分」**。这正是我们铁律 2 要防的「让 LLM 打分当做好了的硬信号」。可借鉴它**把『指令遵从』和『视觉质量』拆成两个正交维度**的思路，但**绝不能照搬「LLM 打 0-5 就算验证通过」**——对咨询级 deck，LLM 看缩略图根本判不出 waterfall 的桥接是否在数值上闭合、Mekko 的列宽是否等于占比。**我们的门必须是 fail-closed 的客观校验（如 python-pptx 读回几何/数值核对），LLM 评分至多当 🟡 辅助参考。**

---

## ④ 关键实现 / 文件位（接手直接定位）

- 编排入口：`pptagent/main_cli.py`（CLI 批处理）/ `pptagent/main_flask.py`（Web UI :8080）/ `pptagent/main.py`（usage）。
- **五阶段类**：`pptagent/classes.py`（Planner:10 / Parser:60 / Processor:146 / Applier:216 / Reporter:643 / SharedLogMemory:683）。
- **对象解析（结构化对象模型真相源）**：`pptagent/utils.py` —— 入口 `parse_active_slide_objects:692`；run 级差分 `parse_text_frame_debug:333` + `snap:274`；分派器 `parse_shape_details`（两份，:508 / :989）；表 `parse_table:371`、图 `parse_chart:402`、图片 `parse_picture:461`、组 `parse_group_shapes:438`、备注 `parse_slide_notes:612`、页属性 `parse_slide_properties:650`。
- **Applier 实战版**：`pptagent/test_Applier.py` —— `test_json_Applier:465`（默认，带自愈重试）、代码生成 prompt `_json_generate_code:143` / `_generate_code:70`、连 PPT `_connect_powerpoint:225`。
- **提示词**：`pptagent/prompt.py`（PLAN_PROMPT:3、Processor prompt `create_process_prompt:93`）。
- **LLM 封装 + 成本核算**：`pptagent/llm_api.py`（`GEMINI_PRICING:131`，按 token 算 cost —— 它能报「便宜 87%」就靠这套逐阶段 token/cost 计量）。
- **评测**：`pptagent/judge_ours.ipynb`（GPT-4o 双图判分 + PROMPT_HEADER 评分 prompt）、`judge_baseline.ipynb`、`evaluation_ours.ipynb` / `evaluation_baseline.ipynb`（跑实验）、`benchmark_stat.ipynb`（统计）；数据 `expanded_instruction_379.json` / `original_instruction_55.json` / `category_map.json` / `evaluation/`（benchmark_ppts 56 个 slide_N.pptx + example_ppts 含 "Architecture pitch deck.pptx" 等真实模板）。
- **baseline（对照组）**：`pptagent/baseline.py` —— **单步 Instruction-to-Code**：直接让 LLM 一把梭写 win32com 代码（`BASELINE_PROMPT`），用来证明「5 阶段分层」相对「不分层」的增益。
- **旁支：对象操作的另一条路（python-pptx 这边）**：根目录 `pptx_to_vba.py`（**python-pptx 读 pptx → 生成 VBA 宏脚本**，COM 之外的离线路径）、`rule_base_vba-to-python.py`（743 行，VBA↔python 规则转换）、`reverse_engineering.py`。说明作者探索过「python-pptx / VBA / COM」多条对象操作后端，最终主线选了 COM。

---

## ⑤ 对 PPT Engine 的落点（能偷什么 / 怎么用）

1. **【最该偷】「编辑 = 结构化对象 diff」的建模**：Parser 注入对象现状 → Processor 产出「同结构、只改该改字段」的目标态 → Applier 算差异落地。这把「改 PPT」从「自由生成」收敛成「**对一个结构化对象树做最小受控修改**」，**天然 fail-closed、可逐字段校验、保留未触及的格式**。我们制作层（python-pptx）应照此建模：**把 deck 读成结构化对象树 → LLM 只输出 diff → 应用 diff → 读回校验 diff 是否精确命中**。这比让 LLM 直接吐 python-pptx 代码可控得多。
2. **「名字优先、内容兜底」的 shape 定位**（`classes.py:459-487`）：先 `shape.name` 精确匹配，失败再按文本内容匹配。我们在 python-pptx 里定位 shape 同样面临「name 不稳定」问题，这个双重 fallback 直接可用。
3. **run 级字体快照差分**（`parse_text_frame_debug`）：拿来做「编辑前后 run 级 diff 校验」——确认 LLM 只动了该动的 run、没误伤其他格式。python-pptx 原生就在 run 层，实现比 TYS 用 COM 重建更省。
4. **LLM 写自动化代码的「踩坑 prompt 护栏」**（`test_Applier.py:88-116`）：BGR/RGB 转换、`**` 加粗无效、双重定位、用已开实例…… 我们若让 LLM 生成 python-pptx 代码，这份清单（换成 python-pptx 的坑）应固化成 prompt 常驻约束。
5. **执行自愈循环**（`test_json_Applier`：exec 报错 → 异常+代码回灌 LLM → 改 → 重试）：是「LLM 生成代码」路线的标配可靠性手法，值得纳入我们的 Applier。
6. **评测维度拆「指令遵从 / 视觉质量」两正交轴**：可借进我们的验收，但**判分手段必须换成客观校验**（见 ③ 警示）。
7. **「按作用对象×作用范围」的编辑能力分类法**（5 类）：给我们「制作层能力清单 / 范本按场景」当骨架参考。
8. **逐阶段 token/cost 计量**（`llm_api.py`）：分层架构要对外讲「省钱」，必须像它一样每阶段记 token/价格。我们做 Engine 自省/仪表盘可加同款计量。

**但要清醒的边界**：
- TYS 收的是**编辑「已有」幻灯片**（translate/typo/recolor/加备注）这类**轻量原子操作**；**它不做我们要的「从 0 生成咨询级 waterfall/Mekko/Gantt」**。它的 Applier helper 列表里 `modify_chart` 还得开 Excel 改数据、且没有任何「画 waterfall 桥接」「按占比算 Mekko 列宽」的几何能力。**所以 TYS 是「编辑层方法论」的范本，不是「高 stakes 图表生成」的范本。**
- 它的 demo 全是 TextEditing / 简单 VisualFormatting（camelCase、变蓝、查错别字、加讲稿），**正是大厂 skill 也能做的通用段**——按我们铁律 4，这部分不是我们的战场。**我们要的是它『对象建模 + 分层 + 评测拆轴』的方法骨架，填进我们自己的高 stakes 图表能力。**

---

## ⑥ License + 坑

- **【大坑】无 LICENSE 文件**：仓库根目录、全仓 md/txt 均无任何 license 声明（已 `grep` 确认）。GitHub 无 license = **默认保留全部版权**，法律上**不可直接复用其代码进我们产品**。研究/拆解/借鉴思想 OK，**抄代码不行**。要用得先找作者授权或自己重写。
- **【强约束】平台锁 Windows + 运行中的 PowerPoint**：主线全靠 `win32com`/`pywin32`（`requirements.txt: pywin32==310`）操作**活动的 PowerPoint.exe COM 会话**（README 明示仅推荐 Windows，要开「信任访问 VBA 工程对象模型」）。**这跟我们 python-pptx 原生离线生成是两条路**——TYS 的执行后端**不能搬到我们的 mac/无 Office 环境**。我们在 macOS、靠 python-pptx 直接读写 .pptx 文件，不依赖 Office 进程。**偷思想，别偷后端。**
- **【一致性坑】README 自相矛盾处**：README §Overview 说「4 大类」，但 `category_map.json` + 韩文说明实为 **5 类**（多了 GlobalPresentationCleanup）；README 把 Reporter 列为正式阶段，但 `main_cli.py` 里 Reporter **被注释掉**、实跑只有 4 阶段产出。引用其「5 阶段」时按代码实情说明 Reporter 可选。
- **【代码味坑】研究代码、非工程化**：大量注释掉的旧实现（`classes.py:754-794` 整个旧版 parser、`test_Applier.py:375-462` 整个旧 Applier 类）、韩文注释混杂、`get_shape_type`/`parse_shape_details` 各定义两遍（后者覆盖前者）、`logs/` 200+ 个调试 log 入库。当**论文复现品 + 思想参考**读，别当生产代码模板。
- **多模型混用**：Planner=Gemini-1.5-flash、Processor/Applier=GPT-4.1-mini、Judge=GPT-4o、ideal_desc=Gemini-2.5-flash、还留了 Claude-3.7-sonnet 接口。凭据走 `credentials.yml`（含 OpenAI/Gemini/Anthropic key）。

---

### 一句话·最该偷的 1 件事
**把「编辑 PPT」建模成「对一棵结构化对象树做最小受控 diff」——Parser 注入对象现状、Processor 只产出『同结构、仅改该改字段』的目标态、Applier 落地差异——这套天然 fail-closed、保留未触及格式、可逐字段校验的对象 diff 范式，正是我们 python-pptx 制作层最该照搬的骨架（而非让 LLM 自由吐代码）。**
