"""allocation/capital_allocation_engine.py — Strategy-aware, performance-weighted allocator."""
from __future__ import annotations
import math
from allocation.capital_allocation_models import (
    AccountState, StrategyPerformanceSnapshot,
    AllocationInput, AllocationDecision,
)
from allocation.regime_sizing_rules import get_sizing_rule

# ── Strategy priority weights ──────────────────────────────────────────────
_STRATEGY_WEIGHTS: dict[str, float] = {
    "XSP_CREDIT_SPREAD":   1.00,
    "XSP_DEBIT_SPREAD":    0.80,
    "XSP_CREDIT_DIAGONAL": 0.60,
    "SINGLE_NAME_DIAGONAL":0.40,
    "CALENDAR":            0.35,
    "DOUBLE_DIAGONAL":     0.25,
    # spread structure aliases from scanner
    "BULL_PUT_SPREAD":     1.00,
    "BEAR_CALL_SPREAD":    1.00,
    "BULL_CALL_SPREAD":    0.80,
    "BEAR_PUT_SPREAD":     0.80,
    "PUT_CREDIT_DIAGONAL": 0.60,
    "CALL_CREDIT_DIAGONAL":0.60,
}

_ADVANCED_STRUCTURES = {
    "XSP_CREDIT_DIAGONAL", "SINGLE_NAME_DIAGONAL",
    "CALENDAR", "DOUBLE_DIAGONAL",
    "PUT_CREDIT_DIAGONAL", "CALL_CREDIT_DIAGONAL",
}

def base_strategy_weight(strategy_type: str) -> float:
    return _STRATEGY_WEIGHTS.get(strategy_type, 0.20)

def is_advanced_structure(strategy_type: str) -> bool:
    return strategy_type in _ADVANCED_STRUCTURES

def performance_multiplier(p: StrategyPerformanceSnapshot | None) -> float:
    if p is None or p.recent_trades < 10:
        return 1.0
    mult = 1.0
    if p.win_rate >= 0.65:            mult += 0.15
    if p.avg_return_on_risk >= 0.20:  mult += 0.10
    if p.force_close_rate >= 0.30:    mult -= 0.20
    return max(0.50, min(1.50, mult))


# ── Full allocator (strategy + performance aware) ─────────────────────────
def allocate_capital(
    account: AccountState,
    environment: str,
    strategy_type: str,
    strategy_perf: StrategyPerformanceSnapshot | None,
    per_contract_risk: float,
) -> AllocationDecision:
    rule = get_sizing_rule(environment)

    # Block advanced structures in restrictive regimes
    if is_advanced_structure(strategy_type) and not rule.contracts_cap > 2:
        return AllocationDecision(
            strategy_type=strategy_type, regime=environment,
            target_weight=0.0, max_contracts=0, max_risk_dollars=0.0,
            allow_new_entries=False,
            reason="Advanced structure blocked in current regime.",
        )

    total_budget     = account.account_equity * rule.max_exposure_pct
    per_trade_budget = account.account_equity * rule.max_risk_per_trade_pct
    remaining        = max(0.0, total_budget - account.open_risk)
    raw_budget       = min(per_trade_budget, remaining)

    base_w   = base_strategy_weight(strategy_type)
    perf_m   = performance_multiplier(strategy_perf)
    weighted = raw_budget * base_w * perf_m

    if per_contract_risk <= 0:
        return AllocationDecision(
            strategy_type=strategy_type, regime=environment,
            target_weight=0.0, max_contracts=0, max_risk_dollars=0.0,
            allow_new_entries=False,
            reason="Risk per contract must be > 0.",
        )

    max_contracts = min(math.floor(weighted / per_contract_risk), rule.contracts_cap)
    max_contracts = max(0, max_contracts)
    allow         = max_contracts >= 1

    return AllocationDecision(
        strategy_type=strategy_type, regime=environment,
        target_weight=round(base_w * perf_m, 4),
        max_contracts=max_contracts,
        max_risk_dollars=round(max_contracts * per_contract_risk, 2),
        allow_new_entries=allow,
        reason=f"{'Approved' if allow else 'Blocked'} — {max_contracts}ct @ ${per_contract_risk:.0f}/ct",
        notes=[
            f"base_weight={base_w:.2f}",
            f"perf_mult={perf_m:.2f}",
            f"weighted_budget=${weighted:.2f}",
            f"regime_cap={rule.contracts_cap}ct",
        ],
    )


# ── Simple allocator (backward-compat with v55 scanner) ───────────────────
def allocate_xsp_position(inp: AllocationInput) -> AllocationDecision:
    """Backward-compatible wrapper using AccountState from cash balance."""
    account = AccountState(
        account_equity=inp.account_cash,
        cash_balance=inp.account_cash,
        available_funds=inp.account_cash,
        buying_power=inp.account_cash * 3,
        margin_used=0.0,
        open_risk=inp.open_positions_risk,
    )
    return allocate_capital(
        account=account,
        environment=inp.regime,
        strategy_type=inp.strategy_type,
        strategy_perf=None,
        per_contract_risk=inp.risk_per_contract,
    )
