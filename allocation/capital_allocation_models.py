"""allocation/capital_allocation_models.py — Input/output models for allocation engine."""
from dataclasses import dataclass, field

@dataclass(slots=True)
class AllocationInput:
    account_cash: float
    regime: str
    strategy_type: str    # BULL_PUT_SPREAD | BEAR_CALL_SPREAD | BULL_CALL_SPREAD | BEAR_PUT_SPREAD
    risk_per_contract: float    # max_loss per contract in dollars
    open_positions_risk: float  # total risk dollars already deployed

@dataclass(slots=True)
class AllocationDecision:
    target_weight: float
    max_contracts: int
    max_risk_dollars: float
    allow_new_entries: bool
    reason: str
    notes: list[str] = field(default_factory=list)
