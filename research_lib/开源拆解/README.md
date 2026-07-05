# 开源拆解 · 总索引（40 项目深拆）

> 拆 `../../../PPT开源参考/` 的 40 个开源项目，提炼对 PPT Engine 的料（每篇笔记保真带出处）。本文 = 一句话"最值得偷 + 落点"总览。
>
> **反复撞见的两条元结论**：
> 1. **防假绿是护城河**：拆到的应用**几乎全部缺"内容/数字质量硬闸"**（fail-open / LLM 判 LLM / 生成即标 success）——我们「🟢必须人工自测 + fail-closed 机检」是差异化主场。
> 2. **难图算法已备齐**：waterfall/Gantt 拆出完整算法、Mekko 缺的列宽公式也找到 → 见 [`06_高stakes难图实现`](../../specs/PPT方法论/06_高stakes难图实现.md)。

## 01 AI 端到端应用（10 · `01应用/`）
| 项目 | 最值得偷 / 定位 |
|---|---|
| ⭐⭐ ppt-master | **11390 行 MIT 纯 Python SVG→DrawingML 引擎 + 71 SVG 图表(含 waterfall/Gantt) + fail-closed 黑名单质检门 → 制作层现成轮子(战略决策)** |
| presenton | Zod schema 字段级长度契约(溢出生成时掐死) |
| PPTist | custGeom 矢量导出(SVG path 降 M/L/C/Z 保可编辑) + AI_PPT_SCHEMA 分两层 |
| AiPPT | 图表数据契约 = OOXML 内嵌 xlsx 镜像(excelData+公式串) |
| presentation-ai | 「生成≠批准」两段式状态机 + LangGraph interrupt + Compare 取舍 |
| LandPPT | 双步确认门(大纲/模板 生成与确认分离) |
| slide-deck-ai | 页型分派器骨架(handler 链短路·可插难图) |
| banana-slides | 可编辑 PPTX 逆向(PNG→MinerU 版面分析→Inpaint→重建) |
| pptmaker | 生图死图反面教材 + 风格/内容正交解耦 |
| (PPTAgent) | 见 03 策略明珠(PPTEval 已填 05 质量门) |

## 01b 待深看 skill（3 · `01b待深看/`）
| frontend-slides | 三级渐进披露(L0索引→L1卡→L2配方)+ token 预算倒逼别全读 |
| guizang-ppt-skill | 质量门=110 行静态正则校验器(exit1 真 fail·零 LLM 打分) |
| huashu-design | 「选择无效铁律」并行出 3 个真实候选让用户选(策略层可移植) |

## 02 Agentic 架构（3 · `02架构/`）
| ppt-agent-skills | 三段式质量门(机器断言+截图存档+人复检)+ svg2pptx 轮子 |
| Auto-Slides | 「程序先验证数字、LLM 不准推翻」+ Verify 写了没接=fail-open 反面教材 |
| Talk-to-Your-Slides | 「编辑 PPT = 对象树最小受控 diff」→ 制作层骨架 |

## 03 策略明珠（料已填方法论 00-05 · `03策略/` 仅 gist 在 `../PPT开源参考/`）
enterprise-ai-skills(麦肯锡 13 skill·金字塔/MECE/Storyline) · issuetrees(SCQA/议题树/假设树) · 2 gist(三道审查门+13 故事框架) · Mck-skill(70 版式+BLOCK_ARC) · PPTAgent(PPTEval 三维)。→ 全部已提炼进 [00-05 方法论](../../specs/PPT方法论/)。

## 04 制作底座（4 · `04制作/`）
| python-pptx | **制作层定的原生底座**(可编辑 pptx)·原生 chart 不支持高级图表(`cx:chart` Issue#583)→ 难图必走 custGeom 自绘 |
| PptxGenJS | createExcelWorksheet 手搓内嵌 xlsx 范本·原生图表同 python-pptx 上限·验证维持 python-pptx 决策 |
| Instrumenta | **Slide Grader fail-closed PPT Linter(38 项分级+自动修白名单)+ 旋转感知真实包围盒** → 制作层/自省层该长的肌肉 |

## 05 图表库（6 · `05图表/`）→ 汇总进 [06 难图实现](../../specs/PPT方法论/06_高stakes难图实现.md)
| highcharts | 商业 license·**Variwide=Mekko 列宽公式 relZ/totalZ×轴长**(自研缺的几何) |
| d3 | stack `[y0,y1]+offset` 统一瀑布/Mekko/堆叠的「算区间」内核 |
| plotly.js | waterfall measure 数组+previousSum(用户填增量引擎算坐标)·Mekko 放弃 |
| echarts | waterfall 通法=堆叠柱+透明占位段隐形 |
| frappe-gantt | Gantt 线性映射公式(日期→像素)·里程碑需自建 |
| plotlyPowerpoint | 桥接=图片化反面教材·声明式 dict schema 可偷 |

## 06 调研 agent（3 · `06调研/`）
| gpt-researcher | 「深度研究=标准研究递归套娃」(子查询起新实例·breadth 逐层砍半)·fact-check 是 LLM 自评不能当 🟢 |
| open_deep_research | LangGraph 多 agent 显式编排(待深化) |
| Perplexica(已改名 Vane) | extractor「数字完整性铁律」prompt(基准/数字原值照抄绝不概括)·偷零件不偷整机 |

## 07 文档预处理（2 · `07文档/`）
| MinerU | 统一中间表示 middle_json 解耦 N 入 N 出·OOXML 图表抠数据非截图·Apache2+附加条款 |
| docling | IBM 文档解析(待汇总细节) |

## 08 素材库（4 · `08素材/`）
| tabler-icons | 6146 图标 MIT·filled 子集 1053 个单一闭合路径可直喂 custGeom |
| lucide | 1744 图标 ISC·100% 同规格·currentColor 一改换主题色 → 默认线性图标底座 |
| open-color | 130 数据色(跨色相同档对齐)·补多系列图表·主色/语义走麦肯锡 |
| Awesome-PPT-Design-Skills | 增量~0·「风格层=可插拔 skill 目录包」封装范式可偷 |

---

## 待办（大汇总后续）
- [x] 06 高 stakes 难图实现（图表库料已汇总）
- [ ] 05 质量门：补各应用 fail-open 交叉印证 + Instrumenta/guizang/Auto-Slides 的 fail-closed 范式
- [ ] 策略写作 skill（SKILL.md）：把 03 场景叙事 + 05 质量门串成可执行流程
- [ ] ppt-master 战略决策（制作层用它引擎 vs 自研）—— 需用户拍板
