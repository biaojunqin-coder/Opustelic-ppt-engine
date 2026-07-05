"""策划团队（策略阶段1.5·多角色分工·2026-07-01 用户拍板）——leader 拍板需要哪些策划角色参与，
严格接力交接完成整份 deck 架构，不是一个人从头包到尾。

对应 03 方法论"三大板块"（策略研究/核心Idea/执行）+ 新增"整合"收尾板块——角色是按板块分组的目录，
不是穷举死列表；leader 根据这份 deck 的 domain/decision_ask 推荐一个子集（不是每次全员出动，内部
复盘 deck 不需要创意/媒介角色）。**单会话换人设执行，不是独立多 agent**——Claude 明确切人设框定
视角做该板块的引导对齐，底层机制仍是"一次一个问题+摊功课+推荐+用户拍板"（CLAUDE.md 铁律0），
人设只改变"问什么问题/看什么信号/给什么推荐"，不改变对齐纪律本身。

严格接力链（用户原话"策划A完成前期搭建交给B完成中期搭建"）：`order` 里排前面的角色必须先
`complete_role`，后面的角色才能 `start_role`——角色也是一个一个来，不是几个角色同时开工再合并
（同"绝不批处理"同一条精神）。

2026-07-01 补两处（用户用过一轮后追加的真实需求）：
① **交接简报结构化**（`key_findings`/`decisions`/`open_questions`三段，不是自由文本一段话）——
   用户原话"本质上是交接工作+理解工作，是一个不断1+1的过程"，自由文本容易漏掉"这件事用户已经拍板
   过了"这类关键信息，导致后面角色重新问一遍已经问过的问题。`decisions` 字段专门扛这个：每条
   {question, answer} 是用户在这个角色的引导对齐里已经拍板的事，后面任何角色开工前必须先读
   `all_decisions_so_far()`，不能对同一件事再问用户一遍。
② **持久化**（`save_team`/`load_team`，同 `storyline_state.py` 的模式）——不能只靠对话上下文记住
   交接内容：本会话可能被自动压缩（系统会在接近上下文上限时压缩早前消息），落盘是防丢失的硬保障，
   不是可选的锦上添花。
③ **新增"整合"收尾板块 + "叙事策划"角色**——用户指出多角色分头产出后还需要一个人把这一切按"演讲
   思路"顺成一份连贯 storyline，这正是既有 `storyline_state.py` 阶段4"搭 storyline"要做的事——
   "叙事策划"角色的工作产出就是调用 `storyline_state.py` 的 `add_line` 把全部角色的 `key_findings`
   编织成 SCR/框架弧完整的页面序列，是接力链里**永远排最后**的角色（要读全部人的产出才能开工）。

2026-07-01 再补（`/yanjiu` 联网四路调研咨询/投行PE/企业战略/pitch deck服务真实团队分工后扩展）：
④ **研究板块新增5个角色**（原6个偏广告campaign，用户指出"太偏广告公司业务"）——`行业专家策划`/
   `商业尽调策划`/`财务尽调策划`/`法务尽调策划`/`数据建模策划`，覆盖 CLAUDE.md 硬纪律4 收窄的
   "咨询诊断/尽调估值"场景，每条证据来源见 `specs/决策记录.md` D10。**执行板块3个角色（媒介/线上
   线下推广）保留但明确标注是广告campaign专属**——四路调研一致显示咨询/投行/企业战略类deck根本不
   经过"媒介执行"这个环节，leader 给这类deck推荐角色时不该带上这三个。
⑤ **一个刻意不做的边界**（四路调研都独立验证到的强证据，直接影响该不该做）：McKinsey 真设有独立
   子公司"Visual Graphics Computing Services India"(1000+人专职视觉排版)、Bain 有 Creative Services
   团队、JPMorgan/RBC 有"Presentation Specialist"真实岗位——多个高 stakes 行业都独立证实"内容定稿"
   和"视觉呈现"是两个严格串行、由不同角色负责的环节。**这验证的是本项目已有的两层架构**（策略工作流
   锁 storyline，制作工作流管视觉执行，`skills/策略工作流/SKILL.md` 开篇即写"本 skill 只搭 storyline
   定稿，不出 pptx"）——**不需要在 `planning_team.py` 里加一个"视觉呈现策划"角色**，那属于制作
   工作流的职责，策略层重复加会打破已经拍板的层间边界。

2026-07-01 再补（用户："能不能把 yanjiu 这个 skill 的能力赋予各个角色"）：
⑥ **两档研究深度**——各角色日常查数据走 `claude-websearch`，遇到 consequential 的关键判断/
   陌生方法论/需要多源交叉验证时直接调用 `/yanjiu` 技能，把它的保真度铁律（核实原始证据·别只
   抄名字丢机制）带进角色研究，不是只留给系统级评估用。覆盖研究板块全部角色，详见
   `skills/策略工作流/SKILL.md` 阶段1"策略研究/诊断"小节。

2026-07-02 D18（第一轮实测反馈·specs/需求_第一轮实测反馈.md FR1.1/FR1.2/FR1.3/FR6.4）：
⑦ **结论强制**（FR1.1）——第一轮实测确诊"角色不摊结论就推进"违铁律0：`complete_role` 新增必填
   `user_summary`（一句话结论+关键发现+建议下一步），不向用户摊结论就收不了工（fail-closed），
   `validate_planning_team` 对 done 角色补查（防绕过 complete_role 手搓 status="done" 的旁路）。
⑧ **确认粒度 + ack 闸**（FR1.2）——leader 开场问用户"本单确认到什么粒度"（every_role/key_nodes/
   minimal·默认关键节点硬停），选择用 `set_confirm_granularity` 落用户原话；关键节点确认用
   `record_user_ack` 留痕（存原话不存布尔位·防假绿）；`storyline_state.handoff_to_production`
   据此拦"没等用户说定稿就交棒"。
⑨ **方向卡发散**（FR1.3/FR6.4）——实测确诊"策略单主线无发散"：发散环节产出 N 张方向卡（默认3·
   `new_direction_card`/`validate_direction_cards`），发散点=硬停点，用户收敛的选择+理由用
   `record_divergence` 留痕并自动记 ack；**用户为什么选它**是飞轮要内化的偏好知识
   （`divergence_ledger` 精简台账供回灌管线消费·FR6.4）。

fail-closed：角色分配前不能开工 / 前序角色未完成不能开工 / 板块顺序跨级倒退 / 交接三段任一为空 /
收工不带 user_summary / 收敛不带 reason·user_quote → error。
"""

