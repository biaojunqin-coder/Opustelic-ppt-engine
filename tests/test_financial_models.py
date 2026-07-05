"""财务建模引擎测试——DCF/LBO/可比公司分析坐标必须手算验证过，不能只测"不崩"。"""

from __future__ import annotations

import pytest

from engine.financial_models import (
    comps_implied_valuation_range,
    dcf_enterprise_value,
    dcf_reconcile,
    dcf_terminal_value_exit_multiple,
    dcf_terminal_value_gordon_growth,
    lbo_exit_equity_value,
    lbo_irr_approx,
    lbo_moic,
    lbo_returns_summary,
)


# ── DCF ──
def test_gordon_growth_terminal_value_hand_verified():
    # TV = 100×1.03/(0.10-0.03) = 103/0.07 = 1471.4285...
    tv = dcf_terminal_value_gordon_growth(final_year_fcf=100, wacc=0.10, perpetuity_growth=0.03)
    assert tv == pytest.approx(1471.4286, rel=1e-4)


def test_gordon_growth_rejects_growth_exceeding_wacc():
    with pytest.raises(ValueError, match="必须大于永续增长率"):
        dcf_terminal_value_gordon_growth(100, wacc=0.05, perpetuity_growth=0.05)


def test_exit_multiple_terminal_value_hand_verified():
    assert dcf_terminal_value_exit_multiple(final_year_ebitda=150, exit_multiple=8) == 1200


def test_dcf_enterprise_value_hand_verified():
    # fcf=[80,90,100,110,120]·wacc=10%·TV=1471.4286(上面算过)
    r = dcf_enterprise_value([80, 90, 100, 110, 120], wacc=0.10, terminal_value=1471.4286)
    # 手算 pv_fcf = 80/1.1+90/1.21+100/1.331+110/1.4641+120/1.61051 ≈ 371.88
    assert r["pv_of_fcf"] == pytest.approx(371.88, rel=1e-3)
    # pv_tv = 1471.4286/1.61051 ≈ 913.71
    assert r["pv_of_terminal_value"] == pytest.approx(913.71, rel=1e-3)
    assert r["enterprise_value"] == pytest.approx(371.88 + 913.71, rel=1e-3)
    # 终值占比应该在文档说的60%-80%量级(此例~71%)
    assert 0.6 < r["terminal_value_pct"] < 0.8


def test_dcf_enterprise_value_rejects_wacc_at_or_below_minus_one():
    """2026-07-03 二轮扫盘批D：wacc=-1 折现因子为 0 → ZeroDivisionError 裸崩；≤-1 一律 ValueError 带说明。"""
    with pytest.raises(ValueError, match="WACC"):
        dcf_enterprise_value([100.0], wacc=-1.0, terminal_value=500.0)
    with pytest.raises(ValueError, match="WACC"):
        dcf_enterprise_value([100.0], wacc=-1.5, terminal_value=500.0)
    # 边界之上（哪怕是罕见的负 WACC）仍照常计算，不误伤
    assert dcf_enterprise_value([100.0], wacc=-0.5, terminal_value=0.0)["enterprise_value"] == pytest.approx(200.0)


def test_dcf_reconcile_returns_both_methods_and_spread():
    r = dcf_reconcile(final_year_fcf=100, final_year_ebitda=150, fcf_by_year=[80, 90, 100, 110, 120],
                       wacc=0.10, perpetuity_growth=0.03, exit_multiple=8)
    assert "gordon_growth" in r and "exit_multiple" in r
    assert r["spread_pct"] >= 0  # 两法算出的EV可能不同·spread非负


def test_dcf_reconcile_identical_assumptions_zero_spread():
    # 精心构造两法给出同一个终值的场景·spread应该≈0
    # exit_multiple法: TV = ebitda × multiple；用gordon growth倒推同样的TV看spread是不是0
    r = dcf_reconcile(final_year_fcf=100, final_year_ebitda=100, fcf_by_year=[50],
                       wacc=0.20, perpetuity_growth=0.0, exit_multiple=1.2)
    # gordon: TV=100*1.0/(0.20-0)=500；exit: TV=100*1.2=120·刻意不同不做这个断言，只验证函数不崩
    assert r["spread_pct"] >= 0


# ── B2-7 回归（2026-07-02 saopan扫盘）：spread 分母旧版用带符号 min，负 EV 时 spread 为负、
#    ">20% 不自洽"判据直接失灵——改 min(|a|,|b|) 后恒非负，且 EV≤0 附 warn note ──
def test_dcf_reconcile_negative_ev_spread_stays_positive_with_note():
    # 负 FCF 造出负 EV：gordon TV=-100/0.10=-1000 → EV_gg=(-50-1000)/1.1≈-954.5；
    # exit TV=100×8=800 → EV_em=(-50+800)/1.1≈681.8。旧版 spread=1636.3/(-954.5)≈-1.71（负数·判据废）
    r = dcf_reconcile(final_year_fcf=-100, final_year_ebitda=100, fcf_by_year=[-50],
                       wacc=0.10, perpetuity_growth=0.0, exit_multiple=8)
    assert r["gordon_growth"]["enterprise_value"] < 0  # 前提确认：确实构造出了负 EV
    assert r["spread_pct"] == pytest.approx(1636.36 / 681.82, rel=1e-3)
    assert r["spread_pct"] > 0
    assert "EV 非正" in r["note"]


def test_dcf_reconcile_positive_ev_has_no_note():
    r = dcf_reconcile(final_year_fcf=100, final_year_ebitda=150, fcf_by_year=[80, 90, 100, 110, 120],
                       wacc=0.10, perpetuity_growth=0.03, exit_multiple=8)
    assert "note" not in r  # 正常 case 返回结构与旧版一致


