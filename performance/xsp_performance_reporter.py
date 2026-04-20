"""performance/xsp_performance_reporter.py — Format XSP performance for dashboard."""
from performance.xsp_performance_tracker import XSPPerformanceTracker

def render_xsp_performance_summary(tracker: XSPPerformanceTracker) -> dict:
    s = tracker.summary()
    return {
        "total_trades":          s.total_trades,
        "win_rate_pct":          round(s.win_rate * 100, 1),
        "avg_realized_pnl":      s.avg_realized_pnl,
        "avg_return_on_risk_pct": round(s.avg_return_on_risk * 100, 2),
        "avg_profit_capture_pct": round(s.avg_profit_capture_pct * 100, 1),
        "force_close_rate_pct":  round(s.force_close_rate * 100, 1),
        "total_realized_pnl":    s.total_realized_pnl,
    }
