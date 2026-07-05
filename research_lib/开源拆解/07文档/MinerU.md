# MinerU 深拆 — 文档预处理 / brief 输入解析层

> 出处：本地 clone `07_文档预处理/MinerU`
> 版本 `mineru/version.py` = **3.4.0**；git HEAD `3e60291`（2026-06-18）；upstream `github.com/opendatalab/MinerU`（72k★，OpenDataLab/上海AI实验室）
> 拆解口径：`ls -R` + README(中英) + 源码精读。下文每条结论都带文件出处，**未读到的不编**。

---

## ① 是什么 + 定位

一句话：**把 PDF / 图片 / DOCX / PPTX / XLSX 统一解析成「LLM-ready 的 Markdown + JSON」的高精度文档解析引擎**（pyproject.toml `description`；README §Project Introduction）。

- 出身：InternLM 预训练期间为「科学文献符号转换」而生（README），所以公式/表格/多栏这种硬骨头是它的主场。
- 定位坐标（对 PPT Engine）：它是**输入端**——用户把一份 PDF/Word/旧 PPT 丢进来当 brief，MinerU 负责「逆向」成结构化中间表示；不负责生成 PPT。已知 banana-slides 用它做版面分析逆向 PPT，印证它「逆向能力强」这一判断。
- 自我能力声明（README §Key Features，保真摘）：
  - 去页眉/页脚/脚注/页码，保证语义连贯；按**人类阅读顺序**输出；保留标题/段落/列表结构。
  - 公式 → LaTeX；表格 → HTML；自动检测扫描件/乱码 PDF 并触发 OCR；OCR 支持 **109 种语言**。
  - 多种输出：多模态 Markdown / NLP Markdown / 按阅读顺序的 JSON / 富中间格式；附 layout 与 span 两种可视化便于核查质量。

### 四套后端（README §Local Deployment 表，精度=OmniDocBench v1.6 端到端总分）

| 后端 | 精度 | 纯 CPU | 特点 | 部署重量 |
|---|---|---|---|---|
| `pipeline` | 86.47 | ✅ | 传统流水线，多模型拼装，**无幻觉**，最稳最轻 | 4GB 显存即可，甚至纯 CPU |
| `vlm`(-engine) | 95.30 | ❌ | 单个视觉语言大模型(MinerU2.5-Pro 1.2B)端到端识图 | 8GB 显存起 / vLLM·LMDeploy·mlx |
| `hybrid`(-engine) | 95.39(high)/95.26(medium) | ❌ | VLM + 原生文本抽取混合，低幻觉，默认 `effort=medium` | 8GB 显存起 |
| `*-http-client` | 同上 | ✅ | 把重活甩给 OpenAI 兼容的远端模型服务，本地只当瘦客户端 | 2GB 显存 |

> 关键取舍：**`pipeline` 纯 CPU 能跑且"无幻觉"**——对解析 brief 这种「宁可漏识别、不可瞎编」的场景，比高分但要 GPU+可能幻觉的 VLM 更对味。

---

## ② PDF / Office → 结构化「怎么做」（核心机制）

### 主干架构：双路汇流到统一中间表示 `middle_json`

整个系统的脊椎是一个**统一中间 JSON（`middle_json`，内含 `pdf_info`=按页的 block 列表）**。两条完全不同的解析路最终都吐出同一个 `middle_json`，下游再分叉成各种输出格式：

```
PDF/图片 ──[模型路: pipeline/vlm/hybrid]──┐
                                          ├──> middle_json(pdf_info: [{page_idx, para_blocks:[...]}])
DOCX/PPTX/XLSX ──[OOXML 原生解析路]────────┘                    │
                                                               ├─> *.md  (mm/nlp markdown)
                              union_make() / office_union_make()├─> *_content_list.json     (按阅读顺序)
                                                               ├─> *_content_list_v2.json  (结构化嵌套)
                                                               └─> *_middle.json / *_model.json
```
出处：`mineru/cli/common.py`（`do_parse` → `_process_office_doc` / `_process_pipeline`；输出写盘逻辑在 283–347 行，dump md / content_list / content_list_v2 / middle / model 五件套）。

**这是最值得偷的设计**：把「不同输入格式」和「不同输出格式」用一层稳定的 `middle_json` 彻底解耦——加一种新输入只要让它产出 `middle_json`，加一种新输出只要消费 `middle_json`，二者互不感知。

### 类型系统（`mineru/utils/enum_class.py`，保真）

