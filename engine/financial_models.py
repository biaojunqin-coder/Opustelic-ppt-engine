"""财务建模引擎——DCF / LBO / 可比公司分析确定性计算（2026-07-01·数据建模策划专业化·D12）。

跟 `chart_shapes.py` 同一类问题：DCF终值/LBO回报(IRR/MOIC)/可比公司隐含估值都是可计算的数学，
不该让 Claude 在"数据建模策划"角色的引导对齐里逐次手算（估值模型比图表坐标更容易算错、错了更难
肉眼发现），该写成确定性函数——调用这里算，不现算。

核心公式联网核实自投行培训权威渠道，带来源链接：
- DCF终值两法(Gordon Growth/Exit Multiple)+"最佳实践是两个都算再互相校验"：
  https://www.wallstreetprep.com/knowledge/terminal-value/
- LBO的MOIC/IRR定义+paper LBO简化算法+sponsor目标区间(2.0-3.0x MOIC/20-25%+ IRR)：
  https://www.wallstreetprep.com/knowledge/moic-multiple-on-invested-capital/ ·
  https://www.streetofwalls.com/finance-training-courses/private-equity-training/paper-lbo-model-example/
- 可比公司分析(算multiple的分位数区间而非单点估值)：
  https://www.wallstreetprep.com/knowledge/comparable-company-analysis-comps/ ·
  https://corporatefinanceinstitute.com/resources/valuation/comparable-company-analysis/
"""

from __future__ import annotations


# ============================== DCF（现金流折现法） ==============================

def dcf_terminal_value_gordon_growth(final_year_fcf: float, wacc: float, perpetuity_growth: float) -> float:
    """Gordon Growth 终值：TV = FCF×(1+g)/(WACC-g)。

    出处【Wall Street Prep - Terminal Value】：g(永续增长率)通常锚定长期GDP增速，
    成熟企业惯例区间 2.0%-3.5%，g 必须小于 WACC 否则终值发散为无穷（数学上就不成立，直接拒绝）。
    """
    if wacc <= perpetuity_growth:
        raise ValueError(f"WACC({wacc})必须大于永续增长率({perpetuity_growth})，否则终值发散为无穷")
    return final_year_fcf * (1 + perpetuity_growth) / (wacc - perpetuity_growth)


def dcf_terminal_value_exit_multiple(final_year_ebitda: float, exit_multiple: float) -> float:
    """Exit Multiple 终值：TV = EBITDA × Exit Multiple。

    出处【Wall Street Prep】：exit multiple 来自可比公司交易乘数/先例交易乘数（不是凭空定的数）。
    """
    return final_year_ebitda * exit_multiple


def dcf_enterprise_value(fcf_by_year: list[float], wacc: float, terminal_value: float) -> dict:
    """DCF企业价值 = Σ FCF_t/(1+WACC)^t + TV/(1+WACC)^n。出处【Street of Walls - DCF】。

    fcf_by_year 从第1年到第n年顺序排列。返回附带 `terminal_value_pct`（终值占比）——出处提醒
    "终值通常占DCF总价值60%-80%，是最敏感假设"，这个占比本身就是该不该信这份估值的重要信号，
    调用方该把这个数字亮出来给用户看，不能只报一个企业价值数字就完事。
    """
    # 2026-07-03 二轮扫盘批D：wacc=-1 时折现因子 (1+WACC)=0，直接 ZeroDivisionError 裸崩；
    # wacc<-1 折现因子为负更是数学上无意义（奇数年"折现"出负号）。fail-closed 带说明拒绝。
    if wacc <= -1:
        raise ValueError(f"WACC({wacc})≤-100%：折现因子(1+WACC)为零或负，折现无数学意义"
                         f"——WACC 应为小数形式（如 9% 传 0.09），检查输入")
    n = len(fcf_by_year)
    pv_fcf = sum(fcf / (1 + wacc) ** t for t, fcf in enumerate(fcf_by_year, start=1))
    pv_tv = terminal_value / (1 + wacc) ** n
    ev = pv_fcf + pv_tv
    return {"pv_of_fcf": pv_fcf, "pv_of_terminal_value": pv_tv, "enterprise_value": ev,
            "terminal_value_pct": (pv_tv / ev) if ev else 0.0}