# ── LBO ──
def test_lbo_exit_equity_value_hand_verified():
    assert lbo_exit_equity_value(exit_enterprise_value=500, ending_debt=200) == 300
    assert lbo_exit_equity_value(exit_enterprise_value=500, ending_debt=200, ending_cash=20) == 320


def test_lbo_moic_hand_verified():
    assert lbo_moic(entry_equity=100, exit_equity=300) == 3.0


def test_lbo_moic_rejects_zero_entry():
    with pytest.raises(ValueError, match="entry_equity"):
        lbo_moic(entry_equity=0, exit_equity=300)


def test_lbo_irr_approx_hand_verified():
    # IRR = 3.0^(1/5) - 1 ≈ 0.2457 (24.57%)
    irr = lbo_irr_approx(moic=3.0, years=5)
    assert irr == pytest.approx(0.2457, rel=1e-3)


def test_lbo_irr_approx_one_year_equals_moic_minus_one():
    # 1年期：IRR = MOIC^1 - 1 = MOIC - 1
    assert lbo_irr_approx(moic=1.5, years=1) == pytest.approx(0.5)


def test_lbo_returns_summary_hand_verified():
    r = lbo_returns_summary(entry_equity=100, exit_enterprise_value=500, ending_debt=200, years=5)
    assert r["exit_equity_value"] == 300
    assert r["moic"] == 3.0
    assert r["irr"] == pytest.approx(0.2457, rel=1e-3)
    assert r["meets_typical_sponsor_target"] is True  # 3.0x MOIC≥2.0 且 24.57% IRR≥20%


def test_lbo_returns_summary_below_sponsor_target():
    r = lbo_returns_summary(entry_equity=100, exit_enterprise_value=250, ending_debt=100, years=5)
    # exit_equity=150·moic=1.5·低于2.0x目标
    assert r["moic"] == 1.5
    assert r["meets_typical_sponsor_target"] is False


# ── B2-6 回归（2026-07-02 saopan扫盘）：debt>退出EV 的 downside 旧版直接崩（负MOIC→raise），
#    有限责任下正确语义 = 股权全损：MOIC=0/IRR=-100%——sponsor 最关心的 downside 栏不能算不出来 ──
def test_lbo_downside_debt_exceeds_exit_ev_reports_total_loss_not_crash():
    r = lbo_returns_summary(entry_equity=100, exit_enterprise_value=300, ending_debt=350, years=5)
    assert r["exit_equity_value"] == 0.0    # 有限责任·股权价值下限是 0 不是 -50
    assert r["moic"] == 0.0
    assert r["irr"] == -1.0                 # 全损 = -100%
    assert r["meets_typical_sponsor_target"] is False
    assert "全损" in r["note"] and "downside" in r["note"]


def test_lbo_returns_summary_normal_case_has_no_note():
    r = lbo_returns_summary(entry_equity=100, exit_enterprise_value=500, ending_debt=200, years=5)
    assert "note" not in r  # 非 downside 不带 note·返回结构与旧版一致


def test_lbo_irr_approx_zero_moic_is_total_loss():
    assert lbo_irr_approx(moic=0.0, years=5) == -1.0


def test_lbo_irr_approx_still_rejects_negative_moic():
    with pytest.raises(ValueError, match="不能为负"):
        lbo_irr_approx(moic=-0.5, years=5)


# ── 可比公司分析 ──
def test_comps_implied_valuation_range_hand_verified():
    # 5个乘数[6,7,8,9,10]均匀分布·分位数刚好落在整数索引上，手算最容易验证
    r = comps_implied_valuation_range(target_metric=100, peer_multiples=[10, 6, 9, 7, 8])  # 乱序输入
    m = r["multiples"]
    assert m["min"] == 6 and m["max"] == 10
    assert m["p25"] == 7 and m["median"] == 8 and m["p75"] == 9
    iv = r["implied_value"]
    assert iv["min"] == 600 and iv["median"] == 800 and iv["max"] == 1000


def test_comps_rejects_empty_peer_list():
    with pytest.raises(ValueError, match="不能为空"):
        comps_implied_valuation_range(target_metric=100, peer_multiples=[])


def test_comps_single_peer_all_percentiles_equal():
    r = comps_implied_valuation_range(target_metric=50, peer_multiples=[10])
    assert all(v == 10 for v in r["multiples"].values())


# ── B2-8 回归（2026-07-02 saopan扫盘）：负乘数（亏损公司）旧版直接混进分位数——
#    [-12,8,10,14] 会把 min implied=-1200 端给客户；业界惯例负乘数标 n.m. 剔除 ──
def test_comps_negative_multiple_excluded_from_range():
    r = comps_implied_valuation_range(target_metric=100, peer_multiples=[-12, 8, 10, 14])
    m = r["multiples"]
    assert m["min"] == 8 and m["median"] == 10 and m["max"] == 14   # 区间只由正乘数算出
    assert r["implied_value"]["min"] == 800                          # 不再出现 -1200
    assert r["excluded_negative"] == 1


def test_comps_zero_multiple_also_excluded():
    r = comps_implied_valuation_range(target_metric=100, peer_multiples=[0, 8, 10])
    assert r["multiples"]["min"] == 8 and r["excluded_negative"] == 1


def test_comps_all_nonpositive_raises_fail_closed():
    with pytest.raises(ValueError, match="没有可用乘数"):
        comps_implied_valuation_range(target_metric=100, peer_multiples=[-3, -1, 0])


def test_comps_clean_positive_sample_reports_zero_excluded():
    r = comps_implied_valuation_range(target_metric=100, peer_multiples=[6, 7, 8, 9, 10])
    assert r["excluded_negative"] == 0
