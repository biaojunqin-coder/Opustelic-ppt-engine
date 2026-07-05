# banana-slides 深拆笔记

> 项目：`../PPT开源参考/01_AI端到端应用/banana-slides`（15.1k★ · **AGPL-3.0** · Vibe PPT · nano-banana-pro 生图）
> ⚠️ 本笔记由主 agent 异常中断后、据其 2 个子 agent 的源码级提炼整理落盘（带文件:行号出处）。
> 定位：**生图型** deck 工具——整页是 AI 生成的 PNG（死图），与本项目「python-pptx 原生可编辑」**主路线相反**；但它的「**可编辑 PPTX 逆向导出**」机制对"用户丢张图当模板"场景有借鉴价值。

## 一、怎么做 deck（生图为主）
- **三入口**（`project_controller.py`）：`idea`(一句话) / `outline`(大纲解析) / `descriptions`(逐页描述)，统一收敛到 **大纲 → 逐页描述 → 逐页生图** 流水线。
- **逐页生图**：每页产「标题+要点+一段极详尽 `visualDescription` 画面描述」→ 当生图 prompt 主体 → nano-banana 出整页 PNG。**文字嵌在图里、不可直接编辑**（死穴）。
- **编排**：纯 **in-memory ThreadPoolExecutor**（`task_manager.py`，无 Celery/Redis，默认 `MAX_WORKERS=16`）+ `ResourceLimiter("image"/"text", capacity=20)` 限流外部 API + `TaskManager` 跟踪 `task_id→Future`；状态机 `PENDING→PROCESSING→COMPLETED/FAILED`；前端**轮询** + 部分步骤 **SSE 流式**。
- **风格/内容正交**（值得偷）：11 套主题各一段 prompt 字符串（`lib/themes.ts`），换风格=换一段描述文本、内容代码一行不动。

## 二、★可编辑 PPTX 导出：把 PNG 逆向成可编辑（最有价值）
入口 `export_service.py:create_editable_pptx_with_recursive_analysis()`。六步把一张 AI 生成的 PNG「逆向」成可编辑 PPTX：
1. **版面分析**（`image_editability/extractors.py`）：默认 **MinerU**（转 PDF 再解析）或 Hybrid（+百度高精 OCR）→ 出 `elements=[{bbox,type,content,...}]`（text/image/table/title/equation）。
2. **坐标映射**（`coordinate_mapper.py`）：局部 bbox → 全局 bbox → 幻灯片 EMU（缩放+平移）。
3. **Inpaint 清背景**（`inpainting_service.py`）：火山/百度/Gemini 三后端，把文字/图抠掉得「干净背景 PNG」。
4. **样式识别**（VLM 混合）：全局识别 bold/italic/align + 单元素裁剪识别 font_color → `TextStyleResult`。
5. **分层重建**（`pptx_builder.py`）：干净背景铺底 + 浮层**可编辑文本框**（**二分查找**最大可放入 bbox 的字号；LaTeX 尝试转 OMML 原生公式）。
6. **递归深化**：表格/图表内部再分析一层。
- **依赖一堆付费视觉 API**（MinerU/火山 Inpaint/百度 OCR/Gemini），`fail_fast` 兜底（失败用默认样式/原图）。

## 三、质检（基本 fail-open）
分辨率校验只 `warning` 不阻断 · DB 事务重试（指数退避）· 单页失败标 FAILED 不回滚 · **无内容/质量硬闸**。→ 又一个「防假绿」反面坐标。

## 四、对 PPT Engine 的落点
- **路线对立、思路互补**：它「**图片→可编辑**」（逆向·依赖付费视觉 API·质量看 Inpaint），我们「**数据→可编辑**」（python-pptx 正向·确定性·不依赖外部 API·咨询级精确）。**主路线仍走正向**；但它的「**分层重建=干净背景铺底 + 浮层可编辑文本框 + 二分查找字号**」在"**用户丢一张参考图/竞品截图当模板**"场景可借鉴（我们届时也要做图→结构）。
- **可偷**：① in-memory `ThreadPoolExecutor + ResourceLimiter` 轻量编排（批量生成限流）② 风格/内容正交解耦 ③ 二分查找字号塞 bbox（文本框自适应）④ LaTeX→OMML 原生公式路径。
- **反面教材**：生图死图不可编辑（主产物）+ 质检 fail-open。

## 五、license + 坑
- **AGPL-3.0** ⚠️：强 copyleft，**借思想/架构、绝不抄码进我们仓库**。
- 坑：可编辑导出依赖 MinerU/火山/百度/Gemini 一串付费 API（咨询客户内网难落地）；生图不可复现；质检 fail-open 报"成功"但可能残缺。