- `BlockType`：image / table / chart / caption / footnote / text / title / interline_equation / list / index / discarded，VLM2.5 又加了 code / algorithm / header / footer / page_number / aside_text…；`pp_doclayout_v2` 再加 abstract / doc_title / paragraph_title 等。**粒度很细**，连"被丢弃区(discarded)""旁注(aside_text)"都建了型。
- `ContentType` / `ContentTypeV2`：v2 把表格细分 `simple_table` / `complex_table`，列表分 `text_list` / `reference_list`，公式分行内/行间——这套「细分类型」就是 LLM-ready 的关键：下游能精确知道每块是什么。
- `MakeMode`：`mm_markdown`(多模态，留图/表HTML) / `nlp_markdown`(纯文本，丢图表，喂 LLM 用) / `content_list` / `content_list_v2`。

### 模型路（PDF/图片）用了哪些模型（`mineru/backend/pipeline/model_init.py`）

`pipeline` 是「多原子模型拼装」，各司其职、可单独开关：
- **版面分析 Layout**：`PP-DocLayoutV2`（`pp_doclayout_v2_model_init`）——出 block 框 + 类型 + 阅读顺序。
- **公式 MFR**：`unimernet_small`（默认）或 `pp_formulanet_plus_m`（开 `MINERU_FORMULA_CH_SUPPORT` 走中文公式）→ LaTeX。
- **OCR**：`PytorchPaddleOCR`，3.4 升级到 **PP-OCRv6**（README Changelog，OmniDocBench 上 +11%）。
- **表格 Table**：先分类器 `PaddleTableClsModel` 判有线/无线，再分别用 `UnetTableModel`(有线/wired) 或 `PaddleTableModel`(SlaNet+，无线/wireless) → HTML；另有方向分类器纠正旋转表格。
- 工程细节：`ModelSingleton` / `AtomModelSingleton` 用 `(lang, formula_enable, table_enable)` 当 key 缓存模型实例，**模型只初始化一次**；多线程推理用 RLock 保护（`PIPELINE_*_INFERENCE_LOCK`，默认靠环境变量关着、需要时再开）。

> 自动判扫描件：`_get_ocr_enable` + `mineru/utils/pdf_classify.py` 的 `classify()`，`parse_method='auto'` 时自动决定是否走 OCR（`pipeline_analyze.py`）。

### Office 路（DOCX/PPTX/XLSX）—— **不调任何模型，纯 OOXML 原生解析**（对 PPT Engine 最关键）

这条路完全绕开 AI 模型，是确定性的 XML 解析，因此**零 GPU、零幻觉、快**：
- 依赖（pyproject.toml）：`python-docx` / `pypptx-with-oxml` / `openpyxl` / `mammoth` / `lxml` / `pylatexenc`。
- 入口：`office_docx_analyze` / `office_pptx_analyze` / `office_xlsx_analyze`（`mineru/backend/office/*_analyze.py`）→ 各自 `convert_binary()`（`mineru/model/{docx,pptx,xlsx}/main.py`）→ `result_to_middle_json()` 归一化成统一 `middle_json`。
- **PPTX 怎么逆向版面**（`mineru/model/pptx/pptx_converter.py`，与 banana-slides 用法直接对应）：
  - 遍历每张 slide 的 shape，递归展开 group（`_FlattenedShape` + `_SlideTransform` 做坐标变换/缩放/平移的 compose），拿到每个形状的真实 bbox。
  - 用 **XY-Cut 排序**（`mineru/model/pptx/xycut_pp_sorter.py` 的 `sort_entries`，参数 `PPTX_XYCUT_BETA=2.0`、密度阈值 0.9）把散落的文本框/图/表**重排成人类阅读顺序**——这正是「逆向 PPT 版面」的核心算法。
  - 占位符语义识别：用 `PP_PLACEHOLDER` 区分标题/正文/页码/日期/页脚，背景大图按面积比(`MIN_PICTURE_AREA_RATIO` 等)过滤。
  - 文字富格式：`OfficeRichTextSegment` 保留字号/加粗（`_effective_font_size_pt` / `_effective_all_bold`），据此反推标题层级。
  - 公式：PPTX 里的 OMML 数学 → LaTeX，走 `mineru/model/docx/tools/math/omml.py` 的 `oMath2Latex`（docx/pptx/xlsx 三家共用同一套 OMML→LaTeX）。
- **图表 chart → HTML 数据表**（`mineru/backend/utils/office_chart.py`，⭐重磅）：直接读嵌入的 OOXML `c:chart` XML，解析出每条数据系列（`SeriesSpec`：类目 / 数值 / 名称 / 缓存值），支持 bar/line/pie/scatter/bubble/radar/area/doughnut/stock/surface 等十几种图型；最后 `_render_html_table(headers, columns, row_count)` 渲染成真正的 `<table>`。**即它不是把图表当一张图截下来，而是把图表背后的数据还原成表格**——这对「PPT brief 里有图表、要拿到底层数据」是降维打击。

