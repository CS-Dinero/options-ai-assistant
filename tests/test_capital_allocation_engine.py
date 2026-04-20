"""tests/test_capital_allocation_engine.py"""
from allocation.capital_allocation_models import (
    AccountState, StrategyPerformanceSnapshot, AllocationInput,
)
from allocation.capital_allocation_engine import (
    allocate_capital, allocate_xsp_position,
    base_strategy_weight, performance_multiplier, is_advanced_structure,
)

def _account(equity=5000.0, open_risk=0.0):
    return AccountState(equity, equity, equity, equity*3, 0.0, open_risk)

def _perf(wr=0.70, ror=0.25, fc=0.10, n=20):
    return StrategyPerformanceSnapshot("XSP_CREDIT_SPREAD", wr, ror, fc, n)

def test_xsp_credit_spread_highest_weight():
    assert base_strategy_weight("XSP_CREDIT_SPREAD") == 1.0
    assert base_strategy_weight("XSP_DEBIT_SPREAD") < 1.0
    assert base_strategy_weight("XSP_CREDIT_DIAGONAL") < base_strategy_weight("XSP_DEBIT_SPREAD")

def test_spread_aliases_correct():
    assert base_strategy_weight("BULL_PUT_SPREAD") == 1.0
    assert base_strategy_weight("BEAR_CALL_SPREAD") == 1.0

def test_good_performance_boosts():
    p_good = _perf(0.70, 0.25, 0.05)
    p_bad  = _perf(0.40, 0.05, 0.40)
    assert performance_multiplier(p_good) > performance_multiplier(p_bad)

def test_none_perf_returns_one():
    assert performance_multiplier(None) == 1.0

def test_few_trades_returns_one():
    assert performance_multiplier(_perf(n=5)) == 1.0

def test_high_force_close_penalizes():
    assert performance_multiplier(_perf(wr=0.50, ror=0.10, fc=0.40)) < 1.0

def test_advanced_blocked_in_high_vol():
    d = allocate_capital(_account(), "HIGH_VOL_DEFENSE", "XSP_CREDIT_DIAGONAL", None, 10.0)
    assert d.allow_new_entries is False
    assert d.max_contracts == 0

def test_spread_not_blocked_in_high_vol():
    # $5000 × 20% = $1000 total, × 1% = $50, × 1.0 = $50 → at $10/ct = 2cts, cap=2
    d = allocate_capital(_account(), "HIGH_VOL_DEFENSE", "XSP_CREDIT_SPREAD", None, 10.0)
    assert d.allow_new_entries is True

def test_approval_with_good_perf():
    # $10k equity → more room; $20/ct risk
    account = _account(equity=10000.0)
    d = allocate_capital(account, "PREMIUM_SELLING", "XSP_CREDIT_SPREAD", _perf(), 20.0)
    assert d.allow_new_entries is True
    assert d.max_contracts >= 1
    assert d.target_weight > 1.0  # good perf boosts above 1.0

def test_exposure_cap_blocks():
    # $5000 × 35% = $1750 cap, $2500 already used → nothing left
    d = allocate_capital(_account(5000.0, open_risk=2500.0), "NEUTRAL_TIME_SPREADS",
                         "XSP_CREDIT_SPREAD", None, 10.0)
    assert d.allow_new_entries is False

def test_backward_compat_wrapper():
    inp = AllocationInput(5000.0, "NEUTRAL_TIME_SPREADS", "BULL_PUT_SPREAD", 10.0, 0.0)
    d = allocate_xsp_position(inp)
    assert d.allow_new_entries is True
    assert d.max_contracts >= 1
