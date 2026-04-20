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


def build_xsp_diagonal_harvest_ticket(
    ticker: str, structure: str, option_type: str,
    short_expiry: str, short_strike: float,
    short_mark_to_close: float, urgency: int,
) -> "XSPExecutionTicket":
    from execution.xsp_execution_models import XSPOptionLeg
    from execution.xsp_limit_price_engine import compute_close_limit
    target, chase = compute_close_limit(
        short_mark_to_close*0.97, short_mark_to_close*1.03,
        0, 0, urgency,
    )
    return XSPExecutionTicket(
        ticket_id=__import__('uuid').uuid4().hex[:8],
        ticker=ticker, structure=structure,
        action="HARVEST_SHORT", order_style="SINGLE_TICKET",
        target_limit=short_mark_to_close,
        max_chase_width=0.05, urgency=urgency,
        legs=[XSPOptionLeg("BTC", option_type, short_strike, short_expiry, 1)],
        notes=["Close short leg only — long remains open."],
        warnings=["Position becomes uncovered long after fill."],
    )


def build_xsp_diagonal_roll_ticket(
    ticker: str, structure: str, option_type: str,
    old_short_expiry: str, old_short_strike: float,
    new_short_expiry: str, new_short_strike: float,
    roll_credit_est: float, urgency: int,
) -> "XSPExecutionTicket":
    from execution.xsp_execution_models import XSPOptionLeg
    return XSPExecutionTicket(
        ticket_id=__import__('uuid').uuid4().hex[:8],
        ticker=ticker, structure=structure,
        action="ROLL_SHORT", order_style="NET_DEBIT",
        target_limit=round(roll_credit_est, 2),
        max_chase_width=0.05, urgency=urgency,
        legs=[
            XSPOptionLeg("BTC", option_type, old_short_strike, old_short_expiry, 1),
            XSPOptionLeg("STO", option_type, new_short_strike, new_short_expiry, 1),
        ],
        notes=["Roll short leg — single combo ticket.", "Keep long coverage throughout."],
        warnings=[],
    )


def build_xsp_diagonal_flip_ticket(
    ticker: str, structure: str, option_type: str,
    long_expiry: str, old_long_strike: float,
    new_long_strike: float, flip_credit_est: float,
    urgency: int,
) -> "XSPExecutionTicket":
    from execution.xsp_execution_models import XSPOptionLeg
    return XSPExecutionTicket(
        ticket_id=__import__('uuid').uuid4().hex[:8],
        ticker=ticker, structure=structure,
        action="FLIP_LONG", order_style="NET_DEBIT",
        target_limit=round(flip_credit_est, 2),
        max_chase_width=0.05, urgency=urgency,
        legs=[
            XSPOptionLeg("STC", option_type, old_long_strike, long_expiry, 1),
            XSPOptionLeg("BTO", option_type, new_long_strike, long_expiry, 1),
        ],
        notes=["Covered flip — single combo ticket.", "Do not leave short uncovered."],
        warnings=["Only when long delta >= 0.93."],
    )


def build_xsp_diagonal_close_ticket(
    ticker: str, structure: str, option_type: str,
    short_expiry: str, short_strike: float,
    long_expiry: str, long_strike: float,
    close_mark_est: float, urgency: int,
) -> "XSPExecutionTicket":
    from execution.xsp_execution_models import XSPOptionLeg
    return XSPExecutionTicket(
        ticket_id=__import__('uuid').uuid4().hex[:8],
        ticker=ticker, structure=structure,
        action="CLOSE_DIAGONAL", order_style="NET_DEBIT",
        target_limit=round(close_mark_est, 2),
        max_chase_width=0.10, urgency=urgency,
        legs=[
            XSPOptionLeg("BTC", option_type, short_strike, short_expiry, 1),
            XSPOptionLeg("STC", option_type, long_strike,  long_expiry,  1),
        ],
        notes=["Close full diagonal — default close-window action."],
        warnings=["Force close — do not delay." if urgency >= 90 else ""],
    )
