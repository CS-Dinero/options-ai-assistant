"""execution/xsp_ticket_builder.py — Build XSP spread close tickets."""
from __future__ import annotations
import uuid
from execution.xsp_execution_models import XSPExecutionTicket, XSPOptionLeg
from execution.xsp_limit_price_engine import compute_close_limit
from lifecycle.xsp_spread_lifecycle_engine import XSPSpreadLifecycleDecision

def build_xsp_close_ticket(
    decision: XSPSpreadLifecycleDecision,
    short_strike: float,
    long_strike: float,
    expiry: str,
    option_type: str,
    contracts: int,
    short_bid: float,
    short_ask: float,
    long_bid: float,
    long_ask: float,
) -> XSPExecutionTicket:
    ot = option_type.upper()
    target, chase = compute_close_limit(short_bid, short_ask, long_bid, long_ask, decision.urgency)
    warnings = []
    if decision.urgency >= 90:
        warnings.append("HIGH URGENCY — accept wider fill if needed.")
    if decision.state == "FORCE_CLOSE":
        warnings.append("FORCE CLOSE — do not delay.")

    return XSPExecutionTicket(
        ticket_id=str(uuid.uuid4())[:8],
        ticker=decision.ticker,
        structure=decision.structure,
        action="CLOSE_SPREAD",
        order_style="NET_DEBIT",
        target_limit=target,
        max_chase_width=chase,
        legs=[
            XSPOptionLeg("BTC", ot, short_strike, expiry, contracts),  # buy back short
            XSPOptionLeg("STC", ot, long_strike,  expiry, contracts),  # sell long
        ],
        urgency=decision.urgency,
        notes=[decision.reason],
        warnings=warnings,
    )
