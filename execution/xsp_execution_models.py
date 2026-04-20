"""execution/xsp_execution_models.py — XSP spread execution data models."""
from __future__ import annotations
from dataclasses import dataclass, field

@dataclass(slots=True)
class XSPOptionLeg:
    action: str        # BTC | STC | BTO | STO
    option_type: str   # PUT | CALL
    strike: float
    expiry: str
    contracts: int

@dataclass(slots=True)
class XSPExecutionTicket:
    ticket_id: str
    ticker: str
    structure: str
    action: str              # CLOSE_SPREAD
    order_style: str         # NET_DEBIT | NET_CREDIT | LIMIT
    target_limit: float
    max_chase_width: float   # max slippage before cancelling
    legs: list[XSPOptionLeg]
    urgency: int
    notes: list[str]  = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
