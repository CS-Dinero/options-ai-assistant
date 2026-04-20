"""allocation/capital_allocation_models.py — Strategy-aware allocation models."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal

StrategyType = Literal[
    "XSP_CREDIT_SPREAD",
    "XSP_DEBIT_SPREAD",
    "XSP_CREDIT_DIAGONAL",
    "SINGLE_NAME_DIAGONAL",
    "CALENDAR",
    "DOUBLE_DIAGONAL",
]

@dataclass(slots=True)
class AccountState:
    account_equity: float
    cash_balance: float
    available_funds: float
    buying_power: float
    margin_used: float
    open_risk: float

@dataclass(slots=True)
class StrategyPerformanceSnapshot:
    strategy_type: str
    win_rate: float
    avg_return_on_risk: float
    force_close_rate: float
    recent_trades: int

@dataclass(slots=True)
class AllocationInput:
    """Simple input for backward-compat with v55/v56 scanner integration."""
    account_cash: float
    regime: str
    strategy_type: str
    risk_per_contract: float
    open_positions_risk: float

@dataclass(slots=True)
class AllocationDecision:
    strategy_type: str
    regime: str
    target_weight: float
    max_contracts: int
    max_risk_dollars: float
    allow_new_entries: bool
    reason: str
    notes: list[str] = field(default_factory=list)
