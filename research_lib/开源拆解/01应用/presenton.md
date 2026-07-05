# presenton 深拆笔记

> 出处：`01_AI端到端应用/presenton`（本机克隆）
> 标签：8.6k★ · Apache-2.0 · 最成熟的自托管 AI PPT 应用 · 内置 MCP + REST API
> 拆解视角：PPT Engine = 咨询级 deck（策略+制作两工作流 · python-pptx 原生可编辑 · fail-closed · 防假绿）。本笔记**保真带出处、不掺常识**，所有"它怎么做"均有源码行号。

---

## 一句话：最值得偷的 1 件事

**「Zod schema 即 LLM 契约、TSX 组件即渲染器，二者同住一个文件」**——每个版式 = 一份带 `.max(字符数)`/`.describe()`/`.default(样例)` 的 Zod schema（喂给 LLM 的硬约束）+ 一个吃 `Partial<z.infer<Schema>>` 的 React 组件（出像素）。LLM 永远只填结构化字段、碰不到排版，溢出靠 schema 的 maxLength 在生成时就被掐死。这套「字段级长度契约」正是 PPT Engine 在 python-pptx 世界里最缺、且能平移的东西（见 §4 落点①）。

---

## ① 是什么 + 定位

- **端到端 AI 演示生成器 + API**，自我定位为 Gamma / Canva / Beautiful AI / Decktopus 的开源平替（README L18）。卖点三连：无 SaaS 锁定、自带模型选择权、数据自托管（README L26）。
- 三种跑法：① Docker 一条命令（`ghcr.io/presenton/presenton`，端口 5001→80，README L208）；② Electron 桌面 app（Mac/Win/Linux）；③ Presenton Cloud 托管。
- **产物形态**：可编辑 PPTX + PDF，README 反复强调 "**Fully editable PPTX export**"（L36）——但**实现路径与 PPT Engine 完全相反**（见 §2 导出）。
- 仓库结构：`servers/fastapi`（Python 后端，约 90 个 .py） + `servers/nextjs`（前端 + 模板 + 导出渲染页） + `electron`（桌面壳）。

## ② 它怎么做 deck（核心）

### 底座 = HTML/Tailwind/React 模板，**不是 python-pptx**
- 每个"版式"是一个 React/TSX 组件，路径 `servers/nextjs/app/presentation-templates/<主题>/<版式>.tsx`。已内置主题：`general / modern / standard / swift / pitch-deck / Code / Education / Report / ProductOverview / neo-*` 等十几套，每套含 10~16 个版式组件。
- **关键模式（样例：`neo-modern/TitleKpiSnapshotGrid.tsx`）**：一个文件里同时导出
  - `Schema`：Zod object，**每个 string 字段带 `.max(30)`、每个 array 带 `.max(8)`、每字段 `.describe('...')`、整体 `.default([...样例数据])`**；
  - `layoutId` / `layoutName` / `layoutDescription`：纯文字描述，喂给 LLM 做版式选择；
  - `dynamicSlideLayout`：`React.FC<{ data: Partial<z.infer<typeof Schema>> }>`，所有字段都 optional-chaining 取（`data?.kpiCards?.map`），颜色全走 CSS 变量 `var(--background-color,#FFF)` / `var(--card-color,...)`——主题换肤靠覆盖 CSS 变量，不改组件。
- 后端只看 schema、不看组件：`PresentationLayoutModel` / `SlideLayoutModel`（`servers/fastapi/templates/presentation_layout.py`）只存 `id/name/description/json_schema`，`to_string()`（L46）把所有版式拼成 markdown 喂 LLM。

