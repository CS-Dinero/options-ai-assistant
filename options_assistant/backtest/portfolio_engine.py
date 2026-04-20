"""
backtest/portfolio_engine.py
Builds equity curve and capital timeline from simulated trades.

MVP model:
  - fixed starting capital
  - realized P/L only (equity updates on trade close, not daily mark)
  - overlapping trades allowed
  - no margin model

This is intentionally simple and correct for Phase 4A.
Capital complexity (locking, margin, position limits) comes in Phase 4B.
"""

from __future__ import annotations


def sort_trades_by_exit_date(simulated_trades: list[dict]) -> list[dict]:
    """Sort completed trades by exit date ascending."""
    return sorted(simulated_trades, key=lambda t: t.get("exit_date", ""))


def extract_trade_cashflows(simulated_trades: list[dict]) -> dict[str, float]:
    """
    Group realized P/L by exit date.
    Returns dict[exit_date, total_pnl_that_day].
    """
    cashflows: dict[str, float] = {}
    for trade in simulated_trades:
        exit_date = trade.get("exit_date")
        pnl       = float(trade.get("pnl", 0))
        if not exit_date:
            continue
        cashflows[exit_date] = cashflows.get(exit_date, 0.0) + pnl
    return dict(sorted(cashflows.items()))


def compute_equity_curve(
    simulated_trades: list[dict],
    starting_capital: float = 100_000.0,
) -> list[dict]:
    """
    Build a dated cumulative capital curve from completed trades.

    Each point represents the running equity after all trades
    that closed on that date are realized.

    Returns list of {date, cashflow, equity} dicts sorted by date.
    """
    cashflows     = extract_trade_cashflows(simulated_trades)
    equity_curve  = []
    equity        = float(starting_capital)

    for date_str, cashflow in cashflows.items():
        equity += cashflow
        equity_curve.append({
            "date":     date_str,
            "cashflow": round(cashflow, 2),
            "equity":   round(equity, 2),
        })

    return equity_curve


def summarize_equity_curve(
    equity_curve: list[dict],
    starting_capital: float = 100_000.0,
) -> dict:
    """
    High-level equity curve summary.
    Returns starting, ending, net profit, peak, and trough.
    """
    if not equity_curve:
        return {
            "starting_capital": float(starting_capital),
            "ending_capital":   float(starting_capital),
            "net_profit":       0.0,
            "max_equity":       float(starting_capital),
            "min_equity":       float(starting_capital),
        }

    equities       = [p["equity"] for p in equity_curve]
    ending_capital = equities[-1]

    return {
        "starting_capital": float(starting_capital),
        "ending_capital":   round(ending_capital, 2),
        "net_profit":       round(ending_capital - starting_capital, 2),
        "max_equity":       round(max(equities), 2),
        "min_equity":       round(min(equities), 2),
    }
