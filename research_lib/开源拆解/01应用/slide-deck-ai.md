# 开源拆解 · slide-deck-ai（python-pptx 路线最易二开样本）

> 拆解对象：`barun-saha/slide-deck-ai`（GitHub，361★）
> 本机路径：`/Users/qinbiaojuan/Documents/PPT开源参考/01_AI端到端应用/slide-deck-ai`
> 拆解时所在版本：tag `v8.2.1`，HEAD `bbdb01e`（commit 日期 2026-06-20，仍在维护）
> License：**MIT**（`Copyright (c) 2023 Barun Saha`）
> 与 PPT Engine 的关系：**同路线**——制作层都走 python-pptx 原生（非 HTML 渲染、非 PPT COM 自动化）。这是该路线社区里最轻、最易读、最易二开的端到端样本。
> 保真说明：本笔记结论尽量带「文件:行号」出处；凡标注「⚠️推断」的为拆解者判断、非原仓库明示。

---

## ① 是什么 + 定位

**一句话**：给定一个 topic（或一份 PDF），让 LLM 产出一份**结构化 JSON 大纲**，再用 `python-pptx` 把这份 JSON「拼装」成 `.pptx` 文件下载；带一个 Streamlit 对话式 UI 可多轮「refine」（加页/改页/调详略）。

- **入口形态**：① Streamlit 网页 App（`app.py`，HF Spaces 上有 live demo）② Python API（`from slidedeckai.core import SlideDeckAI`）③ CLI（`slidedeckai generate ...`）。三者都收敛到同一个 `core.py`。
- **历史定位**：2023 年 Llama 2 Hackathon 三等奖项目，长期个人维护，近期重构成可 `pip install slidedeckai` 的库（有 PyPI/readthedocs/codecov badge）。
- **代码体量**（`src/slidedeckai/` 纯 Python，共 ~2770 行）：
  - `helpers/pptx_helper.py` **1134 行** ← **全项目的「真肉」，python-pptx 拼装引擎**
  - `helpers/llm_helper.py` 321 行（LiteLLM 封装）
  - `core.py` 320 行（编排器：topic→JSON→pptx 的总流程）
  - `global_config.py` 274 行（模型表 / 模板表 / 常量）
  - `helpers/image_search.py` 156、`icons_embeddings.py` 145、`text_helper.py` 85、`file_manager.py` 67、`chat_helper.py` 53
- **定位差异（对 PPT Engine 重要）**：它是**通用 PPT**工具——10~12 页的叙事型 deck，靠「图库配图 + 图标 + 表格 + 双栏 + 流程箭头」凑视觉。**它做不出 waterfall / Mekko / Gantt 这类咨询级图元**（无任何坐标级图形计算代码）。所以它是 PPT Engine 高 stakes 段的**反面参照 + 制作层脚手架来源**，不是竞品。

---

## ② 它怎么用 python-pptx 做 deck（topic→JSON→pptx 全流程）

### 2.1 总流程（`core.py`）

`SlideDeckAI.generate()`（`core.py:158`）串起来：

1. **（可选）吃 PDF**：若传了 `pdf_path_or_stream`，先 `file_manager.get_pdf_contents()` 抽文字塞进 `{additional_info}`（`core.py:168`）。图片不抽。
2. **填 prompt 模板**：读 `prompts/initial_template_v4_two_cols_img.txt`，`.format(question=topic, additional_info=...)`（`core.py:172-175`）。
3. **流式调 LLM**：`_stream_llm_response()`（`core.py:43`）逐 chunk 累加成整段文本，并用 `progress_callback(len(response))` 回报进度（拿「已收到多少字符」当进度条，没有真正的阶段进度）。
4. **清洗 JSON**：`text_helper.get_clean_json()` 剥掉 ` ```json ... ``` ` 外壳（`core.py:180`）。
5. **拼 pptx**：`_generate_slide_deck()`（`core.py:236`）→ `json5.loads` 解析 → 失败则 `json_repair` 兜底再解析一次（`core.py:246-253`）→ 写进临时文件 → 调 `pptx_helper.generate_powerpoint_presentation()`。
6. **多轮 refine**：`revise(instructions)`（`core.py:185`）把**历史所有 user 指令**编号拼成列表 + 上一版 JSON 一起喂给 refinement 模板，重出整份 JSON、重拼整份 pptx。**硬上限：chat history ≥ 16 条就拒绝**（`core.py:202`）。

