"""tests/test_xsp_debit_spread_scanner.py"""
from dataclasses import dataclass
from scanner.xsp_debit_spread_scanner import scan_xsp_debit_spreads

@dataclass
class Q:
    ticker:str; option_type:str; expiry:str; strike:float
    bid:float; ask:float; mid:float; delta:float
    open_interest:int; dte:int

def test_bear_put_found():
    quotes = [
        Q("XSP","PUT","2026-04-24",700.0,3.45,3.55,3.50,-0.58,900,14),
        Q("XSP","PUT","2026-04-24",699.0,2.90,3.00,2.95,-0.52,700,14),
        Q("XSP","PUT","2026-04-24",698.0,2.45,2.55,2.50,-0.47,600,14),
    ]
    r = scan_xsp_debit_spreads("XSP","PUT",quotes,70.0)
    assert len(r) > 0
    assert r[0].structure == "BEAR_PUT_SPREAD"
    assert r[0].reward_risk >= 0.75
