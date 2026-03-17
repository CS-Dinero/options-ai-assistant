"""
backtest/reports.py
Segmented performance reports for Phase 4 backtesting.

Report dimensions:
  - by_strategy     — which trade structures deserve capital
  - by_environment  — where the VGA engine adds value
  - by_symbol       — which underlyings have edge
  - by_regime       — iv_regime, gamma_regime, term_structure breakdown

Uses performance.py helpers so metrics are consistent everywhere.
"""

from __future__ import annotations
from backtest.performance import (
    compute_total_trades, compute_win_rate,
    compute_average_win, compute_average_loss,
    compute_expectancy, compute_profit_factor,
    compute_average_days_held, compute_return_on_risk,
)


def safe_label(value) -> str:
    """Normalize any key value to a non-empty string."""
    if value in (None, "", "unknown"):
        return "unknown"
    return str(value)


def group_trades_by_key(trades: list[dict], key: str) -> dict[str, list[dict]]:
    """Partition trades into groups by the value of a given key."""
    grouped: dict[str, list[dict]] = {}
    for trade in trades:
        label = safe_label(trade.get(key))
        grouped.setdefault(label, []).append(trade)
    return grouped


def summarize_group(trades: list[dict]) -> dict:
    """Compute all standard metrics for a group of trades."""
    return {
        "trades":            compute_total_trades(trades),
        "win_rate":          compute_win_rate(trades),
        "average_win":       compute_average_win(trades),
        "average_loss":      compute_average_loss(trades),
        "expectancy":        compute_expectancy(trades),
        "profit_factor":     compute_profit_factor(trades),
        "average_days_held": compute_average_days_held(trades),
        "return_on_risk":    compute_return_on_risk(trades),
        "total_pnl":         round(sum(float(t.get("pnl", 0)) for t in trades), 2),
    }


def sort_report(report: dict, sort_key: str = "total_pnl") -> dict:
    """Sort a report dict by a metric key descending."""
    return dict(sorted(report.items(), key=lambda kv: kv[1].get(sort_key, 0), reverse=True))


def summarize_by_strategy(trades: list[dict]) -> dict:
    """Performance by strategy_type. Key question: which structures have edge?"""
    groups = group_trades_by_key(trades, "strategy_type")
    return sort_report({label: summarize_group(g) for label, g in groups.items()})


def summarize_by_environment(trades: list[dict]) -> dict:
    """
    Performance by VGA environment. Key question: does the VGA engine help?
    premium_selling should outperform trend_directional for credit spreads, etc.
    """
    groups = group_trades_by_key(trades, "vga_environment")
    return sort_report({label: summarize_group(g) for label, g in groups.items()})


def summarize_by_symbol(trades: list[dict]) -> dict:
    """Performance by underlying symbol. Does edge transfer across symbols?"""
    groups = group_trades_by_key(trades, "symbol")
    return sort_report({label: summarize_group(g) for label, g in groups.items()})


def summarize_by_regime(trades: list[dict]) -> dict:
    """
    Nested performance breakdown by three regime dimensions.
    Returns dict with keys: iv_regime, gamma_regime, term_structure.
    """
    def _summarize_dim(key: str) -> dict:
        groups = group_trades_by_key(trades, key)
        return sort_report({label: summarize_group(g) for label, g in groups.items()})

    return {
        "iv_regime":     _summarize_dim("iv_regime"),
        "gamma_regime":  _summarize_dim("gamma_regime"),
        "term_structure": _summarize_dim("term_structure"),
    }