### 叙事/生成分几步（源码 = `api/v1/ppt/endpoints/presentation.py::generate_presentation_handler` L723-1084）
1. **大纲（outline）** `utils/llm_calls/generate_presentation_outlines.py`：一次 LLM 调用，**流式**出 JSON `{title, slides:[{content: markdown}]}`。system prompt（L93-126）要点：每页 markdown 必有 `## 标题`、首页标题=演示标题、verbosity 控字数（concise≈20 / standard≈40 / text-heavy≈60 词，L61）、"一页一论点、拆过载话题、建从引言到结论的连贯叙事、禁重复填充"。**支持 web_search 接地**（native / searxng / tavily / exa，把搜索结果当 untrusted context 注入）。用 `dirtyjson` 容错解析（L817）。
2. **结构（structure）= 给每页选版式** `utils/llm_calls/generate_presentation_structure.py`：第二次 LLM 调用，输入"所有版式 markdown + 各页大纲"，输出 `[0,1,2,...]` 版式索引数组。两套 system prompt：
   - 通用版（L60）：内容驱动选版式（开场/结尾→标题版式、流程→流程版式、数据→图表版式…），强制"相邻页版式不同、追求视觉多样"。
   - slides_markdown 版（L16）：偏表格/图表判定规则（含表格→选 table/graph 版式、n 列数据→选支持 n-1 个图表的版式）。
   - **若版式集是 `ordered`（如 pitch-deck 固定流程）则跳过 LLM、直接顺序映射**（L893）。
   - 出来的索引会做边界净化：越界的 index 用 `random.randint` 兜底（L906-912）——**注意：兜底=随机版式，无 fail-closed 重试**。
3. **逐页填内容** `utils/llm_calls/generate_slide_content.py`：对每页第三次 LLM 调用，把该版式的 `json_schema`（剔掉 `__image_url__`/`__icon_url__`，加 `__speaker_note__` 100~500 字）作为 strict JSON schema 输出契约。**批量并发**：每批 10 页 `asyncio.gather`，且"本批资产抓取与下一批 LLM 生成并行"（L976-1030）。
4. **资产（图/图标）** `process_slide_and_fetch_assets`：图标走本地语义检索（fastembed），图片走 IMAGE_PROVIDER（DALL-E / Gemini Flash / Pexels / Pixabay…）。失败只记 warning、不阻断（L460）。
5. **导出**（见下）。

### 导出机制 —— **HTML → 无头浏览器 → PDF/PPTX（与 PPT Engine 路线相反）**
- `utils/export_utils.py`：拼一个 URL 指向 Next.js 的 `/pdf-maker?id=...` 页面（L34），把当前 deck 用真实 React 组件渲染成网页。
- `services/export_task_service.py::export_from_url`（L369）：**spawn 一个 Node 子进程**（`presentation-export/index.cjs`），子进程用 **Puppeteer（无头 Chrome）** 加载那个 HTML 页 → 截成 PDF；PPTX 则由随包预编译的 **Python `convert` 二进制**（`py/convert-<platform>-<arch>`，L132-147）处理。
  - 注：`presentation-export/` 与 `convert` 二进制**不在本仓库源码里**，靠 `scripts/sync-presentation-export.cjs` 从别处同步——**PPTX 的真正转换逻辑是闭源/外置的**，本仓库看不到。
- `from pptx import Presentation` 在整个 fastapi 里**只出现一处**：`templates/pptx_font_utils.py`——且只用于**读取**用户上传 PPTX 里的字体（做"从 PPTX 生成模板"用），**不参与 deck 生成**。
- ⚠️ **推断（PPT Engine 已记录的硬伤）**：HTML 底座导出 PPTX 普遍是"文字转图片、不可选"。Presenton 用预编译 `convert` 二进制是否真做到原生可编辑文本框，**本仓库无法证实**（转换器闭源）。README 宣称 "fully editable" 需实测验证，别照搬其结论。

### 「从现有 PPTX 反向生成模板」(AI Template Generation) —— 真亮点
- 入口 `extract_schema`（`export_task_service.py` L511）+ `convert_pptx_to_html`（L403）：上传 PPTX → 转 HTML/图 → 喂多模态 LLM。
- prompt 在 `templates/prompts.py::SLIDE_LAYOUT_CREATION_SYSTEM_PROMPT`，**写得极其工程化、可直接借鉴**：
  - 先把元素分"装饰元素 vs 内容元素"（装饰=箭头/线/背景/logo，原样保留 URL；内容=标题/正文/图表/有意义的图标）；
  - 图片字段强制替换成占位 `/static/images/replaceable_template_image.png`、图标换 `/static/icons/placeholder.svg`；
  - **schema 字段名禁用业务词**（不许 budget/market/revenue/workflow，只许 title/description/heading/image/table…）——保证模板可复用、不被原始内容污染；
  - **每个 string 字段必须 `.max(实际字符数)`、每个 array 必须 `.max(实际项数)`**（L 在 "String and Array Field Rules"）；
  - 固定 1280×720、**禁用 absolute 定位**（必须 flex/grid/gap，列表要能变长居中）；图表用 Recharts。
