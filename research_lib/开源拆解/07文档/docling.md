# docling 拆解 · 文档→结构化（brief 解析层候选）

> 出处：`07_文档预处理/docling`（本地源码，本仓库为 `docling-slim` v2.107.0；上游 `docling-project/docling`，62k★，IBM Research Zurich）。License：**MIT**（`LICENSE`，纯 MIT 无附加条款）。
> 拆解日期：2026-06-30。所有结论标了文件:行号，便于复核。
> 与本目录 `MinerU` 是同一赛道（PDF/Office→结构化）的两个主选，最后一节做对比落点。

---

## ① 是什么 + 定位

**一句话**：把「各种文档格式 → 一个统一的、富结构的文档对象（DoclingDocument）」的解析引擎，再从这个对象导出 Markdown / HTML / JSON / DocTags 等。定位是 **gen-AI / RAG / Agent 工作流的输入端**（README:31、pyproject `description`）。

- **作者/背书**：IBM Research Zurich「AI for knowledge」团队（README:160），现挂在 **LF AI & Data 基金会**（README:154）。有 arXiv 技术报告（2408.09869）。production/stable（pyproject classifiers）。
- **输入格式覆盖很宽**（`datamodel/base_models.py:135-223` 的 `InputFormat` + 扩展名表）：PDF、DOCX/DOTX/DOCM、PPTX/POTX/PPTM、XLSX/XLSM、HTML、Markdown、CSV、AsciiDoc、EPUB、图片（png/tiff/jpg/webp…）、音频（wav/mp3→ASR）、LaTeX，以及一票应用级 XML schema（JATS 科研论文、USPTO 专利、**XBRL 财报**、DocLang）。
- **输出格式**：Markdown / HTML / 无损 JSON / DocTags / WebVTT（README:38）。导出由统一对象 `DoclingDocument` 提供，调用如 `result.document.export_to_markdown()`（`document_converter.py:443`）。
- **运行模式**：① Python SDK（推荐）② CLI（`docling <url/path>`）③ MCP server（接 agent）④ docling-serve API server（当服务跑）。可**完全本地、离线、air-gapped**（README:40）——对高 stakes / 敏感 brief 是硬卖点。

**关键定位差异（vs 通用 PPT agent）**：docling 不碰「生成」，只负责「把脏文档读成干净结构」。它是 PPT Engine 策略工作流的**上游零件**，不是竞品。

---

## ② 文档 → 结构化怎么做（核心机制）

### 2.0 架构总图：四层

```
DocumentConverter（总入口，按格式分发）
  └─ FormatOption：每种 InputFormat → 绑定一个 Backend + 一个 Pipeline
       ├─ Backend（读字节 → 抽原始元素 / 页面）   docling/backend/*.py
       └─ Pipeline（编排模型，把元素装成 DoclingDocument）  docling/pipeline/*.py
            └─ Stages / Models（版面、表格、OCR、富化…）   docling/models/stages/*
  └─ 产物：DoclingDocument（统一对象，来自外部包 docling-core）
```

> **DoclingDocument 本身不在本仓库**：本仓库只 `import`，统一文档模型 + 所有 `export_to_*` 逻辑在依赖包 **`docling-core>=2.84`**（pyproject:51）。本仓库负责「怎么把各格式塞进这个对象」。

### 2.1 ⭐ 最核心的架构智慧：两条流水线，按格式自动分流

`document_converter.py:107-207` 给每种格式绑了 pipeline，**只有两类**：

| pipeline | 绑定的格式 | 干什么 |
|---|---|---|
| **`SimplePipeline`** | DOCX / PPTX / XLSX / HTML / Markdown / CSV / AsciiDoc / ODT/ODS/ODP / JATS / USPTO / DocLang / XBRL | **声明式直转**：backend 自己 `.convert()` 直接吐出 DoclingDocument，**零 ML 模型、零推理、零 GPU** |
| **`StandardPdfPipeline`** | **PDF / Image / METS-GBS** | 重型：版面/表格/OCR 一串模型推理 |

`SimplePipeline` 全文就一句核心（`pipeline/simple_pipeline.py:38`）：
```python
conv_res.document = conv_res.input._backend.convert()
```
backend 必须是 `DeclarativeDocumentBackend`（`abstract_backend.py:66-86`，抽象方法只有一个 `convert() -> DoclingDocument`）。

