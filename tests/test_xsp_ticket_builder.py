"""tests/test_xsp_ticket_builder.py"""
from lifecycle.xsp_spread_lifecycle_engine import evaluate_xsp_spread_lifecycle
from execution.xsp_ticket_builder import build_xsp_close_ticket

def test_close_ticket_built():
    decision = evaluate_xsp_spread_lifecycle("XSP","BULL_PUT_SPREAD",0.55,3,695.0,697.0,3.0)
    ticket = build_xsp_close_ticket(
        decision, 695.0, 694.0, "2026-04-17", "PUT", 10,
        0.30, 0.40, 0.10, 0.15
    )
    assert ticket.action == "CLOSE_SPREAD"
    assert len(ticket.legs) == 2
    assert ticket.legs[0].action == "BTC"
    assert ticket.legs[1].action == "STC"
    assert ticket.target_limit > 0
