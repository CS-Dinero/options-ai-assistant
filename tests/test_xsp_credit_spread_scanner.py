"""tests/test_xsp_credit_spread_scanner.py"""
from dataclasses import dataclass
from scanner.xsp_credit_spread_scanner import scan_xsp_credit_spreads, XSPCreditSpreadScannerConfig

@dataclass
class Q:
    ticker:str; option_type:str; expiry:str; strike:float
    bid:float; ask:float; mid:float; delta:float
    open_interest:int; dte:int

def test_bull_put_found():
    # Credit=0.50 on $1 wide = 50% cwr — passes all filters
    quotes = [
        Q("XSP","PUT","2026-04-17",695.0,1.95,2.05,2.00,-0.25,800,7),
        Q("XSP","PUT","2026-04-17",694.0,1.45,1.55,1.50,-0.22,600,7),
        Q("XSP","PUT","2026-04-17",693.0,1.15,1.25,1.20,-0.20,500,7),
    ]
    r = scan_xsp_credit_spreads("XSP","PUT",quotes,75.0)
    assert len(r) > 0
    assert r[0].structure == "BULL_PUT_SPREAD"
    assert r[0].credit > 0
    assert r[0].credit_width_ratio >= 0.35

def test_no_credit_rejected():
    quotes = [
        Q("XSP","PUT","2026-04-17",695.0,0.05,0.10,0.07,-0.25,800,7),
        Q("XSP","PUT","2026-04-17",694.0,0.05,0.10,0.07,-0.22,600,7),
    ]
    r = scan_xsp_credit_spreads("XSP","PUT",quotes,75.0)
    assert len(r) == 0

def test_bear_call_found():
    quotes = [
        Q("XSP","CALL","2026-04-17",710.0,2.95,3.05,3.00,0.26,700,7),
        Q("XSP","CALL","2026-04-17",711.0,2.45,2.55,2.50,0.22,500,7),
    ]
    r = scan_xsp_credit_spreads("XSP","CALL",quotes,75.0)
    assert len(r) > 0
    assert r[0].structure == "BEAR_CALL_SPREAD"
