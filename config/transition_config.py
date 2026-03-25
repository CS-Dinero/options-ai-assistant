"""
config/transition_config.py
Hard-gate rules for the skew-driven transition engine.
All thresholds live here — nothing is hardcoded in engine files.
"""
from __future__ import annotations

# Per-symbol credit minimums and liquidity rules
SYMBOL_RULES: dict = {
    "SPY":  {"min_flip_credit": 0.80, "max_ba_pct": 0.08},
    "QQQ":  {"min_flip_credit": 0.90, "max_ba_pct": 0.08},
    "IWM":  {"min_flip_credit": 0.80, "max_ba_pct": 0.10},
    "AAPL": {"min_flip_credit": 0.90, "max_ba_pct": 0.10},
    "MSFT": {"min_flip_credit": 0.90, "max_ba_pct": 0.10},
    "TSLA": {"min_flip_credit": 2.00, "max_ba_pct": 0.14},
    "NVDA": {"min_flip_credit": 1.50, "max_ba_pct": 0.14},
    "AMD":  {"min_flip_credit": 1.00, "max_ba_pct": 0.12},
}

# Default for any symbol not in SYMBOL_RULES
DEFAULT_SYMBOL_RULE: dict = {"min_flip_credit": 1.00, "max_ba_pct": 0.12}

# Entry criteria for scanning deep ITM calendars
ENTRY_RULES: dict = {
    "min_long_delta_abs":                 0.80,
    "max_long_extrinsic_pct_of_premium":  0.35,
    "short_dte_min":                       7,
    "short_dte_max":                      21,
    "long_dte_min":                       35,
    "long_dte_max":                       90,
    "min_expiry_gap_days":                21,
}

# Transition approval gates
TRANSITION_RULES: dict = {
    "require_net_credit_for_flip":  True,
    "require_future_rollability":   True,
    "min_future_roll_score":        65.0,
    "min_structure_score":          70.0,
    "max_assignment_risk_score":    70.0,
    "allow_vertical_conversion":    True,
}

# Short-leg target zone for future harvestability
ROLLABILITY_RULES: dict = {
    "target_short_delta_low":       0.18,
    "target_short_delta_high":      0.42,
    "min_next_cycle_credit_ratio":  0.10,   # next_credit / current_risk_basis
    "max_itm_short_pct":            0.03,
}

# Composite scoring weights (must sum to 1.0)
SCORING_WEIGHTS: dict = {
    "credit_score":       0.25,
    "skew_score":         0.20,
    "future_roll_score":  0.20,
    "structure_score":    0.15,
    "liquidity_score":    0.10,
    "assignment_score":   0.10,
}

def get_symbol_rule(symbol: str) -> dict:
    return SYMBOL_RULES.get(str(symbol).upper(), DEFAULT_SYMBOL_RULE)
