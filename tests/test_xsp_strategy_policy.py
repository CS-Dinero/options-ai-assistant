"""tests/test_xsp_strategy_policy.py"""
from policy.xsp_policy_loader import load_xsp_policy
from policy.xsp_policy_validator import validate_xsp_policy

def test_all_variants_valid():
    for regime in ["PREMIUM_SELLING","NEUTRAL_TIME_SPREADS","TRENDING","HIGH_VOL_DEFENSE"]:
        p = load_xsp_policy(regime)
        valid, errs = validate_xsp_policy(p)
        assert valid, f"{regime}: {errs}"
        assert errs == []

def test_high_vol_smaller_size():
    normal = load_xsp_policy("NEUTRAL_TIME_SPREADS")
    hv     = load_xsp_policy("HIGH_VOL_DEFENSE")
    assert hv.max_contracts_cap < normal.max_contracts_cap
    assert hv.max_risk_per_trade_pct < normal.max_risk_per_trade_pct
