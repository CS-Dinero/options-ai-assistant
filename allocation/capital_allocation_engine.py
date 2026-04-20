"""allocation/capital_allocation_engine.py — Decides contract count and entry permission."""
from __future__ import annotations
import math
from allocation.capital_allocation_models import AllocationInput, AllocationDecision
from allocation.regime_sizing_rules import get_sizing_rule

def allocate_xsp_position(inp: AllocationInput) -> AllocationDecision:
    rule = get_sizing_rule(inp.regime)

    max_exposure    = inp.account_cash * rule.max_exposure_pct
    max_trade_risk  = inp.account_cash * rule.max_risk_per_trade_pct
    remaining_cap   = max(0.0, max_exposure - inp.open_positions_risk)

    # Block if already at max exposure
    if inp.open_positions_risk >= max_exposure:
        return AllocationDecision(
            target_weight=0.0, max_contracts=0,
            max_risk_dollars=0.0, allow_new_entries=False,
            reason=f"Exposure cap reached — {inp.open_positions_risk:.0f} >= {max_exposure:.0f}",
        )

    if inp.risk_per_contract <= 0:
        return AllocationDecision(
            target_weight=0.0, max_contracts=0,
            max_risk_dollars=0.0, allow_new_entries=False,
            reason="Risk per contract must be > 0",
        )

    # Max contracts from risk budget
    by_trade_risk   = math.floor(max_trade_risk   / inp.risk_per_contract)
    by_remaining    = math.floor(remaining_cap     / inp.risk_per_contract)
    raw_contracts   = min(by_trade_risk, by_remaining, rule.contracts_cap)
    max_contracts   = max(0, raw_contracts)
    max_risk_dollars= round(max_contracts * inp.risk_per_contract, 2)
    target_weight   = round(max_risk_dollars / max(1.0, inp.account_cash), 4)

    if max_contracts < 1:
        return AllocationDecision(
            target_weight=0.0, max_contracts=0,
            max_risk_dollars=0.0, allow_new_entries=False,
            reason="Insufficient capital for even 1 contract at current risk level.",
        )

    return AllocationDecision(
        target_weight=target_weight,
        max_contracts=max_contracts,
        max_risk_dollars=max_risk_dollars,
        allow_new_entries=True,
        reason=f"Approved {max_contracts}ct — risk ${max_risk_dollars:.0f} of ${max_trade_risk:.0f} budget",
        notes=[
            f"regime={inp.regime}",
            f"exposure_cap=${max_exposure:.0f}",
            f"remaining_cap=${remaining_cap:.0f}",
        ],
    )