> **这条分流是对 PPT Engine 最关键的一点**：Word/PPTX/HTML 的 brief 解析**根本不过模型**——纯结构解析，秒级、CPU、无模型下载。重型模型栈只在 PDF/扫描件才被触发。详见第 ④ 节。

### 2.2 Backend 体系（抽象基类 `abstract_backend.py`）

三种基类，决定了「要不要跑识别流水线」：
- `AbstractDocumentBackend`：根基，`is_valid()` / `supported_formats()` / `unload()`。
- `PaginatedDocumentBackend`：多页文档（PDF/TIFF），加 `page_count()` + 逐页访问。
- `DeclarativeDocumentBackend`：**能直接产出 DoclingDocument**（Office/Web/XML 全走这条），只需实现 `convert()`。

各格式 backend 文件大小已经能看出投入（`backend/` 下）：
- `msword_backend.py`（**110KB**，最重的 backend）——Word brief 的主力，见 ④。
- `html_backend.py`（185KB）、`opendocument_backend.py`（64KB）、`msexcel_backend.py`（50KB）、`mspowerpoint_backend.py`（35KB）、`md_backend.py`（28KB）。
- PDF 侧 backend 是「取页面像素 + 取 PDF 原生文字 cell」：`pypdfium2_backend.py`、`docling_parse_backend.py`（IBM 自研 `docling-parse`，给出词/行级 text-cell + bbox，供表格 cell-matching 用）。

### 2.3 ⭐ PDF 流水线：页级 5-stage 线程流水线 + 文档级富化

这是 docling「高级 PDF 理解」的核心（`pipeline/standard_pdf_pipeline.py`，整个文件 48KB，自带线程框架）。

**页级阶段（每个 stage 一条 daemon 线程 + 有界队列，stage 之间流水线并行，背压 + 显式 close 传播）**——串联在 `standard_pdf_pipeline.py:725-733`：

```
preprocess → ocr → layout → table → assemble
```
1. **preprocess**（`page_preprocessing`）：渲染页图、抽 PDF 原生 text-cell、归一化。
2. **ocr**（`do_ocr` 开关，默认 True）：只对需要的区域跑 OCR（扫描/图片区）。
3. **layout**（版面检测，见 2.4）：页图 → 一批带标签的 bbox（cluster）。
4. **table**（表格结构，见 2.5）：对 layout 标出的表格区跑 TableFormer。
5. **assemble**（`page_assemble`）：把 cell 文本回填进各 cluster，组装成页级元素。

> 并行实现细节：`ThreadedPipelineStage`（:216）每 stage 独立线程；`ThreadedQueue`（:149）有界队列、`put` 阻塞做背压、`close()` 向下游传播确定性终止；run-id 做并发隔离（同一 pipeline 实例可并发 `execute` 不串状态，文件头 docstring 1-14 行明确这是设计目标）。

**文档级阶段（页跑完后，在 DoclingDocument 上做）**：
6. **reading order**（`reading_order/readingorder_model.py`）：把跨页的所有 cluster 排成人类阅读顺序，建立列表/章节层级、合并被切断的元素（`_merge_elements`）、归类 caption/footnote/page-header/footer。**这是「输出按阅读顺序」的关键**，不是简单按坐标排序。
7. **富化栈 `enrichment_pipe`**（`standard_pdf_pipeline.py:621-655`，默认全关，按需开）：
   - **code+formula**（`code_formula` VLM）：代码块识别 + 公式 → LaTeX。
   - **picture classifier**：图片分类（流程图/照片/图标…）。
   - **picture description**：给图生成 caption/描述（可接本地 VLM 或远程 API）。
   - **chart extraction**：Barchart/Piechart/LinePlot **→ 表格 / 代码 + 描述**（README:56，「What's new」）。
   富化阶段统一走 `base_pipeline.py:111` 的 `_enrich_document`：对每个符合条件的 NodeItem 批量喂模型，机制是 `prepare_element` + `elements_batch`。

### 2.4 版面检测（layout）—— `models/stages/layout/layout_model.py`