from __future__ import annotations

import json
from pathlib import Path

BOARDS = ("研究", "Idea", "执行", "整合")  # 三大板块 + 收尾整合，固定顺序不倒退

ROLE_CATALOG = {
    # ── 研究板块：广告campaign向（原6个之二）──
    "市场策划": {"board": "研究", "focus": "行业规模/趋势/竞品格局的客观事实·回答「市场是什么样」"
                                          "·靠调研方法产出，适用任何deck的通用市场背景"},
    "人群策划": {"board": "研究", "focus": "受众画像/痛点/动机·回答「用户是谁、要什么」"},
    # ── 研究板块：咨询/投行/尽调向（2026-07-01 `/yanjiu` 四路调研新增·D10；
    #    2026-07-01 二次调研核实边界·D11，两处改成明确递进关系而非平行角色）──
    "行业专家策划": {"board": "研究",
                    "focus": "特定行业/领域资深人士的经验判断/直觉·回答「这个领域的真相是什么」"
                             "·不是调研方法能查到的(靠从业经验/模式识别)，出处：MBB均设独立于generalist"
                             "晋升线的Expert Track，二次核实confirmed「深度来自调研方法本身触及不到的从业经验」"
                             "·2026-07-01补：怎么把「一个人的直觉」变成可信判断已有一批结构化专家启发"
                             "框架卡`search_frameworks(domain=[\"行业专家判断\"])`(GLG专家访谈六步法/"
                             "SHELF/IDEA/Cooke's种子问题校准/Delphi/Pre-mortem事前验尸/三角验证法)，"
                             "别只是找个专家聊聊天，要用这些协议对抗从众偏差和确认偏误"},
    "商业尽调策划": {"board": "研究", "builds_on": "市场策划",
                    "focus": "针对具体交易/标的做投资决策级压力测试(增长假设站不站得住/管理层计划现实吗)"
                             "·回答「这个生意本身站得住吗」·建立在市场策划的基础研究之上，多一层批判性验证，"
                             "不是替代市场策划(二次核实：PwC官方页面直接是「Commercial and Market Due "
                             "Diligence」，market research是CDD的输入组件，两者递进不是平行)"
                             "·出处：IB/PE真实分工，常见由战略咨询公司承接(Bain/L.E.K.官网confirmed)"
                             "·2026-07-01补：一批真实CDD框架卡(D12批次8张·domain检索含跨域共标卡会多于此)`search_frameworks(domain=[\"商业尽调\"])`"
                             "(TAM/SAM/SOM双路测算/波特五力/客户集中度CRn+HHI/Cohort+NRR留存/"
                             "PVM增长拆解/挑战管理层计划法/Bain全潜力五模块/VOC客户之声)，"
                             "核心动作是「挑战管理层计划」——不核对数字对不对，是独立验证增长可信度"},
    "财务尽调策划": {"board": "研究",
                    "focus": "回溯核实财务健康度/盈利质量(Quality of Earnings)·回答「账面数字信得过吗」"
                             "·出处：IB/PE真实分工，常见由四大会计所承接(PwC真实JD confirmed)"
                             "·2026-07-01补：一批QoE框架卡`search_frameworks(domain=[\"财务尽调\"])`"
                             "(EBITDA标准化调整清单/营运资金正常化NWC Peg/净债务与类债务项识别/"
                             "收入确认风险核查/现金流质量CFO背离分析/财务红旗信号七类清单)"
                             "·出处CBV Institute 2022年论文(访谈31位真实从业者)"
                             "·诚实边界：QoE领域目前没有官方权威准则，各家事务所自建专有指引"},
    "法务尽调策划": {"board": "研究",
                    "focus": "排查合规/合同/诉讼/知识产权风险·回答「有没有法律地雷」"
                             "·出处：IB/PE真实分工，常见由专业律所承接"
                             "·2026-07-01补：一批法务尽调框架卡`search_frameworks(domain=[\"法务尽调\"])`"
                             "(变更控制条款排查/IP权属链条核验/诉讼敞口清单/劳动合规十项排查/"
                             "Phase I环境评估/许可证可转让性判断/数据隐私与AI治理核查)"
                             "·出处Ropes & Gray真实150条DDRL(2025最新版·含AI治理新章节)"},
    "数据建模策划": {"board": "研究",
                    "focus": "前瞻搭建/验证估值或财务模型(LBO/DCF/可比公司)·回答「这笔账算不算得过来」"
                             "·跟财务尽调策划的边界很清晰(前瞻建模·PE内部亲自做 vs 回溯验证·常外包会计所)"
                             "·出处：PE deal team唯一不外包亲自动手的核心工作；FP&A/pitch deck consultancy"
                             "均证实这是独立于内容策略的第三条分支，不是「内容」的子集"
                             "·2026-07-01补：DCF/LBO/可比公司核心计算已有确定性引擎"
                             "`engine/financial_models.py`(公式核实自Wall Street Prep等权威渠道)，"
                             "这个角色引导对齐时该调用算，不是让Claude现场手算估值模型(比图表坐标更"
                             "容易算错、错了更难肉眼查出)"},
    # ── Idea板块 ──
    "创意策划": {"board": "Idea", "focus": "综合研究洞察提炼 big idea·回答「我们想说什么」"},
    # ── 执行板块：广告campaign专属（2026-07-01补注：咨询/投行/企业战略类deck通常不需要这三个，
    #    四路调研独立一致显示这类deck根本不经过"媒介执行"环节，leader推荐角色时别带上）。
    #    2026-07-01 二次调研核实：这三者是**战略→执行的层级关系**，不是三个平行选项——
    #    媒介策划先定渠道/预算分配，线上/线下推广策划在其后针对已分配的渠道做具体执行细化
    #    （查证confirmed："media planners...making strategic decisions about where and how to
    #    allocate marketing budgets" vs digital/activation角色做"day-to-day execution"）──
    "媒介策划": {"board": "执行", "focus": "渠道组合/预算分配的战略决策·回答「在哪触达」（广告campaign专属）"
                                         "·线上/线下推广策划在此之后执行，通常应排在两者之前"
                                         "·2026-07-01补：一批媒介规划框架卡`search_frameworks(domain=[\"媒介推广\"])`"
                                         "(GRP/TRP/Reach-Frequency计算体系/有效频次理论Krugman三次曝光论/"
                                         "媒介规划五阶段流程/媒介组合建模MMM·Google Meridian/"
                                         "边际ROI预算分配法/增量测试Holdout+GeoLift)"
                                         "·诚实边界：GroupM/Omnicom/Publicis三家头部代理商未公开含具体"
                                         "分析步骤的方法论白皮书，官网内容偏公司介绍非方法论细节"},
    "线上推广策划": {"board": "执行", "builds_on": "媒介策划",
                    "focus": "在媒介策划已分配的线上渠道内做具体执行打法·回答「线上怎么做」（广告campaign专属）"
                             "·2026-07-01补：一批线上推广框架卡`search_frameworks(domain=[\"线上推广\"])`"
                             "(SOSTAC策略框架/AARRR海盗指标漏斗/北极星指标法/内容支柱+CMI编辑日历/"
                             "社媒平台分发算法适配/AIPL+RFM私域分层运营/KOL·KOC分层选择法)"
                             "·补齐了此前私域运营/KOL卡片单薄的缺口"},
    "线下推广策划": {"board": "执行", "builds_on": "媒介策划",
                    "focus": "在媒介策划已分配的线下渠道内做activation落地执行·回答「线下怎么做」（广告campaign专属）"
                             "·2026-07-01补：一批线下执行框架卡`search_frameworks(domain=[\"线下推广\"])`"
                             "(体验营销ROI衡量框架/活动执行三阶段清单·事前事中事后/顾客旅程地图线下应用)"
                             "·诚实边界：这块证据链三块里最薄，缺头部代理商一手白皮书，具体ROI数字"
                             "(如25-34%)来自单一行业调研非交叉验证，引导对齐时该如实告知不确定性"},
    # ── 整合板块 ──
    "叙事策划": {"board": "整合", "focus": "把全部角色产出顺成一份连贯 storyline·回答「怎么讲这个故事」"
                                          "·产出=调 storyline_state.add_line 逐页搭建，桥接既有阶段4"
                                          "·出处：企业战略场景Chief of Staff真实承担同一职能"
                                          "(paulcohen.com一手资料+真实CEO案例confirmed)"},
}