### 输出怎么拼（`mineru/backend/office/mkcontent/output_builders.py`）

- `mk_blocks_to_markdown`：按 block 类型渲染——title 出 `#*N`(层级)、image 出 `![](路径)`、table 直接嵌 HTML、chart 嵌还原出的 HTML 表、list/index 递归扁平化；`nlp_markdown` 模式直接 `continue` 掉图/表/chart（给纯文本 LLM 用）。
- `make_blocks_to_content_list_v2`：结构化 JSON，每块带 `type` + `content` + `anchor`(书签锚)，表格还标 `table_type`(simple/complex) 和 `table_nest_level`(嵌套层数，靠数 `<table` 个数 + 检测 colspan/rowspan)。
- 阅读顺序 + 页码：`union_make` 遍历 `pdf_info` 每页，把 `page_idx` 透传进每个 content 项——下游永远知道「这块来自第几页」。

### LLM 只做「锦上添花」，不做核心抽取（`mineru/utils/llm_aided.py`）

值得记一笔：MinerU 里**唯一**用到大语言模型 API（OpenAI 兼容）的地方是**标题层级的后处理纠正**——把所有标题收集成 `title_dict`（带平均行高几何提示），让 LLM 重排层级（`_build_title_optimize_prompt`）。它是**可选、配置开关控制**的，核心解析完全不依赖 LLM。这印证了它的设计哲学：**机制（模型/规则）负责抽取，LLM 只补语义判断**——与本项目「别拿 LLM 打分当做好了的硬信号」的纪律同频。

---

## ③ 能借什么（可迁移的设计/代码）

1. **「统一中间表示解耦输入×输出」的脊椎设计**（`middle_json` + `union_make`）：PPT Engine 若要吃多种 brief 格式（PDF/Word/PPT/图），照搬这个「N 种输入都归一到一个 IR，再由一个 builder 分叉出 N 种下游表示」的结构，扩展性最好。⭐最值得偷。
2. **细粒度 block 类型体系**（`enum_class.py`）：把 `discarded`/`aside_text`/`page_footnote`/`caption` 都单列类型——解析 brief 时能精确剔除噪声(页眉页脚页码)、保留正文，是「LLM-ready」的前提。可直接借这套枚举命名。
3. **OOXML 原生解析三件套思路**（docx/pptx/xlsx converter）：纯 `python-docx`/`pypptx-with-oxml`/`openpyxl`+lxml，**零模型零 GPU**，确定性、可单测。PPT Engine 解析 PPT/Word brief 完全可以只抄这条路（甚至直接 `pip install mineru` 调 `office_*_analyze` 函数）。
4. **PPTX 的 XY-Cut 版面重排 + group 坐标 compose**（`xycut_pp_sorter.py` / `_SlideTransform`）：把"一堆绝对定位的框"还原成"人类阅读顺序"的算法，逆向任何 slide-like 版面都用得上。
5. **图表 OOXML → 数据表还原**（`office_chart.py`）：从嵌入图表里抠出底层 series 数据 → HTML 表。本项目做「咨询级图表」时，逆向参考 deck 里的图表数据，这段是现成轮子。
6. **`nlp_markdown` vs `mm_markdown` 双模式**：同一份解析结果，给纯文本 LLM 时自动剥离图/表，给多模态时保留——「按下游消费者裁剪输出」的小而实用的模式。
7. **模型单例 + (lang,flags) 缓存 key**（`ModelSingleton`）：重活只初始化一次的工程范式。

---

## ④ 对 PPT Engine 的落点（brief 输入解析层 + 部署成本）

**定位**：MinerU = PPT Engine **策略工作流的输入端解析层**。用户丢 PDF/Word/旧PPT 当 brief → MinerU 解析成 `content_list_v2.json`(结构化) + `nlp_markdown`(喂 LLM) → 进入后续「策略提炼 / deck 生成」管线。

**怎么接（两种重量）**：
- **轻接（推荐起步）**：只用 Office 路。`pip install mineru` 后直接调 `from mineru.backend.office.docx_analyze import office_docx_analyze`（pptx/xlsx 同理），传 file_bytes 拿 `middle_json` + 结构化结果。**纯 CPU、无模型下载、无幻觉、确定性**——解析用户上传的 .docx/.pptx/.xlsx brief 这条几乎零成本，且质量门可控（解析失败=报错而非瞎编，契合 fail-closed）。
- **重接（按需）**：要解析 PDF/扫描件 brief 才需要模型路。`pipeline` 后端纯 CPU 可跑（4GB 显存或 CPU），精度 86.47、无幻觉，适合"宁缺毋滥"的 brief 解析；要更高精度再上 `vlm`/`hybrid`（需 GPU 8GB+ 或挂远端 OpenAI 兼容服务走 `*-http-client`）。