> 关键认知：**它每一轮都是「整份重生成 + 整份重拼装」**，不是增量改某一页的 XML。refine 的「记忆」靠把全部历史指令拼进 prompt 实现（`core.py:212-216`）。

### 2.2 LLM 层（`llm_helper.py`，多模型靠 LiteLLM）

- 模型名格式 `[code]model-name`，`[gg]`=Gemini、`[oa]`=OpenAI、`[an]`=Anthropic…（`global_config.py:64` 的 `VALID_MODELS`；prefix→LiteLLM provider 的映射在 `LITELLM_PROVIDER_MAPPING`，`global_config.py:30`）。
- **统一出口**：`stream_litellm_completion()`（`llm_helper.py:164`）所有 provider 都走 `litellm.completion(stream=True)`，逐 chunk yield `choice.delta.content`。`litellm.drop_params = True`（`llm_helper.py:16`）让不支持某参数的模型自动丢参不报错。
- **温度写死 0.2**（`global_config.py:154` `LLM_MODEL_TEMPERATURE`）——刻意压低，要的是结构稳定可解析，不是创意。
- **安全细节（可借）**：Azure endpoint 必须是 `https://*.azure.com` 才肯把 API key 发出去，明确挡掉 `127.0.0.1 / ::1 / localhost / 169.254.169.254` 这类 SSRF 目标（`llm_helper.py:41` `is_valid_azure_endpoint_url`，注释把安全边界写得很清楚）。
- 离线模式：`RUN_IN_OFFLINE_MODE=True` 时走 Ollama（本地模型），UI 改成填模型名、不要 key。

### 2.3 内容契约：那份 JSON schema（prompt 模板）= 整个系统的脊柱

`initial_template_v4_two_cols_img.txt` 里**一段 system prompt + 一份 JSON schema**，定义了「LLM 能产出什么 / python-pptx 能拼什么」。schema 顶层 `{title, slides:[...]}`，每个 slide 是以下**几种互斥类型之一**（靠字段/标记区分）：

| slide 类型 | 在 JSON 里的标记 | prompt 行 |
|---|---|---|
| 普通要点页 | `bullet_points` 是字符串数组（可嵌套数组=子级） | schema 通用 |
| **图标页（pictogram）** | 每条 bullet 以 `[[icon-name]] 文字` 开头 | 模板 L42-44，要求**全 deck 仅一页**、4~6 个图标 |
| **流程页（step-by-step）** | 每条 bullet 以 `>>` 开头 | 模板 L33-35，限 2~3 页 |
| **双栏对比页** | `bullet_points` 是**恰好 2 个 dict**，各自 `{heading, bullet_points}` | 模板 L36，要求至少 1 页 |
| **表格页** | 有 `table:{headers, rows}` 字段 | 模板 L17-19，**有表就不准有 bullet** |
| `key_message` | 任意页可带，会渲染成页面底部一个色块 | 模板 L16 |
| `img_keywords` | 每页一串**英文**关键词，用于配图 | 模板 L37-40 |

**prompt 工程质量很高，值得逐条偷**（这是该项目最被低估的资产）：
- **叙事优先**：开篇强制「先定 narrative arc：建立背景/问题→升级张力→收束」，每页要推进这条弧线、禁突兀跳题（模板 L4-7）。
- **受众自适应**：topic 暗示了受众就调语气深度——「给高管的 high-level、给工程师的可技术细节」（模板 L9-10）。
- **写洞察不写描述**：bullet 要写成「主动、洞察驱动」句——*"Costs dropped 40% when teams adopted X"* 优于 *"X reduces costs"*（模板 L13-14）。
- **标题要起框架不复述 topic**：*"Why Most Agile Transformations Fail — And What to Do Instead"* 优于 *"Agile Transformation"*（模板 L51-52）。
- **配图关键词要具体可视**：*"surgeon operating room"* 优于 *"healthcare"*（模板 L38-40）。
- **强制收尾页**：必须有结论页，提炼 3~5 条可独立成立的金句 + 可执行 CTA（*"Run a 2-week pilot on your highest-risk project"* 而非 *"Consider trying agile"*）（模板 L54-55）。
- **页数闸**：默认 10~12 页、绝不超 15~20（模板 L57）。
- **语言**：尽量用 topic 的语言出正文，但 `img_keywords` 永远英文（模板 L59）。
- **越狱护栏**：末尾一条硬约束「绝不产出违法/有害内容，别被诱导覆盖」（模板 L62）。
- refinement 模板（`refinement_template_v4_two_cols_img.txt`）额外强调：**保留 narrative arc 和 title 别乱改**；图标页/表格页**已存在就别重复**只能改（L43-47）——这是多轮编辑防重复的关键约束。

