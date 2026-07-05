# 开源拆解 · Auto-Slides（ICME2026 · Westlake AGI Lab）

> 日期：2026-06-30 · 方法：`ls -R` + 读 README/LICENSE + 亲读 4 个 agent 实现 + main.py 编排 + tex_validator 闭环（保真·带文件行号出处·代码即真相，不靠论文宣称掺料）。
> 仓库本地路径：`/Users/qinbiaojuan/Documents/PPT开源参考/02_Agentic架构/Auto-Slides` · 上游：[github.com/wzsyyh/Auto-Slides](https://github.com/wzsyyh/Auto-Slides) · arXiv 2509.11062。
> **一句话最值得偷的**：把「质量校验」拆成**先用确定性正则把数字声明在原文里逐个核验（pre-validation），再把核验结果当"已验证白名单"喂给 LLM、明令它别再误报**——这套「程序先验证、LLM 不准推翻」的两层防假阳，正是我们「机检质量门别让 LLM 当唯一裁判」的现成范式。

---

## 0. 最重要的判断（先说结论）

1. **它有两套 verify/repair，但主流程只接了"软"的那套，且是 fail-OPEN**。完整版（`verification_agent.py` 双向校验+幻觉检测）写得很认真却**没接进 main.py**；实际跑的是 simplified 版（只查"覆盖度够不够"），而且**验证不过 = 弹 `input()` 问用户要不要修、异常一律放行**（`main.py:397-406`）。→ 对我们是**反面教材**：它叫"Verification/Repair Agent"，但**不是 fail-closed 闸**，过不过不挡路。我们的"不过就返工"恰恰要避免退化成这个。
2. **项目里唯一真正的 fail-closed 闭环不在"内容层"，在"编译层"**：LaTeX 编译 retry≤5，`returncode==0` 且 PDF 文件真实存在才算过，否则正则抽报错→喂回 LLM 修→重编（`tex_workflow.py:140-183`、`tex_validator.py:172-219`）。**这才是可借的硬闸**——它有客观判据（编译器二值结果），不靠 LLM 自评。
3. **最金贵的细节是"防 LLM 假阳"的两层结构**（见 §2.A）：确定性正则先验 → LLM 在白名单约束下复核。这套思路反过来用在我们"防假绿"上极贴：**别让 LLM 既当运动员又当裁判**。

---

## 1. 是什么 + 定位

- **一句话**：论文 PDF → 结构化"演讲计划"(JSON) → LaTeX Beamer → 编译出 PDF slides 的**学术 paper-to-beamer** 流水线；卖点是"多 agent 协作 + 认知科学导向的叙事重组 + 交互式精修"。
- **形态**：CLI（`python main.py paper.pdf`），LangChain + OpenAI(`gpt-4o`)，marker-pdf 做 PDF 解析。**和我们差异大**：它走 **LaTeX/Beamer** 路线（学术、可编译），不是原生 PPTX；面向**单篇论文转述**，不是咨询/投资人 deck。
- **对我们的相关性**：**不在产物形态，在质量门架构**——它是 §1.5 资源地图里点名的 "Verification + Repair = fail-closed 返工对应物"，本次就是来挖这个对应物到底怎么实现、能借多少。
- **管线全貌**（`main.py` Step 编号即源码注释）：
  `PDF解析(marker) → 内容增强抽取 → Step2 演讲计划(planner,JSON) → Step2.5 验证覆盖度 → Step2.6 自动修复 → Step3 TeX生成+编译闭环 → 交互精修 → (可选)演讲稿`。

---

## 2. ⭐ Verification Agent + Repair Agent 怎么做（重点）

### 2.A 完整版 VerificationAgent（`modules/verification_agent.py`，写了但**主流程没用**）

验**四个维度**，各出一个 0-100 分 + 问题清单（`verify_presentation_plan` L115-193）：

| 维度 | 验什么 | 关键手法 |
|---|---|---|
| ① 事实一致性 `_verify_factual_consistency` L195 | 演讲里的声明与原文是否矛盾 | prompt 明令"**保守**：默认一致，只为已证实的重大矛盾扣分；格式差异不扣"（L643 "STRICT VALIDATION PROTOCOL" + "Conservative Scoring"） |
| ② 幻觉检测 `_detect_hallucinations` L233 | 有没有原文不存在的捏造数据/引用/夸大 | **核心：两层防假阳**（下详） |
| ③ 关键信息保全 `_verify_key_information_preservation` L289 | contributions/methodology/results/conclusions 四块有没有丢 | 按四类抽原文关键信息 vs slides 比对 |
| ④ 定量数据准确性 `_verify_quantitative_data` L341 | 表格数字、百分比、小数位、单位有没有抄错 | 只挑"含 %/数字/含表"的 slide 来验，省 token（L349-351） |

**⭐ 两层防假阳（最值得偷，L240-256 + L498-641）**：
- **第一层 = 确定性正则预校验**（`_pre_validate_numerical_claims` L498）：用正则从 slides 抽出所有"from X to Y"型数字对比和孤立数字，**在原文文本里逐个 `in` 查存在性**，标记 `both_exist` / `comparison_phrase_exists`。**这步完全不靠 LLM，是程序事实。**
- **第二层 = 语义方向校验**（`_validate_semantic_context` L559）：对已确认存在的数字对，截原文 ±200 字上下文，用"improvement/reduction"等词判断"声称变好但数字变大"这类**方向性矛盾**（L612-633）。
- **第三层 = 把前两层结果当白名单喂给 LLM**（`_create_hallucination_detection_prompt_with_prevalidation` L699）：prompt 里直接列"✅ 这些数字已程序核验存在，**不准再标成幻觉**，除非用在完全错误的语境"（L738-746）。甚至举例教 LLM 看表："若表中 VTI=2.90 其余更低，则'最高分'就是对的，别误报"（L778-782）。
  → **本质：用程序的确定性结论，给 LLM 的概率性判断套缰绳，专治 LLM 自由发挥乱报假阳。**

**判过不过**（`_generate_overall_assessment` L390-447，**硬阈值**）：
- 收集四维分数取均值；按区间累积 `critical_issues` / `warnings`（如一致性<70=critical、<85=warning；数据<80=critical；幻觉 severity∈{high,critical}=critical）。
- **过线判据**：`verification_passed = (critical_issues 数==0) AND (overall_score≥75)`（L438）。低于线 → `recommendation="NEEDS_REVISION"`。
- 温度 0.1，且不同子任务用不同超低温（fact_checking=0.03、hallucination=0.02，见 §2.C）。

### 2.B 完整版 RepairAgent（`modules/repair_agent.py`，同样**主流程没用**）

按 verification 报告**分四类对症修**，且**只修 medium/high/critical**（L226、L300、L333）：
- **改事实错** `_repair_factual_inconsistencies` L220 → LLM 据原文生成更正文本 → 在 plan 里字符串替换。
- **补缺失信息** `_add_missing_key_information` L257 → 只补 high/critical → 生成内容 → 按类别(contributions/methodology/results/conclusions)塞进**标题关键词匹配**的 slide（`_add_content_to_appropriate_slide` L511）。
- **修数据** `_fix_data_inaccuracies` L294 → 直接拿"原文正确值"替换"演讲错误值"。
- **删幻觉** `_remove_hallucinated_content` L327 → 先试生成事实替代；**若替代里含"不确定/可能/无法确认"等词就放弃替代、直接删**（`_generate_factual_replacement` L453-455，防"修了等于没修/越修越假"）。
- 修复全在 **JSON 计划层**做字符串增删替换（`_replace_content_in_plan` L463、`_remove_content_from_plan` L488），**不碰已编译产物**——符合"产物只读"的隔离思路。
- **关键缺陷**：repair 之后**没有再跑一次 verification 确认修好了**（main.py 修完直接更新 plan 进入 TeX 生成）。→ **不是闭环，是开环单次修**。

### 2.C 任务级超参数表（`config/llm_params.py`，**这个设计可直接借**）

把 LLM 调用按任务类型配差异化超参，**校验类压到地板、生成类适度放开**：

| 任务 | temperature | 设计意图（原文 description） |
|---|---|---|
| 表格/公式抽取 | **0.02** | 数据/LaTeX 零容错 |
| 幻觉检测 | **0.02** | "ultra-conservative" |
| 事实核查 | **0.03** | "highest precision" |
| 验证/TeX修错 | **0.05** | 一致性评估 |
| 内容修复 | **0.08** | "surgical precision" |
| 演讲计划 | 0.15 | 逻辑结构为主 |
| TeX 生成 | 0.20 | 受控创造 |
| 演讲稿 | 0.25 | 自然 |

→ **可借**："越靠近质量门/事实核验，temperature 越低"是条干净的工程规约，比全程一个温度强。

### 2.D 实际跑的 simplified 版（`simplified_*_agent.py`，**main.py 真正 import 的**）

- **SimplifiedVerification**：docstring 明说"**NO 复杂事实核查/幻觉检测，避免假阳**"（L38），只让 LLM 用**宽松标准**给五块覆盖度打分（problem/contributions/methodology/results/conclusions），**只有总分<60 或多个 high 缺失才判 false**（L263）。所有异常/解析失败一律 `return True`（默认放行，L153/204/292）。
- **SimplifiedRepair**：只"补缺失内容"（add），**不改错、不删幻觉**（docstring L38 "NO complex error correction"），找标题关键词匹配的 slide 追加 2-4 个 bullet，找不到就**新建一页补充 slide**（`_create_supplementary_slide` L350）。
- **设计取向很明确**：作者**主动选择了"宽松、宁可漏报、绝不阻断"**——为了产品不卡壳。**这正是我们要反着来的地方。**

---

## 3. 关键实现 / 文件位（速查）

| 关心点 | 文件:行 |
|---|---|
| 主编排（Step 2.5 验证 / 2.6 修复，**fail-open 的证据**） | `main.py:353-451` |
| 验证不过只 `input()` 问用户、异常放行 | `main.py:397-406` |
| 完整版四维验证 + 硬阈值判过 | `modules/verification_agent.py:115-193, 390-447` |
| ⭐ 正则预校验数字声明（防假阳第一层） | `modules/verification_agent.py:498-557` |
| ⭐ 语义方向校验（防假阳第二层） | `modules/verification_agent.py:559-641` |
| ⭐ 把白名单喂 LLM 的 prompt（防假阳第三层） | `modules/verification_agent.py:699-783` |
| 完整版四类对症修复 | `modules/repair_agent.py:220-370` |
| 修复时遇"不确定"就弃修 | `modules/repair_agent.py:453-455` |
| **真正的 fail-closed 编译闭环**（retry≤5，错误喂回修） | `modules/tex_workflow.py:140-183` |
| 编译判过：returncode==0 且 PDF 存在 | `modules/tex_validator.py:172-219` |
| LaTeX 错误正则提取（喂回 LLM 的料） | `modules/tex_validator.py:407-446` |
| 任务级 temperature 配置表 | `config/llm_params.py:49-181` |
| 主流程实际只 import simplified 版 | `main.py:363, 416` |

---

## 4. ⭐ 对 PPT Engine 的落点（我们的质量门 / 返工闸能借什么）

1. **【直接偷·防假绿】两层裁判：程序先验证、LLM 不准推翻**。我们做投资人 deck 的数字门时，**别让 LLM 当唯一裁判**——先用确定性代码把"deck 里的每个数字/同比/占比"在 source（财务表/调研数据）里核验存在性与口径，把"已核验"清单作为约束喂给 LLM，明令它**只查程序没覆盖的语义层**、不准推翻已核验项。对应它的 `_pre_validate_numerical_claims` + prompt 白名单。**这条最贵，正中我们铁律2"防假绿、不让 LLM 打分当硬信号"。**
2. **【直接偷·真闸长这样】fail-closed 必须有客观二值判据**。它的编译闸能成立，是因为"编译器 returncode + PDF 是否存在"是**程序事实**。我们每道返工闸也要找这种**非 LLM 的硬判据**（如：waterfall 数字首尾是否对得上、Mekko 宽度和是否=100%、引用页码是否真实存在），LLM 评分至多当 🟡 警告，**不当 🟢 放行信号**。
3. **【直接偷·反面警示】别让质量门退化成"问用户要不要修 / 异常放行"**。Auto-Slides 把好端端的 Verification Agent 接成了 fail-open（`input()` + 异常 return True），**等于没有闸**。我们的"不过就返工"必须是**默认阻断、过不了就停在本阶段**，绝不能"出错就当通过"——这恰是它退化、我们要硬住的分水岭。
4. **【可借·超参规约】校验/核验类调用 temperature 压到 0.02-0.08**，生成类才放开。一行规约，立刻降低质量门自身的抖动假阳/假阴。
5. **【可借·修复隔离】repair 只在中间表示（它的 JSON plan）上做增删替换，不碰已编译产物**——和我们"已交付产物只读（铁律4）"同构，可作为"返工只动草稿层"的实现参照。
6. **【补它的坑·闭环要回查】它修完不复验 = 开环**。我们的返工闸必须**修完重跑同一道门**直到过（或到 retry 上限停下报问题），形成真闭环——这是它缺的、我们必须补的。
7. **形态层不借**：LaTeX/Beamer、marker-pdf、单论文转述都与"咨询级原生 PPTX"无关，不引入。

---

## 5. License + 坑

- **License = MIT**，但 LICENSE 文件末尾附注：**"二次开发用于商业目的需联系原作者授权"**（`LICENSE` L23）。⚠️ 这条与纯 MIT 冲突/加码——**若要借鉴代码到商业产品，按"需授权"对待，别直接 copy 代码**；**借"架构思路/方法论"无版权问题**（思想不受版权保护），这正是我们要的（我们偷的是"两层防假阳""硬判据闸"的设计，不是抄它的 Python）。
- LICENSE 抬头仍写 "Paper-to-Beamer Contributors / 2023-2024"（前身项目名），与 Auto-Slides 命名不一致，属遗留。
- **坑1（最大）**：名为 "Verification/Repair Agent" 但**默认 fail-open**，且**完整版没接主流程**——**别被名字误导以为它实现了 fail-closed 返工**。真正在防的只有 LaTeX 编译。
- **坑2**：完整版 verification 的"防假阳"逻辑很重（正则 + 语义 + prompt 三层），但**正则模式写死**（只认 "from X to Y" 句式、`[0-9.]+`），**对中文数字、区间、复杂表述覆盖有限**——借思路别借这套具体正则。
- **坑3**：repair 用**裸字符串 `replace`** 在 plan 里改内容（`repair_agent.py:471-479`），同名子串会误伤；且修复后不复验。
- **坑4**：依赖 marker-pdf（~2GB 模型）+ 本地 LaTeX(xelatex/pdflatex) + OpenAI key，**重**；本机当前缺 pdfplumber/poppler，论文 PDF 正文未能提取（结论全部基于代码事实，不依赖论文宣称）。
