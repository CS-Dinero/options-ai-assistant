"""policy/xsp_policy_loader.py — Load the right policy for a given regime."""
from policy.xsp_strategy_policy import XSPStrategyPolicy
from policy.xsp_policy_variants import (
    premium_selling_policy, neutral_policy, trending_policy, high_vol_defense_policy
)

REGIME_POLICY_MAP = {
    "PREMIUM_SELLING":       premium_selling_policy,
    "NEUTRAL_TIME_SPREADS":  neutral_policy,
    "TRENDING":              trending_policy,
    "LOW_VOL_EXPANSION":     trending_policy,
    "HIGH_VOL_DEFENSE":      high_vol_defense_policy,
}

def load_xsp_policy(regime: str) -> XSPStrategyPolicy:
    fn = REGIME_POLICY_MAP.get(regime.upper(), neutral_policy)
    return fn()
