"""tests/test_xsp_ticket_builder.py — all ticket types."""
from lifecycle.xsp_spread_lifecycle_engine import evaluate_xsp_spread_lifecycle
from execution.xsp_ticket_builder import (
    build_xsp_close_ticket,
    build_xsp_diagonal_harvest_ticket,
    build_xsp_diagonal_roll_ticket,
    build_xsp_diagonal_flip_ticket,
    build_xsp_diagonal_close_ticket,
)

def test_spread_close_ticket():
    d = evaluate_xsp_spread_lifecycle("XSP","BULL_PUT_SPREAD",0.55,3,695.0,697.0,3.0)
    t = build_xsp_close_ticket(d,695.0,694.0,"2026-04-17","PUT",10,0.30,0.40,0.10,0.15)
    assert t.action == "CLOSE_SPREAD"
    assert len(t.legs) == 2
    assert t.legs[0].action == "BTC"

def test_diagonal_harvest_ticket():
    t = build_xsp_diagonal_harvest_ticket("XSP","PUT_CREDIT_DIAGONAL","PUT",
        "2026-04-17",695.0,2.50,80)
    assert t.action == "HARVEST_SHORT"
    assert len(t.legs) == 1
    assert t.order_style == "SINGLE_TICKET"

def test_diagonal_roll_ticket():
    t = build_xsp_diagonal_roll_ticket("XSP","PUT_CREDIT_DIAGONAL","PUT",
        "2026-04-17",695.0,"2026-04-18",694.0,0.30,85)
    assert t.action == "ROLL_SHORT"
    assert len(t.legs) == 2
    assert t.legs[0].action == "BTC"
    assert t.legs[1].action == "STO"

def test_diagonal_flip_ticket():
    t = build_xsp_diagonal_flip_ticket("XSP","PUT_CREDIT_DIAGONAL","PUT",
        "2026-05-15",720.0,715.0,0.20,80)
    assert t.action == "FLIP_LONG"
    assert len(t.legs) == 2
    assert t.legs[0].action == "STC"
    assert t.legs[1].action == "BTO"

def test_diagonal_close_ticket():
    t = build_xsp_diagonal_close_ticket("XSP","PUT_CREDIT_DIAGONAL","PUT",
        "2026-04-17",695.0,"2026-05-15",690.0,4.50,95)
    assert t.action == "CLOSE_DIAGONAL"
    assert len(t.legs) == 2
    assert t.urgency == 95

def test_force_close_has_warning():
    t = build_xsp_diagonal_close_ticket("XSP","PUT_CREDIT_DIAGONAL","PUT",
        "2026-04-17",695.0,"2026-05-15",690.0,4.50,95)
    assert any("Force close" in w for w in t.warnings if w)