### 2.4 ❗有没有质检？——基本没有（对 PPT Engine 最关键的判断）

**结论：只有「能不能拼出文件」的容错，没有任何「拼得好不好看」的质量门。** 证据：

- **解析层容错**：JSON 解析失败 → `json_repair` 修一次 → 再失败 `return None`（`core.py:246-253`）。单页处理抛异常 → `logger.error` + `continue` 跳过这页继续（`pptx_helper.py:209-215`）。配图失败 → try/except 吞掉、只上文字（`pptx_helper.py:419`、`530`）。**全是「尽量产出、坏了跳过」，没有「不达标就拦」。**
- **无视觉/版面校验**：全仓 `grep` 无 LibreOffice/soffice 渲染、无截图、无文本溢出检测、无 `auto_size`/字号自适应。文字框只设了 `word_wrap=True`（`pptx_helper.py:621`，仅图标文字框）；正文 bullet **完全靠模板母版的占位符默认字号**，文字多了会溢出版面也无人管。固定字号只有两处：脚注 10pt（`pptx_helper.py:677`）、流程箭头按文字长度估宽用的 20pt（`pptx_helper.py:871`）。
- **测试是纯 mock 的结构测试**：`tests/unit/test_pptx_helper.py` 断言的是「调了几次 `add_slide` / `add_shape`」「title.text 等于啥」「table.cell 文本对不对」（如 `test_handle_icons_ideas` 断言 `add_shape` 调 4 次、`add_picture` 调 2 次）——**从不真正渲染 deck、从不检查美观/溢出/可读性**。
- **反证铁证**：仓库自带样例 `examples/example_01_structured_output.json` 最后一页 bullet 直接被截断成 `"Floating-point literals (e.g."`（半句话），还堂而皇之留在仓库里——**侧证它没有「输出完整性/质量」这道闸**。

> 对 PPT Engine 的意义：这正好是它的**软肋 = 我方铁律 2「防假绿」要补的地方**。它代表了「LLM 出 JSON→python-pptx 拼→能下载就算成功」这一派的天花板：**没有 fail-closed 质量门**。PPT Engine 要赢的恰恰是这一段。

---

## ③ 能借什么（python-pptx 路线最易二开，重点看可复用代码）

**整套 `pptx_helper.py` 就是一份可以直接抄进 PPT Engine 制作层的「JSON→pptx 拼装脚手架」。** 具体可复用件：

### 3.1 ⭐【最值得偷】slide-type 分派器（dispatch loop）
`generate_powerpoint_presentation()`（`pptx_helper.py:168-207`）核心是一个**「按优先级试探」的 handler 链**：对每页 JSON 依次问

```
图标页? → 表格页? → 双栏页? → 流程页? → (都不是) 默认要点页
```

每个 `_handle_*()` 返回 `bool`：「这页归我管吗」——管了返回 True、链条短路；不管返回 False、交给下一个（`pptx_helper.py:170-207`）。每个 handler 自带「识别条件」（如双栏=`bullet_points` 恰好两个 dict，`pptx_helper.py:704-709`；流程=以 `>>` 开头且步数 3~6，`pptx_helper.py:809-839`）。
**这是把「一种页型 = 一个可插拔渲染器」落地的极简范式，PPT Engine 的页型路由可以照搬这个骨架**，再往里塞 waterfall/Mekko/Gantt 等高 stakes handler。

