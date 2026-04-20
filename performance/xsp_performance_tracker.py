"""performance/xsp_performance_tracker.py — Track and compute XSP spread performance."""
from __future__ import annotations
from performance.xsp_performance_models import XSPTradeRecord, XSPPerformanceSummary

class XSPPerformanceTracker:
    def __init__(self):
        self._records: list[XSPTradeRecord] = []

    def record_close(self, record: XSPTradeRecord) -> None:
        self._records.append(record)

    def summary(self) -> XSPPerformanceSummary:
        if not self._records:
            return XSPPerformanceSummary()

        n        = len(self._records)
        wins     = [r for r in self._records if r.realized_pnl > 0]
        losses   = [r for r in self._records if r.realized_pnl <= 0]
        fc       = [r for r in self._records if r.close_reason == "FORCE_CLOSE"]

        total_pnl       = sum(r.realized_pnl for r in self._records)
        avg_pnl         = round(total_pnl / n, 2)
        avg_ror         = round(sum(r.realized_pnl / max(0.01, r.max_loss) for r in self._records) / n, 4)
        avg_capture     = round(sum(r.profit_capture_pct for r in self._records) / n, 4)

        return XSPPerformanceSummary(
            total_trades=n, wins=len(wins), losses=len(losses),
            win_rate=round(len(wins)/n, 4),
            avg_realized_pnl=avg_pnl,
            avg_return_on_risk=avg_ror,
            avg_profit_capture_pct=avg_capture,
            force_close_rate=round(len(fc)/n, 4),
            total_realized_pnl=round(total_pnl, 2),
        )

    def records(self) -> list[XSPTradeRecord]:
        return list(self._records)
