"""tests/test_xsp_performance_tracker.py"""
from performance.xsp_performance_tracker import XSPPerformanceTracker
from performance.xsp_performance_models import XSPTradeRecord

def test_performance_metrics():
    t = XSPPerformanceTracker()
    t.record_close(XSPTradeRecord("1","XSP","BULL_PUT_SPREAD","2026-04-14","2026-04-16",
        1.80,1.00,180.0,10,"HARVEST",800.0,0.44))
    t.record_close(XSPTradeRecord("2","XSP","BULL_PUT_SPREAD","2026-04-14","2026-04-16",
        1.80,0.50,180.0,10,"FORCE_CLOSE",-500.0,-0.28))
    s = t.summary()
    assert s.total_trades == 2
    assert s.wins == 1
    assert s.force_close_rate == 0.5
    assert s.total_realized_pnl == 300.0