- 生成后过校验闸 `templates/layout_code_validation.py::validate_layout_code`：POST 到 Next.js `/api/validate-layout-code` **真编译 TSX/Zod**，编不过返回 line/column 报错——**这是个客观、非 LLM 自评的硬闸**（对应 PPT Engine "防假绿"思路，见 §4 落点④）。

### MCP / API 怎么暴露
- **MCP**：`mcp_server.py` 用 `FastMCP.from_openapi(openapi_spec)` **从一份精简 OpenAPI spec 自动生成 MCP server**（不是手写 tool）。那份 `openai_spec.json` **只暴露 2 个工具**：`POST /api/v1/ppt/presentation/generate` 和 `GET /api/v1/ppt/template/all`。即：对外只给"生成整份 deck"+"列模板"，不暴露细粒度编辑。
  - MCP 跑 HTTP transport（默认 8001），转发到内部 FastAPI（127.0.0.1:8000）。auth 走 bearer token（登录拿 session token），Electron 桌面版**禁用 MCP**（避免 auth 冲突，mcp_server.py L42-44）。
- **REST API**：主端点 `POST /api/v1/ppt/presentation/generate`（README L492），HTTP Basic auth。请求体含 `content / slides_markdown / instructions / tone / verbosity / web_search / n_slides / language / template / include_title_slide / files / export_as`。有同步 + 异步（`/generate/async` + `/status/{id}` 轮询，L1135）+ webhook（成功/失败回调）。返回 `{presentation_id, path, edit_path}`。
- **内部聊天式编辑**（前端 chat，非对外 API）：`services/chat/tools.py` 定义了 17 个细粒度 LLM tool（`getPresentationOutline / searchSlides / getSlideAtIndex / saveSlide / deleteSlide / setPresentationTheme / generateAssets / getContentSchemaFromLayoutId`…）。**`saveSlide` 有"服务端按 schema 校验、超 maxLength 返回 `saved:false + validation_errors` 让 LLM 缩短重试"的闭环**（tools.py L192-201）——这是它"对话改稿"的质量门。

## ③ 能借什么

| 可借物 | 在哪 | 怎么用于 PPT Engine |
|---|---|---|
| **字段级长度契约**（Zod `.max(N)` per field/array + `.describe` + `.default`） | 模板组件 + `prompts.py` 生成规则 | 平移成 python-pptx 文本框的"字符上限/行数上限"硬约束，喂给内容生成 LLM（见落点①） |
| **三步流水线**（outline→structure→content）+ **每步独立 LLM 调用 + strict JSON schema** | `utils/llm_calls/*` | 与"策略工作流→制作工作流"天然对齐；structure 那步"喂全部版式描述让 LLM 选"可直接借 |
| **"从 PPTX 反推模板"的 prompt 工程** | `templates/prompts.py` | 装饰/内容二分 + 字段名去业务化 + 占位符替换，是"范本库扩充"的现成方法论（对接 Mck-ppt-design-skill 70 版式） |
| **TSX 真编译校验闸**（非 LLM 自评） | `layout_code_validation.py` + Next `/api/validate-layout-code` | 对应"编译层 fail-closed"（与 Auto-Slides 的 LaTeX 编译闸同构）；PPT Engine 可设"python-pptx 真能 open 且页数/字段齐"的二值闸 |
| **saveSlide 校验-重试闭环** | `services/chat/tools.py` | 改稿时"超限→返错→LLM 缩短→重存"，是防溢出的可借模式 |
| **多 LLM provider 抽象** | 依赖包 `llmai`（vendored，**不在本仓库源码内**）+ `utils/llm_config.py` | 支持 14 家 provider（openai/anthropic/google/vertex/azure/bedrock/deepseek/ollama/lmstudio/…）。抽象本体看不到源码，只能借"配置项设计"不能直接抄代码 |
| **自托管架构样板** | `docker-compose.yml`(21KB) + `Dockerfile` + `nginx.conf` + `start.js` | fastapi + nextjs + nginx + 本地 Qdrant/SQLite(Mem0) 的一体化打包，是"真能力做成可部署服务"的参考 |
| **异步生成 + webhook + 状态轮询** | `presentation.py` `/generate/async` | deck 生成耗时长（MCP timeout 设 600s），这套异步骨架可借 |

## ④ 对 PPT Engine 的落点

