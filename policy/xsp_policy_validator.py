"""policy/xsp_policy_validator.py — Validate XSP policy values."""
from __future__ import annotations
from policy.xsp_strategy_policy import XSPStrategyPolicy

def validate_xsp_policy(p: XSPStrategyPolicy) -> tuple[bool, list[str]]:
    errors = []
    if not (0 < p.credit_short_delta_min < p.credit_short_delta_max < 1):
        errors.append("credit delta range invalid")
    if p.credit_min_credit <= 0:
        errors.append("min_credit must be > 0")
    if not (0 < p.credit_profit_take_min <= p.credit_profit_take_target <= 1):
        errors.append("profit take levels invalid")
    if p.max_contracts_cap < 1:
        errors.append("max_contracts_cap must be >= 1")
    if not (0 < p.max_risk_per_trade_pct < 1):
        errors.append("max_risk_per_trade_pct out of range")
    return (len(errors) == 0, errors)