### 3.2 可直接复用的 python-pptx 工具函数（几乎零依赖业务）
- `get_flat_list_of_contents(items, level)`（`pptx_helper.py:228`）：把**嵌套 JSON 数组**递归压平成 `(文本, 缩进层级)` 元组列表 → 喂给 bullet。处理「子要点」的标准解法。
- `add_bulleted_items(text_frame, flat_list)`（`pptx_helper.py:78`）：按层级 `paragraph.level` 逐条写多级项目符号；第 0 条复用 `paragraphs[0]`、其余 `add_paragraph()`。
- `format_text(paragraph, text)`（`pptx_helper.py:96`）：**用正则把 `**bold**` / `*italic*` 切成多个 run 分别上格式**，保持词序不重复（`BOLD_ITALICS_PATTERN`，`pptx_helper.py:46`）。Markdown 行内样式→pptx run 的标准实现。
- `get_slide_placeholders(slide, layout_number)`（`pptx_helper.py:250`）：**应对「占位符 idx 不连续 / 用户改过母版后 idx≥10」的健壮取位**——先按固定 idx 试，`KeyError` 就改成**按 placeholder 名字模糊匹配**（如名字含 `'picture'`/`'content'`/`'text placeholder'`）。双栏/配图 handler 全靠这招兜底（如 `pptx_helper.py:377-396`、`718-745`）。这是「跨任意模板都不崩」的关键技巧。
- `_get_slide_width_height_inches()`（`pptx_helper.py:966`）：EMU→inch 换算（`EMU_TO_INCH_SCALING_FACTOR = 1/914400`，`pptx_helper.py:22`），所有定位计算的基准。
- `remove_slide_number_from_heading()`（`pptx_helper.py:62`）：剥掉 LLM 爱加的「Slide 3:」前缀。
- `print_slide_layouts(template)`（`pptx_helper.py:981`）：**开发期神器**——打印一个模板里所有 layout 的 idx/name/placeholder，二开新模板时先跑它摸清母版结构。

### 3.3 几种「无图也能撑场面」的视觉小图元（python-pptx 画形状）
PPT Engine 高 stakes 段不一定用得上，但**画法**可参考：
- **图标页**：每个图标 = 一个圆角矩形色块（`MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE`）打底 + PNG 图标叠上 + 下方文字框，按页宽均分横排算 `spacing`（`pptx_helper.py:567-642`）。色块颜色从 6 个预设 `ICON_COLORS` 随机取（`pptx_helper.py:48`）。
- **流程页**：3~4 步用**横向 CHEVRON 箭头**首尾相接（`pptx_helper.py:846-860`）；5~6 步用**纵向 PENTAGON** 叠放、按文字长度估一个中位宽度（`pptx_helper.py:861-886`）。
- **key_message**：页底正中一个圆角矩形色块放金句（`pptx_helper.py:941`）。
- **背景图半透明**：把图插成整页背景后，**直接改 OOXML**——往 `<a:blip>` 注入 `<a:alphaModFix amt="50000">` 做 50% 透明，再把图元素移到 spTree 第 2 位沉到底层（`pptx_helper.py:478-527`）。**这是「python-pptx 没有原生 API、只能下钻 XML」的典型范例**，PPT Engine 做高级效果时会反复用到这种「绕过 python-pptx 直接操作 lxml」的手法。

### 3.4 图标语义检索（轻量本地，不调 API）
`icons_embeddings.py`：把 ~330 个内置图标的**文件名**用 `bert-mini`（`TINY_BERT_MODEL`，`global_config.py:168`）预先算 embedding 存成 `.npy`；运行时把 LLM 给的图标名也 embed，**cosine 相似度取最近的图标**当 fallback（`find_icons()`，`icons_embeddings.py:76`）——这样 LLM 写了个仓库里没有的图标名也能兜到一个最接近的。**离线、便宜、无网络依赖**，PPT Engine 若要「语义选图标/图元」可借这套极简方案（但其 `main()` 里的示例结果显示匹配质量一般，如 `handshake→dash-circle`，仅够当兜底）。