GRANULARITIES = ("every_role", "key_nodes", "minimal", "direct_through")  # D18 FR1.2 三档 + D21 直通档

# 批③🟡（防假绿·启发式）："用户原话"里出现这些机制黑话，几乎可以断定是 AI 把自己的工序词
# 当 user_quote 代填了——真实用户拍板不会说 "waiver"/"ack闸" 这种系统内部术语。
_MECHANISM_JARGON = ("waiver", "ack闸", "假设台账", "auto_decided", "granularity",
                     "record_", "fail-closed", "留痕豁免")


def _reject_suspected_proxy_quote(user_quote: str) -> None:
    """user_quote 疑似代填拒收（批③🟡·启发式·防假绿）。

    留痕的全部价值在"事后可回放用户真实说过什么"——AI 顺手把工序描述（"waiver 留痕豁免"）写进
    user_quote，整条审计链就变成 AI 自己给自己签字。quote 含 _MECHANISM_JARGON 任一术语
    （大小写不敏感）→ ValueError 拒收。

    诚实边界：这是**启发式不是证明**——理论上用户可以亲口念出机制术语（误伤），但用户不说
    机制黑话，误伤概率极低；换来的是堵住"AI 把系统术语当用户原话代填"这条最顺手的假绿路径。
    真被误伤时用户换个说法复述一遍即可通过。只在写入口（set_confirm_granularity/
    record_user_ack/record_divergence）拦，不追溯已落盘的历史 team_state（历史数据只读）。
    """
    low = (user_quote or "").lower()
    for term in _MECHANISM_JARGON:
        if term.lower() in low:
            raise ValueError(f"疑似代填：用户原话不会包含机制术语「{term}」——必须逐字记用户真实说的话"
                             f"（批③🟡·启发式防假绿·quote={user_quote!r}）")