def dcf_reconcile(final_year_fcf: float, final_year_ebitda: float, fcf_by_year: list[float],
                   wacc: float, perpetuity_growth: float, exit_multiple: float) -> dict:
    """两种终值法都跑一遍再对照——出处【Wall Street Prep】"best practice不是二选一，是两个都算
    再互相校验"。返回 {gordon_growth, exit_multiple, spread_pct[, note]}——spread过大（如>20%）提示
    两组假设互相不自洽，该回头检查 g/WACC/exit_multiple 是不是选得有问题，而不是随便挑一个数字用；
    任一 EV≤0 时附 note 警示（此时 spread 判据仅供参考）。
    """
    tv_gg = dcf_terminal_value_gordon_growth(final_year_fcf, wacc, perpetuity_growth)
    tv_em = dcf_terminal_value_exit_multiple(final_year_ebitda, exit_multiple)
    r_gg = dcf_enterprise_value(fcf_by_year, wacc, tv_gg)
    r_em = dcf_enterprise_value(fcf_by_year, wacc, tv_em)
    ev_gg, ev_em = r_gg["enterprise_value"], r_em["enterprise_value"]
    # 2026-07-02 saopan扫盘揪出：spread 分母旧版用带符号 min——任一 EV 为负时分母为负，spread 算成
    # 负数，">20% 提示不自洽"的判据直接失灵。改用 min(|a|,|b|)（分母为 0 记 inf），spread 恒非负；
    # EV≤0 本身就说明 FCF/假设有问题，附 warn note 亮给用户而不是闷头给个数。
    denom = min(abs(ev_gg), abs(ev_em))
    spread = abs(ev_gg - ev_em) / denom if denom else float("inf")
    out = {"gordon_growth": r_gg, "exit_multiple": r_em, "spread_pct": spread}
    if ev_gg <= 0 or ev_em <= 0:
        out["note"] = "两法 EV 非正·检查 FCF/假设是否自洽（EV≤0 时 spread 判据仅供参考，先修数据再谈校验）"
    return out


# ============================== LBO（杠杆收购）回报 ==============================

def lbo_exit_equity_value(exit_enterprise_value: float, ending_debt: float, ending_cash: float = 0.0) -> float:
    """Exit Equity Value = Exit TEV − Ending Debt + Ending Cash。出处【Wall Street Prep paper LBO】。"""
    return exit_enterprise_value - ending_debt + ending_cash


def lbo_moic(entry_equity: float, exit_equity: float) -> float:
    """MOIC = Total Capital Returned / Total Capital Invested。出处【Wall Street Prep - MOIC】。"""
    if entry_equity <= 0:
        raise ValueError("entry_equity 必须 > 0")
    return exit_equity / entry_equity


def lbo_irr_approx(moic: float, years: float) -> float:
    """简化 IRR（paper LBO 标准算法，假设单次进入单次退出、无中间分红/追加投资）：
    IRR = MOIC^(1/年数) − 1。出处【Wall Street Prep - IRR】。

    ⚠️ 有中间现金流（分红/追加投资）的真实LBO需要完整现金流序列算IRR（如 numpy_financial.irr
    或等价牛顿迭代法），这个简化版只适用于"一笔进一笔出"的估算场景——调用前先确认这笔交易是不是
    这种简单结构，不是的话这个数字会算错，别硬套。
    """
    if years <= 0:
        raise ValueError("years 必须 > 0")
    if moic < 0:
        raise ValueError("moic 不能为负")
    if moic == 0:
        # 2026-07-02 saopan扫盘补：股权全损（downside 场景·见 lbo_returns_summary）——
        # 有限责任下最多亏光本金，IRR 语义下限就是 -100%，显式放行别让 0**x 的浮点路径背语义。
        return -1.0
    return moic ** (1 / years) - 1