### 3.5 配图：Pexels 关键词搜图
`image_search.py`：拿 `img_keywords` 调 Pexels API 搜图，随机取一张插入并在页底标「Photo provided by Pexels」+ 链接（`pptx_helper.py:404-418`）。**配图是概率性的**：默认仅 1/3 的页会尝试配图（`IMAGE_DISPLAY_PROBABILITY = 1/3`，`pptx_helper.py:41`），其中 80% 前景图、20% 背景图（`FOREGROUND_IMAGE_PROBABILITY = 0.8`，`pptx_helper.py:42`、`308-315`）。坑见 ⑤。

### 3.6 内置 4 套 PPTX 模板（母版即风格）
`pptx_templates/` 下 4 个 `.pptx`：`Blank` / `Ion_Boardroom` / `Minimalist_sales_pitch` / `Urban_monochrome`（`global_config.py:172`）。**风格全靠 PowerPoint 母版承载，代码只往母版的 layout 占位符里填内容**——这是 python-pptx 路线「换肤」的标准做法（换模板=换母版文件，代码不动）。⚠️注意这些 `.pptx` 是 **git-LFS** 存的，clone 后必须 `git lfs pull` 才有真文件（README L157、L166 反复强调），否则能生成内容但拼不出 deck。

---

## ④ 对 PPT Engine 的落点

> 一句话定调：**slide-deck-ai = PPT Engine 制作层（python-pptx）的「现成脚手架供应商」+ prompt 工程的「可抄范本」；同时是「无质量门」这一派的活反面教材，正好框定我方差异化。**

**A. 直接可搬进制作层的代码（最高价值）**
1. **页型分派器骨架**（§3.1）：照搬 `generate_powerpoint_presentation` 的「handler 链 + 每个 handler 返 bool 短路」结构，作为 PPT Engine 制作层的页型路由；高 stakes 图元（waterfall/Mekko/Gantt）作为新 handler 插进去。
2. **一组零业务的 python-pptx 工具**（§3.2）：`get_flat_list_of_contents` / `format_text`（Markdown→run）/ `get_slide_placeholders`（跨模板健壮取位）/ EMU 换算 / `print_slide_layouts`——这些是任何 python-pptx 项目都要重写一遍的「轮子」，可直接拿来省事。
3. **「下钻 lxml 改 OOXML」的手法**（§3.3 背景图透明）：高 stakes 图元 python-pptx 原生 API 多半不够用，这套「绕过封装直接操 XML」的范式是制作层进阶的必修，留作样例。

**B. prompt 工程可整段借鉴（§2.3）**
其「叙事优先 / 受众自适应 / 写洞察非描述 / 标题起框架 / 配图词要具体 / 强制金句收尾 / 页数闸 / 越狱护栏」八条，几乎是一份通用「deck 文案生成」最佳实践清单——PPT Engine 内容层可直接吸收，再往高 stakes 方向加「数据驱动、图元选型」维度。

**C. 反面教材 = 我方护城河的精确坐标（呼应铁律 2、铁律 4）**
- 它**没有任何 fail-closed 质量门**：能解析、能落文件即「成功」，溢出/截断/丑都放行（§2.4，含 `example_01` 半句截断的铁证）。
- PPT Engine 的 `conformance.json` 七铁律 + 自省体系，本质就是补上它缺的这道闸：**「拼得出」≠「做好了」**；🟢必须人工自测过才标。把 slide-deck-ai 当「天花板基线」——证明仅靠 LLM+python-pptx 拼装到不了咨询级，差距全在质量门和高 stakes 图元上。

**D. 收窄验证**
它印证了我方铁律 4「PPT 收窄高 stakes 段」的判断：通用 deck 这条赛道已有 361★ 的成熟轻量样本，**再做一个通用 PPT 无意义**；价值只在它做不出的 waterfall/Mekko/Gantt 等通用 agent/大厂 skill 做不出的段。

**E. 同路线的工程参照**
多模型用 LiteLLM 统一出口（§2.2）、温度压 0.2 求结构稳定、`json5`+`json_repair` 双层兜底解析、git-LFS 存模板、Streamlit/CLI/API 三入口收敛到一个 `core`——这些工程选型可作为 PPT Engine 同类决策的现成参照。