def new_planning_team(brief_purpose: str, confirm_granularity: str = "key_nodes") -> dict:
    """建团队骨架（leader 阶段1对齐完目的卡+mode+delivery_purpose后·拍板角色前）。

    confirm_granularity（D18 FR1.2）：本单确认粒度——leader 开场就要问用户一次，问完用
    `set_confirm_granularity` 落用户选择原话。默认 key_nodes=关键节点硬停（发散点/设计定稿/
    storyline定稿/交棒制作必须等用户 ack）；every_role 更密（每个角色收工都停）；minimal 最松
    （用户明确赶时间才选——交棒 ack 闸随之放开，那是用户自己的选择而非系统自作主张跳过）；
    direct_through=直通档（D21·2026-07-03 用户拍板"字面直通"）：开场这一问之后全程零停顿直到
    成品 publish——发散点由 AI 按推荐代拍（record_divergence auto_decided=True 留痕·进
    assumption_ledger 假设台账交付时摊）、人审闸走 publish_deck(direct_through_waiver=根授权
    原话) 豁免。敢放的依据同 minimal：granularity_quote 留了用户亲口选直通的原话。
    """
    if confirm_granularity not in GRANULARITIES:
        raise ValueError(f"confirm_granularity={confirm_granularity!r} 非法"
                         f"（应 {sorted(GRANULARITIES)} 之一·D18 FR1.2）")
    return {"brief_purpose": brief_purpose, "order": [], "roles": {},
            "confirm_granularity": confirm_granularity,  # D18 FR1.2 确认粒度（用户拍板项）
            "granularity_quote": "",       # 用户选粒度的原话（set_confirm_granularity 落）
            "user_acks": [],               # D18 FR1.2 关键节点确认留痕 [{node, user_quote}]
            "divergences": []}             # D18 FR1.3/FR6.4 发散-收敛留痕（飞轮内化载体）


def set_confirm_granularity(team: dict, granularity: str, user_quote: str) -> dict:
    """leader 开场问完"本单确认到什么粒度"后落下用户的选择（D18 FR1.2）。

    为什么必须带 user_quote：粒度决定后面每一步"停不停"，minimal 档还会放开交棒 ack 闸——
    这种改变流程刚性的选择必须能回放"当初是用户自己选的快进"，没有原话的留痕不算留痕
    （同 record_user_ack 的防假绿纪律）。quote 含机制黑话按疑似代填拒收
    （启发式·见 _reject_suspected_proxy_quote）。
    """
    if granularity not in GRANULARITIES:
        raise ValueError(f"confirm_granularity={granularity!r} 非法（应 {sorted(GRANULARITIES)} 之一·D18 FR1.2）")
    if not user_quote:
        raise ValueError("set_confirm_granularity 必须带用户选择原话 user_quote——"
                         "没有原话的留痕不算留痕（D18 FR1.2·铁律0）")
    _reject_suspected_proxy_quote(user_quote)   # 批③🟡：根授权原话是直通档全部豁免的依据，代填即全链失真
    team["confirm_granularity"] = granularity
    team["granularity_quote"] = user_quote
    return team


def record_user_ack(team: dict, node: str, user_quote: str) -> dict:
    """关键节点确认留痕（D18 FR1.2）：node 是自由字符串（如 "方向收敛:策略方向"/"storyline定稿"/
    "设计定稿"/"交棒制作"），user_quote 是用户确认的原话。

    为什么存原话而不是布尔位：True/False 自己就能悄悄置上（假绿的老路），原话才证明"用户真的
    说过这句"，事后可回放可对质——`storyline_state.handoff_to_production` 的 ack 闸只认这里的
    记录。setdefault 兼容旧落盘 team（D18 前的 team_state.json 没有 user_acks 字段）。
    quote 含机制黑话按疑似代填拒收（启发式·见 _reject_suspected_proxy_quote）。
    """
    if not node:
        raise ValueError("record_user_ack 的 node 不能空——不知道确认的是哪个节点，留痕无意义（D18 FR1.2）")
    if not user_quote:
        raise ValueError(f"节点「{node}」确认留痕必须带用户原话 user_quote——"
                         f"没有原话就当没确认过（D18 FR1.2·fail-closed·防假绿同一条纪律）")
    _reject_suspected_proxy_quote(user_quote)   # 批③🟡：ack 只认真人原话，机制黑话=疑似 AI 代签
    team.setdefault("user_acks", []).append({"node": node, "user_quote": user_quote})
    return team


def assign_roles(team: dict, role_ids: list[str]) -> dict:
    """leader 拍板选中的角色，按用户确认过的执行顺序传入（严格接力链的顺序）。
    未知角色名直接拒绝（防手滑打错字·同 validate_storyline 的 framework 非法检查同一条纪律）。
    """
    unknown = [rid for rid in role_ids if rid not in ROLE_CATALOG]
    if unknown:
        raise ValueError(f"未知角色 {unknown}（应是 {sorted(ROLE_CATALOG)} 之一）")
    team["order"] = list(role_ids)
    team["roles"] = {rid: {"status": "pending", "handoff": None} for rid in role_ids}
    return team


def start_role(team: dict, role_id: str) -> dict:
    """角色开工前置检查：`order` 里排在它之前的角色必须全部 done，才能开工——严格接力，
    不并行、不能插队（fail-closed，不静默放行跳过前序）。
    """
    if role_id not in team.get("roles", {}):
        raise ValueError(f"{role_id} 未被 leader 分配·不能开工")
    idx = team["order"].index(role_id)
    unfinished = [rid for rid in team["order"][:idx] if team["roles"][rid]["status"] != "done"]
    if unfinished:
        raise ValueError(f"{role_id} 不能开工——前面还有角色未完成：{unfinished}")
    team["roles"][role_id]["status"] = "in_progress"
    return team


