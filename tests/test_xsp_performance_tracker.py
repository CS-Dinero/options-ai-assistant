"""tests/test_xsp_performance_tracker.py — spread + diagonal performance."""
from performance.xsp_performance_models import XSPTradeRecord
from performance.xsp_performance_tracker import summarize_xsp_performance, XSPPerformanceTracker
from performance.xsp_performance_reporter import xsp_performance_summary_to_dict, render_xsp_performance_text

def _spread(pnl, force=False, capture=0.50):
    return XSPTradeRecord(
        trade_id="s1", ticker="XSP", structure="BULL_PUT_SPREAD",
        opened_utc="2026-04-14T10:00:00Z", closed_utc="2026-04-14T14:00:00Z",
        max_risk=100.0, entry_credit=0.50, realized_pnl=pnl,
        exit_type="FORCE_CLOSE" if force else "HARVEST",
        hold_minutes=120, was_force_closed=force,
        profit_capture_pct=capture,
    )

def _diag(pnl, rolls=1, flips=0, force=False):
    return XSPTradeRecord(
        trade_id="d1", ticker="XSP", structure="PUT_CREDIT_DIAGONAL",
        opened_utc="2026-04-14T10:00:00Z", closed_utc="2026-04-14T15:00:00Z",
        max_risk=40.0, entry_credit=0.10, realized_pnl=pnl,
        exit_type="ROLL", hold_minutes=300, was_force_closed=force,
        harvest_collected=0.35, roll_count=rolls, roll_credit_total=0.20,
        flip_count=flips, flip_realized_value=0.15 if flips else 0.0,
        long_leg_sale_value=0.40,
    )

def test_spread_and_diagonal_split():
    records = [_spread(30.0), _diag(25.0)]
    s = summarize_xsp_performance(records)
    assert s.total_trades == 2
    assert s.spread_trades == 1
    assert s.diagonal_trades == 1
    assert s.win_rate == 1.0
    assert s.roll_success_rate == 1.0
    assert s.avg_flip_realized_value == 0.0  # flip_count=0 by default

def test_force_close_tracking():
    s = summarize_xsp_performance([_spread(-50.0, force=True, capture=-0.5)])
    assert s.spread_force_close_rate == 1.0
    assert s.win_rate == 0.0

def test_diagonal_flip_tracking():
    s = summarize_xsp_performance([_diag(20.0, flips=1)])
    assert s.avg_flip_realized_value == 0.15

def test_tracker_class():
    t = XSPPerformanceTracker()
    t.record_close(_spread(20.0))
    assert len(t.spread_records()) == 1
    assert len(t.diagonal_records()) == 0
    assert t.summary().total_trades == 1

def test_reporter_dict():
    s = summarize_xsp_performance([_spread(30.0), _diag(25.0)])
    d = xsp_performance_summary_to_dict(s)
    assert "spread_win_rate" in d
    assert "diagonal_win_rate" in d
    assert "roll_success_rate" in d

def test_reporter_text():
    s = summarize_xsp_performance([_spread(30.0)])
    text = render_xsp_performance_text(s)
    assert "SPREADS" in text
    assert "DIAGONALS" in text