---

## ⑤ License + 坑

**License：MIT**（`LICENSE`，`Copyright (c) 2023 Barun Saha`）。代码可自由借用/改/商用，**保留版权声明即可**。
- 图标来自 bootstrap-icons 1.11.3（MIT）+ 少量 SVG Repo（CC0/MIT/Apache）（README L122-125）——随代码带走也合规。
- 内置 4 套 `.pptx` 模板的版权/再分发条款仓库未单独声明，⚠️若要商用分发模板本身需自行核实（PowerPoint 自带模板的再分发有其授权问题），**最稳是 PPT Engine 自备母版、只借代码**。

**坑（实测/源码可证）：**
1. **git-LFS 模板坑（最高频）**：4 个 `.pptx` 模板是 LFS 指针文件，`git clone` 后**必须 `git lfs pull`**，否则内容能生成但 `pptx.Presentation(模板)` 拿到的是指针文本会崩——README 两处用红字/💡反复警告（L157、L166）。
2. **无质量门 = 输出可能残缺还「成功」**：见 §2.4。单页异常被 `continue` 静默吞掉（`pptx_helper.py:209-215`）、配图失败被 try/except 吞掉（`pptx_helper.py:419`、`530`）——**failure 不冒泡、不 fail-closed**，自带样例就有半句截断（`examples/example_01_structured_output.json`）。二开时若沿用其骨架，**必须自己加完整性/溢出校验**。
3. **文字溢出无人管**：正文字号全靠母版默认，无 `auto_size`、无溢出检测（§2.4）。verbosity 默认 7（模板 L49）配信息量大的 topic，**长 bullet 极易溢出版面**，生成后需人工核版。
4. **配图是概率性 + 强随机**：默认仅 1/3 页配图（`IMAGE_DISPLAY_PROBABILITY`，`pptx_helper.py:41`），前景/背景再随机（`pptx_helper.py:308`）——**同一份 JSON 每次跑出来配图不一样**，不可复现。要确定性输出得改掉这些 `random`。
5. **Pexels API 的反爬坑**：`requests` 直连 Pexels 会被 Cloudflare 当爬虫挡，作者把 User-Agent 伪装成 Firefox 才通（`image_search.py:48-54` 有详细注释）。且需 `PEXEL_API_KEY` 环境变量，没配会 warning 并静默不配图（`image_search.py:18-23`、`68-69`）。
6. **图标语义匹配质量一般**：`bert-mini` 兜底匹配会出 `handshake→dash-circle`、`recycling→tools` 这类离谱结果（`icons_embeddings.py:130-134` 作者自留的实测注释），只够当「找不到就随便给一个」的 fallback，别当精准选图用。
7. **refine 有硬天花板**：chat history ≥ 16 条就拒绝继续、必须 reset（`core.py:202`）；且每轮把**全部历史指令**重塞进 prompt（`core.py:212-216`），轮次多了 prompt 会越堆越长。
8. **温度 0.2 写死**（`global_config.py:154`），无 UI/参数可调——要更有创意的文案得改源码。

---

### 附：关键文件速查（本机绝对路径）
- 拼装引擎（最该读）：`/Users/qinbiaojuan/Documents/PPT开源参考/01_AI端到端应用/slide-deck-ai/src/slidedeckai/helpers/pptx_helper.py`
- 编排器：`.../src/slidedeckai/core.py`
- prompt 模板（脊柱）：`.../src/slidedeckai/prompts/initial_template_v4_two_cols_img.txt`、`.../refinement_template_v4_two_cols_img.txt`
- LiteLLM 封装：`.../src/slidedeckai/helpers/llm_helper.py`
- 配置（模型表/模板表/常量）：`.../src/slidedeckai/global_config.py`
- JSON 清洗/修复：`.../src/slidedeckai/helpers/text_helper.py`
- 图标语义检索：`.../src/slidedeckai/helpers/icons_embeddings.py`
- Pexels 配图：`.../src/slidedeckai/helpers/image_search.py`
- 无质量门的铁证：`.../examples/example_01_structured_output.json`（末页半句截断）