def complete_role(team: dict, role_id: str, *, key_findings: list[str],
                   user_summary: dict | None = None,
                   decisions: list[dict] | None = None, open_questions: list[str] | None = None) -> dict:
    """角色收工，留一份**结构化**交接（三段·不是自由文本一段话）+ 向用户摊的结论（D18 FR1.1）：

    key_findings：这个角色产出的关键事实/洞察（列表·扫读友好，不是让下一个角色去读大段散文）。
    user_summary（D18 FR1.1·必填——默认 None 只是为了给出讲清缘由的 ValueError，不是可选）：
      收工前**向用户摊的结论** {"conclusion": 一句话结论, "highlights": [3-5条关键发现],
      "next_step": 建议下一步}。第一轮实测确诊"角色不摊结论就推进"违铁律0——交接简报是给
      下一个角色看的（工作语言），user_summary 是给用户看的（拍板语言），两者受众不同不能互替。
      硬校验：conclusion 非空 + highlights ≥1 条有效（3-5 条是建议档），缺任一拒绝收工（fail-closed）。
    decisions：本角色引导对齐过程中用户已经拍板的事 [{question, answer}]——**下一个角色开工前
      必须先读这些，不能对同一件事再问用户一遍**（用户原话"防止...每次交接角色的时候导致原角色
      信息丢失"，这是专门堵这个漏洞的字段）。
    open_questions：本角色没解决、留给后面角色注意的事（缺省 []·不是每个角色都会留)。

    key_findings 不能空（没有产出的角色没有交接的意义）；decisions 允许空列表（有的角色阶段可能
    确实没有需要用户拍板的新决定，但不能传 None 让下游误判"没读到"和"真的没有"）。
    """
    if not key_findings:
        raise ValueError(f"{role_id} 交接的 key_findings 不能空——下一个角色靠这个接手，不是让它猜")
    # D18 FR1.1 结论强制：空/缺 conclusion/highlights 不足 1 条有效 → 拒绝收工。
    # highlights 只数有效条目（过滤空串/None）——塞空字符串凑数是"字段有了、结论没摊"的假绿路径。
    us = user_summary or {}
    highlights = [h for h in (us.get("highlights") or []) if h]
    if not us.get("conclusion") or not highlights:
        raise ValueError(
            f"{role_id} 收工被拒——user_summary 缺失或不完整（必填 conclusion 一句话结论 + "
            f"highlights ≥1 条关键发现[建议3-5条]，另配 next_step 建议下一步）："
            f"角色收工必须先向用户摊结论等拍板，不能闷头推进下一角色（D18 FR1.1·铁律0 以人为主全程引导对齐）")
    team["roles"][role_id] = {
        "status": "done",
        "handoff": {
            "key_findings": list(key_findings),
            "user_summary": {"conclusion": us["conclusion"], "highlights": highlights,
                             "next_step": us.get("next_step", "")},
            "decisions": list(decisions) if decisions is not None else [],
            "open_questions": list(open_questions) if open_questions is not None else [],
        },
    }
    return team


def handoff_briefs_for(team: dict, role_id: str) -> list[dict]:
    """给即将开工的 role_id 读它能看到的交接——`order` 里排在它前面、已收工角色的全部结构化交接
    （**全部**·不是只给上一个角色的，"1+1累积"要求越往后的角色能看到的上下文越完整，不能只看局部）。
    """
    idx = team["order"].index(role_id)
    return [{"role": rid, "board": ROLE_CATALOG[rid]["board"], **team["roles"][rid]["handoff"]}
            for rid in team["order"][:idx] if team["roles"][rid]["status"] == "done"]


def all_decisions_so_far(team: dict) -> list[dict]:
    """汇总目前为止全部已收工角色的 decisions，附来源角色——任何角色开工前的必读项，
    防止用户已经拍板过的事被后面角色不知情地重新问一遍。
    """
    out = []
    for rid in team.get("order", []):
        role = team["roles"].get(rid) or {}
        if role.get("status") == "done":
            for d in role["handoff"]["decisions"]:
                out.append({"role": rid, **d})
    return out


# ── D18 FR1.3 方向卡发散（发散产出物=N 张方向卡·默认 N=3·发散点=硬停点）─────────────
# 第一轮实测确诊"策略单主线无发散"：研究群收工后一条道走到黑，用户从没被给过"还能怎么打"的
# 选择空间。方向卡是发散的标准载体：每张自带"为什么可能赢/主要风险"（不给权衡的选项等于替用户
# 做决定），用户收敛的选择+理由必须留痕——那个"为什么"正是飞轮要内化的偏好知识（FR6.4）。


def new_direction_card(name: str, core_logic: str, supporting_findings: list[str],
                       play_summary: str, why_win: str, risks: str, fit: str) -> dict:
    """造一张方向卡（schema 见需求 FR1.3）。

    name=方向名；core_logic=一句话核心逻辑；supporting_findings=支撑洞察（**引用已有角色交接的
    key_findings 原文，不重新调研**——发散是对已有研究的多种组合解读，不是再做一轮研究）；
    play_summary=打法概要；why_win=为什么可能赢；risks=主要风险；fit=适配度（跟 brief 诉求/
    预算/时间窗的匹配说明）。纯构造不校验——合法性统一走 validate_direction_cards：
    "≥2 张才叫发散"/"name 不重复"是组级约束，单张卡自己查不了。
    """
    return {"name": name, "core_logic": core_logic,
            "supporting_findings": list(supporting_findings or []),
            "play_summary": play_summary, "why_win": why_win, "risks": risks, "fit": fit}