def lbo_returns_summary(entry_equity: float, exit_enterprise_value: float, ending_debt: float,
                         years: float, ending_cash: float = 0.0) -> dict:
    """一次性算完 LBO 核心回报指标。返回 {exit_equity_value, moic, irr, meets_typical_sponsor_target
    [, note]}——meets 一项对照【Wall Street Prep】sponsor 常见目标区间(2.0-3.0x MOIC/20-25%+ IRR·约5年)
    给个快速参照，不是说没达到这个区间这笔交易就一定不好，只是喂一个行业惯例基准，判断权仍在人。
    退出时债务超过企业价值（downside）→ 股权全损：exit_equity_value=0/MOIC=0/IRR=-100%，附 note 说明。
    """
    # 2026-07-02 saopan扫盘揪出：debt>退出EV 的 downside 场景旧版直接崩（负 exit_equity → 负 MOIC
    # → lbo_irr_approx raise），而有限责任下的正确语义是"股权全损"：MOIC=0、IRR=-100%。
    # sponsor 的 downside case 恰恰是 deck 里最要紧的一栏，不能连算都算不出来。
    raw_exit_equity = lbo_exit_equity_value(exit_enterprise_value, ending_debt, ending_cash)
    exit_equity = max(0.0, raw_exit_equity)
    moic = lbo_moic(entry_equity, exit_equity)
    irr = lbo_irr_approx(moic, years)
    out = {
        "exit_equity_value": exit_equity, "moic": moic, "irr": irr,
        "meets_typical_sponsor_target": moic >= 2.0 and irr >= 0.20,
    }
    if raw_exit_equity < 0:
        out["note"] = (f"退出时债务超过企业价值（缺口 {-raw_exit_equity:.1f}）·股权全损（downside 场景）——"
                       f"有限责任下股东最多亏光本金，MOIC=0/IRR=-100%")
    return out


# ============================== 可比公司分析（Trading Comps） ==============================

def _percentile(sorted_vals: list[float], p: float) -> float:
    """线性插值分位数（p∈[0,1]），sorted_vals 必须已排序。"""
    n = len(sorted_vals)
    idx = p * (n - 1)
    lo, hi = int(idx), min(int(idx) + 1, n - 1)
    frac = idx - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


def comps_implied_valuation_range(target_metric: float, peer_multiples: list[float]) -> dict:
    """可比公司隐含估值区间——出处【CFI/Wall Street Prep】：算 peer multiple 的 min/25分位/中位数/
    75分位/max，各自乘 target_metric 得一个**区间**而非单点估值（"不是精确测量，是给市场定价划一个
    参照区间"，出处同上）。≤0 的乘数按业界惯例标 n.m. 剔除，返回值附 excluded_negative 计数
    （deck 里该把"剔了几家、为什么"亮出来，不能只给区间）。

    ⚠️ `target_metric` 必须跟 multiple 的分子分母口径匹配（EV系multiple如EV/EBITDA要配企业层面
    指标，P/E这类权益乘数要配净利润这类权益层面指标）——出处【CFI】"the represented investor
    group must match on both the numerator and the denominator"，这是语义判断不是数学问题，
    这个函数不做口径校验，调用方（人/Claude）自己对齐好口径再传进来。
    """
    if not peer_multiples:
        raise ValueError("peer_multiples 不能为空")
    # 2026-07-02 saopan扫盘揪出：负/零乘数（亏损公司的 P/E、负 EBITDA 的 EV/EBITDA）此前直接混进
    # 分位数——[-12,8,10,14] 会把 min implied=-1200 端给客户。业界惯例是负乘数标 n.m.（not
    # meaningful）剔除样本，出处【Wall Street Prep - Comps】。剔完为空 → raise（fail-closed）。
    valid = [m for m in peer_multiples if m > 0]
    excluded = len(peer_multiples) - len(valid)
    if not valid:
        raise ValueError("peer_multiples 全部 ≤0（负/零乘数业界标 n.m. 剔除）——没有可用乘数，"
                         "无法算隐含估值区间；换一组可比公司或换估值口径")
    sorted_m = sorted(valid)
    percentiles = {"min": sorted_m[0], "p25": _percentile(sorted_m, 0.25),
                   "median": _percentile(sorted_m, 0.5), "p75": _percentile(sorted_m, 0.75),
                   "max": sorted_m[-1]}
    return {"multiples": percentiles,
            "implied_value": {k: target_metric * v for k, v in percentiles.items()},
            "excluded_negative": excluded}