**① 偷"字段级长度契约"，但落进 python-pptx 而非 HTML（最高优先）**
Presenton 靠 Zod `.max()` 在生成时就掐死溢出，这正是 PPT Engine 当前空白。落法：制作层每个版式定义一份"字段 → (max字符, max行, 占位)"契约表，喂内容 LLM 当 strict 输出约束 + 渲染后做客观校验。**这是能直接平移、且最补短板的一件事**。

**② 它的路线选择反向印证了 PPT Engine 的铁律（不是要学、是要确认分野）**
Presenton = HTML/React → Puppeteer → 导出；PPT Engine 已立铁律 = python-pptx 原生可编辑（`研究层资源地图` §2-3）。两者根本对立：HTML 底座做"通用好看 deck"快，但**导出 PPTX 文字可编辑性存疑、且做不出 waterfall/Mekko/Gantt 原生图表**（PPT Engine 收窄的高 stakes 段）。结论：**Presenton 的渲染/导出栈不可照搬**，只偷它的"内容契约 + prompt 工程 + 校验闸架构"。

**③ 三步流水线可直接映射到两工作流，且 structure 那步是现成的**
outline（叙事）→ structure（选版式）→ content（填字段）。其中 **structure 步"把所有版式描述拼成 markdown 喂 LLM、输出索引数组"** 可几乎原样借给制作工作流的"版式选择"。但要补 Presenton 缺的：它选错版式只用 `random` 兜底、**无 fail-closed 重试**——PPT Engine 这里恰恰要做成"选不出/越界=返工"。

**④ 校验闸架构正面可借，但要补"内容层"那道闸**
Presenton 有两道客观闸：TSX 编译闸（生成模板时）+ saveSlide schema 校验闸（改稿时）——都不靠 LLM 自评，符合 PPT Engine "别让 LLM 既当运动员又当裁判"（与 `02架构/Auto-Slides.md` §2 结论一致）。**但 Presenton 在内容质量层是 fail-open**（资产失败只 warning、版式越界随机兜底、大纲页数不符才报错且只重试不阻断）。PPT Engine 要做的"一页一论点/action title/叙事不断档"这类**内容层硬闸，Presenton 没有**——这是 PPT Engine 的差异化空间。

**⑤ MCP "只暴露 2 个粗粒度工具" 是个值得对照的取舍**
Presenton 对外 MCP 只给"生成整份 deck"，把 17 个细粒度编辑工具留在内部 chat。PPT Engine 设计对外接口时可参考这个"粗粒度对外、细粒度内用"的分层，避免把易出错的细粒度编辑直接暴露给外部 agent。

## ⑤ License + 坑

- **License = Apache-2.0**（`LICENSE` 确认；README L13、L139）。**可商用、可改、可闭源分发**，只需保留版权/NOTICE + 声明改动。代码与 prompt 工程**可放心借鉴**。
- `NOTICE` 巨大（26825 行）= 打包了海量第三方依赖的归属声明；若直接 fork 需连带遵守这些子依赖的 license。
- **坑 1（最大）：PPTX 转换器闭源/外置**。`presentation-export/` 的 Node runtime 和 `convert` 二进制不在仓库里（靠 sync 脚本拉），**deck→PPTX 的真正实现看不到源码**。"fully editable PPTX" 是 README 宣称、本仓库无法证实——**别照搬其"已解决"结论，必须自己实测导出文件文字是否可选**。
- **坑 2：核心多 LLM 抽象 `llmai` 是 vendored 依赖、不在源码树**。`from llmai import get_client` 到处用，但包本体不在本克隆里——能学配置项设计，**不能直接抄抽象层代码**。
- **坑 3：内容质量层整体 fail-open**。版式越界→random、资产失败→warning、structure 选错→无重试。**作为"产物质量"参考是反面教材的一半**（校验闸架构正面、内容层兜底反面），别误以为它的质量门完整。
- **坑 4：默认依赖一堆外部服务**（Mem0+Qdrant 做每-deck 记忆、fastembed 做图标检索、spaCy、LiteParse 文档解析、各 IMAGE_PROVIDER）。自托管"全家桶"重，借单点能力时注意别把整套依赖拖进来。
- **坑 5：Electron 桌面版功能阉割**（禁 MCP、`DISABLE_AUTH=true`）——若参考"桌面 app 形态"，注意它和 server 版能力不对等。
