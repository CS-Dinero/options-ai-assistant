"""tests/test_xsp_lifecycle_rules.py"""
from lifecycle.xsp_spread_lifecycle_engine import evaluate_xsp_spread_lifecycle

def test_harvest_at_target():
    d = evaluate_xsp_spread_lifecycle("XSP","BULL_PUT_SPREAD",0.52,5,695.0,697.0,3.0)
    assert d.state == "HARVEST"
    assert d.action == "CLOSE"

def test_force_close_threatened():
    d = evaluate_xsp_spread_lifecycle("XSP","BULL_PUT_SPREAD",0.10,2,695.0,695.5,2.0)
    assert d.state == "FORCE_CLOSE"
    assert d.urgency >= 90

def test_force_close_dte_only():
    d = evaluate_xsp_spread_lifecycle("XSP","BULL_PUT_SPREAD",0.10,2,695.0,700.0,3.0)
    assert d.state == "FORCE_CLOSE"

def test_hold():
    d = evaluate_xsp_spread_lifecycle("XSP","BULL_PUT_SPREAD",0.15,6,695.0,700.0,3.0)
    assert d.state == "HOLD"
