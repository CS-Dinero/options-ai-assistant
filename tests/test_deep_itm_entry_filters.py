"""tests/test_deep_itm_entry_filters.py — Entry filter pass/fail correctness."""
from scanner.deep_itm_entry_filters import (
    DeepITMEntryFilterConfig, compute_liquidity_score, evaluate_deep_itm_entry_filters,
)
from tests.fixtures.deep_itm_campaign_fixtures import (
    long_put_deep_itm_valid, short_put_valid, long_put_expensive,
)

def test_valid_deep_itm_entry_filters():
    cfg=DeepITMEntryFilterConfig(long_delta_min=0.70,long_delta_max=0.92,
        max_entry_debit_width_ratio=0.35,max_long_extrinsic_cost=8.0,
        min_projected_recovery_ratio=1.20,min_future_roll_score=60.0,min_open_interest=50,min_volume=5)
    ll=long_put_deep_itm_valid(); sl=short_put_valid()
    liq=compute_liquidity_score(ll,sl,cfg)
    result=evaluate_deep_itm_entry_filters(250.0,"PUT",ll,sl,45,10,25.0,7.5,10.5,72.0,liq,85.0,cfg)
    assert result.passed is True
    assert round(result.entry_debit_width_ratio,2) == 0.30
    assert round(result.long_intrinsic_value,2) == 20.00
    assert round(result.long_extrinsic_cost,2) == 3.00
    assert round(result.projected_recovery_ratio,2) == 1.40
    assert result.entry_cheapness_score > 65

def test_reject_expensive_entry():
    cfg=DeepITMEntryFilterConfig(max_entry_debit_width_ratio=0.35,max_long_extrinsic_cost=8.0,
        min_projected_recovery_ratio=1.20,min_future_roll_score=60.0,min_open_interest=50,min_volume=5)
    ll=long_put_expensive(); sl=short_put_valid()
    liq=compute_liquidity_score(ll,sl,cfg)
    result=evaluate_deep_itm_entry_filters(250.0,"PUT",ll,sl,45,10,25.0,14.5,10.5,72.0,liq,85.0,cfg)
    assert result.passed is False
    assert any("ratio" in r.lower() or "debit" in r.lower() for r in result.reasons)
    assert any("extrinsic" in r.lower() for r in result.reasons)

def test_reject_weak_future_roll():
    cfg=DeepITMEntryFilterConfig(max_entry_debit_width_ratio=0.35,max_long_extrinsic_cost=8.0,
        min_projected_recovery_ratio=1.20,min_future_roll_score=60.0,min_open_interest=50,min_volume=5)
    ll=long_put_deep_itm_valid(); sl=short_put_valid()
    liq=compute_liquidity_score(ll,sl,cfg)
    result=evaluate_deep_itm_entry_filters(250.0,"PUT",ll,sl,45,10,25.0,7.5,5.0,42.0,liq,85.0,cfg)
    assert result.passed is False
    assert any("roll" in r.lower() for r in result.reasons)