def validate_direction_cards(cards: list[dict]) -> list[dict]:
    """方向卡组校验 → error 列表（空列表=合法·D18 FR1.3）。

    组级：≥2 张才叫发散（1 张只是"通知用户我要这么干"，没有选择空间）+ name 不重复（重名卡
    用户没法指认选了哪张）。卡级：name/core_logic/why_win 必填——名字（指认用）、核心逻辑
    （凭什么算一个独立方向）、为什么可能赢（用户拍板的最小依据）缺一不可。
    """
    errors = []
    cards = cards or []
    if len(cards) < 2:
        errors.append({"sev": "error",
                       "msg": f"方向卡仅 {len(cards)} 张——≥2 张才叫发散，单一选项等于没给用户"
                              f"选择空间（D18 FR1.3·默认 3 张）"})
    seen = set()
    for i, c in enumerate(cards):
        for k in ("name", "core_logic", "why_win"):
            if not c.get(k):
                errors.append({"sev": "error",
                               "msg": f"方向卡[{i}]（{c.get('name') or '未命名'}）缺 {k}"
                                      f"（name/core_logic/why_win 必填·D18 FR1.3）"})
        name = c.get("name")
        if name and name in seen:
            errors.append({"sev": "error",
                           "msg": f"方向卡 name 重复：「{name}」——重名用户没法指认选的是哪张"})
        seen.add(name)
    return errors


def record_divergence(team: dict, node: str, cards: list[dict], chosen: str, reason: str,
                      user_quote: str = "", *, auto_decided: bool = False) -> dict:
    """发散-收敛留痕（D18 FR1.3）+ 自动记该发散点的 ack。

    node=发散节点名（如 "策略方向"/"创意概念"）；cards=摊给用户的全部方向卡
    （validate_direction_cards 必须过）；chosen=用户选的方向卡 name，或 "混合:" 前缀的自由文案
    （"要 A 的打法+B 的渠道"这类真实收敛结果，不硬逼二选一）；reason=**用户为什么选它——
    飞轮要内化的最金贵知识（FR6.4），只记结果不记理由等于白发散一轮**；user_quote=用户拍板原话
    （含机制黑话按疑似代填拒收·启发式·见 _reject_suspected_proxy_quote）。

    收敛即确认：自动 record_user_ack(team, f"方向收敛:{node}", user_quote)，发散点的 ack 不用
    再手记一遍。全部校验先行、全过才写入——不留"divergence 记了、ack 没记上"的半截中间态。

    auto_decided=True（D21 直通档专用）：AI 按推荐方向代拍。三道防线换着守留痕，不是放松——
    ① 只有 confirm_granularity="direct_through" 的 team 才允许（非直通档代拍=越俎代庖，直接拒）；
    ② user_quote 必须为空（AI 绝不能编造用户原话——这是防假绿的底线，有真原话就不该走 auto）；
    ③ reason 语义变为「AI 为什么替用户选它」照样必填，条目带 auto_decided=True + auth_quote=
    根授权原话（用户开场选直通档的那句），进 assumption_ledger 交付时摊给用户验收。
    auto 条目**不记 ack**（user_acks 列表只放真人确认）、**不进偏好回灌与跨 deck 历史注入**
    （divergence_ledger/divergence_history 都滤掉——否则飞轮学到的是 AI 自己的偏好，
    往后的"越来越懂你"就是假的·D21 防飞轮污染）。
    """
    if not node:
        raise ValueError("record_divergence 的 node 不能空——不知道是哪个发散节点，留痕无意义（D18 FR1.3）")
    errs = validate_direction_cards(cards)
    if errs:
        raise ValueError(f"方向卡不合法·拒绝记录收敛（D18 FR1.3）：{errs}")
    names = [c.get("name") for c in cards]
    if not (chosen in names or (isinstance(chosen, str) and chosen.startswith("混合:"))):
        raise ValueError(f"chosen={chosen!r} 不在方向卡 {names} 内，也不是「混合:」前缀的自由收敛"
                         f"——用户到底选了哪个必须说清（D18 FR1.3）")
    if not reason:
        raise ValueError("收敛必须带 reason（用户为什么选它）——选择偏好是飞轮要内化的知识，"
                         "只记选了哪个不记为什么，回灌管线学不到任何东西（D18 FR6.4）")
    if auto_decided:
        if team.get("confirm_granularity") != "direct_through":
            raise ValueError(
                f"发散节点「{node}」auto_decided=True 但本单粒度是 "
                f"{team.get('confirm_granularity')!r}——只有用户亲选 direct_through 直通档才允许 "
                f"AI 代拍方向，其余档位发散点必须用户收敛（D21·铁律0）")
        auth = team.get("granularity_quote") or ""
        if not auth:
            raise ValueError("直通档代拍必须有根授权原话（granularity_quote 为空=用户没亲口选过"
                             "直通，代拍即越权·D21 fail-closed）")
        if user_quote:
            raise ValueError("auto_decided=True 时 user_quote 必须为空——AI 不能编造用户原话；"
                             "真有用户拍板原话就不该走 auto 路径（D21·防假绿同一条纪律）")
        team.setdefault("divergences", []).append(
            {"node": node, "cards": list(cards), "chosen": chosen, "reason": reason,
             "user_quote": "", "auto_decided": True, "auth_quote": auth})
        return team
    if not user_quote:
        raise ValueError(f"发散节点「{node}」收敛必须带用户拍板原话 user_quote"
                         f"（发散点=硬停点·D18 FR1.3·铁律0）")
    # 批③🟡：疑似代填在写入前拦（启发式·见 _reject_suspected_proxy_quote）——放在 append 之前，
    # 守住"全部校验先行、全过才写入"的无半截纪律
    _reject_suspected_proxy_quote(user_quote)
    team.setdefault("divergences", []).append(
        {"node": node, "cards": list(cards), "chosen": chosen, "reason": reason,
         "user_quote": user_quote})
    record_user_ack(team, f"方向收敛:{node}", user_quote)
    return team