**部署成本分级**（README §Local Deployment 表）：
- 纯 CPU 可行：`pipeline`、`*-http-client`、**全部 Office 路**。Python 3.10–3.13，Win/Linux/macOS(≥14.0)。
- 要 GPU：`vlm-engine`/`hybrid-engine`（Volta+ 架构 N 卡或 Apple Silicon，8GB 显存，RAM 建议 32G，磁盘 20G+ 装模型）。
- 集成形态丰富：CLI(`mineru -p in -o out`)、FastAPI、Gradio WebUI、Python SDK、**MCP Server**（README §Integration，可直接挂 Claude Desktop/Cursor）、Docker（仅 Linux/WSL2）。

**落点建议**：PPT Engine 第一步只吃 **Office brief**，直接复用 MinerU 的 `office_*_analyze` + `content_list_v2`，零 GPU、零幻觉、可单测、立刻能用；PDF/扫描件 brief 留作第二阶段，那时再决定本地 `pipeline` 还是挂远端 VLM。**这与本项目「收窄高 stakes、fail-closed」纪律完全对齐**——解析层确定性强、失败即报错，不会把"瞎编的 brief"污染下游。

---

## ⑤ License + 坑

### License（`LICENSE.md`，重要——非纯 Apache）

**Apache 2.0 + 附加条款**（自定义 `LicenseRef-MinerU-Open-Source-License`）：
1. **商用阈值**：可免费商用，但若你（及关联方合并口径）**MAU > 1 亿** 或 **月营收 > 2000 万美元**，必须另购商业授权。
2. **在线服务署名义务**：基于 MinerU 对外提供在线服务，必须在产品界面或公开文档**显著标注用了 MinerU**。
3. 违反 1/2 → 授权自动终止。
> 对 PPT Engine：当前体量远未触阈值，免费商用没问题；但**若把它做进对外在线服务，记得加"Powered by MinerU"署名**，否则违约。这条比纯 Apache 多了义务，必须留意。
> 另：贡献代码需签 CLA（`MinerU_CLA.md`）。模型权重另算——`PP-DocLayoutV2`/`PaddleOCR`/`unimernet` 等各有自己的 license，私有部署前要逐个核（README §License Information 也强调依赖各组件协议）。

### 坑 / 限制

- **官方只保「主线环境」**（README 醒目 WARNING）：硬件/软件组合多样，非推荐环境不保证 100% 可用，先读 FAQ。
- **Docker 仅 Linux/WSL2**，macOS 用户只能用 pip/uv 装（README §Docker）。
- **Windows 上 `ray` 不支持 Python 3.13**，Win 只能 3.10–3.12（README 脚注 4）；macOS 需 ≥14.0（脚注 5）。
- **复杂版面/扫描/手写仍可能翻车**（README §Quick Start 自承），官方建议先上在线 demo 评估再决定部署方式——**别假设它对任意 brief 都完美**，PPT Engine 接入时要给解析结果留人工核查口（它自带 layout/span 两种 bbox 可视化正是为此）。
- **VLM 路有"幻觉"风险**（README 表里 pipeline 特意标"no hallucination"作对比）：解析高 stakes brief 用 VLM 要警惕模型瞎补内容；`pipeline`/`hybrid` 更稳。
- **模型首次下载**：`vlm`/`pipeline` 要拉模型（HF/ModelScope，3.4 加了自动选源+本地缓存命中复用），首次联网+磁盘 20G+；Office 路无此坑。
- **依赖偏重**：`mineru[all]` 拉一堆（torch 系在 vlm extra 里）；只要 Office 解析的话，core 依赖里已含 `python-docx`/`openpyxl`/`pypptx-with-oxml`，不必装 `[all]`。

---

## 一句话：最值得偷的 1 件事

**偷它"统一中间表示（`middle_json` + `union_make`）把 N 种输入和 N 种输出彻底解耦"这套脊椎**——任何 brief 格式都先归一到一个细粒度 typed IR，再由一个 builder 分叉出"喂 LLM 的纯文本"和"带图表/HTML 的结构化 JSON"；新增格式不动下游、新增输出不动上游，扩展性和 fail-closed 质量门都最好落地。
