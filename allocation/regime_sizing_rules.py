"""allocation/regime_sizing_rules.py — Per-regime sizing parameters."""
from dataclasses import dataclass

@dataclass(slots=True)
class RegimeSizingRule:
    max_exposure_pct: float
    max_risk_per_trade_pct: float
    contracts_cap: int

REGIME_SIZING: dict[str, RegimeSizingRule] = {
    "PREMIUM_SELLING":    RegimeSizingRule(0.30, 0.015, 4),
    "NEUTRAL_TIME_SPREADS": RegimeSizingRule(0.35, 0.020, 5),
    "TRENDING":           RegimeSizingRule(0.30, 0.020, 4),
    "LOW_VOL_EXPANSION":  RegimeSizingRule(0.25, 0.015, 3),
    "HIGH_VOL_DEFENSE":   RegimeSizingRule(0.20, 0.010, 2),
}

def get_sizing_rule(regime: str) -> RegimeSizingRule:
    return REGIME_SIZING.get(regime.upper(), REGIME_SIZING["NEUTRAL_TIME_SPREADS"])
