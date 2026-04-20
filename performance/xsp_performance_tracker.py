"""performance/xsp_performance_tracker.py — Spread + diagonal performance aggregation."""
from __future__ import annotations
from performance.xsp_performance_models import XSPTradeRecord, XSPPerformanceSummary

_SPREAD_STRUCTURES = {
    "BULL_PUT_SPREAD", "BEAR_CALL_SPREAD",
    "BULL_CALL_SPREAD", "BEAR_PUT_SPREAD",
}
_DIAG_STRUCTURES = {"PUT_CREDIT_DIAGONAL", "CALL_CREDIT_DIAGONAL"}

def _is_spread(r: XSPTradeRecord) -> bool:
    return r.structure in _SPREAD_STRUCTURES

def _is_diagonal(r: XSPTradeRecord) -> bool:
    return r.structure in _DIAG_STRUCTURES

def _safe_avg(vals: list[float]) -> float:
    return sum(vals) / len(vals) if vals else 0.0

def summarize_xsp_performance(records: list[XSPTradeRecord]) -> XSPPerformanceSummary:
    if not records:
        return XSPPerformanceSummary()

    spreads = [r for r in records if _is_spread(r)]
    diags   = [r for r in records if _is_diagonal(r)]
    n       = len(records)

    # Global
    win_rate        = _safe_avg([1.0 if r.realized_pnl > 0 else 0.0 for r in records])
    avg_pnl         = _safe_avg([r.realized_pnl for r in records])
    avg_ror         = _safe_avg([r.realized_pnl / max(0.01, r.max_risk) for r in records])
    total_pnl       = round(sum(r.realized_pnl for r in records), 2)

    # Spreads
    spread_win      = _safe_avg([1.0 if r.realized_pnl > 0 else 0.0 for r in spreads])
    spread_capture  = _safe_avg([r.profit_capture_pct for r in spreads
                                 if r.profit_capture_pct is not None])
    spread_fc       = _safe_avg([1.0 if r.was_force_closed else 0.0 for r in spreads])

    # Diagonals
    diag_win        = _safe_avg([1.0 if r.realized_pnl > 0 else 0.0 for r in diags])
    avg_harvest     = _safe_avg([r.harvest_collected for r in diags])
    avg_rolls       = _safe_avg([float(r.roll_count) for r in diags])
    roll_flags      = [1.0 if r.roll_credit_total > 0 else 0.0
                       for r in diags if r.roll_count > 0]
    roll_success    = _safe_avg(roll_flags)
    flip_vals       = [r.flip_realized_value for r in diags if r.flip_count > 0]
    avg_flip        = _safe_avg(flip_vals)
    diag_fc         = _safe_avg([1.0 if r.was_force_closed else 0.0 for r in diags])

    return XSPPerformanceSummary(
        total_trades=n, spread_trades=len(spreads), diagonal_trades=len(diags),
        win_rate=round(win_rate, 4), avg_realized_pnl=round(avg_pnl, 4),
        avg_return_on_risk=round(avg_ror, 4), total_realized_pnl=total_pnl,
        spread_win_rate=round(spread_win, 4),
        avg_spread_profit_capture=round(spread_capture, 4),
        spread_force_close_rate=round(spread_fc, 4),
        diagonal_win_rate=round(diag_win, 4),
        avg_diagonal_harvest=round(avg_harvest, 4),
        avg_roll_count=round(avg_rolls, 4),
        roll_success_rate=round(roll_success, 4),
        avg_flip_realized_value=round(avg_flip, 4),
        diagonal_force_close_rate=round(diag_fc, 4),
    )


class XSPPerformanceTracker:
    """Stateful tracker — append records, query summaries."""
    def __init__(self):
        self._records: list[XSPTradeRecord] = []

    def record_close(self, record: XSPTradeRecord) -> None:
        self._records.append(record)

    def summary(self) -> XSPPerformanceSummary:
        return summarize_xsp_performance(self._records)

    def records(self) -> list[XSPTradeRecord]:
        return list(self._records)

    def spread_records(self) -> list[XSPTradeRecord]:
        return [r for r in self._records if _is_spread(r)]

    def diagonal_records(self) -> list[XSPTradeRecord]:
        return [r for r in self._records if _is_diagonal(r)]