def divergence_ledger(team: dict) -> list[dict]:
    """只读：发散-收敛精简台账 [{node, chosen, reason}]，供后续回灌管线消费（D18 FR6.4）。

    **用户的选择偏好是飞轮最金贵的知识（D18 FR6.4）**：方向卡是 AI 生成的、可再生成，但
    "用户在这些选项里选了哪个、为什么"只有这一份。回灌消费这份精简列表就够——全量 cards
    留在 team["divergences"] 原始记录里可回放，台账不背全量。

    auto_decided 条目滤掉（D21 防飞轮污染）：直通档 AI 代拍的不是用户偏好，回灌了飞轮
    就在学 AI 自己——代拍决策的去处是 assumption_ledger（交付时摊给用户验收）。
    """
    return [{"node": d.get("node"), "chosen": d.get("chosen"), "reason": d.get("reason")}
            for d in team.get("divergences") or [] if not d.get("auto_decided")]


def assumption_ledger(team: dict) -> list[dict]:
    """只读：直通档假设台账 [{node, chosen, reason, auth_quote}]——AI 代拍过哪些方向、为什么、
    依据哪句根授权（D21）。

    直通档的"以人为主"从过程操盘换成**验收操盘**：用户看不到过程里的每次收敛，就必须在交付时
    一眼看全"AI 替我假设了什么"。交付摊面/交接卡把这份台账带上（SKILL 工序），用户重点核对
    代拍项——发现假设歪了，改动走新版本（铁律4）。非直通档 team 返回空列表。
    """
    return [{"node": d.get("node"), "chosen": d.get("chosen"), "reason": d.get("reason"),
             "auth_quote": d.get("auth_quote")}
            for d in team.get("divergences") or [] if d.get("auto_decided")]


_DECKS_ROOT_DEFAULT = Path(__file__).resolve().parent.parent / "data" / "decks"


def divergence_history(decks_root=None) -> list[dict]:
    """跨 deck 聚合全部发散-收敛决策 → [{deck_id, node, chosen, reason}]（D19 FR4.2）。

    扫 decks_root（默认项目根 data/decks/）下每个 ``*/team_state.json``——**含已 published
    的 deck**（历史决策都算：published 只是产物只读，用户为什么那样拍板正是要跨单沉淀的
    偏好知识）。结果按 team_state.json 的 mtime 升序（旧→新·注入 prompt 时读起来是时间线），
    直接喂 ``strategy_prompts.prompt_divergence(history=...)``。

    韧性纪律（聚合读取器对脏数据要韧·不 raise 拒全部）：损坏 JSON / 非 dict / 缺
    node·chosen·reason 任一字段的条目**跳过并继续**——一份坏文件不该让全部历史偏好瞬间
    失明。这与 save_team 的 fail-closed 是两类场景：写入把门要严，跨库聚合要韧。

    **暂不做偏好画像提炼——2 条样本抽象必歪，等 5+ 条决策再人工评估是否提炼
    （过早抽象是飞轮大忌·D19 用户拍板）**：本函数永远只回原话记录，不做任何归纳/打标/
    聚类，消费方把原话注入 prompt 即止。
    """
    root = Path(decks_root) if decks_root is not None else _DECKS_ROOT_DEFAULT
    if not root.is_dir():
        return []
    try:
        files = sorted(root.glob("*/team_state.json"), key=lambda p: p.stat().st_mtime)
    except OSError:
        return []
    out: list[dict] = []
    for f in files:
        try:
            team = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            continue  # 坏文件跳过·别的 deck 的历史照读
        if not isinstance(team, dict):
            continue
        divergences = team.get("divergences")
        if not isinstance(divergences, list):
            continue
        for d in divergences:
            if not isinstance(d, dict):
                continue
            node, chosen, reason = d.get("node"), d.get("chosen"), d.get("reason")
            if not (node and chosen and reason):
                continue  # 缺字段的条目跳过（半截留痕不当偏好知识用）
            if d.get("auto_decided"):
                continue  # D21 防飞轮污染：直通档 AI 代拍的不是用户偏好——注入了 prompt，
                          # 往后的"按你过往偏好推荐"就在自我强化 AI 自己的选择
            out.append({"deck_id": f.parent.name, "node": node,
                        "chosen": chosen, "reason": reason})
    return out


