"""policy/xsp_policy_variants.py — Regime-based policy variants."""
from policy.xsp_strategy_policy import XSPStrategyPolicy
from dataclasses import replace

def premium_selling_policy() -> XSPStrategyPolicy:
    """High IV premium selling — tighter credit standards, smaller size."""
    return replace(XSPStrategyPolicy(),
        credit_min_credit=0.40, credit_min_cwr=0.40,
        max_risk_per_trade_pct=0.015, max_total_exposure_pct=0.30)

def neutral_policy() -> XSPStrategyPolicy:
    """Neutral / range-bound — conservative, spreads only."""
    return XSPStrategyPolicy()

def trending_policy() -> XSPStrategyPolicy:
    """Trending — debit spreads prioritized, wider width."""
    return replace(XSPStrategyPolicy(),
        debit_spread_widths=(1.0, 2.0, 3.0),
        debit_min_reward_risk=0.60,
        max_total_exposure_pct=0.30)

def high_vol_defense_policy() -> XSPStrategyPolicy:
    """High vol shock — smallest size, strictest entry."""
    return replace(XSPStrategyPolicy(),
        max_contracts_cap=2,
        credit_min_credit=0.50, credit_min_cwr=0.45,
        max_risk_per_trade_pct=0.01, max_total_exposure_pct=0.20)