- 用 IBM 自研 **`docling-ibm-models` 的 `LayoutPredictor`**（:56），对整批页图做 `predict_batch`（:182）。
- 输出每个 bbox 的 `label`（`DocItemLabel`）+ confidence + bbox，包成 `Cluster`（:205）。标签集很全（:29-47）：TEXT / SECTION_HEADER / PAGE_HEADER / PAGE_FOOTER / CAPTION / FOOTNOTE / LIST_ITEM / CODE / FORMULA / TABLE / DOCUMENT_INDEX / PICTURE / FORM / KEY_VALUE_REGION / CHECKBOX。
- **后处理是重点**：`LayoutPostprocessor(page, clusters, options).postprocess()`（:220）做去重/吸附/孤儿聚类（`create_orphan_clusters` 默认 True，`pipeline_options.py` LayoutOptions），同时回写 `page.cells`。
- **默认版面模型 = `DOCLING_LAYOUT_HERON`**（`LayoutOptions` docstring，`pipeline_options.py:1419` 附近）；想更准可换 `EGRET_LARGE/XLARGE`（`layout_model_specs.py:84-123`，全是 HF repo：`docling-project/docling-layout-heron` / `-egret-*`）。
- 顺手算页置信度：`layout_score` = cluster 平均 confidence，`ocr_score` = OCR cell 平均（:233-239）——**自带每页质量分**，对 fail-closed 门很有用（见 ③）。

### 2.5 表格结构（table）—— `models/stages/table_structure/`

这是 docling 的招牌能力之一，三套实现并存：
- `table_structure_model.py`（TableFormer V1，默认）、`_v2.py`、`_granite_vision.py`（VLM 版）。
- 核心模型 **TableFormer**（`docling-ibm-models`），输出 **OTSL 序列**（一种表结构标记语言，`otsl_seq`，:281）+ 单元格。
- **两个关键开关**（`pipeline_options.py:122-157`，`TableStructureOptions`）：
  - **`mode`**：`ACCURATE`（默认） / `FAST`。ACCURATE 更准更慢（推荐生产），FAST 给简单表/高吞吐（:93-107）。
  - **`do_cell_matching`**（默认 True）：把模型预测的格子**回贴到 PDF 原生 text-cell**（用 backend 给的词/行级 cell，:228-260）。开 = 文字保真（直接拿 PDF 里的真字）；关 = 让模型自己定文字（PDF cell 跨列合并时反而更稳）。注释原话见 :150-156。
- 表格区从 layout 的 TABLE/DOCUMENT_INDEX cluster 来；对每个表 crop 出图喂 TableFormer，回填进 `TableItem`。

### 2.6 另一条路：VLM 流水线（端到端大模型直出）

`pipeline/vlm_pipeline.py`（29KB）。**不走「版面+表格 N 个小模型」，而是一个视觉语言模型直接把页图 → DocTags / Markdown**：
- 默认模型 **GraniteDocling-258M**（IBM，`vlm_model_specs.py:22` `ibm-granite/granite-docling-258M`），还支持 SmolDocling-256M、各种 API VLM（vLLM / Ollama / 远程）。
- 多后端：HF Transformers / MLX（Mac 原生）/ vLLM / 远程 API（`vlm_pipeline_models/`）。
- `force_backend_text`（:114）：DocTags 模式下可选「文字仍从 PDF backend 按 VLM 给的 bbox 取」而非用 VLM 生成的文字——**保真 vs 省事的开关**。
- CLI 一键切：`docling --pipeline vlm --vlm-model granite_docling <pdf>`（README:88）。

> 对 PPT Engine：VLM 路线是「一个模型搞定一切」的省心路，但 258M 模型 + 推理，对极致版面/复杂表的可控性不如「小模型 + 强后处理」路线。brief 解析建议优先标准路线，VLM 当扫描件/疑难页的兜底。

---

## ③ 能借什么（可直接搬进 PPT Engine 的设计）

