"""
backtest/performance.py
Core performance metrics for the Phase 4 backtesting engine.

All functions are pure, stateless, and accept normalized trade lists.
Designed to be reused by reports.py and run_backtest.py.
"""

from __future__ import annotations
import math


def compute_total_trades(trades: list[dict]) -> int:
    return len(trades)


def compute_win_rate(trades: list[dict]) -> float:
    if not trades:
        return 0.0
    wins = sum(1 for t in trades if float(t.get("pnl", 0)) > 0)
    return round(wins / len(trades), 4)


def compute_average_win(trades: list[dict]) -> float:
    wins = [float(t["pnl"]) for t in trades if float(t.get("pnl", 0)) > 0]
    return round(sum(wins) / len(wins), 2) if wins else 0.0


def compute_average_loss(trades: list[dict]) -> float:
    losses = [abs(float(t["pnl"])) for t in trades if float(t.get("pnl", 0)) < 0]
    return round(sum(losses) / len(losses), 2) if losses else 0.0


def compute_expectancy(trades: list[dict]) -> float:
    """E[trade] = WinRate * AvgWin - LossRate * AvgLoss"""
    if not trades:
        return 0.0
    wr      = compute_win_rate(trades)
    avg_win = compute_average_win(trades)
    avg_los = compute_average_loss(trades)
    return round(wr * avg_win - (1 - wr) * avg_los, 2)


def compute_profit_factor(trades: list[dict]) -> float:
    """GrossProfit / GrossLoss — infinity if no losses."""
    gross_profit = sum(float(t["pnl"]) for t in trades if float(t.get("pnl", 0)) > 0)
    gross_loss   = abs(sum(float(t["pnl"]) for t in trades if float(t.get("pnl", 0)) < 0))
    if gross_loss == 0:
        return float("inf") if gross_profit > 0 else 0.0
    return round(gross_profit / gross_loss, 4)


def compute_max_drawdown(equity_curve: list[dict]) -> float:
    """Maximum peak-to-trough drawdown as a decimal (0.072 = 7.2%)."""
    if not equity_curve:
        return 0.0
    peak   = equity_curve[0]["equity"]
    max_dd = 0.0
    for point in equity_curve:
        eq = point["equity"]
        if eq > peak:
            peak = eq
        dd = (peak - eq) / peak if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd
    return round(max_dd, 4)


def compute_sharpe(returns: list[float], annualization: float = 252.0) -> float:
    """Annualized Sharpe ratio. Assumes daily returns, no risk-free rate."""
    if not returns:
        return 0.0
    mean   = sum(returns) / len(returns)
    var    = sum((r - mean) ** 2 for r in returns) / len(returns)
    std    = math.sqrt(var)
    if std == 0:
        return 0.0
    return round((mean / std) * math.sqrt(annualization), 4)


def compute_sortino(returns: list[float], annualization: float = 252.0) -> float:
    """Annualized Sortino ratio using downside deviation."""
    if not returns:
        return 0.0
    mean     = sum(returns) / len(returns)
    downside = [r for r in returns if r < 0]
    if not downside:
        return float("inf") if mean > 0 else 0.0
    ds_var = sum(r ** 2 for r in downside) / len(downside)
    ds_std = math.sqrt(ds_var)
    if ds_std == 0:
        return 0.0
    return round((mean / ds_std) * math.sqrt(annualization), 4)


def compute_average_days_held(trades: list[dict]) -> float:
    if not trades:
        return 0.0
    return round(sum(int(t.get("days_held", 0)) for t in trades) / len(trades), 2)


def compute_return_on_risk(trades: list[dict]) -> float:
    """Total P/L divided by total capital at risk."""
    total_pnl  = sum(float(t.get("pnl", 0)) for t in trades)
    total_risk = sum(float(t.get("max_loss", 0)) for t in trades)
    if total_risk == 0:
        return 0.0
    return round(total_pnl / total_risk, 4)


def summarize_performance(
    trades:       list[dict],
    equity_curve: list[dict],
    returns:      list[float],
) -> dict:
    """Full performance summary — consumed by reports.py and run_backtest.py."""
    return {
        "total_trades":       compute_total_trades(trades),
        "win_rate":           compute_win_rate(trades),
        "average_win":        compute_average_win(trades),
        "average_loss":       compute_average_loss(trades),
        "expectancy":         compute_expectancy(trades),
        "profit_factor":      compute_profit_factor(trades),
        "max_drawdown":       compute_max_drawdown(equity_curve),
        "sharpe":             compute_sharpe(returns),
        "sortino":            compute_sortino(returns),
        "average_days_held":  compute_average_days_held(trades),
        "return_on_risk":     compute_return_on_risk(trades),
    }
