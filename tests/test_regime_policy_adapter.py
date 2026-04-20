"""tests/test_regime_policy_adapter.py"""
from regime.regime_policy_adapter import run_xsp_credit_or_debit

def test_premium_selling_runs_credit():
    r = run_xsp_credit_or_debit("PREMIUM_SELLING")
    assert r["run_credit"] is True
    assert r["run_debit"] is False

def test_trending_runs_debit():
    r = run_xsp_credit_or_debit("TRENDING")
    assert r["run_debit"] is True
    assert r["run_credit"] is False