1. **⭐「两流水线按格式分流」的架构决策**：声明式格式（Office/Web）走零模型 `SimplePipeline`，只有 PDF/扫描件才上重型模型栈。**brief 解析层照抄这个分流**——Word/PPTX brief 纯解析、PDF brief 才调模型。这是省部署成本的关键设计，不是实现细节。
2. **统一中间对象 + 多导出（DoclingDocument 模式）**：先把任何输入解析成一个富结构对象，再从它导出 Markdown/JSON/DocTags。PPT Engine 的 brief 解析层应同样产出**一个结构化中间对象**（章节树 + 表格 + 图 + provenance），喂给下游策略层，而不是直接吐字符串。
3. **provenance（出处）贯穿到元素级**：每个元素带 `ProvenanceItem`（page_no + charspan + bbox，如 `mspowerpoint_backend.py:159`）。**brief 里每条事实可溯源到原文哪页哪块**——正好接 PPT Engine 的 fail-closed / 防假绿纪律（哪句话来自 brief 哪里，可审）。
4. **自带每页质量分**（`layout_score` / `ocr_score`，layout_model.py:233）+ 结构化错误模型（`ErrorItem` + `FailureCategory`，standard_pdf_pipeline.py:80-106；`is_partial_success` / `is_complete_failure`，:140-146）。**直接当 brief 解析的准入门**：解析置信度低于阈值就拦下让人确认，不带病进策略层。
5. **`do_cell_matching` 思路（结构 vs 原文保真的显式开关）**：表格既要结构又要原字——把「模型结构 + 回贴原始文字」做成可切开关，是处理高 stakes 数字表（财报/咨询数据）的正解，避免模型把数字读错。
6. **页级线程流水线框架**（`ThreadedQueue` + `ThreadedPipelineStage` + run-id 隔离）：若 PPT Engine 要批量解析多份 brief / 多页并行，这套有界队列 + 背压 + 确定性 close 的实现可参考（standard_pdf_pipeline.py:149-370，自包含、无外部依赖）。
7. **模块化 extras 安装**（pyproject `optional-dependencies`）：base 仅 ~50MB / 8 包，按需 `[format-office]` / `[format-pdf,models-local]` / `[feat-ocr-rapidocr]`。**PPT Engine 集成时只装需要的格式 extra**，不背整包。

---

## ④ 对 PPT Engine 的落点：当 brief 解析层，docling vs MinerU 怎么选

> 背景：PPT Engine 策略工作流输入端要解析 **PDF / Word brief**。本目录两个主选 docling 与 MinerU 在同赛道。

### 关键事实对照