def validate_planning_team(team: dict) -> dict:
    """校验 → {issues, valid}。fail-closed：至少分配1个角色 + 板块顺序不倒退（研究→Idea→执行→整合）
    + done 角色必有完整 user_summary（D18 FR1.1）+ confirm_granularity 合法（D18 FR1.2）。"""
    issues = []
    order = team.get("order", [])
    if not order:
        issues.append({"sev": "error", "msg": "未分配任何角色"})
    unknown = [rid for rid in order if rid not in ROLE_CATALOG]
    if unknown:
        issues.append({"sev": "error", "msg": f"未知角色 {unknown}"})
    board_rank = {b: i for i, b in enumerate(BOARDS)}
    ranks = [board_rank[ROLE_CATALOG[rid]["board"]] for rid in order if rid in ROLE_CATALOG]
    if any(ranks[i] > ranks[i + 1] for i in range(len(ranks) - 1)):
        issues.append({"sev": "error",
                       "msg": f"角色顺序跨板块倒退（应按 {'→'.join(BOARDS)} 推进，不回头）"})
    if order and "叙事策划" in ROLE_CATALOG and "叙事策划" in order and order[-1] != "叙事策划":
        issues.append({"sev": "warn",
                       "msg": "「叙事策划」不是接力链最后一个角色——它要读全部人的产出才能开工，通常应排最后"})
    # 软依赖顺序提醒（2026-07-01·D11二次调研核实：部分"看似平行"的角色其实是递进关系，
    # 如商业尽调策划建立在市场策划之上、线上线下推广策划在媒介策划分配渠道之后执行）——
    # warn不是error：真实场景允许跳过基础角色直接做（比如已经在别处做过市场研究），
    # 只是提醒确认是不是有意跳过，不强制要求。
    for rid in order:
        builds_on = ROLE_CATALOG.get(rid, {}).get("builds_on")
        if not builds_on:
            continue
        if builds_on not in order:
            issues.append({"sev": "warn",
                           "msg": f"{rid} 通常建立在 {builds_on} 之上，但这次没有分配 {builds_on}"
                                   f"——确认是不是有意跳过（比如别处已经做过），不是必须但容易漏想"})
        elif order.index(builds_on) > order.index(rid):
            issues.append({"sev": "warn",
                           "msg": f"{rid} 排在了 {builds_on} 前面——{builds_on} 通常该先做，确认顺序是不是反了"})
    # D18 FR1.2：确认粒度合法性——字段存在才查（旧落盘 team 没这个字段·已交付产物只读不追溯补字段），
    # new_planning_team/set_confirm_granularity 已在入口拦，这里兜"手改 json 塞非法值"的旁路。
    gran = team.get("confirm_granularity")
    if gran is not None and gran not in GRANULARITIES:
        issues.append({"sev": "error",
                       "msg": f"confirm_granularity={gran!r} 非法（应 {sorted(GRANULARITIES)} 之一·D18 FR1.2）"})
    # D18 FR1.1：done 角色必有完整 user_summary——"收工=已向用户摊过结论"要在数据上立得住，
    # 堵绕过 complete_role 直接手搓 status="done" 的旁路（同 spec_lock 被静默跳过是 D15 最高优先级
    # 缺口的教训：入口校验没有出口复查配合，等于没锁）。
    # D26 二轮扫盘：历史豁免语义——某品牌（D18 校验上线前交付·已 published 只读）用现行校验
    # 6 角色全 error，但**回填 user_summary=伪造历史**（当时没摊过结论就是没摊过·防假绿），
    # 改 deck 又违铁律4。判据同 handoff_to_production 的三态兼容：无 confirm_granularity 字段
    # = pre-D18 形态 → user_summary 缺失如实降 warn（历史 deck 校验上线前交付·非放行新单）。
    _pre_d18 = "confirm_granularity" not in team
    for rid in order:
        role = team.get("roles", {}).get(rid) or {}
        if role.get("status") != "done":
            continue
        us = (role.get("handoff") or {}).get("user_summary") or {}
        if not us.get("conclusion") or not [h for h in us.get("highlights") or [] if h]:
            if _pre_d18:
                issues.append({"sev": "warn",
                               "msg": f"{rid} user_summary 缺失（pre-D18 历史 team·该机制上线前交付"
                                      f"——如实标注不回填不伪造·D26 历史豁免；新单缺失仍是 error）"})
            else:
                issues.append({"sev": "error",
                               "msg": f"{rid} 已标 done 但 user_summary 缺失或不完整（conclusion + "
                                      f"highlights ≥1 条必填）——角色收工必须向用户摊结论（D18 FR1.1·铁律0）"})
    return {"issues": issues, "valid": not any(i["sev"] == "error" for i in issues)}


def check_open_questions_carried(team: dict) -> list[dict]:
    """遗留问题收口弱提示（2026-07-01·对标小说引擎伏笔未回收，问题收口调研 R-B）：全流程累积下来的
    open_questions，有没有明显"从头到尾没人再提过"的——只做存在性弱提示(open_question 关键片段是否
    出现在后续任一角色的 key_findings/decisions 文本里)，不做语义判断(判断"是否真的解决了"是人审的
    活，机检只提醒"这条可能被遗忘了，去确认一下")。子串匹配天然误报率偏高，是三条问题收口检查里
    最弱的一个信号，价值在于防极端情况(问题被完全忘记)，不追求精确。
    """
    out = []
    order = team.get("order", [])
    for i, rid in enumerate(order):
        role = team["roles"].get(rid) or {}
        if role.get("status") != "done":
            continue
        for q in role["handoff"]["open_questions"]:
            later_text = "".join(
                "".join(team["roles"][r2]["handoff"]["key_findings"]) +
                "".join(d.get("answer", "") for d in team["roles"][r2]["handoff"]["decisions"])
                for r2 in order[i + 1:] if team["roles"].get(r2, {}).get("status") == "done"
            )
            if q[:6] not in later_text and q not in later_text:
                out.append({"sev": "warn", "role": rid, "question": q,
                            "note": f"「{rid}」留的遗留问题「{q}」，后续角色产出里没找到明显呼应"
                                    f"（是被静默放弃了，还是真的处理了但没写进交接？）"})
    return out


def all_done(team: dict) -> bool:
    """全部分配的角色是否都已收工（leader 拿这个判断整份 deck 架构是否搭完）。"""
    order = team.get("order", [])
    return bool(order) and all(team["roles"].get(rid, {}).get("status") == "done" for rid in order)


def load_team(path) -> dict:
    """从磁盘读回团队状态——**防上下文丢失的硬保障**，不是可选功能：本会话可能被自动压缩，
    早前角色交接的细节不能只指望对话记忆，落盘才是真正靠得住的记录（同 storyline_state.py 模式）。
    """
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_team(team: dict, path) -> dict:
    """校验通过才写（fail-closed·非法拒写，同 storyline_state.py 模式）。"""
    r = validate_planning_team(team)
    if not r["valid"]:
        raise ValueError(f"策划团队非法·拒写：{r['issues']}")
    Path(path).write_text(json.dumps(team, ensure_ascii=False, indent=2), encoding="utf-8")
    return r