| 维度 | **docling** | **MinerU** |
|---|---|---|
| License | **MIT**（无附加条款，`LICENSE`） | **Apache-2.0 + 附加商业阈值条款**：规模超阈值须另购商业授权，违反则授权自动终止（`MinerU/LICENSE.md` §1） |
| 出身 | IBM Research，LF AI & Data 基金会 | OpenDataLab（上海AI实验室）|
| 输入广度 | 极宽：PDF/Office/HTML/MD/EPUB/音频/LaTeX/JATS/USPTO/**XBRL财报** | PDF/DOCX/PPTX/XLSX/图片/网页（`MinerU/README.md`）|
| **Office 解析路径** | **DOCX/PPTX/XLSX 走零模型 `SimplePipeline`**（纯结构解析，CPU·秒级·无模型下载） | 同样原生支持 DOCX/PPTX/XLSX 解析 |
| PDF 路线 | 双路：①小模型栈（版面 Heron + 表 TableFormer + OCR）②VLM（GraniteDocling-258M） | VLM + OCR 双引擎，109 语言 OCR；强项扫描件/手写/跨页表合并 |
| 部署成本（最小） | base ~50MB / 8 包；Office-only 不下任何模型；PDF 才下版面/表格模型（HF） | 偏重：VLM/OCR 引擎 + 模型权重，GPU 友好；主打高精度，对国产 AI 芯片适配好 |
| 自带质量分/出处 | ✅ 每页 layout/ocr score + 元素级 provenance + 结构化错误模型 | 文档未在本地核到等价的元素级置信度门（需进一步核 MinerU 源码再断） |

### 结论（落点建议）

**brief 解析层主选 docling**，理由按 PPT Engine 纪律排序：

1. **License 干净（决定性）**：docling 纯 MIT，商用/再分发零负担。MinerU 的 Apache-2.0 **带规模商业阈值附加条款**——一旦 PPT Engine 商业化到阈值就有授权风险，且「违反即自动终止授权」。对一个要验证可复制、可能商业化的 Engine，这是硬约束。
2. **多数 brief 是 Word/PDF 文档而非扫描件**：docling 的 Office→`SimplePipeline` 零模型直转，**部署成本极低**（不下模型、CPU、秒级、可离线）。这正好压在 PPT Engine「策略工作流输入端」最常见的形态上。MinerU 的强项（扫描件/手写/109 语言 OCR）对「咨询/投资人 brief」是 overkill。
3. **fail-closed 友好**：docling 自带每页质量分 + 元素级 provenance + 结构化错误分类，能直接接 PPT Engine 的防假绿 / 准入门——解析不确定就拦，且每条事实可溯源回 brief 原文。
4. **air-gapped**：高 stakes brief 常涉敏感数据，docling 明确支持完全本地离线，符合「敏感数据本地执行」诉求。

**何时用 MinerU 兜底**：brief 是**扫描件 / 拍照 PDF / 多语言（尤其中文扫描）/ 复杂跨页大表**时，MinerU 的 OCR + 跨页表合并更强，可作为 docling 的降级兜底引擎。但默认主路是 docling。

> 注：MinerU 这里只取了「定位 + license」级事实（来自其 README/LICENSE），未深拆其源码；若要把 MinerU 正式定为兜底引擎，建议后续单独拆 `07_文档预处理/MinerU` 源码，核其置信度/出处机制再定。

---

## ⑤ license + 坑

- **License = MIT**（`LICENSE`，Copyright IBM 2024）。代码可商用/改/再分发，无附加条款。
  - ⚠️ 但 **模型权重各自有 license**：README:151-152 明确「individual model usage 看原包的 model license」。版面模型（docling-layout-heron/egret）、TableFormer、GraniteDocling-258M 等是单独的 HF 仓库，**集成前要逐个核模型权重的 license**，别假设全是 MIT。
- **坑 / 注意点**：
  1. **DoclingDocument 不在本仓库**：核心数据模型 + 所有 `export_to_*` 在依赖包 `docling-core`（pyproject:51）。要看「结构化对象长啥样 / 导出细节」得去那个包，本仓库查不到 class 定义（已确认 `grep "class DoclingDocument" docling/` 为空）。
  2. **PDF 路线要下模型 + 装重 extra**：`format-pdf` + `models-local` 才有版面/表格能力，首次跑会从 HF 下载权重（沙箱/离线环境需预置 `artifacts_path`，`layout_model.py:66` 支持指定本地模型目录）。本项目沙箱**禁网**（见 MEMORY git/Clash 坑），集成时必须先离线把模型 cache 好。
  3. **本仓库是 `docling-slim`**（模块化版，包名 `docling-slim`），不是大包 `docling`。功能等价但**安装要带 extras**（`pip install docling-slim[format-pdf,models-local,...]`），漏装 extra 会在运行时报「backend 不支持」。便利包 `standard` extra ≈ 完整 `docling`（pyproject:263）。
  4. **OCR 引擎默认随 `standard` bundle 是 rapidocr**（`standard` extra 含 `feat-ocr-rapidocr`，pyproject:263）；easyocr/tesseract/ocrmac 要另装对应 extra（`feat-ocr-easyocr` 等，pyproject:171-197）。Mac 上 `feat-ocr-mac` 用系统 Vision 框架最省事。
  5. **VLM 路线对硬件挑剔**：GraniteDocling 推理在 CPU 上慢；Mac 走 MLX、有 GPU 走 vLLM 才舒服。当成兜底而非主路。
  6. **表格 `do_cell_matching` 双刃**：默认 True 拿 PDF 原字最准，但注释明说「PDF cell 跨列合并时会把表搞乱」（:151-153）——遇到合并单元格多的复杂表，可能要关掉它让模型自己定文字。高 stakes 数字表建议两种都跑比对。

---

## 一句话：最值得偷的 1 件事

**「按格式自动分两条流水线」**——声明式格式（Word/PPTX/HTML/MD）走零模型 `SimplePipeline`（backend 直接 `.convert()` 吐统一对象，CPU·秒级·零模型下载），只有 PDF/扫描件才触发重型版面+表格+OCR 模型栈。PPT Engine 的 brief 解析层照这个分流抄，就能让最常见的 Word/PDF brief 解析几乎零部署成本，把重型推理省到只在真正需要时才花。
